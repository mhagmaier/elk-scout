"""Land ownership (public vs private) -> work/ownership.geojson (EPSG:4326).

Contract — fetch_ownership(net, ws, bbox4326):
1. ws.manual_path("ownership") if present.
2. endpoints.BLM_SMA: pick the polygon layer discovered from ?f=json — prefer
   layers whose name contains 'Surface Management Agency', confirmed polygonal
   via layer metadata (discovered, not hardcoded). Query bbox, out_fields '*',
   max_allowable_offset 0.0003 deg (SMA polygons are huge).
3. Normalize: a string column `agency` (canonical SMA code: BLM, USFS, BOR,
   STATE, LG, PVT, ...) from the first existing field among ADMIN_AGENCY_CODE /
   ADMIN_UNIT_NAME / ADMIN_DEPT_CODE / MGMT_AGNCY / SMA, and a boolean `public`
   column. An explicit `public` column in a manual drop-in wins; otherwise
   public = agency in cfg.land_access.open_agencies. State trust (STATE) and
   local-government (LG) land are therefore CLOSED unless the state's registry
   rules open them — the original "anything not private is public" rule put
   waypoints on closed Colorado trust land.
4. Write ws.ownership_geojson; copy the optional `public_access` drop-in
   (walk-in programs, enrolled trust parcels — always open) to
   ws.public_access_geojson.

Cells with no ownership polygon at all score as public=True downstream
(SMA has slivers of no-data on federal land); the README documents this
default and hunters must verify parcels.
Offline miss -> OfflineMissError("ownership", ws).
"""

from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

from .. import endpoints
from ..config import LandAccessCfg
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


def fetch_ownership(
    net: Net,
    ws: Workspace,
    bbox4326: tuple[float, float, float, float],
    land_access: LandAccessCfg | None = None,
) -> None:
    rules = land_access or LandAccessCfg()
    _copy_public_access(ws)
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
    gdf = _normalize(gdf, rules)
    _write(ws, gdf)
    n_closed = int((~gdf["public"]).sum()) if len(gdf) else 0
    log.info(
        "ownership: %d polygons (%d closed; open agencies %s) -> %s",
        len(gdf), n_closed, rules.open_agencies, ws.ownership_geojson,
    )


# SMA / free-text agency values -> canonical codes.
_ALIASES = {
    "FS": "USFS",
    "FOREST SERVICE": "USFS",
    "US FOREST SERVICE": "USFS",
    "BUREAU OF LAND MANAGEMENT": "BLM",
    "BUREAU OF RECLAMATION": "BOR",
    "PRIVATE": "PVT",
    "STATE TRUST": "STATE",
    "STATE LAND": "STATE",
    "LOCAL GOVERNMENT": "LG",
}


def canonical_agency(value: str) -> str:
    v = str(value).strip().upper()
    if v in _ALIASES:
        return _ALIASES[v]
    if "PRIVATE" in v:
        return "PVT"
    return v or "UNKNOWN"


def _copy_public_access(ws: Workspace) -> None:
    src = ws.manual_path("public_access")
    dst = ws.public_access_geojson
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.unlink(missing_ok=True)
    if src.exists():
        gdf = gpd.read_file(src)
        gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")
        _write_gdf(dst, gdf)
        log.info("ownership: %d public-access overlay polygon(s) (always open) from %s", len(gdf), src)


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


def _normalize(gdf: gpd.GeoDataFrame, rules: LandAccessCfg) -> gpd.GeoDataFrame:
    if len(gdf) == 0:
        return gdf
    lower = {c.lower(): c for c in gdf.columns if c != gdf.geometry.name}
    agency_col = next((lower[f.lower()] for f in _AGENCY_FIELDS if f.lower() in lower), None)
    if agency_col is None:
        log.warning("ownership: no agency field among columns %s; using 'UNKNOWN'", list(gdf.columns))
        agency = pd.Series(["UNKNOWN"] * len(gdf), index=gdf.index)
    else:
        agency = gdf[agency_col].map(
            lambda v: "UNKNOWN" if v is None or (isinstance(v, float) and pd.isna(v)) else canonical_agency(v)
        )
    gdf = gdf.copy()
    gdf["agency"] = agency
    if "public" in lower:
        gdf["public"] = gdf[lower["public"]].astype(bool)
    else:
        gdf["public"] = agency.isin(rules.open_agencies)
    return gdf


def _write(ws: Workspace, gdf: gpd.GeoDataFrame) -> None:
    _write_gdf(ws.ownership_geojson, gdf)


def _write_gdf(path, gdf: gpd.GeoDataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    if len(gdf) == 0:
        path.write_text('{"type": "FeatureCollection", "features": []}\n', encoding="utf-8")
        return
    gdf.to_file(path, driver="GeoJSON")
