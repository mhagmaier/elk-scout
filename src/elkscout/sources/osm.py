"""OpenStreetMap via Overpass: motorized ways, trails, trailheads, springs.

Contract — fetch_osm(net, ws, bbox4326) writes four EPSG:4326 GeoJSON artifacts
(each falls back to its manual drop-in first: osm_motorized / osm_trails /
osm_trailheads / osm_springs):

- ws.motorized_geojson  (LineStrings): ways with highway in (motorway, trunk,
  primary, secondary, tertiary, unclassified, residential, service, track)
  EXCLUDING those tagged motor_vehicle in (no, private) or access in (no, private).
  NOTE: factors.py later unions this with MVUM roads; write OSM-only here.
- ws.trails_geojson (LineStrings): highway in (path, footway, bridleway, cycleway)
  plus track with motor_vehicle=no.
- ws.trailheads_geojson (Points): highway=trailhead nodes, plus amenity=parking
  nodes/way-centroids within ~150 m of any trail line.
- ws.springs_geojson (Points): natural=spring nodes.

Implementation notes:
- One Overpass QL POST per theme (data=<query>), [out:json][timeout:180],
  bbox filter (south,west,north,east). Rotate endpoints.OVERPASS on failure.
- Convert Overpass JSON (use `out geom;` so ways carry geometry) to shapely
  LineString/Point; skip degenerate geometries. Keep tags: name, highway, ref.
- Empty results are fine — write an empty FeatureCollection (factors handles it).
- Offline with no cache/manual -> raise paths.OfflineMissError(key, ws).
"""

from __future__ import annotations

from ..net import Net
from ..paths import Workspace


def fetch_osm(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float]) -> None:
    raise NotImplementedError
