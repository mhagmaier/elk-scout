"""Unit boundary: a state's GMU polygon -> work/boundary.geojson (EPSG:4326).

Contract:
- fetch_boundary(net, ws, cfg): resolution order
    1. ws.manual_path("boundary") if it exists (any GeoJSON polygon; assumed/reprojected 4326)
    2. The config's `boundary:` BoundarySource (generated configs carry their
       state's service), falling back to the built-in IDFG default. Hosts are
       tried in order (base_url, then alt_urls); the layer is explicit or
       discovered by name hint; the unit-name field is explicit, hint-matched,
       or discovered by the generic NAME/UNIT/GMU heuristic. Query
       where "<field>" = '<formatted unit>'; empty exact match retries LIKE.
  Dissolve all returned features to a single (multi)polygon, keep a `unit`
  column, write ws.boundary_geojson, return the GeoDataFrame (EPSG:4326).
- load_boundary(ws): read ws.boundary_geojson -> GeoDataFrame (EPSG:4326).
- synth_boundary_from_bbox(ws, bbox4326): rectangle boundary for --aoi-bbox
  test/smoke mode; never touches the network.
"""

from __future__ import annotations

import logging

import geopandas as gpd
from shapely.geometry import box

from .. import endpoints
from ..config import BoundarySource, Config
from ..net import Net, OfflineError
from ..paths import OfflineMissError, Workspace
from .arcgis import layer_info, query_layer_geojson

log = logging.getLogger("elkscout.boundary")

SOURCE = "boundary"

# Generic unit-name field discovery priority: first field whose uppercased name
# contains the token, tokens tried in this order.
_FIELD_TOKENS = ("NAME", "UNIT", "GMU")


def resolve_boundary_source(cfg: Config) -> BoundarySource:
    """The config's own boundary source, or the built-in IDFG default."""
    return cfg.boundary or endpoints.idfg_default_boundary()


def fetch_boundary(net: Net, ws: Workspace, cfg: Config) -> gpd.GeoDataFrame:
    manual = ws.manual_path(SOURCE)
    if manual.exists():
        log.info("boundary: using manual drop-in %s", manual)
        gdf = gpd.read_file(manual)
        gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")
        return _finalize(ws, gdf, cfg.unit)

    src = resolve_boundary_source(cfg)
    errors: list[Exception] = []
    for base_url in (src.base_url, *src.alt_urls):
        try:
            gdf = _query_unit(net, src, base_url, cfg.unit)
            return _finalize(ws, gdf, cfg.unit)
        except Exception as e:  # noqa: BLE001 - any host failure -> try the alt host
            errors.append(e)
            log.warning("boundary: host %s failed: %s", base_url, e)

    if all(isinstance(e, OfflineError) for e in errors):
        raise OfflineMissError(SOURCE, ws) from errors[-1]
    raise RuntimeError(
        f"could not fetch unit {cfg.unit!r} boundary from any configured host "
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

def _resolve_layer(net: Net, src: BoundarySource, base_url: str) -> int:
    if src.layer is not None:
        return src.layer
    info = net.fetch_json(base_url, {"f": "json"}, source=SOURCE)
    layers = info.get("layers") or []
    hint = (src.layer_hint or "unit").lower()
    named = [l for l in layers if hint in str(l.get("name", "")).lower()]
    for layer in named or layers:
        meta = layer_info(net, base_url, int(layer["id"]), SOURCE)
        if meta.get("geometryType") == "esriGeometryPolygon":
            log.info("boundary: discovered layer %s (%r) on %s", layer["id"], layer.get("name"), base_url)
            return int(layer["id"])
    raise RuntimeError(
        f"no polygon layer matching hint {hint!r} on {base_url} "
        f"(layers: {[l.get('name') for l in layers]})"
    )


def _query_unit(net: Net, src: BoundarySource, base_url: str, unit: str) -> gpd.GeoDataFrame:
    layer = _resolve_layer(net, src, base_url)
    info = layer_info(net, base_url, layer, SOURCE)
    field = _unit_field(src, info)
    value = src.unit_value_format.format(unit=unit)
    exact = f"\"{field}\" = '{value}'"
    gdf = query_layer_geojson(net, base_url, layer, source=SOURCE, where=exact)
    if len(gdf) == 0:
        like = f"\"{field}\" LIKE '%{value}%'"
        log.info("boundary: exact match %s empty; retrying with %s", exact, like)
        gdf = query_layer_geojson(net, base_url, layer, source=SOURCE, where=like)
        gdf = _prefer_exact(gdf, field, value)
    if len(gdf) == 0:
        raise RuntimeError(
            f"layer {base_url}/{layer} returned no features where "
            f"{field} matches {value!r}; check the config `unit` against the layer's values"
        )
    return gdf


def _unit_field(src: BoundarySource, info: dict) -> str:
    names = [f.get("name", "") for f in info.get("fields") or []]
    if src.unit_field:
        for name in names:
            if name.upper() == src.unit_field.upper():
                return name
        raise RuntimeError(f"configured unit_field {src.unit_field!r} not among layer fields {names}")
    for token in (*src.unit_field_hints, *_FIELD_TOKENS):
        for name in names:
            if token.upper() in name.upper():
                return name
    raise RuntimeError(
        f"could not find a unit-name field (hints {src.unit_field_hints} or NAME/UNIT/GMU) "
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
