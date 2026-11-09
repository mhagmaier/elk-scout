"""Legal access points: MVUM road ends the hunter's vehicle may drive to.

build_access_points(ws, cfg) -> work/access_points.geojson (EPSG:4326 points)

A road end qualifies when its MVUM route is open to the profile's vehicle
class (cfg.access.vehicle -> config.VEHICLE_FIELDS) on EVERY hunt day, the
endpoint touches no other open route (a true dead end, i.e. where you park and
walk), and it sits on public land within cfg.access.max_unit_dist_mi of the
unit. waypoints.py ranks these together with public trailheads to pick ACCESS
waypoints.

Conservative by design: a route whose dates-open field is blank does NOT
count, because blank usually means closed to that vehicle class. The hunter
still checks the current MVUM; the guide says so.
"""

from __future__ import annotations

import datetime as dt
import json
import logging

import geopandas as gpd
import numpy as np
from shapely import STRtree
from shapely.geometry import Point

from .config import VEHICLE_FIELDS, Config
from .factors import _read_vec
from .grid import Grid
from .paths import Workspace
from .sources.mvum import mvum_roads_path

log = logging.getLogger("elkscout.access")

M_PER_MI = 1609.344
DEAD_END_TOL_M = 30.0


def _md(s: str) -> tuple[int, int]:
    m, d = s.strip().split("/")
    return int(m), int(d)


def open_on(dates: str | None, day: dt.date) -> bool:
    """MVUM 'MM/DD-MM/DD[,MM/DD-MM/DD]' windows; windows may wrap the new year."""
    if not dates or not isinstance(dates, str):
        return False
    md = (day.month, day.day)
    for span in dates.split(","):
        if "-" not in span:
            continue
        try:
            a, b = (_md(x) for x in span.split("-", 1))
        except ValueError:
            continue
        if (a <= b and a <= md <= b) or (a > b and (md >= a or md <= b)):
            return True
    return False


def _field(columns, name: str) -> str | None:
    lower = {c.lower(): c for c in columns}
    return lower.get(name.lower())


def legal_routes(mvum: gpd.GeoDataFrame, vehicle: str, days: list[dt.date]) -> gpd.GeoDataFrame:
    """Routes open to `vehicle` on every day in `days`."""
    if len(mvum) == 0:
        return mvum
    allow_name, dates_name = VEHICLE_FIELDS[vehicle]
    allow_col = _field(mvum.columns, allow_name)
    dates_col = _field(mvum.columns, dates_name)
    if allow_col is None or dates_col is None:
        log.warning("access: MVUM layer lacks %s/%s fields; no road ends for vehicle %s",
                    allow_name, dates_name, vehicle)
        return mvum.iloc[0:0]
    ok = mvum.apply(
        lambda r: str(r.get(allow_col) or "").strip().lower() == "open"
        and all(open_on(r.get(dates_col), d) for d in days),
        axis=1,
    )
    return mvum[ok]


def road_ends(routes_utm: gpd.GeoDataFrame) -> list[tuple[Point, int]]:
    """(endpoint, route index) for endpoints touching no OTHER open route."""
    geoms = list(routes_utm.geometry.values)
    if not geoms:
        return []
    tree = STRtree(geoms)
    ends: list[tuple[Point, int]] = []
    for i, geom in enumerate(geoms):
        lines = list(getattr(geom, "geoms", [geom]))
        for line in lines:
            if line.is_empty or len(line.coords) < 2:
                continue
            for xy in (line.coords[0], line.coords[-1]):
                p = Point(xy)
                touching = set(tree.query(p, predicate="dwithin", distance=DEAD_END_TOL_M).tolist())
                touching.discard(i)
                if not touching:
                    ends.append((p, i))
    return ends


def build_access_points(ws: Workspace, cfg: Config) -> gpd.GeoDataFrame:
    grid = Grid.load(ws.grid_json)
    days = [
        cfg.hunt_window.start + dt.timedelta(days=i)
        for i in range((cfg.hunt_window.end - cfg.hunt_window.start).days + 1)
    ]
    mvum = _read_vec(mvum_roads_path(ws))
    routes = legal_routes(mvum, cfg.access.vehicle, days)
    log.info("access: %d MVUM routes, %d open to %s on all %d hunt days",
             len(mvum), len(routes), cfg.access.vehicle, len(days))

    rows: list[dict] = []
    if len(routes):
        utm = routes.to_crs(epsg=grid.epsg).reset_index(drop=True)
        name_col = _field(utm.columns, "name")
        id_col = _field(utm.columns, "id")
        for p, i in road_ends(utm):
            rid = str(utm.iloc[i][id_col]) if id_col else ""
            rname = str(utm.iloc[i][name_col]).title() if name_col and utm.iloc[i][name_col] else ""
            rows.append({
                "name": f"FR {rid} {rname} road end".replace("  ", " ").strip(),
                "highway": "road_end",
                "ref": f"FR {rid}".strip(),
                "vehicle": cfg.access.vehicle,
                "geometry": p,
            })
    pts = gpd.GeoDataFrame(rows, geometry="geometry", crs=f"EPSG:{grid.epsg}") if rows else \
        gpd.GeoDataFrame({"name": [], "highway": [], "ref": [], "vehicle": []},
                         geometry=gpd.GeoSeries([], dtype="geometry"), crs=f"EPSG:{grid.epsg}")

    pts = filter_public_near_unit(pts, ws, grid, cfg.access.max_unit_dist_mi)
    out = pts.to_crs(epsg=4326)
    ws.access_points_geojson.unlink(missing_ok=True)
    if len(out):
        out.to_file(ws.access_points_geojson, driver="GeoJSON")
    else:
        ws.access_points_geojson.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    log.info("access: %d legal road end(s) on public land near the unit -> %s", len(out), ws.access_points_geojson)
    return out


def filter_public_near_unit(pts: gpd.GeoDataFrame, ws: Workspace, grid: Grid, max_mi: float) -> gpd.GeoDataFrame:
    """Keep points on public cells within max_mi of the unit (uses factors.tif)."""
    if len(pts) == 0:
        return pts
    from scipy import ndimage

    from .factors import load_factors

    fx, _ = load_factors(ws)
    near_unit = ndimage.distance_transform_edt(fx["unit"] < 0.5, sampling=grid.res) <= max_mi * M_PER_MI
    p = pts.to_crs(epsg=grid.epsg)
    rows, cols = grid.rowcol(p.geometry.x.values, p.geometry.y.values)
    rows, cols = np.atleast_1d(rows), np.atleast_1d(cols)
    inside = (rows >= 0) & (rows < grid.height) & (cols >= 0) & (cols < grid.width)
    keep = np.zeros(len(p), dtype=bool)
    keep[inside] = (fx["public"][rows[inside], cols[inside]] > 0.5) & near_unit[rows[inside], cols[inside]]
    dropped = int((~keep).sum())
    if dropped:
        log.info("access: dropped %d candidate(s) off public land or too far from the unit", dropped)
    return p[keep]
