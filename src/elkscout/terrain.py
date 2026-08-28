"""Terrain derivatives from the on-grid DEM -> work/terrain.tif.

Contract — run_terrain(ws): load dem via sources.dem.load_dem, compute the six
bands below with compute_terrain, write ws.terrain_tif via grid.write_raster
(band names exactly as listed), float32, NaN nodata.

compute_terrain(dem, grid) -> dict with keys:
- "slope_pct":  Horn's 3x3 method on the on-grid DEM, 100 * tan(slope_angle).
                NaN where dem NaN.
- "aspect_deg": downslope azimuth, 0=N, 90=E, clockwise; NaN where dem NaN or
                slope < 1% (flat — callers treat as neutral).
- "tpi300":     dem - mean(dem within 300 m radius disk), NaN-safe via the
                masked-mean trick (filter(dem*mask)/filter(mask)).
- "tpi1000":    same at 1000 m radius.
- "slope_pos":  (dem - local_min) / (local_max - local_min) within a 1000 m
                radius square window, in [0,1]; 0.5 where degenerate.
- "hillshade":  standard 315 deg azimuth / 45 deg altitude, in [0,1].

load_terrain(ws) -> (dict[str, np.ndarray], Grid) via grid.read_raster.
Pure numpy/scipy — no GDAL DEM utilities.
"""

from __future__ import annotations

import logging

import numpy as np
from scipy import ndimage
from scipy.signal import fftconvolve

from .grid import Grid, read_raster, write_raster
from .paths import Workspace

log = logging.getLogger("elkscout.terrain")

TERRAIN_BANDS = ["slope_pct", "aspect_deg", "tpi300", "tpi1000", "slope_pos", "hillshade"]

TPI_SMALL_RADIUS_M = 300.0
TPI_LARGE_RADIUS_M = 1000.0
SLOPE_POS_RADIUS_M = 1000.0
FLAT_SLOPE_PCT = 1.0  # below this, aspect is meaningless -> NaN
SUN_AZIMUTH_DEG = 315.0
SUN_ALTITUDE_DEG = 45.0

# Horn (1981) 3x3 weights for use with ndimage.correlate (no kernel flip):
# east-positive dz/dx and, with row 0 at the northern edge, north-positive dz/dy.
_HORN_X = np.array([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]])
_HORN_Y = np.array([[1.0, 2.0, 1.0], [0.0, 0.0, 0.0], [-1.0, -2.0, -1.0]])


def _radius_cells(radius_m: float, res_m: float) -> int:
    return max(1, int(round(radius_m / res_m)))


def _disk_kernel(radius_m: float, res_m: float) -> np.ndarray:
    r = _radius_cells(radius_m, res_m)
    yy, xx = np.ogrid[-r : r + 1, -r : r + 1]
    return (xx * xx + yy * yy <= r * r).astype(np.float64)


def _horn_gradients(dem: np.ndarray, res_m: float) -> tuple[np.ndarray, np.ndarray]:
    """(dz/dx east-positive, dz/dy north-positive); NaN spreads one cell."""
    dzdx = ndimage.correlate(dem, _HORN_X / (8.0 * res_m), mode="nearest")
    dzdy = ndimage.correlate(dem, _HORN_Y / (8.0 * res_m), mode="nearest")
    return dzdx, dzdy


def _nan_mean_filter(dem: np.ndarray, valid: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Mean of valid dem cells under the kernel footprint (masked-mean trick)."""
    filled = np.where(valid, dem, 0.0)
    num = fftconvolve(filled, kernel, mode="same")
    cnt = fftconvolve(valid.astype(np.float64), kernel, mode="same")
    # Every valid cell has itself in the footprint, so cnt >= 1 wherever it matters;
    # the floor only guards FFT round-off in all-NaN regions.
    return num / np.maximum(cnt, 1e-9)


def _slope_position(dem: np.ndarray, valid: np.ndarray, radius_m: float, res_m: float) -> np.ndarray:
    """Relative height within the local min/max window: 0=valley .. 1=ridge."""
    size = 2 * _radius_cells(radius_m, res_m) + 1
    lmin = ndimage.minimum_filter(np.where(valid, dem, np.inf), size=size, mode="nearest")
    lmax = ndimage.maximum_filter(np.where(valid, dem, -np.inf), size=size, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = (dem - lmin) / (lmax - lmin)
    # Degenerate windows (flat, or no other valid cell) yield non-finite -> neutral.
    return np.where(np.isfinite(pos), np.clip(pos, 0.0, 1.0), 0.5)


def _hillshade(dzdx: np.ndarray, dzdy: np.ndarray) -> np.ndarray:
    """Dot product of the surface normal with the sun vector, clipped to [0,1]."""
    az = np.deg2rad(SUN_AZIMUTH_DEG)
    alt = np.deg2rad(SUN_ALTITUDE_DEG)
    sun_e = np.sin(az) * np.cos(alt)
    sun_n = np.cos(az) * np.cos(alt)
    sun_z = np.sin(alt)
    shade = (sun_z - dzdx * sun_e - dzdy * sun_n) / np.sqrt(1.0 + dzdx * dzdx + dzdy * dzdy)
    return np.clip(shade, 0.0, 1.0)


def compute_terrain(dem: np.ndarray, grid: Grid) -> dict[str, np.ndarray]:
    if dem.shape != grid.shape:
        raise ValueError(f"dem shape {dem.shape} != grid shape {grid.shape}")
    dem64 = np.asarray(dem, dtype=np.float64)
    valid = np.isfinite(dem64)
    res = grid.res

    dzdx, dzdy = _horn_gradients(dem64, res)
    with np.errstate(invalid="ignore"):
        slope_pct = 100.0 * np.hypot(dzdx, dzdy)
        aspect_deg = np.degrees(np.arctan2(-dzdx, -dzdy)) % 360.0
    # NaN slope compares False, so this also NaNs aspect near missing dem.
    aspect_deg = np.where(slope_pct >= FLAT_SLOPE_PCT, aspect_deg, np.nan)

    bands = {
        "slope_pct": slope_pct,
        "aspect_deg": aspect_deg,
        "tpi300": dem64 - _nan_mean_filter(dem64, valid, _disk_kernel(TPI_SMALL_RADIUS_M, res)),
        "tpi1000": dem64 - _nan_mean_filter(dem64, valid, _disk_kernel(TPI_LARGE_RADIUS_M, res)),
        "slope_pos": _slope_position(dem64, valid, SLOPE_POS_RADIUS_M, res),
        "hillshade": _hillshade(dzdx, dzdy),
    }
    return {name: np.where(valid, bands[name], np.nan).astype(np.float32) for name in TERRAIN_BANDS}


def run_terrain(ws: Workspace) -> None:
    from .sources.dem import load_dem  # deferred: sources package needs no import at terrain import time

    dem, grid = load_dem(ws)
    log.info(
        "terrain: DEM %dx%d at %.0f m, %.1f%% valid",
        grid.width,
        grid.height,
        grid.res,
        100.0 * np.count_nonzero(np.isfinite(dem)) / dem.size,
    )
    bands = compute_terrain(dem, grid)
    write_raster(ws.terrain_tif, grid, bands)
    log.info("terrain: wrote %s (%d bands)", ws.terrain_tif, len(bands))


def load_terrain(ws: Workspace) -> tuple[dict[str, np.ndarray], "Grid"]:
    bands, grid = read_raster(ws.terrain_tif)
    return bands, grid
