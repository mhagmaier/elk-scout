"""Generic ArcGIS REST helpers: paginated feature queries and DEM tile export.

Handles the realities of public ArcGIS servers: maxRecordCount caps with
exceededTransferLimit, servers that ignore resultOffset (objectid-chunk
fallback), and ImageServer exportImage size limits (tile + mosaic).
"""

from __future__ import annotations

import logging

import geopandas as gpd

from ..net import Net

log = logging.getLogger("elkscout.arcgis")


def layer_info(net: Net, base_url: str, layer_id: int, source: str) -> dict:
    """Layer metadata (fields, maxRecordCount, capabilities)."""
    return net.fetch_json(f"{base_url}/{layer_id}", {"f": "json"}, source=source)


def _query_page(net: Net, url: str, params: dict, source: str) -> dict:
    return net.fetch_json(url, params, source=source, min_interval_s=0.2)


def query_layer_geojson(
    net: Net,
    base_url: str,
    layer_id: int,
    *,
    source: str,
    where: str = "1=1",
    bbox4326: tuple[float, float, float, float] | None = None,
    out_fields: str = "*",
    max_allowable_offset: float | None = None,
    page_size: int = 1000,
) -> gpd.GeoDataFrame:
    """Query an ArcGIS feature layer to a GeoDataFrame in EPSG:4326.

    Paginates with resultOffset while exceededTransferLimit; if the server
    makes no progress (ignores resultOffset), falls back to fetching all
    object IDs and chunking `WHERE objectid IN (...)`.
    """
    url = f"{base_url}/{layer_id}/query"
    base_params: dict = {
        "where": where,
        "outFields": out_fields,
        "outSR": 4326,
        "f": "geojson",
    }
    if bbox4326 is not None:
        minx, miny, maxx, maxy = bbox4326
        base_params.update(
            {
                "geometry": f"{minx},{miny},{maxx},{maxy}",
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
            }
        )
    if max_allowable_offset is not None:
        base_params["maxAllowableOffset"] = max_allowable_offset

    features: list[dict] = []
    offset = 0
    while True:
        params = dict(base_params)
        params["resultOffset"] = offset
        params["resultRecordCount"] = page_size
        page = _query_page(net, url, params, source)
        page_feats = page.get("features", [])
        features.extend(page_feats)
        more = bool(page.get("exceededTransferLimit") or (page.get("properties") or {}).get("exceededTransferLimit"))
        if not page_feats:
            break
        if not more and len(page_feats) < page_size:
            break
        offset += len(page_feats)
        if offset > 500_000:
            raise RuntimeError(f"runaway pagination on {url}")
        # Server ignoring pagination: same page returned forever -> objectid fallback
        if len(features) >= 2 * page_size and features[0] == features[page_size]:
            log.warning("%s ignores resultOffset; falling back to objectid chunks", url)
            return _query_by_objectids(net, base_url, layer_id, base_params, source, page_size)

    return _to_gdf(features)


def _query_by_objectids(
    net: Net, base_url: str, layer_id: int, base_params: dict, source: str, page_size: int
) -> gpd.GeoDataFrame:
    url = f"{base_url}/{layer_id}/query"
    id_params = {k: v for k, v in base_params.items() if k not in ("outFields", "f")}
    id_params.update({"returnIdsOnly": "true", "f": "json"})
    resp = _query_page(net, url, id_params, source)
    ids = resp.get("objectIds") or []
    oid_field = resp.get("objectIdFieldName", "OBJECTID")
    features: list[dict] = []
    for i in range(0, len(ids), page_size):
        chunk = ids[i : i + page_size]
        params = dict(base_params)
        # objectIds param avoids WHERE-clause length limits
        params["objectIds"] = ",".join(str(x) for x in chunk)
        params.pop("geometry", None)
        params.pop("geometryType", None)
        params.pop("inSR", None)
        params.pop("spatialRel", None)
        page = _query_page(net, url, params, source)
        features.extend(page.get("features", []))
    log.info("objectid fallback fetched %d features via %s (%s)", len(features), oid_field, source)
    return _to_gdf(features)


def _to_gdf(features: list[dict]) -> gpd.GeoDataFrame:
    if not features:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    fc = {"type": "FeatureCollection", "features": features}
    gdf = gpd.GeoDataFrame.from_features(fc["features"], crs="EPSG:4326")
    return gdf


def export_image_tiles(
    net: Net,
    image_url: str,
    *,
    source: str,
    bounds: tuple[float, float, float, float],
    epsg: int,
    res_m: float,
    tile_px: int = 2048,
    overlap_px: int = 32,
) -> list[bytes]:
    """Fetch an ImageServer extent as GeoTIFF tiles (caller mosaics them).

    Requests are made in the target CRS (bboxSR = imageSR = epsg) at res_m so
    tiles land nearly aligned to the scoring grid; the caller still warps the
    mosaic onto the exact grid transform.
    """
    minx, miny, maxx, maxy = bounds
    span_x = maxx - minx
    span_y = maxy - miny
    step = (tile_px - overlap_px) * res_m
    tiles: list[bytes] = []
    y = miny
    while y < maxy:
        x = minx
        y_top = min(y + tile_px * res_m, maxy)
        while x < maxx:
            x_right = min(x + tile_px * res_m, maxx)
            w_px = max(1, int(round((x_right - x) / res_m)))
            h_px = max(1, int(round((y_top - y) / res_m)))
            params = {
                "bbox": f"{x},{y},{x_right},{y_top}",
                "bboxSR": epsg,
                "imageSR": epsg,
                "size": f"{w_px},{h_px}",
                "format": "tiff",
                "pixelType": "F32",
                "noDataInterpretation": "esriNoDataMatchAny",
                "interpolation": "RSP_BilinearInterpolation",
                "f": "image",
            }
            tiles.append(
                net.fetch_bytes(f"{image_url}/exportImage", params, source=source, ext="tif", min_interval_s=0.2)
            )
            x += step
        y += step
    log.info("fetched %d DEM tiles for %.0f x %.0f km extent", len(tiles), span_x / 1000, span_y / 1000)
    return tiles
