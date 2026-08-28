"""Export ElkScout waypoints to an Excel workbook.

Usage: python scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx
Reads work/waypoints.geojson + work/hunt_areas.geojson from the workspace and
writes three sheets: Waypoints (one row per point, with evidence columns and a
Google Maps link), Hunt Areas (formula-driven per-area summary), and About
(provenance + how to regenerate).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F4D2E")  # dark timber green
HEADER_FONT = Font(name=FONT, bold=True, color="FFFFFF")
BODY_FONT = Font(name=FONT, size=10)
WARN_FONT = Font(name=FONT, size=11, bold=True, color="B00000")

WP_COLUMNS = [
    ("Waypoint", 22),
    ("Type", 9),
    ("Hunt area", 12),
    ("Area rank", 9),
    ("Latitude", 11),
    ("Longitude", 12),
    ("Elevation (ft)", 12),
    ("Score", 8),
    ("Aspect", 8),
    ("Slope (%)", 9),
    ("Canopy (%)", 10),
    ("Motorized dist (mi)", 16),
    ("Water dist (mi)", 13),
    ("Burn", 20),
    ("Map link", 12),
    ("Why this point", 90),
]
WP_TYPES = ["BED", "FEED", "WATER", "SADDLE", "GLASS", "CAMP", "ACCESS"]


def _evidence(row) -> dict:
    raw = row.get("evidence_json")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}


def _style_header(ws, n_cols: int) -> None:
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"


def export_xlsx(data_dir: Path, out_path: Path, demo_note: str | None = None) -> Path:
    work = data_dir / "work"
    wp = gpd.read_file(work / "waypoints.geojson")
    areas = gpd.read_file(work / "hunt_areas.geojson")
    wp = wp.sort_values(["area_rank", "wp_type", "score"], ascending=[True, True, False]).reset_index(drop=True)

    wb = Workbook()

    # -- Waypoints -----------------------------------------------------------
    ws = wb.active
    ws.title = "Waypoints"
    for c, (title, width) in enumerate(WP_COLUMNS, start=1):
        ws.cell(row=1, column=c, value=title)
        ws.column_dimensions[get_column_letter(c)].width = width
    _style_header(ws, len(WP_COLUMNS))

    for i, row in wp.iterrows():
        ev = _evidence(row)
        r = i + 2
        burn = f"{ev.get('burn_year')} {ev.get('burn_name')}" if ev.get("burn_year") else ""
        lat, lon = round(float(row.geometry.y), 6), round(float(row.geometry.x), 6)
        values = [
            row["name"], row["wp_type"], row["hunt_area"], int(row["area_rank"]),
            lat, lon, int(row["elevation_ft"]), float(row["score"]),
            ev.get("aspect_compass") or "", ev.get("slope_pct"), ev.get("canopy_pct"),
            ev.get("dist_motorized_mi"), ev.get("dist_water_mi"), burn,
            f'=HYPERLINK("https://maps.google.com/?q={lat},{lon}","open map")',
            row["desc"],
        ]
        for c, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = BODY_FONT
        ws.cell(row=r, column=5).number_format = "0.000000"
        ws.cell(row=r, column=6).number_format = "0.000000"
        ws.cell(row=r, column=7).number_format = "#,##0"
        ws.cell(row=r, column=8).number_format = "0.000"
        ws.cell(row=r, column=16).alignment = Alignment(wrap_text=True)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(WP_COLUMNS))}{len(wp) + 1}"

    # -- Hunt Areas (formula-driven off the Waypoints sheet) -----------------
    wa = wb.create_sheet("Hunt Areas")
    headers = ["Hunt area", "Rank", "Waypoints", "Mean score", *WP_TYPES]
    for c, title in enumerate(headers, start=1):
        wa.cell(row=1, column=c, value=title)
        wa.column_dimensions[get_column_letter(c)].width = 12 if c > 1 else 16
    _style_header(wa, len(headers))
    # Bounded ranges, not $C:$C — LibreOffice recalc is pathologically slow on
    # full-column COUNTIFS.
    last = len(wp) + 1
    col_area = f"Waypoints!$C$2:$C${last}"
    col_type = f"Waypoints!$B$2:$B${last}"
    col_score = f"Waypoints!$H$2:$H${last}"
    for i, (_, area) in enumerate(areas.sort_values("rank").iterrows()):
        r = i + 2
        wa.cell(row=r, column=1, value=area["name"]).font = BODY_FONT
        wa.cell(row=r, column=2, value=int(area["rank"])).font = BODY_FONT
        wa.cell(row=r, column=3, value=f"=COUNTIFS({col_area},$A{r})").font = BODY_FONT
        mean = wa.cell(row=r, column=4, value=f"=AVERAGEIFS({col_score},{col_area},$A{r})")
        mean.font = BODY_FONT
        mean.number_format = "0.000"
        for j, t in enumerate(WP_TYPES):
            c = 5 + j
            wa.cell(
                row=r, column=c,
                value=f'=COUNTIFS({col_area},$A{r},{col_type},"{t}")',
            ).font = BODY_FONT

    # -- About ---------------------------------------------------------------
    ab = wb.create_sheet("About")
    ab.column_dimensions["A"].width = 110
    lines = [
        ("ElkScout waypoint export", Font(name=FONT, size=14, bold=True)),
        ("", None),
    ]
    if demo_note:
        lines.append((demo_note, WARN_FONT))
        lines.append(("", None))
    lines += [
        ("Each row on the Waypoints sheet is a scored habitat cell from the ElkScout model: "
         "a weighted 30 m-grid composite of security (distance from motorized routes), bedding "
         "(aspect/canopy/slope benches), feed (meadows, burns, edges), elevation (snow-shifted), "
         "water, and hunting-pressure factors.", None),
        ("Type legend: BED bedding, FEED feed, WATER water, SADDLE travel saddle, GLASS glassing "
         "vantage, CAMP backpack camp, ACCESS trailhead.", None),
        ("The Hunt Areas sheet is formula-driven (COUNTIFS/AVERAGEIFS over the Waypoints sheet).", None),
        ("", None),
        ("Regenerate with real data on a networked machine:", Font(name=FONT, bold=True)),
        ("  1. elkscout run --config configs/unit33_oct_rifle.yaml", None),
        ("  2. python scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx", None),
        ("", None),
        ("Data sources: USGS 3DEP, NHD, NLCD, MTBS, BLM SMA, OSM/USFS MVUM, NRCS SNOTEL, Open-Meteo. "
         "Verify land status and current IDFG regulations before hunting.", None),
    ]
    for i, (text, font) in enumerate(lines, start=1):
        cell = ab.cell(row=i, column=1, value=text)
        cell.font = font or BODY_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data", help="workspace root (default: ./data)")
    ap.add_argument("--out", default=None, help="output .xlsx (default: <data>/out/waypoints.xlsx)")
    ap.add_argument("--demo-note", default=None, help="warning line for the About sheet")
    args = ap.parse_args()
    data = Path(args.data)
    out = Path(args.out) if args.out else data / "out" / "waypoints.xlsx"
    path = export_xlsx(data, out, demo_note=args.demo_note)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
