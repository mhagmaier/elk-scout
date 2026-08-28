"""Hydrography: perennial streams, waterbodies, HUC12 watersheds.

Contract — fetch_water(net, ws, bbox4326) writes three EPSG:4326 artifacts
(manual keys: water_lines / water_bodies / huc12):

- ws.water_lines_geojson: NHDPlus HR flowlines, PERENNIAL ONLY (FCode 46006);
  flowline layer id discovered from endpoints.NHDPLUS_HR ?f=json by name
  containing 'flowline' (small-scale variants excluded — prefer the plain one).
  Keeps GNIS_NAME if present. maxAllowableOffset ~0.0001 deg (outSR units)
  tames vertex counts.
- ws.water_bodies_geojson: NHD waterbody polygons (layer name containing
  'waterbody'), FCode lake/pond (39000-39012) and reservoir (43600-43626)
  families; keeps GNIS_NAME.
- ws.huc12_geojson: WBD HUC12 polygons from endpoints.WBD (layer name
  containing '12'); keeps fields normalized to `name` + `huc12`.

Each artifact resolves manual drop-in first, then the network. Empty results
allowed. Offline miss -> OfflineMissError(key, ws).
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd

from .. import endpoints
from ..net import Net, OfflineError
from ..paths import OfflineMissError, Workspace
from .arcgis import query_layer_geojson

log = logging.getLogger("elkscout.water")

SOURCE = "water"

_OFFSET_DEG = 0.0001  # ~10 m; well under the 30 m scoring grid

WHERE_PERENNIAL = "FCode = 46006"
WHERE_WATERBODY = "(FCode >= 39000 AND FCode <= 39012) OR (FCode >= 43600 AND FCode <= 43626)"


def fetch_water(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float]) -> None:
    _fetch_one(
        net, ws, bbox4326,
        key="water_lines",
        out_path=ws.water_lines_geojson,
        base_url=endpoints.NHDPLUS_HR,
        layer_token="flowline",
        where=WHERE_PERENNIAL,
        normalize=_keep_gnis_name,
    )
    _fetch_one(
        net, ws, bbox4326,
        key="water_bodies",
        out_path=ws.water_bodies_geojson,
        base_url=endpoints.NHDPLUS_HR,
        layer_token="waterbody",
        where=WHERE_WATERBODY,
        normalize=_keep_gnis_name,
    )
    _fetch_one(
        net, ws, bbox4326,
        key="huc12",
        out_path=ws.huc12_geojson,
        base_url=endpoints.WBD,
        layer_token="12",
        where="1=1",
        normalize=_normalize_huc12,
    )


# -- internals ---------------------------------------------------------------

def _fetch_one(
    net: Net,
    ws: Workspace,
    bbox4326: tuple[float, float, float, float],
    *,
    key: str,
    out_path: Path,
    base_url: str,
    layer_token: str,
    where: str,
    normalize,
) -> None:
    manual = ws.manual_path(key)
    if manual.exists():
        log.info("%s: using manual drop-in %s", key, manual)
        gdf = gpd.read_file(manual)
        gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")
    else:
        try:
            layer_id = _discover_layer(net, base_url, layer_token)
            gdf = query_layer_geojson(
                net,
                base_url,
                layer_id,
                source=SOURCE,
                where=where,
                bbox4326=bbox4326,
                max_allowable_offset=_OFFSET_DEG,
            )
        except OfflineError as e:
            raise OfflineMissError(key, ws) from e
    _write_geojson(out_path, normalize(gdf, key))
    log.info("%s: %d features -> %s", key, len(gdf), out_path)


def _discover_layer(net: Net, base_url: str, token: str) -> int:
    """First layer whose name contains `token` (case-insensitive), preferring
    names without 'small' (excludes small-scale cartographic variants)."""
    info = net.fetch_json(base_url, {"f": "json"}, source=SOURCE)
    layers = info.get("layers") or []
    candidates = [l for l in layers if token in str(l.get("name", "")).lower()]
    preferred = [l for l in candidates if "small" not in str(l.get("name", "")).lower()]
    for layer in preferred or candidates:
        return int(layer["id"])
    raise RuntimeError(
        f"no layer name containing {token!r} on {base_url} "
        f"(layers: {[l.get('name') for l in layers]})"
    )


def _find_col(gdf: gpd.GeoDataFrame, *names: str) -> str | None:
    lower = {c.lower(): c for c in gdf.columns if c != gdf.geometry.name}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def _keep_gnis_name(gdf: gpd.GeoDataFrame, key: str) -> gpd.GeoDataFrame:
    if len(gdf) == 0:
        return gdf
    col = _find_col(gdf, "GNIS_NAME")
    keep = [col] if col else []
    return gdf[keep + [gdf.geometry.name]].rename(columns={col: "GNIS_NAME"} if col else {})


def _normalize_huc12(gdf: gpd.GeoDataFrame, key: str) -> gpd.GeoDataFrame:
    if len(gdf) == 0:
        return gdf
    rename: dict[str, str] = {}
    for target in ("name", "huc12"):
        col = _find_col(gdf, target)
        if col:
            rename[col] = target
        else:
            log.warning("huc12: no %r field among columns %s", target, list(gdf.columns))
    out = gdf.rename(columns=rename)
    keep = [c for c in ("name", "huc12") if c in out.columns]
    return out[keep + [out.geometry.name]]


def _write_geojson(path: Path, gdf: gpd.GeoDataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    if len(gdf) == 0:
        path.write_text('{"type": "FeatureCollection", "features": []}\n', encoding="utf-8")
        return
    gdf.to_file(path, driver="GeoJSON")
