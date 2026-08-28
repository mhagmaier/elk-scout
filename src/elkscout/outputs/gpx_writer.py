"""GPX output (the OnX deliverable).

Contract — write_gpx_files(ws, cfg) -> list[Path]:
- Read ws.waypoints_geojson. Write with gpxpy:
  1. ws.gpx_all(cfg.unit): every waypoint.
  2. ws.gpx_area(cfg.unit, slug) for each distinct area_slug.
- Per waypoint: gpxpy GPXWaypoint(latitude, longitude,
  elevation=elevation_ft/3.28084 [GPX elevation is meters], name=name,
  description=desc, symbol=SYMBOLS[wp_type], comment=None).
- SYMBOLS (Garmin-standard names OnX tolerates):
  BED "Flag, Blue"; FEED "Flag, Green"; WATER "Drinking Water";
  SADDLE "Flag, Red"; GLASS "Binoculars"; CAMP "Campground";
  ACCESS "Parking Area".
- GPX metadata: name "ElkScout Unit <unit>", description with profile name and
  generation provenance, time left None (deterministic output).
- Hard asserts after writing EACH file: waypoint count <= cfg.outputs
  .gpx_max_waypoints, file size <= cfg.outputs.gpx_max_bytes, file re-parses
  with gpxpy and yields the same count, every name ASCII and <= 32 chars,
  every desc <= cfg.outputs.desc_max_chars. Raise on violation.
Returns paths written (all-file first).
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..paths import Workspace

SYMBOLS = {
    "BED": "Flag, Blue",
    "FEED": "Flag, Green",
    "WATER": "Drinking Water",
    "SADDLE": "Flag, Red",
    "GLASS": "Binoculars",
    "CAMP": "Campground",
    "ACCESS": "Parking Area",
}


def write_gpx_files(ws: Workspace, cfg: Config) -> list[Path]:
    raise NotImplementedError
