"""Waypoint extraction, typing, and hunt-area clustering.

Pipeline:
1. BED/FEED/WATER/CAMP from their type-score rasters: local maxima above the
   score floor, greedy non-max suppression (same-type min_spacing_m,
   cross-type cross_type_spacing_m). WATER candidates must sit within 300 m
   of mapped water.
2. SADDLE: elevation minima along the skeletonized ridge mask of a ~90 m
   downsampled DEM, kept when both bedding and feed habitat exist within the
   travel radius.
3. GLASS: high-TPI knobs scored by a radial line-of-sight viewshed over the
   FEED score raster.
4. ACCESS: public trailheads + legal road ends for the hunter's vehicle
   (access.py), on public land near the unit, ranked by nearby composite score.
5. Hunt areas: HUC12 watershed clustering (quadrant fallback when no HUC12
   layer exists), small areas merged into neighbors, ranked by mean waypoint
   score, capped at max_areas.
6. Naming (B2-03 <tag> <elev>) + evidence sentences -> waypoints.geojson and
   hunt_areas.geojson (EPSG:4326).
"""

from __future__ import annotations

import json
import logging
import math
import re
import warnings

import geopandas as gpd
import numpy as np
from scipy import ndimage
from shapely.geometry import box
from skimage.measure import block_reduce
from skimage.morphology import skeletonize

from . import evidence
from .config import Config
from .factors import load_factors, _read_vec
from .grid import Grid, read_raster
from .paths import Workspace
from .scoring import load_scores
from .sources.dem import load_dem
from .terrain import load_terrain

log = logging.getLogger("elkscout.waypoints")

TYPE_CODES = {"BED": "B", "FEED": "F", "WATER": "W", "SADDLE": "S", "GLASS": "G", "CAMP": "C", "ACCESS": "A"}
SELECTION_ORDER = ["BED", "FEED", "WATER", "SADDLE", "GLASS", "CAMP", "ACCESS"]
LOCALMAX_WINDOW = 5
WATER_MAX_DIST_M = 300.0
SADDLE_FLOOR_FRACTION = 0.6
SADDLE_HABITAT_MIN = 0.5
GLASS_MIN_SCORE = 0.05
GLASS_KNOB_SPACING_M = 500.0
ACCESS_CONTEXT_M = 2000.0
VIEWSHED_RAYS = 48
OBSERVER_HEIGHT_M = 2.0


class _Selector:
    """Greedy spatial non-max suppression across all types."""

    def __init__(self, grid: Grid, cfg: Config):
        self.grid = grid
        self.cfg = cfg
        self.selected: list[dict] = []

    def try_add(self, wp_type: str, row: int, col: int, score: float) -> bool:
        x, y = self.grid.xy(row, col)
        x, y = float(x), float(y)
        for s in self.selected:
            limit = (
                self.cfg.waypoints.min_spacing_m
                if s["wp_type"] == wp_type
                else self.cfg.waypoints.cross_type_spacing_m
            )
            if math.hypot(x - s["x"], y - s["y"]) < limit:
                return False
        self.selected.append({"wp_type": wp_type, "row": row, "col": col, "x": x, "y": y, "score": float(score)})
        return True


