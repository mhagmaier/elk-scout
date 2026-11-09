"""USFS Motor Vehicle Use Map routes -> work/mvum_roads.geojson (EPSG:4326 lines).

Contract — fetch_mvum(net, ws, bbox4326):
1. ws.manual_path("mvum_roads") if present.
2. endpoints.MVUM ?f=json to list layers; query every polyline layer whose name
   contains 'road' or 'trail' (case-insensitive) with the bbox; concatenate.
   Kept columns (where present): NAME, ID, SBS_SYMBOL_NAME, SEASONAL plus every
   vehicle-class allowance + dates-open field (see config.VEHICLE_FIELDS).
Empty result -> empty FeatureCollection (OSM covers most routes anyway).
Offline miss -> OfflineMissError("mvum_roads", ws).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .. import endpoints
from ..config import VEHICLE_FIELDS
from ..net import Net, OfflineError
from ..paths import OfflineMissError, Workspace
from .arcgis import layer_info, query_layer_geojson

log = logging.getLogger("elkscout.mvum")

SOURCE = "mvum_roads"
# Route identity + every vehicle-class allowance/dates field, so access.py can
# decide which routes the hunter's own vehicle may drive on the hunt dates.
_KEPT = ("NAME", "ID", "SBS_SYMBOL_NAME", "SEASONAL", "MVUM_SYMBOL_NAME") + tuple(
    f.upper() for pair in VEHICLE_FIELDS.values() for f in pair
)


def mvum_roads_path(ws: Workspace) -> Path:
    return ws.work / "mvum_roads.geojson"


def fetch_mvum(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float]) -> None:
    manual = ws.manual_path(SOURCE)
    if manual.exists():
        log.info("mvum: using manual drop-in %s", manual)
        gdf = gpd.read_file(manual)
        gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")
    else:
        try:
            gdf = _query_all_route_layers(net, bbox4326)
        except OfflineError as e:
            raise OfflineMissError(SOURCE, ws) from e
    _write(ws, gdf)
    log.info("mvum: %d route(s) -> %s", len(gdf), mvum_roads_path(ws))


def _query_all_route_layers(net: Net, bbox4326: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    info = net.fetch_json(endpoints.MVUM, {"f": "json"}, source=SOURCE)
    parts: list[gpd.GeoDataFrame] = []
    for layer in info.get("layers") or []:
        name = str(layer.get("name", "")).lower()
        if "road" not in name and "trail" not in name:
            continue
        meta = layer_info(net, endpoints.MVUM, int(layer["id"]), SOURCE)
        if meta.get("geometryType") != "esriGeometryPolyline":
            continue
        gdf = query_layer_geojson(
            net, endpoints.MVUM, int(layer["id"]), source=SOURCE, bbox4326=bbox4326
        )
        if len(gdf):
            keep = [c for c in gdf.columns if c.upper() in _KEPT or c == gdf.geometry.name]
            parts.append(gdf[keep])
            log.info("mvum: layer %s (%r): %d routes", layer["id"], layer.get("name"), len(gdf))
    if not parts:
        return gpd.GeoDataFrame(geometry=gpd.GeoSeries([], dtype="geometry"), crs="EPSG:4326")
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs="EPSG:4326")


def _write(ws: Workspace, gdf: gpd.GeoDataFrame) -> None:
    path = mvum_roads_path(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    if len(gdf) == 0:
        path.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
        return
    gdf.to_file(path, driver="GeoJSON")
