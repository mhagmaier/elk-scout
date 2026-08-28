"""Land ownership (public vs private) -> work/ownership.geojson (EPSG:4326).

Contract — fetch_ownership(net, ws, bbox4326):
1. ws.manual_path("ownership") if present.
2. endpoints.BLM_SMA: pick the polygon layer discovered from ?f=json — prefer
   layers whose name contains 'Surface Management Agency', confirmed polygonal
   via layer metadata (discovered, not hardcoded). Query bbox, out_fields '*',
   max_allowable_offset 0.0003 deg (SMA polygons are huge).
3. Normalize: add a string column `agency` from the first existing field among
   ADMIN_AGENCY_CODE / ADMIN_UNIT_NAME / ADMIN_DEPT_CODE / MGMT_AGNCY / SMA
   (fall back to 'UNKNOWN'), and a boolean column `public` — True unless agency
   text (uppercased) contains 'PRIVATE' or equals 'PVT'.
4. Write ws.ownership_geojson.

Cells with no ownership polygon at all score as public=True downstream
(federal land dominates unit 33 and SMA has slivers of no-data); the README
documents this default and hunters must verify parcels.
Offline miss -> OfflineMissError("ownership", ws).
"""

from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

from .. import endpoints
from ..net import Net, OfflineError
from ..paths import OfflineMissError, Workspace
from .arcgis import layer_info, query_layer_geojson

log = logging.getLogger("elkscout.ownership")

SOURCE = "ownership"

_OFFSET_DEG = 0.0003
_LAYER_TOKEN = "surface management agency"
# Agency-field discovery priority; a pre-normalized `agency` column wins so
# manual drop-ins round-trip unchanged.
_AGENCY_FIELDS = ("agency", "ADMIN_AGENCY_CODE", "ADMIN_UNIT_NAME", "ADMIN_DEPT_CODE", "MGMT_AGNCY", "SMA")


def fetch_ownership(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float]) -> None:
    manual = ws.manual_path(SOURCE)
    if manual.exists():
        log.info("ownership: using manual drop-in %s", manual)
        gdf = gpd.read_file(manual)
        gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")
    else:
        try:
            layer_id = _discover_polygon_layer(net)
            gdf = query_layer_geojson(
                net,
                endpoints.BLM_SMA,
                layer_id,
                source=SOURCE,
                bbox4326=bbox4326,
                out_fields="*",
                max_allowable_offset=_OFFSET_DEG,
            )
        except OfflineError as e:
            raise OfflineMissError(SOURCE, ws) from e
    gdf = _normalize(gdf)
    _write(ws, gdf)
    n_private = int((~gdf["public"]).sum()) if len(gdf) else 0
    log.info("ownership: %d polygons (%d private) -> %s", len(gdf), n_private, ws.ownership_geojson)


# -- internals ---------------------------------------------------------------

def _discover_polygon_layer(net: Net) -> int:
    info = net.fetch_json(endpoints.BLM_SMA, {"f": "json"}, source=SOURCE)
    layers = info.get("layers") or []
    named = [l for l in layers if _LAYER_TOKEN in str(l.get("name", "")).lower()]
    for layer in named or layers:
        meta = layer_info(net, endpoints.BLM_SMA, int(layer["id"]), SOURCE)
        if meta.get("geometryType") == "esriGeometryPolygon":
            log.info("ownership: using layer %s (%r)", layer["id"], layer.get("name"))
            return int(layer["id"])
    raise RuntimeError(
        f"no polygon layer found on {endpoints.BLM_SMA} "
        f"(layers: {[l.get('name') for l in layers]})"
    )


def _normalize(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if len(gdf) == 0:
        return gdf
    lower = {c.lower(): c for c in gdf.columns if c != gdf.geometry.name}
    agency_col = next((lower[f.lower()] for f in _AGENCY_FIELDS if f.lower() in lower), None)
    if agency_col is None:
        log.warning("ownership: no agency field among columns %s; using 'UNKNOWN'", list(gdf.columns))
        agency = pd.Series(["UNKNOWN"] * len(gdf), index=gdf.index)
    else:
        agency = gdf[agency_col].map(lambda v: "UNKNOWN" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v))
    gdf = gdf.copy()
    gdf["agency"] = agency
    if "public" in lower:
        gdf["public"] = gdf[lower["public"]].astype(bool)
    else:
        upper = agency.str.upper()
        gdf["public"] = ~(upper.str.contains("PRIVATE", regex=False) | (upper == "PVT"))
    return gdf


def _write(ws: Workspace, gdf: gpd.GeoDataFrame) -> None:
    path = ws.ownership_geojson
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    if len(gdf) == 0:
        path.write_text('{"type": "FeatureCollection", "features": []}\n', encoding="utf-8")
        return
    gdf.to_file(path, driver="GeoJSON")
