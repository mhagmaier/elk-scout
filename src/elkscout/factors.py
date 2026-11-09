"""Measurement rasters (distances, ages, classes, masks) -> work/factors.tif.

scoring.py turns these MEASUREMENTS into [0,1] scores; this module never
applies suitability curves.

Bands written (float32, on-grid; masks as 0/1; distances in meters):
  dist_motorized_m   EDT distance to OSM-motorized ∪ MVUM routes
  dist_trailhead_m   EDT distance to trailheads (motorized cells as fallback seeds)
  dist_water_m       EDT distance to perennial lines ∪ waterbodies ∪ springs
  burn_age_yr        hunt year minus burn year; NaN unburned; youngest wins
  feed_class         per-class feed quality in [0,1] from
                     cfg.factors.feed.landcover_scores (default 1.0 for NLCD
                     52 shrub, 71 grass, 90/95 wetland — the original binary)
  timber             canopy >= 50 (valid cells) or NLCD in {41, 42, 43}
  edge_dist_m        distance to the timber/feed(+burn) interface
  riparian           dist_water <= 60 m and slope <= 25 %
  public             ownership `public` column; uncovered cells default public
  open_water         NLCD 11 or inside a waterbody polygon
  unit               inside the unit boundary polygon

Missing optional layers (springs, burns, mvum, trailheads) are treated as
empty; missing required rasters (terrain/landcover) raise a clear error.
Empty feature sets yield a large constant distance (100 km), never NaN.
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
from scipy import ndimage

from .config import Config
from .grid import Grid, read_raster, write_raster
from .paths import Workspace
from .sources.boundary import load_boundary
from .sources.mvum import mvum_roads_path

log = logging.getLogger("elkscout.factors")

FACTOR_BANDS = [
    "dist_motorized_m",
    "dist_trailhead_m",
    "dist_water_m",
    "burn_age_yr",
    "feed_class",
    "timber",
    "edge_dist_m",
    "riparian",
    "public",
    "open_water",
    "unit",
]

FAR_M = 100_000.0
NLCD_OPEN_WATER = (11,)
NLCD_FOREST = (41, 42, 43)
NLCD_FEED = (52, 71, 90, 95)
CANOPY_TIMBER_PCT = 50
RIPARIAN_WATER_M = 60.0
RIPARIAN_MAX_SLOPE_PCT = 25.0
BURN_AGE_RANGE = (2, 20)
NODATA_U8 = 255


def _read_vec(path: Path) -> gpd.GeoDataFrame:
    """Vector artifact -> GeoDataFrame in EPSG:4326; missing/empty file -> empty frame."""
    if not path.exists():
        log.warning("factors: %s missing; treating as empty", path.name)
        return gpd.GeoDataFrame(geometry=gpd.GeoSeries([], dtype="geometry"), crs="EPSG:4326")
    gdf = gpd.read_file(path)
    if len(gdf) and gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf


def _dist_to(mask: np.ndarray, res: float) -> np.ndarray:
    """Meters to the nearest True cell; FAR_M when there are none."""
    if not mask.any():
        return np.full(mask.shape, FAR_M, dtype=np.float32)
    return ndimage.distance_transform_edt(~mask, sampling=res).astype(np.float32)


def _isin(arr: np.ndarray, values: tuple[int, ...]) -> np.ndarray:
    return np.isin(arr, values)


def _landcover_scores(landcover: np.ndarray, scores: dict[int, float]) -> np.ndarray:
    """Per-class feed quality raster in [0,1] from the config's landcover_scores."""
    out = np.zeros(landcover.shape, dtype=np.float32)
    for code, score in scores.items():
        out[landcover == code] = score
    return out


def _burn_age(grid: Grid, burns: gpd.GeoDataFrame, hunt_year: int) -> np.ndarray:
    if len(burns) == 0 or "year" not in burns.columns:
        return np.full(grid.shape, np.nan, dtype=np.float32)
    b = burns.to_crs(epsg=grid.epsg)
    ages = (hunt_year - b["year"].astype(int)).to_numpy()
    order = np.argsort(-ages)  # oldest first; youngest rasterized last wins overlaps
    raster = grid.rasterize(
        b.geometry.to_numpy()[order], values=ages[order].astype(float), fill=0.0, all_touched=True
    )
    return np.where(raster > 0, raster, np.nan).astype(np.float32)


