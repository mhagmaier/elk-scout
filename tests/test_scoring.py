"""Scoring engine on synthetic artifacts, plus curve math."""

import json

import numpy as np
import pytest

from elkscout.config import load_config
from elkscout.curves import apply_curve, aspect_score, shift_curve_x, validate_curve
from elkscout.grid import Grid, write_raster
from elkscout.paths import Workspace
from elkscout.scoring import M_TO_FT, load_scores, run_scoring
from elkscout.terrain import TERRAIN_BANDS

CFG = load_config("configs/unit33_oct_rifle.yaml")


# -- curves ------------------------------------------------------------------

def test_apply_curve_hits_breakpoints_and_clamps():
    pts = [[0, 0.0], [10, 1.0], [20, 0.5]]
    x = np.array([-5, 0, 5, 10, 15, 20, 99], dtype=float)
    out = apply_curve(x, pts)
    assert np.allclose(out, [0.0, 0.0, 0.5, 1.0, 0.75, 0.5, 0.5])


def test_apply_curve_nan_passthrough():
    out = apply_curve(np.array([np.nan, 5.0]), [[0, 0], [10, 1]])
    assert np.isnan(out[0]) and out[1] == pytest.approx(0.5)


def test_validate_curve_rejects_bad_input():
    with pytest.raises(ValueError):
        validate_curve([[0, 0]])
    with pytest.raises(ValueError):
        validate_curve([[5, 0], [5, 1]])


def test_shift_curve_x():
    shifted = shift_curve_x([[100, 0], [200, 1]], -50)
    assert shifted == [(50.0, 0.0), (150.0, 1.0)]


def test_aspect_score_poles():
    out = aspect_score(np.array([22.0, 202.0, np.nan]), 22.0, 1.5)
    assert out[0] == pytest.approx(1.0)
    assert out[1] == pytest.approx(0.0, abs=1e-6)
    assert np.isnan(out[2])


# -- run_scoring on a synthetic workspace ------------------------------------

N = 40  # 40x40 cells at 30 m = 1.2 km square


@pytest.fixture()
def scored_ws(tmp_path):
    ws = Workspace(tmp_path / "data")
    ws.ensure_dirs()
    grid = Grid.from_bounds((600000, 4899990, 600000 + N * 30, 4899990 + N * 30), 30, 32611)
    grid.save(ws.grid_json)

    # DEM: 6000 ft everywhere except a 7000 ft east strip (columns >= 30).
    dem_ft = np.full(grid.shape, 6000.0, dtype=np.float32)
    dem_ft[:, 30:] = 7000.0
    write_raster(ws.dem_tif, grid, {"dem": dem_ft / M_TO_FT})

    terrain = {name: np.zeros(grid.shape, dtype=np.float32) for name in TERRAIN_BANDS}
    terrain["aspect_deg"] = np.full(grid.shape, 22.0, dtype=np.float32)  # ideal bedding aspect
    terrain["slope_pct"] = np.full(grid.shape, 25.0, dtype=np.float32)   # ideal bedding slope
    terrain["slope_pos"] = np.full(grid.shape, 0.8, dtype=np.float32)
    terrain["slope_pct"][0, 0] = 80.0   # cliff cell -> hard-masked
    terrain["slope_pct"][5, 5] = 25.0
    write_raster(ws.terrain_tif, grid, terrain)

    write_raster(ws.canopy_tif, grid, {"canopy": np.full(grid.shape, 70, dtype=np.uint8)}, nodata=255, dtype="uint8")
    write_raster(ws.landcover_tif, grid, {"landcover": np.full(grid.shape, 42, dtype=np.uint8)}, nodata=255, dtype="uint8")

    # Factors: road along column 0; water along row 0; trailhead at (0, 0).
    cols_m = np.tile(np.arange(N, dtype=np.float32) * 30, (N, 1))
    rows_m = np.tile(np.arange(N, dtype=np.float32)[:, None] * 30, (1, N))
    factors = {
        "dist_motorized_m": cols_m,
        "dist_trailhead_m": np.sqrt(cols_m**2 + rows_m**2).astype(np.float32),
        "dist_water_m": rows_m,
        "burn_age_yr": np.full(grid.shape, np.nan, dtype=np.float32),
        "feed_class": np.zeros(grid.shape, dtype=np.float32),
        "timber": np.ones(grid.shape, dtype=np.float32),
        "edge_dist_m": np.full(grid.shape, 1000.0, dtype=np.float32),
        "riparian": np.zeros(grid.shape, dtype=np.float32),
        "public": np.ones(grid.shape, dtype=np.float32),
        "open_water": np.zeros(grid.shape, dtype=np.float32),
        "unit": np.ones(grid.shape, dtype=np.float32),
    }
    factors["public"][10, 10] = 0.0  # private cell -> hard-masked
    factors["burn_age_yr"][20, 20] = 8.0  # prime burn age
    factors["edge_dist_m"][20, 20] = 0.0
    write_raster(ws.factors_tif, grid, factors)
    return ws, grid


