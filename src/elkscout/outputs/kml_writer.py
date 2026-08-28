"""KML output for Google Earth — hand-rolled with xml.etree (no simplekml dep).

Contract — write_kml(ws, cfg) -> Path:
- Read ws.waypoints_geojson and ws.hunt_areas_geojson.
- Document structure: <Document><name>ElkScout Unit 33</name>
  shared <Style> per waypoint type (id "style-BED" etc.) using standard Google
  pin/paddle icon URLs (http://maps.google.com/mapfiles/kml/...) with distinct
  colors: BED blue, FEED green, WATER light blue, SADDLE red, GLASS yellow,
  CAMP purple, ACCESS white.
  One <Folder> per hunt area (by rank), Placemarks inside:
  <name>, <description> (evidence sentence, HTML-escaped, plus score),
  <styleUrl>, <Point><coordinates>lon,lat,0</coordinates>.
  A final Folder "Hunt areas" with polygon outlines (no fill, 2px line).
- Write ws.kml(cfg.unit) with xml.etree.ElementTree, kml namespace
  "http://www.opengis.net/kml/2.2", pretty-ish (indent via ET.indent).
- Validate: re-parse with ET.parse; count Placemarks == waypoints + areas.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..paths import Workspace


def write_kml(ws: Workspace, cfg: Config) -> Path:
    raise NotImplementedError
