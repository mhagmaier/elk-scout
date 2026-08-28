"""Hydrography: perennial streams, waterbodies, HUC12 watersheds.

Contract — fetch_water(net, ws, bbox4326) writes three EPSG:4326 artifacts
(manual keys: water_lines / water_bodies / huc12):

- ws.water_lines_geojson: NHDPlus HR flowlines, PERENNIAL ONLY (FCode 46006);
  discover the flowline layer id from endpoints.NHDPLUS_HR ?f=json by name
  containing 'flowline' (small-scale variants excluded — prefer the plain one).
  Keep GNIS_NAME if present. Use max_allowable_offset≈10 (meters in 4326? no —
  offset is in outSR units, so ~0.0001 deg) to tame vertex counts.
- ws.water_bodies_geojson: NHD waterbody polygons (layer name containing
  'waterbody'), FCode lake/pond/reservoir families (390xx, 436xx); keep GNIS_NAME.
- ws.huc12_geojson: WBD HUC12 polygons from endpoints.WBD (layer name containing
  '12'); keep fields name + huc12 (field names vary: NAME/name, HUC12/huc12).

Empty results allowed. Offline miss -> OfflineMissError(key, ws).
"""

from __future__ import annotations

from ..net import Net
from ..paths import Workspace


def fetch_water(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float]) -> None:
    raise NotImplementedError
