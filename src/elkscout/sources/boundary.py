"""Unit boundary: IDFG GMU polygon -> work/boundary.geojson (EPSG:4326).

Contract:
- fetch_boundary(net, ws, cfg): resolution order
    1. ws.manual_path("boundary") if it exists (any GeoJSON polygon; reprojected/assumed 4326)
    2. IDFG ArcGIS layer (endpoints.IDFG_HUNTING layer IDFG_GMU_LAYER, alt host fallback):
       discover the unit-name field from layer_info() fields — first field whose
       uppercased name contains NAME, then UNIT, then GMU. Query where
       "<field>" = '<cfg.unit>'; if the exact match returns nothing, retry with LIKE.
  Dissolve all returned features to a single (multi)polygon, keep a `unit` column,
  write ws.boundary_geojson, return the GeoDataFrame (EPSG:4326).
  Raise RuntimeError with a helpful message if the query returns no features.
- load_boundary(ws): read ws.boundary_geojson -> GeoDataFrame (EPSG:4326).
- synth_boundary_from_bbox(ws, bbox4326): build a rectangle boundary from
  (minlon, minlat, maxlon, maxlat), write the same artifact, return it. Used by
  --aoi-bbox test/smoke mode and never touches the network.
"""

from __future__ import annotations

import logging

import geopandas as gpd
from shapely.geometry import box

from .. import endpoints
from ..config import Config
from ..net import Net, OfflineError
from ..paths import OfflineMissError, Workspace
from .arcgis import layer_info, query_layer_geojson

log = logging.getLogger("elkscout.boundary")

SOURCE = "boundary"

# Unit-name field discovery priority: first field whose uppercased name contains
# the token, tokens tried in this order.
_FIELD_TOKENS = ("NAME", "UNIT", "GMU")


def fetch_boundary(net: Net, ws: Workspace, cfg: Config) -> gpd.GeoDataFrame:
    manual = ws.manual_path(SOURCE)
    if manual.exists():
        log.info("boundary: using manual drop-in %s", manual)
        gdf = gpd.read_file(manual)
        gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")
        return _finalize(ws, gdf, cfg.unit)

    errors: list[Exception] = []
    for base_url in (endpoints.IDFG_HUNTING, endpoints.IDFG_HUNTING_ALT):
        try:
            gdf = _query_unit(net, base_url, cfg.unit)
            return _finalize(ws, gdf, cfg.unit)
        except Exception as e:  # noqa: BLE001 - any host failure -> try the alt host
            errors.append(e)
            log.warning("boundary: host %s failed: %s", base_url, e)

    if all(isinstance(e, OfflineError) for e in errors):
        raise OfflineMissError(SOURCE, ws) from errors[-1]
    raise RuntimeError(
        f"could not fetch GMU {cfg.unit!r} boundary from any IDFG host "
        f"(last error: {errors[-1]})"
    ) from errors[-1]


def load_boundary(ws: Workspace) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(ws.boundary_geojson)
    return gdf.set_crs("EPSG:4326", allow_override=True)


def synth_boundary_from_bbox(ws: Workspace, bbox4326: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    minlon, minlat, maxlon, maxlat = bbox4326
    if not (minlon < maxlon and minlat < maxlat):
        raise ValueError(f"bbox must be (minlon, minlat, maxlon, maxlat) with min < max, got {bbox4326}")
    gdf = gpd.GeoDataFrame(
        {"unit": ["AOI"]}, geometry=[box(minlon, minlat, maxlon, maxlat)], crs="EPSG:4326"
    )
    _write(ws, gdf)
    log.info("boundary: synthetic AOI rectangle %s written to %s", bbox4326, ws.boundary_geojson)
    return gdf


# -- internals ---------------------------------------------------------------

def _query_unit(net: Net, base_url: str, unit: str) -> gpd.GeoDataFrame:
    info = layer_info(net, base_url, endpoints.IDFG_GMU_LAYER, SOURCE)
    field = _unit_field(info)
    exact = f"\"{field}\" = '{unit}'"
    gdf = query_layer_geojson(net, base_url, endpoints.IDFG_GMU_LAYER, source=SOURCE, where=exact)
    if len(gdf) == 0:
        like = f"\"{field}\" LIKE '%{unit}%'"
        log.info("boundary: exact match %s empty; retrying with %s", exact, like)
        gdf = query_layer_geojson(net, base_url, endpoints.IDFG_GMU_LAYER, source=SOURCE, where=like)
        gdf = _prefer_exact(gdf, field, unit)
    if len(gdf) == 0:
        raise RuntimeError(
            f"IDFG layer {base_url}/{endpoints.IDFG_GMU_LAYER} returned no features where "
            f"{field} matches {unit!r}; check the config `unit` against the layer's values"
        )
    return gdf


def _unit_field(info: dict) -> str:
    names = [f.get("name", "") for f in info.get("fields") or []]
    for token in _FIELD_TOKENS:
        for name in names:
            if token in name.upper():
                return name
    raise RuntimeError(
        f"could not find a unit-name field (name containing NAME, UNIT, or GMU) "
        f"among layer fields {names}"
    )


def _prefer_exact(gdf: gpd.GeoDataFrame, field: str, unit: str) -> gpd.GeoDataFrame:
    """Narrow a LIKE result to rows whose value equals `unit` after stripping.

    LIKE '%33%' can also match '33A' or '133'; keep only true matches when any
    exist, otherwise return the LIKE result unchanged.
    """
    col = next((c for c in gdf.columns if c.upper() == field.upper()), None)
    if col is None or len(gdf) == 0:
        return gdf
    match = gdf[gdf[col].astype(str).str.strip() == unit]
    return match if len(match) else gdf


def _finalize(ws: Workspace, gdf: gpd.GeoDataFrame, unit: str) -> gpd.GeoDataFrame:
    if len(gdf) == 0:
        raise RuntimeError(f"boundary source for unit {unit!r} contains no features")
    geom = gdf.geometry.union_all()
    if geom.is_empty:
        raise RuntimeError(f"boundary geometry for unit {unit!r} dissolved to an empty shape")
    out = gpd.GeoDataFrame({"unit": [unit]}, geometry=[geom], crs="EPSG:4326")
    _write(ws, out)
    log.info("boundary: unit %s dissolved from %d feature(s) -> %s", unit, len(gdf), ws.boundary_geojson)
    return out


def _write(ws: Workspace, gdf: gpd.GeoDataFrame) -> None:
    ws.boundary_geojson.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(ws.boundary_geojson, driver="GeoJSON")
