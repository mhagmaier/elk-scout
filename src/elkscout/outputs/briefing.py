"""Written hunt briefing -> data/out/briefing.md.

Contract — write_briefing(ws, cfg) -> Path. Markdown structure:

# Unit <unit> Elk Hunt Briefing — <profile>
- Generated-from data summary: hunt window, snow state (from ws.snow_json:
  median SNWD, station list, elevation-shift applied; note if no_data),
  weather (from ws.weather_json: per-day table if mode=forecast, else the
  climatology note verbatim).
- "How to read this": one paragraph on the model (factors + weights from cfg,
  rendered as a small table) and the waypoint type legend.
- Wind & thermals doctrine (static text, central Idaho October): prevailing SW
  winds ahead of fronts; downslope (katabatic) thermals until mid-morning,
  upslope (anabatic) from ~2h after sun hits the slope, back downslope at
  dusk; hunt uphill of elk in the morning... (write it like a seasoned elk
  hunter's brief, ~8 sentences).
- ## Per hunt area (by rank): name, n waypoints, mean score, then:
  - Access: nearest ACCESS/trailhead waypoint if any + dist from area centroid.
  - Camp: the CAMP waypoint(s) in the area.
  - Morning plan: reference its GLASS points (glass at first light over the
    FEED points), then still-hunt toward BED benches as thermals switch.
  - Evening plan: feed edges and WATER/SADDLE ambushes.
  - Waypoint table: | name | type | elev ft | score | why |  (why = desc).
- Footer: data provenance one-liner per source + "verify current IDFG season
  rules and land status before hunting" disclaimer.

All content derives from artifacts on disk (waypoints/hunt_areas/snow/weather
jsons + cfg); no network. Returns ws.briefing_md.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..paths import Workspace


def write_briefing(ws: Workspace, cfg: Config) -> Path:
    raise NotImplementedError