def _score_after_snow(ws, snwd_in: float):
    stations = [] if snwd_in == 0 else [{"triplet": "x", "name": "Fake", "elevation_ft": 7000, "snwd_in": snwd_in, "wteq_in": None}]
    xs = [p[0] for p in CFG.snow.band_shift_ft]
    ys = [p[1] for p in CFG.snow.band_shift_ft]
    shift = float(np.interp(snwd_in, xs, ys))
    ws.snow_json.write_text(json.dumps({
        "stations": stations, "median_snwd_in": snwd_in, "band_shift_ft": shift,
        "as_of": "2026-10-01", "no_data": snwd_in == 0,
    }))
    run_scoring(ws, CFG)
    return load_scores(ws)


def test_scoring_end_to_end(scored_ws):
    ws, _ = scored_ws
    comp, types, _ = _score_after_snow(ws, 0.0)

    assert set(comp) == {"composite", "f_elevation", "f_security", "f_bedding", "f_feed", "f_water", "f_pressure", "hard_mask"}
    assert set(types) == {"BED", "FEED", "WATER", "CAMP"}

    c = comp["composite"]
    assert np.nanmin(c) >= 0.0 and np.nanmax(c) <= 1.0
    # Hard mask: cliff and private cells zeroed.
    assert comp["hard_mask"][0, 0] == 0.0 and c[0, 0] == 0.0
    assert comp["hard_mask"][10, 10] == 0.0 and c[10, 10] == 0.0
    # Security: 0 on the road column; column 39 is 1,170 m out — on the
    # 0.8->1.2 km ramp, linearly interpolated to 0.9625.
    assert comp["f_security"][5, 0] == pytest.approx(0.0)
    assert comp["f_security"][5, 39] == pytest.approx(0.9625, abs=1e-4)
    # Elevation with no snow: 6000 ft cells score 1.0.
    assert comp["f_elevation"][5, 5] == pytest.approx(1.0)
    # Burned edge cell feeds better than sterile timber.
    assert comp["f_feed"][20, 20] > comp["f_feed"][20, 25]
    # CAMP zero where slope > camp limit (whole synthetic slope is 25%).
    assert types["CAMP"].max() == 0.0


def test_snow_shifts_elevation_band(scored_ws):
    ws, _ = scored_ws
    comp0, _, _ = _score_after_snow(ws, 0.0)
    comp12, _, _ = _score_after_snow(ws, 12.0)  # -900 ft shift
    # 7000 ft strip: fine at 0 snow (inside 6000-8200 optimum), still fine at -900 (5100-7300).
    assert comp0["f_elevation"][5, 35] == pytest.approx(1.0)
    assert comp12["f_elevation"][5, 35] == pytest.approx(1.0)
    # 6000 ft cells: optimal with no snow; after -900 ft the optimum band's top
    # falls to 7300 and the low knee to 5100, so 6000 stays 1.0 — but the curve's
    # first breakpoints also fall, so a 5100 ft cell would now score 1.0. Verify
    # the shift direction using the curve directly at the shifted knee.
    from elkscout.curves import apply_curve, shift_curve_x
    curve12 = shift_curve_x(CFG.factors.elevation.curve_elevation_ft, -900)
    assert float(apply_curve(np.array([5100.0]), curve12)[0]) == pytest.approx(1.0)
    assert float(apply_curve(np.array([5100.0]), CFG.factors.elevation.curve_elevation_ft)[0]) < 0.5


def test_late_season_bedding_switch_is_snow_gated(scored_ws):
    """South-slope thermal bedding applies only once snow reaches the elk band."""
    ws, _ = scored_ws
    cfg = CFG.model_copy(deep=True)
    cfg.factors.bedding.snow_aspect_center_deg = 180.0  # synthetic terrain faces NNE (22 deg)

    def run(in_band: bool):
        ws.snow_json.write_text(json.dumps({
            "stations": [], "median_snwd_in": 0.0, "band_shift_ft": 0.0,
            "snow_in_band": in_band, "as_of": "2026-11-10", "no_data": False,
        }))
        run_scoring(ws, cfg)
        return load_scores(ws)[0]["f_bedding"][5, 5]

    no_snow = run(False)
    snowed = run(True)
    assert no_snow > snowed  # NNE dark-timber beds win until snow arrives