def run_factors(ws: Workspace, cfg: Config) -> None:
    grid = Grid.load(ws.grid_json)
    terrain, _ = read_raster(ws.terrain_tif)
    slope = terrain["slope_pct"]
    landcover = read_raster(ws.landcover_tif)[0]["landcover"]
    canopy = read_raster(ws.canopy_tif)[0]["canopy"]
    res = grid.res

    boundary = load_boundary(ws)
    motorized = _read_vec(ws.motorized_geojson)
    mvum = _read_vec(mvum_roads_path(ws))
    trailheads = _read_vec(ws.trailheads_geojson)
    water_lines = _read_vec(ws.water_lines_geojson)
    water_bodies = _read_vec(ws.water_bodies_geojson)
    springs = _read_vec(ws.springs_geojson)
    ownership = _read_vec(ws.ownership_geojson)
    burns = _read_vec(ws.burns_geojson)

    motorized_mask = (
        grid.rasterize_gdf(motorized, dtype="uint8").astype(bool)
        | grid.rasterize_gdf(mvum, dtype="uint8").astype(bool)
    )
    dist_motorized = _dist_to(motorized_mask, res)

    trailhead_mask = grid.rasterize_gdf(trailheads, dtype="uint8").astype(bool)
    if not trailhead_mask.any():
        log.warning("factors: no trailheads; using motorized cells as pressure seeds")
        trailhead_mask = motorized_mask
    dist_trailhead = _dist_to(trailhead_mask, res)

    waterbody_mask = grid.rasterize_gdf(water_bodies, dtype="uint8").astype(bool)
    water_mask = (
        grid.rasterize_gdf(water_lines, dtype="uint8").astype(bool)
        | waterbody_mask
        | grid.rasterize_gdf(springs, dtype="uint8").astype(bool)
    )
    dist_water = _dist_to(water_mask, res)

    burn_age = _burn_age(grid, burns, cfg.hunt_window.start.year)

    canopy_valid = canopy != NODATA_U8
    feed_class = _landcover_scores(landcover, cfg.factors.feed.landcover_scores)
    timber = (canopy_valid & (canopy >= CANOPY_TIMBER_PCT)) | _isin(landcover, NLCD_FOREST)

    age_filled = np.nan_to_num(burn_age, nan=-1.0)
    burn_feed = (age_filled >= BURN_AGE_RANGE[0]) & (age_filled <= BURN_AGE_RANGE[1])
    feedish = (feed_class > 0) | burn_feed
    interface = timber & ndimage.binary_dilation(feedish, structure=np.ones((3, 3), bool))
    edge_dist = _dist_to(interface, res)

    with np.errstate(invalid="ignore"):
        riparian = (dist_water <= RIPARIAN_WATER_M) & (np.nan_to_num(slope, nan=99.0) <= RIPARIAN_MAX_SLOPE_PCT)

    public = np.ones(grid.shape, dtype=np.float32)
    if len(ownership) and "public" in ownership.columns:
        private = ownership[~ownership["public"].astype(bool)]
        if len(private):
            public -= grid.rasterize_gdf(private, dtype="float32")
            public = np.clip(public, 0.0, 1.0)
    elif len(ownership):
        log.warning("factors: ownership has no `public` column; treating all cells as public")

    open_water = _isin(landcover, NLCD_OPEN_WATER) | waterbody_mask
    unit = grid.rasterize_gdf(boundary, dtype="float32")

    bands = {
        "dist_motorized_m": dist_motorized,
        "dist_trailhead_m": dist_trailhead,
        "dist_water_m": dist_water,
        "burn_age_yr": burn_age,
        "feed_class": feed_class.astype(np.float32),
        "timber": timber.astype(np.float32),
        "edge_dist_m": edge_dist,
        "riparian": riparian.astype(np.float32),
        "public": public,
        "open_water": open_water.astype(np.float32),
        "unit": unit,
    }
    write_raster(ws.factors_tif, grid, {k: bands[k].astype(np.float32) for k in FACTOR_BANDS})
    log.info(
        "factors: wrote %s (unit cells %d, motorized within grid: %s, burned cells %d)",
        ws.factors_tif,
        int(unit.sum()),
        bool(motorized_mask.any()),
        int(np.count_nonzero(~np.isnan(burn_age))),
    )


def load_factors(ws: Workspace) -> tuple[dict[str, np.ndarray], Grid]:
    bands, grid = read_raster(ws.factors_tif)
    return bands, grid
