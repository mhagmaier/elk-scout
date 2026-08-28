"""Offline tests for terrain derivatives on synthetic analytic surfaces."""

from __future__ import annotations

import math

import numpy as np
import pytest

from elkscout.grid import Grid, write_raster
from elkscout.paths import Workspace
from elkscout.terrain import TERRAIN_BANDS, compute_terrain, load_terrain, run_terrain

RES = 30.0
INTERIOR = (slice(2, -2), slice(2, -2))


@pytest.fixture()
def grid() -> Grid:
    return Grid.from_bounds((0.0, 0.0, 3000.0, 3000.0), RES, 32611)


def coords(grid: Grid) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = grid.cell_centers()
    return np.meshgrid(xs, ys)


def plane(grid: Grid, gx: float, gy: float, z0: float = 1500.0) -> np.ndarray:
    """DEM with constant gradient (gx east, gy north), in meters."""
    x, y = coords(grid)
    return (z0 + gx * x + gy * y).astype(np.float32)


def gaussian(grid: Grid, amp: float, sigma_m: float = 300.0, z0: float = 2000.0) -> np.ndarray:
    """Gaussian bump (amp>0 hill, amp<0 pit) centered on the center cell."""
    x, y = coords(grid)
    cx, cy = grid.xy(grid.height // 2 - 1, grid.width // 2 - 1)
    r2 = (x - cx) ** 2 + (y - cy) ** 2
    return (z0 + amp * np.exp(-r2 / (2.0 * sigma_m**2))).astype(np.float32)


CENTER = (49, 49)  # row, col of the bump peak on the 100x100 grid


@pytest.mark.parametrize(
    ("gx", "gy", "exp_slope_pct", "exp_aspect_deg"),
    [
        (0.10, 0.00, 10.0, 270.0),  # rises east -> downslope due west
        (0.00, 0.20, 20.0, 180.0),  # rises north -> downslope due south
        (0.06, -0.08, 10.0, 323.13),  # downslope vector (-0.06, +0.08), WNW
    ],
)
def test_slope_aspect_tilted_plane(grid, gx, gy, exp_slope_pct, exp_aspect_deg):
    t = compute_terrain(plane(grid, gx, gy), grid)
    assert np.allclose(t["slope_pct"][INTERIOR], exp_slope_pct, atol=0.02)
    assert np.allclose(t["aspect_deg"][INTERIOR], exp_aspect_deg, atol=0.05)


def test_flat_plane_aspect_nan(grid):
    t = compute_terrain(plane(grid, 0.0, 0.0), grid)
    assert np.all(np.isnan(t["aspect_deg"]))
    assert np.allclose(t["slope_pct"], 0.0, atol=1e-4)
    # Flat ground under a 45 deg sun: hillshade = sin(45 deg).
    assert np.allclose(t["hillshade"], math.sin(math.radians(45.0)), atol=1e-3)


def test_tpi_positive_on_hill_negative_in_pit(grid):
    hill = compute_terrain(gaussian(grid, +400.0), grid)
    pit = compute_terrain(gaussian(grid, -400.0), grid)
    for band in ("tpi300", "tpi1000"):
        assert hill[band][CENTER] > 20.0
        assert pit[band][CENTER] < -20.0


def test_slope_pos_bounds_and_extremes(grid):
    hill = compute_terrain(gaussian(grid, +400.0), grid)
    pit = compute_terrain(gaussian(grid, -400.0), grid)
    for t in (hill, pit):
        sp = t["slope_pos"]
        assert np.all(sp >= 0.0) and np.all(sp <= 1.0)
    assert hill["slope_pos"][CENTER] > 0.9  # peak is the local max -> ridge
    assert pit["slope_pos"][CENTER] < 0.1  # pit floor is the local min -> valley


def test_hillshade_range(grid):
    t = compute_terrain(gaussian(grid, +400.0), grid)
    hs = t["hillshade"]
    assert not np.any(np.isnan(hs))
    assert np.all(hs >= 0.0) and np.all(hs <= 1.0)


def test_nan_dem_propagates_to_all_bands(grid):
    dem = plane(grid, 0.10, 0.05)
    dem[10:15, 10:15] = np.nan
    t = compute_terrain(dem, grid)
    assert list(t) == TERRAIN_BANDS
    for name in TERRAIN_BANDS:
        assert np.all(np.isnan(t[name][10:15, 10:15])), name
        assert np.all(np.isfinite(t[name][40:60, 40:60])), name


def test_compute_terrain_shape_mismatch_raises(grid):
    with pytest.raises(ValueError):
        compute_terrain(np.zeros((10, 10), dtype=np.float32), grid)


def test_run_terrain_roundtrip(tmp_path, grid):
    ws = Workspace(tmp_path / "data")
    ws.ensure_dirs()
    dem = gaussian(grid, +400.0)
    write_raster(ws.dem_tif, grid, {"dem": dem})

    run_terrain(ws)

    bands, grid2 = load_terrain(ws)
    assert list(bands) == TERRAIN_BANDS
    assert grid2.shape == grid.shape
    assert grid2.epsg == grid.epsg
    assert tuple(grid2.transform)[:6] == pytest.approx(tuple(grid.transform)[:6])
    expected = compute_terrain(dem, grid)
    for name in TERRAIN_BANDS:
        assert bands[name].dtype == np.float32
        assert np.allclose(bands[name], expected[name], atol=1e-5, equal_nan=True), name
