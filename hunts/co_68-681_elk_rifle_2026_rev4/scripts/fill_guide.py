"""Fill the revision-4 guide template from the run's artifacts.

Placeholders: {{STATION_TABLE}} {{FORECAST_TABLE}} {{WEIGHTS}} {{TIMBER_TABLE}}
{{BED_TABLE}} {{WAYPOINT_INDEX}} {{FC_<date>}} {{EV_<code>}} {{PACK_<code>}}
{{TOUT_<code>}} (nearest legal road end + distance + climb), {{T_STATS}} values.

Usage (repo root): python3 fill_guide.py --data data --config <profile.yaml> --context work/guide_context.json
                   --template templates/guide_template.md --out data/out/guide.md
                   --extra REGS_TABLE=templates/regs_table.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

import geopandas as gpd  # noqa: E402

from elkscout.config import FACTOR_NAMES, load_config  # noqa: E402

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(deg: float) -> str:
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def r0(x: float) -> int:
    return int(float(x) + 0.5)  # half-up, not banker's


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--config", required=True)
    ap.add_argument("--context", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", action="append", default=[], help="PLACEHOLDER=path")
    a = ap.parse_args()
    w = Path(a.data) / "work"
    cfg = load_config(a.config)
    ctx = json.loads(Path(a.context).read_text())
    snow = json.loads((w / "snow.json").read_text())
    wx = json.loads((w / "weather.json").read_text())
    rev = json.loads((w / "imagery_review.json").read_text())
    wp = gpd.read_file(w / "waypoints.geojson")
    blocks = gpd.read_file(w / "timber_blocks.geojson")
    fills: dict[str, str] = {}

    rows = ["| station | elevation ft | snow depth in | SWE in |", "|---|---|---|---|"]
    for s in sorted(snow["stations"], key=lambda s: s["elevation_ft"]):
        rows.append(f"| {s['name']} | {round(s['elevation_ft']):,} | {s['snwd_in']} | {s['wteq_in']} |")
    fills["STATION_TABLE"] = "\n".join(rows)

    d = wx["points"][0]["daily"]
    rows = ["| date | high °F | low °F | precip in | snow in | max wind mph | wind from |", "|---|---|---|---|---|---|---|"]
    for i, day in enumerate(d["time"]):
        if str(cfg.hunt_window.start) <= day <= str(cfg.hunt_window.end):
            hi, lo, wind, deg = d["temperature_2m_max"][i], d["temperature_2m_min"][i], d["wind_speed_10m_max"][i], d["wind_direction_10m_dominant"][i]
            rows.append(f"| {dt.date.fromisoformat(day):%a %b %-d} | {r0(hi)} | {r0(lo)} | {d['precipitation_sum'][i]} | "
                        f"{d['snowfall_sum'][i]} | {r0(wind)} | {compass(deg)} ({r0(deg)}°) |")
            snow_txt = f", {d['snowfall_sum'][i]} in of snow" if d["snowfall_sum"][i] else (
                f", {d['precipitation_sum'][i]} in of precipitation" if d["precipitation_sum"][i] else ", dry")
            fills[f"FC_{day}"] = f"{r0(lo)}–{r0(hi)}°F, {compass(deg)} wind to {r0(wind)} mph{snow_txt}"
    fills["FORECAST_TABLE"] = "\n".join(rows)

    fills["WEIGHTS"] = "\n".join(f"| {f} | {getattr(cfg.factors, f).weight:.2f} |" for f in FACTOR_NAMES)

    rows = ["| block | acres | elevation ft | north-facing | from roads, median (max) | nearest road legal for your RZR | waypoints within 1 mi | photos | satellite / color-infrared |",
            "|---|---|---|---|---|---|---|---|---|"]
    live_ac = dead_ac = 0
    for _, b in blocks.sort_values("acres", ascending=False).iterrows():
        bid = b["id"]
        v = rev["blocks"].get(bid, {})
        verdict = v.get("verdict", "")
        dates = v.get("dates") or {}
        dead = "dead" in verdict.lower() and "live" not in verdict.lower().replace("dead", "")
        if dead:
            dead_ac += int(b["acres"])
        else:
            live_ac += int(b["acres"])
        c = ctx["blocks"][bid]
        rows.append(
            f"| {bid} | {int(b['acres']):,} | {int(b['elev_lo_ft']):,}–{int(b['elev_hi_ft']):,} | {round(b['north_share'] * 100)}% | "
            f"{b['road_mi_median']:.2f} mi ({b['road_mi_max']:.2f} mi) | {c['route'].replace('  ', ' ')}, {c['route_mi']} mi | "
            f"{', '.join(c['wps_1mi']) or '—'} | {'**' + verdict + '**' if dead else verdict} | "
            f"{dates.get('esri', '—')} / {dates.get('naip-cir', '—')} |")
    fills["TIMBER_TABLE"] = "\n".join(rows)
    fills["LIVE_AC"] = f"{live_ac:,}"
    fills["DEAD_AC"] = f"{dead_ac:,}"

    rows = ["| bed | block | what the photos show | satellite | color-infrared | nearest legal road end | packout with a partner |",
            "|---|---|---|---|---|---|---|"]
    for code in sorted(k for k in ctx["waypoints"] if k.startswith("B")):
        c = ctx["waypoints"][code]
        entry = next(v for v in rev["waypoints"].values() if v["name"].split()[0] == code)
        blk = re.search(r"security timber (T\d+)", wp.loc[wp["name"].str.startswith(code), "desc"].iloc[0])
        loads_mi = (round(2 * 2 * c["end_mi"]), round(3 * 2 * c["end_mi"]))
        rows.append(f"| {code} | {blk.group(1) if blk else '—'} | {entry['verdict']} | {entry['dates'].get('esri', '—')} | "
                    f"{entry['dates'].get('naip-cir', '—')} | {c['end'].replace(' road end', '')}, {c['end_mi']} mi, "
                    f"{abs(c['end_climb_ft']):,} ft {'down' if c['end_climb_ft'] >= 0 else 'up'} to the truck | "
                    f"2–3 loads each, {loads_mi[0]}–{loads_mi[1]} round-trip mi apiece |")
    fills["BED_TABLE"] = "\n".join(rows)

    for code, c in ctx["waypoints"].items():
        fills[f"TOUT_{code}"] = (f"{c['end_mi']} mi from the {c['end'].replace(' road end', '')} road end, "
                                 f"{abs(c['end_climb_ft']):,} ft {'above' if c['end_climb_ft'] >= 0 else 'below'} it")
        route = c["route"].replace("  ", " ")
        fills[f"ROUTE_{code}"] = f"{c['route_mi']} mi off {route}"
        lo, hi = round(2 * 2 * c["end_mi"]), round(3 * 2 * c["end_mi"])
        slo, shi = round(4 * 2 * c["end_mi"]), round(5 * 2 * c["end_mi"])
        shorter = (f" If you park along {route} instead, it's {c['route_mi']} mi to the nearest stretch of it."
                   if c["route_mi"] + 0.05 < c["end_mi"] else "")
        fills[f"PACK_{code}"] = (f"{c['end_mi']} mi and {abs(c['end_climb_ft']):,} ft "
                                 f"{'down' if c['end_climb_ft'] >= 0 else 'up'} to the {c['end'].replace(' road end', '')} road end: "
                                 f"2–3 loads each with your partner, about {lo}–{hi} round-trip miles apiece (solo it would be {slo}–{shi}).{shorter}")

    for _, p in wp.iterrows():
        fills[f"EV_{p['name'].split()[0]}"] = p["desc"]

    rows = ["| waypoint | type | area | lat | lon | elev ft | land | note |", "|---|---|---|---|---|---|---|---|"]
    for _, p in wp.sort_values(["area_rank", "wp_type", "name"]).iterrows():
        c = ctx["waypoints"][p["name"].split()[0]]
        rows.append(f"| {p['name']} | {p['wp_type']} | {int(p['area_rank'])} {p['hunt_area']} | {c['lat']:.5f} | {c['lon']:.5f} | "
                    f"{int(p['elevation_ft']):,} | {c['land']} | {p['desc']} |")
    fills["WAYPOINT_INDEX"] = "\n".join(rows)

    for kv in a.extra:
        k, v = kv.split("=", 1)
        fills[k] = Path(v).read_text().strip()

    t = Path(a.template).read_text()

    def sub(m: re.Match) -> str:
        k = m.group(1)
        if k not in fills:
            raise KeyError(f"no fill for {k}")
        return fills[k]

    out = re.sub(r"\{\{([A-Za-z0-9_\-]+)\}\}", sub, t)
    Path(a.out).write_text(out)
    print(f"wrote {a.out}: {len(out.splitlines())} lines; live {live_ac} ac, dead {dead_ac} ac")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
