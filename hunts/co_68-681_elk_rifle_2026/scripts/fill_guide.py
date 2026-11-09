"""Fill the guide template's data placeholders straight from the run's artifacts.

Usage (repo root): python3 fill_guide.py --data data --config <profile.yaml>
                   --template <guide_template.md> --out data/out/guide.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

import geopandas as gpd  # noqa: E402

from elkscout.config import FACTOR_NAMES, load_config  # noqa: E402
from elkscout.curves import shift_curve_x  # noqa: E402

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(deg: float) -> str:
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--config", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", action="append", default=[], help="PLACEHOLDER=path to a markdown snippet")
    ap.add_argument("--imagery-notes", default=None, help="JSON {code: note}; adds an imagery column to the index")
    a = ap.parse_args()
    img = json.loads(Path(a.imagery_notes).read_text()) if a.imagery_notes else None
    data = Path(a.data)
    cfg = load_config(a.config)
    snow = json.loads((data / "work" / "snow.json").read_text())
    wx = json.loads((data / "work" / "weather.json").read_text())
    wp = gpd.read_file(data / "work" / "waypoints.geojson")
    own = gpd.read_file(data / "manual" / "ownership.geojson")
    t = Path(a.template).read_text()

    curve = shift_curve_x(cfg.factors.elevation.curve_elevation_ft, float(snow["band_shift_ft"]))
    full = [x for x, y in curve if y >= 1.0]
    zero = [x for x, y in curve if y <= 0.0]
    fills = {
        "SNOW_ASOF": snow["as_of"],
        "SNOW_MEDIAN": f"{snow['median_snwd_in']:.1f}",
        "SNOW_N": str(len(snow["stations"])),
        "SNOW_SHIFT": f"{abs(round(snow['band_shift_ft'])):,}",
        "BAND_LO": f"{round(min(full)):,}", "BAND_HI": f"{round(max(full)):,}",
        "BAND_ZERO_LO": f"{round(min(zero)):,}", "BAND_ZERO_HI": f"{round(max(zero)):,}",
    }
    rows = ["| station | elevation ft | snow depth in | SWE in |", "|---|---|---|---|"]
    for s in sorted(snow["stations"], key=lambda s: s["elevation_ft"]):
        rows.append(f"| {s['name']} | {round(s['elevation_ft']):,} | {s['snwd_in']} | {s['wteq_in']} |")
    fills["SNOW_TABLE"] = "\n".join(rows)

    d = wx["points"][0]["daily"]
    start, end = str(cfg.hunt_window.start), str(cfg.hunt_window.end)
    rows = ["| date | hi °F | lo °F | precip in | snow in | max wind mph | dominant dir |", "|---|---|---|---|---|---|---|"]
    for i, day in enumerate(d["time"]):
        if start <= day <= end:
            rows.append(
                f"| {day} | {d['temperature_2m_max'][i]:.0f} | {d['temperature_2m_min'][i]:.0f} | "
                f"{d['precipitation_sum'][i]} | {d['snowfall_sum'][i]} | {d['wind_speed_10m_max'][i]:.0f} | "
                f"{compass(d['wind_direction_10m_dominant'][i])} ({d['wind_direction_10m_dominant'][i]:.0f}°) |"
            )
    fills["FORECAST_TABLE"] = "\n".join(rows)

    fills["WEIGHTS_ROWS"] = "\n".join(
        f"| {f} | {getattr(cfg.factors, f).weight:.2f} |" for f in FACTOR_NAMES
    )

    for _, r in wp.iterrows():
        code = r["name"].split()[0]
        fills[f"EV_{code}"] = r["desc"]

    j = gpd.sjoin(wp.to_crs(32613), own.to_crs(32613)[["agency", "cpw_property", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    rows = ["| waypoint | type | area | lat | lon | elev ft | land | evidence |" + (" imagery |" if img else ""),
            "|---|---|---|---|---|---|---|---|" + ("---|" if img else "")]
    for _, r in j.sort_values(["area_rank", "wp_type", "name"]).iterrows():
        ev = r["evidence_json"] if isinstance(r["evidence_json"], dict) else json.loads(r["evidence_json"])
        land = r["cpw_property"] if isinstance(r["cpw_property"], str) else r["agency"]
        rows.append(
            f"| {r['name']} | {r['wp_type']} | {r['area_rank']} {r['hunt_area']} | {ev['lat']:.5f} | {ev['lon']:.5f} | "
            f"{int(r['elevation_ft']):,} | {land} | {r['desc']} |" + (f" {img[r['name'].split()[0]]} |" if img else "")
        )
    fills["WAYPOINT_INDEX"] = "\n".join(rows)

    for kv in a.extra:
        k, v = kv.split("=", 1)
        fills[k] = Path(v).read_text().strip()

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in fills:
            raise KeyError(f"no fill for placeholder {key}")
        return fills[key]

    out = re.sub(r"\{\{([A-Z0-9_\-]+)\}\}", sub, t)
    Path(a.out).write_text(out)
    print(f"wrote {a.out} ({len(out.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
