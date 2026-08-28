"""Terrain derivatives from the on-grid DEM -> work/terrain.tif.

Contract — run_terrain(ws): load dem via sources.dem.load_dem, compute the six
bands below with compute_terrain, write ws.terrain_tif via grid.write_raster
(band names exactly as listed), float32, NaN nodata.

compute_terrain(dem, grid) -> dict with keys:
- "slope_pct":  Horn's method on the 30 m DEM (np.gradient or 3x3 kernels),
                100 * tan(slope_angle). NaN where dem NaN.
- "aspect_deg": downslope azimuth, 0=N, 90=E, clockwise; NaN where dem NaN or
                slope < 1% (flat — callers treat as neutral).
- "tpi300":     dem - mean(dem within 300 m radius disk); use
                scipy.ndimage.uniform_filter or convolve with a disk kernel;
                handle NaN via the standard masked-mean trick
                (filter(dem*mask)/filter(mask)).
- "tpi1000":    same at 1000 m radius.
- "slope_pos":  (dem - local_min) / (local_max - local_min) within a 1000 m
                window (scipy.ndimage minimum_filter/maximum_filter, disk or
                square footprint), in [0,1]; 0.5 where degenerate.
- "hillshade":  standard 315 deg azimuth / 45 deg altitude, in [0,1].

load_terrain(ws) -> (dict[str, np.ndarray], Grid) via grid.read_raster.
Pure numpy/scipy — no GDAL DEM utilities.
"""

from __future__ import annotations

import numpy as np

from .grid import Grid, read_raster
from .paths import Workspace

TERRAIN_BANDS = ["slope_pct", "aspect_deg", "tpi300", "tpi1000", "slope_pos", "hillshade"]


def compute_terrain(dem: np.ndarray, grid: Grid) -> dict[str, np.ndarray]:
    raise NotImplementedError


def run_terrain(ws: Workspace) -> None:
    raise NotImplementedError


def load_terrain(ws: Workspace) -> tuple[dict[str, np.ndarray], "Grid"]:
    bands, grid = read_raster(ws.terrain_tif)
    return bands, grid
