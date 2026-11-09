"""Written hunt briefing -> data/out/briefing.md.

Everything derives from artifacts on disk (waypoints, hunt areas, snow.json,
weather.json) plus the config — no network. Structure: conditions summary,
how-to-read-the-model, wind/thermal doctrine, then a section per hunt area
with access, camp, morning/evening plans, and the waypoint evidence table.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..config import Config
from ..paths import Workspace

log = logging.getLogger("elkscout.briefing")

_TYPE_LEGEND = {
    "BED": "bedding (dark timber benches, cool aspects)",
    "FEED": "feed (meadows, burns, edges)",
    "WATER": "water (creeks, springs)",
    "SADDLE": "travel saddle (ambush on movement)",
    "GLASS": "glassing vantage",
    "CAMP": "backpack camp candidate",
    "ACCESS": "trailhead / access",
}

_THERMALS = """\
Wind rules this game. Prevailing flow here is southwest ahead of every front, but
what kills you day-to-day is thermals: cold air pours DOWNHILL from last light
until roughly two hours after sun first hits the slope, then it lifts and pulls
UPHILL through midday, and rolls back downhill at dusk. So in the morning come in
from above — drop onto bedded elk with the rising thermal in your face — and in
the evening work from below. Never still-hunt a north-slope bench at midday from
the bottom; your scent is riding the elevator straight to their beds. The day
behind a cold front, with fresh snow and a hard barometer, is the day you burn a
vacation day. If the wind is wrong for an area, hunt a different area — that is
what the per-area GPX files are for."""


def _fmt_forecast(weather: dict) -> list[str]:
    lines: list[str] = []
    if weather.get("mode") == "forecast":
        pt = (weather.get("points") or [{}])[0]
        daily = pt.get("daily") or {}
        times = daily.get("time") or []
        if times:
            lines.append("| date | hi F | lo F | precip in | snow in | wind mph | dir |")
            lines.append("|---|---|---|---|---|---|---|")
            for i, day in enumerate(times):
                def _g(key):
                    vals = daily.get(key) or []
                    return vals[i] if i < len(vals) else ""
                lines.append(
                    f"| {day} | {_g('temperature_2m_max')} | {_g('temperature_2m_min')} "
                    f"| {_g('precipitation_sum')} | {_g('snowfall_sum')} "
                    f"| {_g('wind_speed_10m_max')} | {_g('wind_direction_10m_dominant')} |"
                )
        covered = weather.get("window_days_covered")
        if covered is not None:
            lines.append("")
            lines.append(f"_Forecast covers {covered} day(s) of the hunt window._")
    else:
        lines.append(weather.get("note", "No weather data."))
    return lines


def _snow_summary(snow: dict) -> str:
    if snow.get("no_data"):
        return (
            "No SNOTEL data was available at run time - the model assumed ZERO snow, "
            "so the elevation band is un-shifted. Re-run before the hunt."
        )
    stations = ", ".join(
        f"{s.get('name', s.get('triplet', '?'))} ({s.get('snwd_in', '?')}\" SNWD)"
        for s in snow.get("stations", [])
        if s.get("snwd_in") is not None
    )
    return (
        f"Median snow depth {snow.get('median_snwd_in', 0):.1f}\" as of {snow.get('as_of', '?')} "
        f"({stations or 'no reporting stations'}); the elevation optimum is shifted "
        f"{snow.get('band_shift_ft', 0):+.0f} ft accordingly."
    )


def _timber_section(ws: Workspace) -> list[str]:
    from ..timber import load_blocks

    blocks = load_blocks(ws)
    if len(blocks) == 0:
        return []
    stats = json.loads(ws.timber_json.read_text()) if ws.timber_json.exists() else {}
    L = ["## Security timber", ""]
    L.append(
        f"Dark conifer here means NLCD evergreen/mixed forest at {stats.get('dark_canopy_pct', '?')}%+ canopy"
        + (" (auto: the local conifer 75th percentile)" if stats.get("dark_canopy_auto") else "")
        + f". A security block is {stats.get('min_acres', 100):.0f}+ contiguous public acres at least "
        f"{stats.get('min_road_mi', 0.5)} mi from any motorized route — where pressured bulls go. "
        f"{len(blocks)} block(s), {stats.get('block_acres_total', 0):,} ac total."
    )
    if stats.get("dead_conifer_acres_removed"):
        L.append("")
        L.append(f"Sentinel-2 change detection removed {stats['dead_conifer_acres_removed']:,} ac of conifer that has "
                 "lost its greenness (likely beetle kill, fire, or logging) before the blocks were drawn.")
    L += ["", "| block | acres | elevation ft | north-facing | from roads, median (max) | imagery |", "|---|---|---|---|---|---|"]
    for _, b in blocks.sort_values("acres", ascending=False).head(15).iterrows():
        L.append(
            f"| {b['id']} | {int(b['acres']):,} | {b['elev_lo_ft']:,}-{b['elev_hi_ft']:,} | "
            f"{int(round(b['north_share'] * 100))}% | {b['road_mi_median']} mi ({b['road_mi_max']} mi) | "
            f"{b.get('imagery') or 'not yet checked'} |"
        )
    L += ["", "Import `elkscout_unit*_timber_blocks.kml` into OnX to see the outlines.", ""]
    return L


def write_briefing(ws: Workspace, cfg: Config) -> Path:
    from ..waypoints import load_waypoints

    wp, areas = load_waypoints(ws)
    snow = json.loads(ws.snow_json.read_text()) if ws.snow_json.exists() else {"no_data": True}
    weather = json.loads(ws.weather_json.read_text()) if ws.weather_json.exists() else {"mode": "none"}

    L: list[str] = []
    L.append(f"# Unit {cfg.unit} Elk Hunt Briefing - {cfg.profile}")
    L.append("")
    L.append(f"Hunt window **{cfg.hunt_window.start} to {cfg.hunt_window.end}** - "
             f"{len(wp)} waypoints across {len(areas)} hunt areas.")
    L.append("")
    L.append("## Conditions")
    L.append("")
    L.append(f"**Snow:** {_snow_summary(snow)}")
    L.append("")
    L.append("**Weather:**")
    L.append("")
    L.extend(_fmt_forecast(weather))
    L.append("")
    L.append("## How to read this")
    L.append("")
    L.append(
        "Every waypoint is a cell that won a weighted habitat model on a 30 m grid, "
        "not a guess. Factor weights in this profile:"
    )
    L.append("")
    L.append("| factor | weight |")
    L.append("|---|---|")
    for name, w in cfg.factors.weights().items():
        L.append(f"| {name} | {w:.2f} |")
    L.append("")
    L.append("Waypoint types: " + "; ".join(f"**{k}** = {v}" for k, v in _TYPE_LEGEND.items()) + ".")
    L.append("")
    L.append("## Wind and thermals")
    L.append("")
    L.append(_THERMALS)
    L.append("")
    L.extend(_timber_section(ws))

    for _, area in areas.sort_values("rank").iterrows():
        sub = wp[wp["area_slug"] == area["slug"]]
        L.append(f"## Area {area['rank']}: {area['name']}")
        L.append("")
        timber_ac = area.get("timber_acres")
        timber_txt = f", {int(timber_ac):,} ac of security timber within reach" if timber_ac else ""
        L.append(f"{area['n_waypoints']} waypoints, mean score {area['mean_score']}{timber_txt}.")
        L.append("")
        access = sub[sub["wp_type"] == "ACCESS"]
        camps = sub[sub["wp_type"] == "CAMP"]
        glass = sub[sub["wp_type"] == "GLASS"]
        feeds = sub[sub["wp_type"] == "FEED"]
        beds = sub[sub["wp_type"] == "BED"]
        saddles = sub[sub["wp_type"] == "SADDLE"]
        waters = sub[sub["wp_type"] == "WATER"]

        if len(access):
            L.append(f"**Access:** start from {', '.join(access['name'])}.")
        else:
            L.append("**Access:** no mapped trailhead in this area - come in from the nearest "
                     "motorized route on the map and log your own parking waypoint.")
        if len(camps):
            L.append(f"**Camp:** {', '.join(camps['name'])} - flat, watered, and deep enough "
                     "to be inside the elk instead of commuting to them.")
        L.append("")
        morning = (
            f"**Morning:** be on {glass['name'].iloc[0] if len(glass) else 'the highest knob you can reach in the dark'} "
            "at gray light and take the first hour apart with glass"
        )
        if len(feeds):
            morning += f" - work the feed at {', '.join(feeds['name'].head(3))}"
        if len(beds):
            morning += (
                f". As thermals switch, move ABOVE the bedding benches ({', '.join(beds['name'].head(3))}) "
                "and still-hunt down into the wind"
            )
        L.append(morning + ".")
        evening = "**Evening:** post the last two hours where elk stage before dark"
        if len(feeds) or len(waters) or len(saddles):
            spots = list(feeds["name"].head(2)) + list(waters["name"].head(1)) + list(saddles["name"].head(2))
            evening += f" - {', '.join(spots)}"
        L.append(evening + ".")
        L.append("")
        L.append("| waypoint | type | elev ft | score | why |")
        L.append("|---|---|---|---|---|")
        for _, row in sub.sort_values(["wp_type", "score"], ascending=[True, False]).iterrows():
            L.append(f"| {row['name']} | {row['wp_type']} | {row['elevation_ft']:,} | {row['score']} | {row['desc']} |")
        L.append("")

    L.append("---")
    L.append("")
    L.append(
        "_Data: USGS 3DEP terrain; NHD hydrography; NLCD landcover/canopy; MTBS burn "
        "perimeters; BLM Surface Management Agency ownership; OSM + USFS MVUM routes; "
        "NRCS SNOTEL; Open-Meteo. The ownership layer defaults unmapped slivers to "
        "public - verify parcels on the ground. Verify current season dates, unit rules, "
        "and tag validity with the state wildlife agency before hunting. This is a scouting aid, not a "
        "substitute for boots, glass, and judgment._"
    )
    out = ws.briefing_md
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    log.info("briefing: wrote %s (%d lines)", out, len(L))
    return out
