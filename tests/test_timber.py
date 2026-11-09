"""Security timber: thresholds, block detection, dead-timber removal, timber-aware ranking."""

import json

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point, box

from elkscout.config import load_config
from elkscout.grid import Grid, write_raster
from elkscout.paths import Workspace
from elkscout.terrain import TERRAIN_BANDS
from elkscout.timber import block_mask, dark_canopy_threshold, load_blocks, run_timber
from elkscout.waypoints import _assign_areas, area_timber_acres

CFG = load_config("configs/templates/elk.yaml")
N = 80  # 80x80 at 30 m = 2.4 km


def _grid():
    return Grid.from_bounds((400020, 4200000, 400020 + N * 30, 4200000 + N * 30), 30, 32613)


def test_threshold_auto_fixed_and_floor():
    can = np.array([[20, 30, 40, 50, 60, 70, 80, 90]], dtype=np.uint8)
    conifer = np.ones_like(can, dtype=bool)
    thr, auto = dark_canopy_threshold(can, conifer, CFG)
    assert auto and thr == pytest.approx(np.percentile(can, 75))
    fixed = CFG.model_copy(deep=True)
    fixed.timber.dark_canopy_pct = 60
    assert dark_canopy_threshold(can, conifer, fixed) == (60.0, False)
    low = np.full((1, 8), 20, dtype=np.uint8)
    assert dark_canopy_threshold(low, conifer, CFG)[0] == CFG.timber.min_dark_canopy_pct


@pytest.fixture()
def timber_ws(tmp_path):
    """Two dark-conifer patches: a big one far from the road (east), a small one."""
    ws = Workspace(tmp_path)
    ws.ensure_dirs()
    grid = _grid()
    grid.save(ws.grid_json)
    cols = np.arange(N)[None, :].repeat(N, axis=0)
    lc = np.full(grid.shape, 71, np.uint8)  # meadow
    can = np.full(grid.shape, 5, np.uint8)
    lc[10:70, 45:75] = 42
    can[10:70, 45:75] = 70          # big dark block: 60x30 cells = 400 ac
    lc[5:12, 20:27] = 42
    can[5:12, 20:27] = 70           # small 49 cells = 11 ac (below 100 ac)
    lc[40:60, 5:30] = 42
    can[40:60, 5:30] = 30           # thin conifer: sets the low quartile
    write_raster(ws.landcover_tif, grid, {"landcover": lc}, nodata=255, dtype="uint8")
    write_raster(ws.canopy_tif, grid, {"canopy": can}, nodata=255, dtype="uint8")
    write_raster(ws.dem_tif, grid, {"dem": np.full(grid.shape, 3000.0, np.float32)})
    terrain = {b: np.zeros(grid.shape, np.float32) for b in TERRAIN_BANDS}
    terrain["aspect_deg"] = np.full(grid.shape, 10.0, np.float32)
    write_raster(ws.terrain_tif, grid, terrain)
    factors = {k: np.zeros(grid.shape, np.float32) for k in (
        "dist_trailhead_m", "dist_water_m", "burn_age_yr", "feed_class",
        "timber", "edge_dist_m", "riparian", "open_water")}
    factors["dist_motorized_m"] = (cols * 30.0).astype(np.float32)  # road along column 0
    factors["public"] = np.ones(grid.shape, np.float32)
    factors["unit"] = np.ones(grid.shape, np.float32)
    write_raster(ws.factors_tif, grid, factors)
    return ws, grid


def test_run_timber_finds_big_secure_block_only(timber_ws):
    ws, grid = timber_ws
    blocks = run_timber(ws, CFG)
    assert len(blocks) == 1
    b = blocks.iloc[0]
    assert b["id"] == "T01"
    assert 380 <= b["acres"] <= 420
    assert b["north_share"] == 1.0
    assert b["road_mi_median"] > 0.5
    stats = json.loads(ws.timber_json.read_text())
    assert stats["n_blocks"] == 1 and stats["dark_canopy_auto"] is True
    assert block_mask(ws, grid).sum() > 0
    assert len(load_blocks(ws)) == 1


def test_private_land_excluded(timber_ws):
    ws, grid = timber_ws
    from elkscout.grid import read_raster

    fx, _ = read_raster(ws.factors_tif)
    fx["public"][:, 45:75] = 0.0  # the big block is private
    write_raster(ws.factors_tif, grid, fx)
    assert len(run_timber(ws, CFG)) == 0


def test_dead_timber_removed_before_blocks(timber_ws):
    """Sentinel-2 'dead' cells (beetle kill NLCD still maps as dense) break up blocks."""
    ws, grid = timber_ws
    dead = np.zeros(grid.shape, np.float32)
    dead[10:70, 45:75] = 1.0
    write_raster(ws.sentinel_tif, grid, {"snow_now": np.zeros(grid.shape, np.float32),
                                         "ndvi_now": np.zeros(grid.shape, np.float32),
                                         "dndvi": np.zeros(grid.shape, np.float32),
                                         "dead": dead})
    assert len(run_timber(ws, CFG)) == 0
    assert json.loads(ws.timber_json.read_text())["dead_conifer_acres_removed"] > 300


def test_area_ranking_rewards_nearby_security_timber():
    """The 68/681 failure: a high-score area with no timber outranked the timber country."""
    epsg = 32613
    pts = []
    for i in range(6):  # open area: higher scores, no timber
        pts.append({"wp_type": "BED", "score": 0.91, "geometry": Point(400000 + i * 100, 4200000)})
    for i in range(6):  # timber area: slightly lower scores, a 4,600 ac block nearby
        pts.append({"wp_type": "BED", "score": 0.85, "geometry": Point(430000 + i * 100, 4200000)})
    wp = gpd.GeoDataFrame(pts, crs=f"EPSG:{epsg}").to_crs(4326)
    areas = gpd.GeoDataFrame(
        {"name": ["Open", "Timber"]},
        geometry=[box(399000, 4199000, 402000, 4201000), box(429000, 4199000, 432000, 4201000)],
        crs=f"EPSG:{epsg}",
    ).to_crs(4326)
    blocks = gpd.GeoDataFrame(
        {"id": ["T01"], "acres": [4646]}, geometry=[box(430500, 4201000, 433000, 4203000)], crs=f"EPSG:{epsg}"
    ).to_crs(4326)

    labeled = gpd.sjoin(wp, areas[["name", "geometry"]], how="left", predicate="within").drop(columns="index_right")
    acres = area_timber_acres(labeled, blocks, 3.0, epsg)
    assert acres == {"Open": 0, "Timber": 4646}

    _, ranked = _assign_areas(wp.copy(), areas, CFG, blocks, epsg)
    order = list(ranked.sort_values("rank")["name"])
    assert order == ["Timber", "Open"]
    assert int(ranked.set_index("name").loc["Timber", "timber_acres"]) == 4646

    _, no_timber = _assign_areas(wp.copy(), areas, CFG, None, epsg)
    assert list(no_timber.sort_values("rank")["name"]) == ["Open", "Timber"]  # old behavior without blocks
