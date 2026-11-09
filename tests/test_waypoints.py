"""Waypoint extraction (NMS properties, end-to-end) and evidence rendering."""

import json
import math

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Point

from elkscout.config import load_config
from elkscout.evidence import render_sentence, short_tag
from elkscout.grid import Grid, write_raster
from elkscout.paths import Workspace
from elkscout.scoring import M_TO_FT, run_scoring
from elkscout.terrain import TERRAIN_BANDS
from elkscout.waypoints import _Selector, _extract_raster_type, load_waypoints, run_waypoints

CFG = load_config("configs/unit33_oct_rifle.yaml")
N = 80  # 80x80 at 30 m = 2.4 km square


def _grid():
    return Grid.from_bounds((600000, 4899990, 600000 + N * 30, 4899990 + N * 30), 30, 32611)


# -- NMS properties ----------------------------------------------------------

def test_nms_enforces_spacing_and_counts():
    grid = _grid()
    rng = np.random.default_rng(7)
    band = rng.uniform(0.5, 1.0, size=grid.shape).astype(np.float32)  # everything above floor
    sel = _Selector(grid, CFG)
    added = _extract_raster_type(sel, "BED", band, CFG.waypoints.score_floor)
    assert 0 < added <= CFG.waypoints.counts["BED"]
    pts = [(s["x"], s["y"]) for s in sel.selected]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
            assert d >= CFG.waypoints.min_spacing_m


def test_nms_cross_type_spacing():
    grid = _grid()
    band = np.full(grid.shape, 0.9, dtype=np.float32)
    sel = _Selector(grid, CFG)
    _extract_raster_type(sel, "BED", band, 0.5)
    _extract_raster_type(sel, "FEED", band, 0.5)
    for a in sel.selected:
        for b in sel.selected:
            if a is b:
                continue
            d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            limit = CFG.waypoints.min_spacing_m if a["wp_type"] == b["wp_type"] else CFG.waypoints.cross_type_spacing_m
            assert d >= limit


# -- evidence rendering ------------------------------------------------------

def _ev(**overrides):
    base = {
        "elevation_ft": 7410, "aspect_deg": 15.0, "aspect_compass": "N",
        "slope_pct": 24, "tpi_class": "bench", "canopy_pct": 62,
        "dist_motorized_mi": 1.8, "dist_trailhead_mi": 2.4, "dist_water_mi": 0.4,
        "burn_name": None, "burn_year": None, "nearest_water_name": None,
        "agency": "USFS", "huc12_name": None, "lon": -115.6, "lat": 44.1,
    }
    base.update(overrides)
    return base


def test_render_sentence_full_clauses():
    s = render_sentence(_ev(), "BED")
    assert "North-facing bench at 7,410 ft" in s
    assert "62% canopy" in s and "24% slope" in s
    assert "1.8 mi from the nearest motorized route" in s
    assert "0.40 mi to water" in s
    assert s.isascii()


def test_render_sentence_burn_and_named_water():
    s = render_sentence(_ev(burn_name="Pioneer", burn_year=2016, nearest_water_name="Fixture Creek"), "FEED")
    assert "2016 Pioneer burn" in s
    assert "Fixture Creek" in s


def test_render_sentence_feed_aspect_reads_mid_sentence():
    assert render_sentence(_ev(aspect_compass="E", tpi_class="slope"), "FEED").startswith("Feed on an east-facing slope at 7,410 ft")
    assert render_sentence(_ev(aspect_compass="SE", tpi_class="knob"), "FEED").startswith("Feed on a southeast-facing knob")
    assert render_sentence(_ev(aspect_compass=None, tpi_class="flat"), "FEED").startswith("Feed on a flat at 7,410 ft")
    assert render_sentence(_ev(aspect_compass="E"), "BED").startswith("East-facing bench")


def test_render_sentence_omits_none_clauses():
    s = render_sentence(_ev(canopy_pct=None, aspect_compass=None), "BED")
    assert "canopy" not in s
    assert s.startswith("Bench at 7,410 ft")


def test_short_tag_shapes():
    assert short_tag(_ev(), "BED") == "N-bench"
    assert short_tag(_ev(burn_year=2016), "FEED") == "burn-edge"
    assert short_tag(_ev(), "SADDLE") == "saddle"
    assert len(short_tag(_ev(aspect_compass="NW", tpi_class="slope"), "BED")) <= 10


# -- end-to-end with quadrant fallback ---------------------------------------

