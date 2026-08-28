"""USFS Motor Vehicle Use Map roads -> work/mvum_roads.geojson (EPSG:4326 lines).

Contract — fetch_mvum(net, ws, bbox4326):
1. ws.manual_path("mvum_roads") if present.
2. Query endpoints.MVUM service ?f=json to list layers; pick every layer whose
   name matches (case-insensitive) 'road' or 'trail' AND whose geometryType is
   esriGeometryPolyline; arcgis.query_layer_geojson each with the bbox; concat.
   Keep columns that exist among: NAME, ID, SBS_SYMBOL_NAME, SEASONAL.
3. Write ws.mvum_geojson artifact — note: the Workspace exposes this as
   part of the motorized union consumed by factors; write to
   ws.work / "mvum_roads.geojson".
Empty result -> empty FeatureCollection (OSM covers most routes anyway).
Offline miss -> paths.OfflineMissError("mvum_roads", ws).
"""

from __future__ import annotations

from pathlib import Path

from ..net import Net
from ..paths import Workspace


def mvum_roads_path(ws: Workspace) -> Path:
    return ws.work / "mvum_roads.geojson"


def fetch_mvum(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float]) -> None:
    raise NotImplementedError
