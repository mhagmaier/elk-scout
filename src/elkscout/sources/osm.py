"""OpenStreetMap via Overpass: motorized ways, trails, trailheads, springs.

Contract — fetch_osm(net, ws, bbox4326) writes four EPSG:4326 GeoJSON artifacts
(each falls back to its manual drop-in first: osm_motorized / osm_trails /
osm_trailheads / osm_springs):

- ws.motorized_geojson (LineStrings): ways with highway in (motorway, trunk,
  primary, secondary, tertiary, unclassified, residential, service, track)
  EXCLUDING those tagged motor_vehicle in (no, private) or access in (no, private).
  NOTE: factors.py later unions this with MVUM roads; write OSM-only here.
- ws.trails_geojson (LineStrings): highway in (path, footway, bridleway, cycleway)
  plus track with motor_vehicle=no.
- ws.trailheads_geojson (Points): highway=trailhead nodes, plus amenity=parking
  nodes/way-centroids within 150 m of any trail line (distance in EPSG:32611).
- ws.springs_geojson (Points): natural=spring nodes.

One Overpass QL POST per theme ([out:json][timeout:180], global bbox setting,
`out geom;` so ways carry coordinate arrays), rotating endpoints.OVERPASS until
one succeeds. Ways with fewer than 2 nodes are skipped. Kept tags: name,
highway, ref. Empty results write an empty FeatureCollection. Offline with no
cache/manual -> paths.OfflineMissError(key, ws).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Iterable

import geopandas as gpd
import requests
from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

from .. import endpoints
from ..net import Net, OfflineError
from ..paths import OfflineMissError, Workspace

log = logging.getLogger("elkscout.osm")

SOURCE = "osm"
KEPT_TAGS = ("name", "highway", "ref")
TRAILHEAD_SNAP_M = 150.0
_UTM_EPSG = 32611
_OVERPASS_TIMEOUT_S = 180

_MOTORIZED_RE = "motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|track"
_TRAIL_RE = "path|footway|bridleway|cycleway"

_MOTORIZED_STMTS = (
    f'way["highway"~"^({_MOTORIZED_RE})$"]'
    '["motor_vehicle"!~"^(no|private)$"]["access"!~"^(no|private)$"];'
)
_TRAILS_STMTS = f'way["highway"~"^({_TRAIL_RE})$"];way["highway"="track"]["motor_vehicle"="no"];'
_TRAILHEADS_STMTS = 'node["highway"="trailhead"];node["amenity"="parking"];way["amenity"="parking"];'
_SPRINGS_STMTS = 'node["natural"="spring"];'


def fetch_osm(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float]) -> None:
    _fetch_theme(net, ws, "osm_motorized", ws.motorized_geojson, _MOTORIZED_STMTS, bbox4326, _ways_gdf)
    trails = _fetch_theme(net, ws, "osm_trails", ws.trails_geojson, _TRAILS_STMTS, bbox4326, _ways_gdf)
    _fetch_theme(
        net,
        ws,
        "osm_trailheads",
        ws.trailheads_geojson,
        _TRAILHEADS_STMTS,
        bbox4326,
        lambda elements: _trailheads_gdf(elements, trails),
    )
    _fetch_theme(net, ws, "osm_springs", ws.springs_geojson, _SPRINGS_STMTS, bbox4326, _nodes_gdf)


# -- theme plumbing ----------------------------------------------------------

def _fetch_theme(
    net: Net,
    ws: Workspace,
    key: str,
    out_path: Path,
    statements: str,
    bbox4326: tuple[float, float, float, float],
    to_gdf: Callable[[list[dict]], gpd.GeoDataFrame],
) -> gpd.GeoDataFrame:
    gdf = _manual_gdf(ws, key)
    if gdf is None:
        elements = _query_overpass(net, ws, key, _build_ql(bbox4326, statements))
        gdf = to_gdf(elements)
    _write_geojson(out_path, gdf)
    log.info("osm %s: %d feature(s) -> %s", key, len(gdf), out_path)
    return gdf


def _manual_gdf(ws: Workspace, key: str) -> gpd.GeoDataFrame | None:
    p = ws.manual_path(key)
    if not p.exists():
        return None
    log.info("osm %s: using manual drop-in %s", key, p)
    gdf = gpd.read_file(p)
    return gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")


def _build_ql(bbox4326: tuple[float, float, float, float], statements: str) -> str:
    minlon, minlat, maxlon, maxlat = bbox4326
    return (
        f"[out:json][timeout:{_OVERPASS_TIMEOUT_S}]"
        f"[bbox:{minlat},{minlon},{maxlat},{maxlon}];\n"
        f"({statements});\nout geom;"
    )


def _query_overpass(net: Net, ws: Workspace, key: str, ql: str) -> list[dict]:
    """POST the query to each Overpass endpoint in order; first success wins."""
    errors: list[Exception] = []
    for url in endpoints.OVERPASS:
        try:
            raw = net.fetch_bytes(
                url, None, source=SOURCE, ext="json", method="POST", data={"data": ql}, min_interval_s=1.0
            )
            data = json.loads(raw)
            remark = str(data.get("remark") or "")
            if "error" in remark.lower():
                raise RuntimeError(f"overpass remark: {remark}")
            elements = data.get("elements")
            if not isinstance(elements, list):
                raise RuntimeError("malformed overpass response (no 'elements' array)")
            return elements
        except (requests.RequestException, RuntimeError, ValueError) as e:
            errors.append(e)
            log.warning("osm %s: endpoint %s failed: %s", key, url, e)
    if errors and all(isinstance(e, OfflineError) for e in errors):
        raise OfflineMissError(key, ws) from errors[-1]
    raise RuntimeError(f"all overpass endpoints failed for {key} (last: {errors[-1]})") from errors[-1]


# -- Overpass JSON -> GeoDataFrame -------------------------------------------

def _props(el: dict) -> dict:
    tags = el.get("tags") or {}
    return {k: tags.get(k) for k in KEPT_TAGS}


def _node_point(el: dict) -> Point | None:
    lon, lat = el.get("lon"), el.get("lat")
    return Point(lon, lat) if lon is not None and lat is not None else None


def _way_line(el: dict) -> LineString | None:
    pts = [(g["lon"], g["lat"]) for g in el.get("geometry") or [] if g]
    return LineString(pts) if len(pts) >= 2 else None


def _way_centroid(el: dict) -> Point | None:
    line = _way_line(el)
    if line is None:
        return None
    coords = list(line.coords)
    if len(coords) >= 4 and coords[0] == coords[-1]:
        poly = Polygon(coords)
        if poly.is_valid and poly.area > 0:
            return poly.centroid
    return line.centroid


def _gdf(rows: list[dict], geoms: list[BaseGeometry]) -> gpd.GeoDataFrame:
    if not geoms:
        return gpd.GeoDataFrame(
            {k: [] for k in KEPT_TAGS},
            geometry=gpd.GeoSeries([], dtype="geometry"),
            crs="EPSG:4326",
        )
    return gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:4326")


def _ways_gdf(elements: Iterable[dict]) -> gpd.GeoDataFrame:
    rows: list[dict] = []
    geoms: list[BaseGeometry] = []
    for el in elements:
        if el.get("type") != "way":
            continue
        line = _way_line(el)
        if line is None:
            continue  # <2 nodes
        rows.append(_props(el))
        geoms.append(line)
    return _gdf(rows, geoms)


def _nodes_gdf(elements: Iterable[dict]) -> gpd.GeoDataFrame:
    rows: list[dict] = []
    geoms: list[BaseGeometry] = []
    for el in elements:
        if el.get("type") != "node":
            continue
        pt = _node_point(el)
        if pt is None:
            continue
        rows.append(_props(el))
        geoms.append(pt)
    return _gdf(rows, geoms)


def _trailheads_gdf(elements: Iterable[dict], trails: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Trailhead nodes unconditionally; parking points only near a trail."""
    th_rows: list[dict] = []
    th_geoms: list[BaseGeometry] = []
    pk_rows: list[dict] = []
    pk_geoms: list[Point] = []
    for el in elements:
        tags = el.get("tags") or {}
        typ = el.get("type")
        if typ == "node" and tags.get("highway") == "trailhead":
            pt = _node_point(el)
            if pt is not None:
                th_rows.append(_props(el))
                th_geoms.append(pt)
        elif tags.get("amenity") == "parking":
            pt = _node_point(el) if typ == "node" else _way_centroid(el) if typ == "way" else None
            if pt is not None:
                pk_rows.append(_props(el))
                pk_geoms.append(pt)
    keep = _near_trails(pk_geoms, trails, TRAILHEAD_SNAP_M)
    rows = th_rows + [r for r, k in zip(pk_rows, keep) if k]
    geoms = th_geoms + [g for g, k in zip(pk_geoms, keep) if k]
    dropped = len(pk_geoms) - sum(keep)
    if dropped:
        log.info("osm trailheads: dropped %d parking point(s) farther than %.0f m from any trail", dropped, TRAILHEAD_SNAP_M)
    return _gdf(rows, geoms)


def _near_trails(points: list[Point], trails: gpd.GeoDataFrame, max_dist_m: float) -> list[bool]:
    if not points or trails is None or len(trails) == 0:
        return [False] * len(points)
    trail_geoms = trails.to_crs(epsg=_UTM_EPSG).geometry.to_numpy()
    pts = gpd.GeoSeries(points, crs="EPSG:4326").to_crs(epsg=_UTM_EPSG).to_numpy()
    tree = STRtree(trail_geoms)
    pairs = tree.query(pts, predicate="dwithin", distance=max_dist_m)
    near = set(pairs[0].tolist())
    return [i in near for i in range(len(points))]


# -- output ------------------------------------------------------------------

def _write_geojson(path: Path, gdf: gpd.GeoDataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    if len(gdf) == 0:
        path.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
        return
    gdf.to_file(path, driver="GeoJSON")
