"""Unit boundary: IDFG GMU polygon -> work/boundary.geojson (EPSG:4326).

Contract:
- fetch_boundary(net, ws, cfg): resolution order
    1. ws.manual_path("boundary") if it exists (any GeoJSON polygon; reprojected/assumed 4326)
    2. IDFG ArcGIS layer (endpoints.IDFG_HUNTING layer IDFG_GMU_LAYER, alt host fallback):
       discover the unit-name field from layer_info() fields — try, in order,
       case-insensitive names containing: NAME, UNIT, GMU. Query where <field>='<cfg.unit>'.
  Dissolve all returned features to a single (multi)polygon, keep a `unit` column,
  write ws.boundary_geojson, return the GeoDataFrame (EPSG:4326).
  Raise RuntimeError with a helpful message if the query returns no features.
- load_boundary(ws): read ws.boundary_geojson -> GeoDataFrame (EPSG:4326).
- synth_boundary_from_bbox(ws, bbox4326): build a rectangle boundary from
  (minlon, minlat, maxlon, maxlat), write the same artifact, return it. Used by
  --aoi-bbox test/smoke mode and never touches the network.
"""

from __future__ import annotations

import geopandas as gpd

from ..config import Config
from ..net import Net
from ..paths import Workspace


def fetch_boundary(net: Net, ws: Workspace, cfg: Config) -> gpd.GeoDataFrame:
    raise NotImplementedError


def load_boundary(ws: Workspace) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(ws.boundary_geojson)
    return gdf.set_crs("EPSG:4326", allow_override=True)


def synth_boundary_from_bbox(ws: Workspace, bbox4326: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    raise NotImplementedError