@pytest.fixture()
def full_ws(tmp_path):
    """Synthetic 2.4 km AOI: ridge down the middle, road west, creek east."""
    ws = Workspace(tmp_path / "data")
    ws.ensure_dirs()
    grid = _grid()
    grid.save(ws.grid_json)

    cols = np.arange(N, dtype=np.float32)[None, :].repeat(N, axis=0)
    rows = np.arange(N, dtype=np.float32)[:, None].repeat(N, axis=1)

    # Elevation: 6,200 ft valley floor rising to 7,600 ft ridge at the center column.
    ridge = 1.0 - np.abs(cols - N / 2) / (N / 2)
    dem_ft = 6200 + 1400 * ridge
    write_raster(ws.dem_tif, grid, {"dem": (dem_ft / M_TO_FT).astype(np.float32)})

    terrain = {name: np.zeros(grid.shape, dtype=np.float32) for name in TERRAIN_BANDS}
    terrain["aspect_deg"] = np.where(cols < N / 2, 90.0, 270.0).astype(np.float32)
    terrain["aspect_deg"][rows < N / 4] = 22.0
    terrain["slope_pct"] = np.full(grid.shape, 25.0, dtype=np.float32)
    terrain["slope_pos"] = np.clip(ridge + 0.2, 0, 1).astype(np.float32)
    terrain["tpi300"] = np.zeros(grid.shape, dtype=np.float32)
    terrain["tpi1000"] = (60 * (ridge - 0.5)).astype(np.float32)  # + on ridge, - in valleys
    write_raster(ws.terrain_tif, grid, terrain)

    write_raster(ws.canopy_tif, grid, {"canopy": np.full(grid.shape, 65, dtype=np.uint8)}, nodata=255, dtype="uint8")
    lc = np.full(grid.shape, 42, dtype=np.uint8)
    lc[:, 60:] = 71  # east meadow strip
    write_raster(ws.landcover_tif, grid, {"landcover": lc}, nodata=255, dtype="uint8")

    dist_road = (cols * 30).astype(np.float32)  # road at column 0
    dist_water = (np.abs(cols - 70) * 30).astype(np.float32)  # creek at column 70
    factors = {
        "dist_motorized_m": dist_road,
        "dist_trailhead_m": np.sqrt((cols * 30) ** 2 + (rows * 30) ** 2).astype(np.float32),
        "dist_water_m": dist_water,
        "burn_age_yr": np.full(grid.shape, np.nan, dtype=np.float32),
        "feed_class": (lc == 71).astype(np.float32),
        "timber": (lc == 42).astype(np.float32),
        "edge_dist_m": (np.abs(cols - 60) * 30).astype(np.float32),
        "riparian": np.zeros(grid.shape, dtype=np.float32),
        "public": np.ones(grid.shape, dtype=np.float32),
        "open_water": np.zeros(grid.shape, dtype=np.float32),
        "unit": np.ones(grid.shape, dtype=np.float32),
    }
    write_raster(ws.factors_tif, grid, factors)

    ws.snow_json.write_text(json.dumps({
        "stations": [], "median_snwd_in": 0.0, "band_shift_ft": 0.0,
        "as_of": "2026-10-01", "no_data": True,
    }))

    # Vectors: named creek, empty huc12 (quadrant fallback), a trailhead, no burns/private.
    creek_x = 600000 + 70 * 30
    creek = gpd.GeoDataFrame(
        {"GNIS_NAME": ["Fixture Creek"]},
        geometry=[LineString([grid.xy_to_lonlat(creek_x, 4899990 + 10), grid.xy_to_lonlat(creek_x, 4899990 + N * 30 - 10)])],
        crs="EPSG:4326",
    )
    creek.to_file(ws.water_lines_geojson, driver="GeoJSON")
    for p in (ws.water_bodies_geojson, ws.springs_geojson, ws.burns_geojson, ws.ownership_geojson, ws.huc12_geojson):
        p.write_text('{"type": "FeatureCollection", "features": []}')
    th_lonlat = grid.xy_to_lonlat(600000 + 15, 4899990 + 15)
    gpd.GeoDataFrame({"name": ["TH"]}, geometry=[Point(*th_lonlat)], crs="EPSG:4326").to_file(
        ws.trailheads_geojson, driver="GeoJSON"
    )
    gpd.GeoDataFrame({"unit": ["33"]}, geometry=[gpd.GeoSeries([Point(0, 0)]).buffer(0).iloc[0]], crs="EPSG:4326")
    # boundary: full AOI rectangle
    from shapely.geometry import box as _box
    minlon, minlat, maxlon, maxlat = grid.bbox4326()
    gpd.GeoDataFrame({"unit": ["33"]}, geometry=[_box(minlon, minlat, maxlon, maxlat)], crs="EPSG:4326").to_file(
        ws.boundary_geojson, driver="GeoJSON"
    )
    return ws


def test_run_waypoints_end_to_end(full_ws):
    ws = full_ws
    run_scoring(ws, CFG)
    run_waypoints(ws, CFG)
    wp, areas = load_waypoints(ws)

    assert len(wp) >= 5
    assert set(wp["wp_type"]).issuperset({"BED", "FEED"})
    # Quadrant fallback names.
    assert set(areas["name"]).issubset({"NW", "NE", "SW", "SE"})
    # Names: ASCII, <= 32 chars, unique; scores recorded; evidence parses.
    assert wp["name"].str.len().max() <= 32
    assert wp["name"].is_unique
    assert wp["name"].map(str.isascii).all()
    assert (wp["score"] >= 0).all()
    raw_ev = wp.iloc[0]["evidence_json"]
    ev = raw_ev if isinstance(raw_ev, dict) else json.loads(raw_ev)  # GeoJSON driver may parse JSON strings
    assert "elevation_ft" in ev and ev["elevation_ft"] > 5000
    # Security floor: nothing within 400 m of the road column.
    for _, row in wp.iterrows():
        if row["wp_type"] in ("BED", "FEED"):
            lon = row.geometry.x
            assert lon > grid_lon_at_col_min()


def grid_lon_at_col_min():
    grid = _grid()
    lon, _ = grid.xy_to_lonlat(600000 + 400.0, 4899990 + 40 * 30)
    return lon
