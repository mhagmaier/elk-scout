"""Measurement rasters (distances, ages, classes, masks) -> work/factors.tif.

scoring.py turns these MEASUREMENTS into [0,1] scores; this module never
applies suitability curves.

Contract — run_factors(ws, cfg): load Grid (ws.grid_json), boundary, vectors,
landcover/canopy, burns; compute the bands below; write ws.factors_tif via
grid.write_raster with EXACTLY these band names (float32; masks as 0/1 floats):

- "dist_motorized_m":  EDT distance (scipy.ndimage.distance_transform_edt,
    sampling=grid.res) to the union of ws.motorized_geojson and
    sources.mvum.mvum_roads_path(ws) lines, rasterized all_touched.
- "dist_trailhead_m":  distance to ws.trailheads_geojson points; if there are
    no trailheads, use motorized-road cells as proxy seeds instead.
- "dist_water_m":      distance to union of water_lines, water_bodies
    (boundaries + interior), springs.
- "burn_age_yr":       hunt-year (cfg.hunt_window.start.year) minus burn year,
    burned cells only; NaN where unburned; where perimeters overlap take the
    YOUNGEST burn (min age).
- "feed_class":        1.0 where NLCD in {52, 71, 90, 95} (shrub/grass/wetland
    meadow), else 0.
- "timber":            1.0 where canopy >= 50 or NLCD in {41, 42, 43}, else 0.
- "edge_dist_m":       distance to the timber/feed interface: cells where a
    timber cell is 8-adjacent to a feed_class or burned (burn_age 2-20) cell;
    distance measured from that interface set.
- "riparian":          1.0 where dist_water_m <= 60 AND slope_pct (from
    terrain.tif) <= 25 — riparian meadow proxy.
- "public":            1.0 public / 0.0 private from ws.ownership_geojson
    `public` column; cells covered by NO ownership polygon default to 1.0
    (documented default; SMA has slivers of no-data on NF land).
- "open_water":        1.0 where NLCD == 11 or inside a waterbody polygon.
- "unit":              1.0 inside the unit boundary polygon (no buffer).

Also loads ws.snow_json only to VALIDATE it exists? No — snow is scoring's
concern; factors ignores it.

Missing optional artifacts (springs, burns, mvum empty) are tolerated: treat as
empty layers. Missing required artifacts (dem/terrain/landcover) -> clear error.

load_factors(ws) -> (dict[str, np.ndarray], Grid).
"""

from __future__ import annotations

import numpy as np

from .config import Config
from .grid import Grid, read_raster
from .paths import Workspace

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


def run_factors(ws: Workspace, cfg: Config) -> None:
    raise NotImplementedError


def load_factors(ws: Workspace) -> tuple[dict[str, np.ndarray], Grid]:
    bands, grid = read_raster(ws.factors_tif)
    return bands, grid