def _local_maxima(arr: np.ndarray, floor: float, extra_mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    a = np.nan_to_num(arr, nan=0.0)
    peaks = (a == ndimage.maximum_filter(a, size=LOCALMAX_WINDOW)) & (a >= floor)
    if extra_mask is not None:
        peaks &= extra_mask
    return np.nonzero(peaks)


def _extract_raster_type(sel: _Selector, wp_type: str, band: np.ndarray, floor: float, extra_mask=None) -> int:
    rows, cols = _local_maxima(band, floor, extra_mask)
    if len(rows) == 0:
        return 0
    vals = np.nan_to_num(band, nan=0.0)[rows, cols]
    order = np.argsort(-vals)
    target = sel.cfg.waypoints.counts.get(wp_type, 0)
    added = 0
    for i in order:
        if added >= target:
            break
        if sel.try_add(wp_type, int(rows[i]), int(cols[i]), float(vals[i])):
            added += 1
    return added


def _downsample(arr: np.ndarray, factor: int, func) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # nanmean of all-NaN blocks
        return block_reduce(arr, block_size=(factor, factor), func=func, cval=np.nan)


def _window_max(arr: np.ndarray, r: int, c: int, radius: int) -> float:
    r0, r1 = max(0, r - radius), min(arr.shape[0], r + radius + 1)
    c0, c1 = max(0, c - radius), min(arr.shape[1], c + radius + 1)
    window = arr[r0:r1, c0:c1]
    return float(np.nanmax(window)) if window.size else 0.0


def _extract_saddles(sel: _Selector, dem: np.ndarray, terrain, type_scores, composite, grid: Grid) -> int:
    cfg = sel.cfg
    factor = max(1, int(round(cfg.waypoints.saddle.dem_downsample_m / grid.res)))
    dem_ds = _downsample(dem.astype(np.float64), factor, np.nanmean)
    tpi_ds = _downsample(terrain["tpi1000"].astype(np.float64), factor, np.nanmean)
    bed_ds = _downsample(np.nan_to_num(type_scores["BED"], nan=0.0), factor, np.max)
    feed_ds = _downsample(np.nan_to_num(type_scores["FEED"], nan=0.0), factor, np.max)

    finite = tpi_ds[np.isfinite(tpi_ds)]
    if finite.size == 0:
        return 0
    ridge = np.nan_to_num(tpi_ds, nan=-np.inf) >= np.quantile(finite, 0.9)
    if not ridge.any():
        return 0
    skel = skeletonize(ridge)
    travel_cells = max(1, int(round(cfg.waypoints.saddle.travel_max_km * 1000 / (factor * grid.res))))

    candidates: list[tuple[float, int, int]] = []
    dem_on_skel = np.where(skel & np.isfinite(dem_ds), dem_ds, np.inf)
    rows, cols = np.nonzero(skel)
    for r, c in zip(rows, cols):
        r0, r1 = max(0, r - 1), min(skel.shape[0], r + 2)
        c0, c1 = max(0, c - 1), min(skel.shape[1], c + 2)
        if dem_on_skel[r, c] > np.min(dem_on_skel[r0:r1, c0:c1]):
            continue  # not the low point of the ridge line locally
        if _window_max(bed_ds, r, c, travel_cells) < SADDLE_HABITAT_MIN:
            continue
        if _window_max(feed_ds, r, c, travel_cells) < SADDLE_HABITAT_MIN:
            continue
        fr = min(sel.grid.height - 1, r * factor + factor // 2)
        fc = min(sel.grid.width - 1, c * factor + factor // 2)
        score = float(np.nan_to_num(composite[fr, fc], nan=0.0))
        if score >= cfg.waypoints.score_floor * SADDLE_FLOOR_FRACTION:
            candidates.append((score, fr, fc))

    added = 0
    for score, fr, fc in sorted(candidates, reverse=True):
        if added >= cfg.waypoints.counts.get("SADDLE", 0):
            break
        if sel.try_add("SADDLE", fr, fc, score):
            added += 1
    return added


def _viewshed_score(dem_ds: np.ndarray, feed_ds: np.ndarray, r0: int, c0: int, radius_cells: int, res_ds: float) -> float:
    h, w = dem_ds.shape
    base = dem_ds[r0, c0]
    if not np.isfinite(base):
        return 0.0
    eye = base + OBSERVER_HEIGHT_M
    total, n = 0.0, 0
    for az in np.linspace(0.0, 2.0 * np.pi, VIEWSHED_RAYS, endpoint=False):
        dr, dc = -np.cos(az), np.sin(az)
        horizon = -np.inf
        for step in range(1, radius_cells + 1):
            r = int(round(r0 + dr * step))
            c = int(round(c0 + dc * step))
            if not (0 <= r < h and 0 <= c < w):
                break
            z = dem_ds[r, c]
            if not np.isfinite(z):
                continue
            angle = (z - eye) / (step * res_ds)
            if angle >= horizon:
                v = feed_ds[r, c]
                if np.isfinite(v):
                    total += float(v)
                    n += 1
                horizon = angle
    return total / n if n else 0.0


def _extract_glass(sel: _Selector, dem: np.ndarray, terrain, type_scores, grid: Grid) -> int:
    cfg = sel.cfg
    factor = max(1, int(round(cfg.waypoints.saddle.dem_downsample_m / grid.res)))
    res_ds = factor * grid.res
    dem_ds = _downsample(dem.astype(np.float64), factor, np.nanmean)
    tpi_ds = _downsample(terrain["tpi1000"].astype(np.float64), factor, np.nanmean)
    feed_ds = _downsample(np.nan_to_num(type_scores["FEED"], nan=0.0), factor, np.mean)
    radius_cells = max(1, int(round(cfg.waypoints.glass.viewshed_radius_km * 1000 / res_ds)))
    spacing_cells = max(1, int(round(GLASS_KNOB_SPACING_M / res_ds)))

    flat = np.nan_to_num(tpi_ds, nan=-np.inf).ravel()
    order = np.argsort(-flat)
    knobs: list[tuple[int, int]] = []
    for idx in order:
        if len(knobs) >= cfg.waypoints.glass.max_candidates or flat[idx] == -np.inf:
            break
        r, c = divmod(int(idx), tpi_ds.shape[1])
        if all(max(abs(r - kr), abs(c - kc)) >= spacing_cells for kr, kc in knobs):
            knobs.append((r, c))

    scored: list[tuple[float, int, int]] = []
    for r, c in knobs:
        s = _viewshed_score(dem_ds, feed_ds, r, c, radius_cells, res_ds)
        if s >= GLASS_MIN_SCORE:
            fr = min(grid.height - 1, r * factor + factor // 2)
            fc = min(grid.width - 1, c * factor + factor // 2)
            scored.append((s, fr, fc))

    added = 0
    for s, fr, fc in sorted(scored, reverse=True):
        if added >= cfg.waypoints.counts.get("GLASS", 0):
            break
        if sel.try_add("GLASS", fr, fc, s):
            added += 1
    return added


def _access_candidates(ws: Workspace, grid: Grid, cfg: Config) -> gpd.GeoDataFrame:
    """Trailheads + legal road ends, kept only on public land near the unit.

    Before this filter the GMU 68/681 run put ACCESS points in town and on
    private ground: OSM trailheads/parking aren't guaranteed public.
    """
    import pandas as pd

    from .access import filter_public_near_unit

    parts = [g for g in (_read_vec(ws.trailheads_geojson), _read_vec(ws.access_points_geojson)) if len(g)]
    if not parts:
        return gpd.GeoDataFrame(geometry=gpd.GeoSeries([], dtype="geometry"), crs="EPSG:4326")
    cand = gpd.GeoDataFrame(pd.concat([g.to_crs(epsg=4326) for g in parts], ignore_index=True), crs="EPSG:4326")
    return filter_public_near_unit(cand, ws, grid, cfg.access.max_unit_dist_mi)


def _extract_access(sel: _Selector, trailheads: gpd.GeoDataFrame, composite: np.ndarray, grid: Grid) -> int:
    if trailheads is None or len(trailheads) == 0:
        return 0
    cfg = sel.cfg
    radius = max(1, int(round(ACCESS_CONTEXT_M / grid.res)))
    th = trailheads.to_crs(epsg=grid.epsg)
    cands: list[tuple[float, int, int]] = []
    comp = np.nan_to_num(composite, nan=0.0)
    for geom in th.geometry:
        p = geom.centroid
        row, col = grid.rowcol(p.x, p.y)
        row, col = int(row), int(col)
        if not (0 <= row < grid.height and 0 <= col < grid.width):
            continue
        r0, r1 = max(0, row - radius), min(grid.height, row + radius + 1)
        c0, c1 = max(0, col - radius), min(grid.width, col + radius + 1)
        cands.append((float(comp[r0:r1, c0:c1].mean()), row, col))
    added = 0
    for s, r, c in sorted(cands, reverse=True):
        if added >= cfg.waypoints.counts.get("ACCESS", 0):
            break
        if sel.try_add("ACCESS", r, c, s):
            added += 1
    return added


# -- hunt areas --------------------------------------------------------------

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "area"


def _quadrant_areas(grid: Grid) -> gpd.GeoDataFrame:
    minlon, minlat, maxlon, maxlat = grid.bbox4326()
    midlon, midlat = (minlon + maxlon) / 2, (minlat + maxlat) / 2
    quads = {
        "NW": box(minlon, midlat, midlon, maxlat),
        "NE": box(midlon, midlat, maxlon, maxlat),
        "SW": box(minlon, minlat, midlon, midlat),
        "SE": box(midlon, minlat, maxlon, midlat),
    }
    return gpd.GeoDataFrame({"name": list(quads)}, geometry=list(quads.values()), crs="EPSG:4326")


def _assign_areas(wp: gpd.GeoDataFrame, areas: gpd.GeoDataFrame, cfg: Config) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Attach hunt_area/area_slug/area_rank to waypoints; return (wp, area polygons)."""
    joined = gpd.sjoin(wp, areas[["name", "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]
    # Waypoints outside every polygon -> nearest area.
    missing = joined["name"].isna()
    if missing.any():
        area_geoms = areas.geometry.values
        for idx in joined.index[missing]:
            dists = [joined.geometry.loc[idx].distance(g) for g in area_geoms]
            joined.loc[idx, "name"] = areas.iloc[int(np.argmin(dists))]["name"]
    wp = joined.drop(columns=[c for c in ("index_right",) if c in joined.columns])

    # Merge undersized areas into the neighbor holding the most waypoints.
    dissolved = {n: areas[areas["name"] == n].geometry.union_all() for n in wp["name"].unique()}
    counts = wp["name"].value_counts().to_dict()
    while len(counts) > 1:
        small = min(counts, key=counts.get)
        if counts[small] >= cfg.hunt_areas.min_waypoints:
            break
        neighbors = [n for n in counts if n != small and dissolved[n].intersects(dissolved[small].buffer(1e-6))]
        pool = neighbors or [n for n in counts if n != small]
        target = max(pool, key=counts.get)
        wp.loc[wp["name"] == small, "name"] = target
        dissolved[target] = dissolved[target].union(dissolved[small])
        del dissolved[small]
        counts = wp["name"].value_counts().to_dict()

    # Rank by mean waypoint score; cap at max_areas (dropping weakest areas + waypoints).
    means = wp.groupby("name")["score"].mean().sort_values(ascending=False)
    keep = list(means.index[: cfg.hunt_areas.max_areas])
    dropped = set(means.index) - set(keep)
    if dropped:
        n_dropped = int(wp["name"].isin(dropped).sum())
        log.warning("hunt areas: dropping %d weakest area(s) (%s) and their %d waypoints", len(dropped), sorted(dropped), n_dropped)
        wp = wp[~wp["name"].isin(dropped)].copy()

    rank = {name: i + 1 for i, name in enumerate(keep)}
    wp["hunt_area"] = wp["name"].map(lambda n: str(n).title() if str(n) not in ("NW", "NE", "SW", "SE") else str(n))
    wp["area_rank"] = wp["name"].map(rank)
    wp["area_slug"] = wp["hunt_area"].map(_slugify)
    wp = wp.drop(columns=["name"])

    rows = []
    for name in keep:
        sub = wp[wp["area_rank"] == rank[name]]
        rows.append(
            {
                "name": sub["hunt_area"].iloc[0],
                "slug": sub["area_slug"].iloc[0],
                "rank": rank[name],
                "n_waypoints": len(sub),
                "mean_score": round(float(sub["score"].mean()), 3),
                "geometry": dissolved[name],
            }
        )
    return wp, gpd.GeoDataFrame(rows, crs="EPSG:4326")


# -- main --------------------------------------------------------------------

def run_waypoints(ws: Workspace, cfg: Config) -> None:
    grid = Grid.load(ws.grid_json)
    dem, _ = load_dem(ws)
    terrain, _ = load_terrain(ws)
    fx, _ = load_factors(ws)
    comp_bands, type_scores, _ = load_scores(ws)
    composite = comp_bands["composite"]
    canopy_u8 = read_raster(ws.canopy_tif)[0]["canopy"]
    terrain_ev = dict(terrain)
    terrain_ev["canopy"] = np.where(canopy_u8 == 255, np.nan, canopy_u8.astype(np.float32))

    vectors = {
        "water_lines": _read_vec(ws.water_lines_geojson),
        "burns": _read_vec(ws.burns_geojson),
        "ownership": _read_vec(ws.ownership_geojson),
        "huc12": _read_vec(ws.huc12_geojson),
    }
    trailheads = _access_candidates(ws, grid, cfg)

    sel = _Selector(grid, cfg)
    floor = cfg.waypoints.score_floor
    counts = {}
    for wp_type in SELECTION_ORDER:
        if wp_type == "BED":
            counts[wp_type] = _extract_raster_type(sel, "BED", type_scores["BED"], floor)
        elif wp_type == "FEED":
            counts[wp_type] = _extract_raster_type(sel, "FEED", type_scores["FEED"], floor)
        elif wp_type == "WATER":
            near_water = fx["dist_water_m"] <= WATER_MAX_DIST_M
            counts[wp_type] = _extract_raster_type(sel, "WATER", type_scores["WATER"], floor, near_water)
        elif wp_type == "SADDLE":
            counts[wp_type] = _extract_saddles(sel, dem, terrain, type_scores, composite, grid)
        elif wp_type == "GLASS":
            counts[wp_type] = _extract_glass(sel, dem, terrain, type_scores, grid)
        elif wp_type == "CAMP":
            counts[wp_type] = _extract_raster_type(sel, "CAMP", type_scores["CAMP"], floor)
        elif wp_type == "ACCESS":
            counts[wp_type] = _extract_access(sel, trailheads, composite, grid)
    log.info("waypoints extracted: %s", counts)

    if not sel.selected:
        raise RuntimeError(
            "no waypoints extracted — check that scoring produced non-zero scores "
            f"(score floor {floor}) and that the AOI has usable habitat"
        )

    xs = np.array([s["x"] for s in sel.selected])
    ys = np.array([s["y"] for s in sel.selected])
    lons, lats = grid.xy_to_lonlat(xs, ys)
    wp = gpd.GeoDataFrame(
        {
            "wp_type": [s["wp_type"] for s in sel.selected],
            "score": [round(s["score"], 3) for s in sel.selected],
            "row": [s["row"] for s in sel.selected],
            "col": [s["col"] for s in sel.selected],
        },
        geometry=gpd.points_from_xy(lons, lats),
        crs="EPSG:4326",
    )

    areas_src = vectors["huc12"]
    if len(areas_src) and "name" in areas_src.columns:
        # A null/empty-named HUC12 would silently corrupt waypoint names and
        # drop its waypoints from ranked output — let those cells fall to the
        # nearest NAMED area instead.
        named = areas_src["name"].notna() & (areas_src["name"].astype(str).str.strip() != "")
        areas_src = areas_src[named].reset_index(drop=True)
    if len(areas_src) == 0 or "name" not in areas_src.columns:
        log.info("hunt areas: no (named) HUC12 layer; using quadrant fallback")
        areas_src = _quadrant_areas(grid)
    wp, areas = _assign_areas(wp, areas_src, cfg)

    # Names + evidence, per (area, type), ordered by score.
    names: list[str] = []
    descs: list[str] = []
    evs: list[str] = []
    elevs: list[int] = []
    used: set[str] = set()
    wp = wp.sort_values(["area_rank", "wp_type", "score"], ascending=[True, True, False]).reset_index(drop=True)
    seq: dict[tuple[int, str], int] = {}
    for _, row in wp.iterrows():
        ev = evidence.build_evidence(int(row["row"]), int(row["col"]), row["wp_type"], grid, dem, terrain_ev, fx, vectors)
        n = seq.get((row["area_rank"], row["wp_type"]), 0) + 1
        seq[(row["area_rank"], row["wp_type"])] = n
        tag = evidence.short_tag(ev, row["wp_type"])
        elev = ev.get("elevation_ft") or 0
        name = f"{TYPE_CODES[row['wp_type']]}{row['area_rank']}-{n:02d} {tag} {elev}"
        name = name.encode("ascii", "replace").decode("ascii")[:32]
        while name in used:  # collisions only possible after truncation
            n += 1
            name = f"{TYPE_CODES[row['wp_type']]}{row['area_rank']}-{n:02d} {tag}"[:32]
        used.add(name)
        names.append(name)
        descs.append(evidence.render_sentence(ev, row["wp_type"]))
        evs.append(json.dumps(ev))
        elevs.append(int(elev))

    wp["name"] = names
    wp["desc"] = descs
    wp["evidence_json"] = evs
    wp["elevation_ft"] = elevs
    wp = wp.drop(columns=["row", "col"])

    ws.waypoints_geojson.unlink(missing_ok=True)
    wp.to_file(ws.waypoints_geojson, driver="GeoJSON")
    ws.hunt_areas_geojson.unlink(missing_ok=True)
    areas.to_file(ws.hunt_areas_geojson, driver="GeoJSON")
    log.info(
        "wrote %d waypoints across %d hunt areas -> %s",
        len(wp),
        len(areas),
        ws.waypoints_geojson,
    )


def load_waypoints(ws: Workspace) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    wp = gpd.read_file(ws.waypoints_geojson)
    areas = gpd.read_file(ws.hunt_areas_geojson)
    return wp, areas
