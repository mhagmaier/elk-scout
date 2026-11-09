"""Legal access: MVUM vehicle/date windows, dead-end detection, public/unit filter,
and the land-cover picker's lower-48 rules."""

import datetime as dt
import json

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Point

from elkscout.access import build_access_points, legal_routes, open_on, road_ends
from elkscout.config import load_config
from elkscout.grid import Grid, write_raster
from elkscout.paths import Workspace
from elkscout.sources.mvum import mvum_roads_path

HUNT = [dt.date(2026, 11, 18) + dt.timedelta(days=i) for i in range(5)]


@pytest.mark.parametrize(
    ("dates", "day", "expected"),
    [
        ("05/16-03/14", dt.date(2026, 11, 20), True),   # wraps the new year (FR 870 Middle Creek)
        ("05/16-03/14", dt.date(2026, 4, 1), False),
        ("06/16-11/15", dt.date(2026, 11, 18), False),  # closes before the hunt
        ("01/01-12/31", dt.date(2026, 11, 18), True),
        ("06/16-09/30,11/01-11/30", dt.date(2026, 11, 22), True),
        ("", dt.date(2026, 11, 18), False),             # blank = not open (conservative)
        (None, dt.date(2026, 11, 18), False),
        ("garbage", dt.date(2026, 11, 18), False),
    ],
)
def test_open_on(dates, day, expected):
    assert open_on(dates, day) is expected


def _mvum(rows):
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def test_legal_routes_respect_vehicle_class_and_every_hunt_day():
    g = _mvum([
        {"id": "870", "other_ohv_gt50inches": "open", "other_ohv_gt50_datesopen": "05/16-03/14",
         "geometry": LineString([(0, 0), (0, 0.01)])},
        {"id": "880", "other_ohv_gt50inches": "open", "other_ohv_gt50_datesopen": "06/16-11/20",
         "geometry": LineString([(1, 0), (1, 0.01)])},   # closes mid-hunt
        {"id": "999", "other_ohv_gt50inches": None, "other_ohv_gt50_datesopen": None,
         "geometry": LineString([(2, 0), (2, 0.01)])},   # not open to wide OHVs
    ])
    assert list(legal_routes(g, "ohv_gt50", HUNT)["id"]) == ["870"]


def test_legal_routes_missing_fields_returns_empty():
    g = _mvum([{"id": "1", "geometry": LineString([(0, 0), (0, 1)])}])
    assert len(legal_routes(g, "atv", HUNT)) == 0


def test_road_ends_ignore_junctions():
    # A T: route 0 runs north; route 1 branches east from its midpoint.
    routes = gpd.GeoDataFrame(
        geometry=[LineString([(0, 0), (0, 1000)]), LineString([(0, 500), (800, 500)])],
        crs="EPSG:32613",
    )
    ends = sorted((round(p.x), round(p.y)) for p, _ in road_ends(routes))
    # (0,500) is a junction on route 0, so route 1's west end is not a dead end.
    assert ends == [(0, 0), (0, 1000), (800, 500)]


def _seed_factors(ws, grid, public_mask):
    unit = np.zeros(grid.shape, np.float32)
    unit[10:30, 10:30] = 1.0
    bands = {k: np.zeros(grid.shape, np.float32) for k in (
        "dist_motorized_m", "dist_trailhead_m", "dist_water_m", "burn_age_yr", "feed_class",
        "timber", "edge_dist_m", "riparian", "open_water")}
    bands["public"] = public_mask.astype(np.float32)
    bands["unit"] = unit
    write_raster(ws.factors_tif, grid, bands)


def test_build_access_points_keeps_public_and_near_unit(tmp_path):
    ws = Workspace(tmp_path)
    ws.ensure_dirs()
    grid = Grid.from_bounds((400020, 4200000, 401220, 4201200), 30, 32613)  # 40x40 cells
    grid.save(ws.grid_json)
    public = np.ones(grid.shape, bool)
    public[:, :8] = False  # private strip on the west edge
    _seed_factors(ws, grid, public)

    def ll(x, y):
        lon, lat = grid.xy_to_lonlat(np.array([x]), np.array([y]))
        return float(lon[0]), float(lat[0])

    # Dead-end spur ending in the middle of public land; another ending on private.
    spur_pub = LineString([ll(400020 + 15 * 30, 4200600), ll(400020 + 20 * 30, 4200600)])
    spur_pvt = LineString([ll(400020 + 3 * 30, 4200300), ll(400020 + 6 * 30, 4200300)])
    g = _mvum([
        {"id": "870", "name": "MIDDLE CR", "other_ohv_gt50inches": "open",
         "other_ohv_gt50_datesopen": "05/16-03/14", "geometry": spur_pub},
        {"id": "871", "name": "TOWN RD", "other_ohv_gt50inches": "open",
         "other_ohv_gt50_datesopen": "01/01-12/31", "geometry": spur_pvt},
    ])
    g.to_file(mvum_roads_path(ws), driver="GeoJSON")

    cfg = load_config("configs/templates/elk.yaml").model_copy(deep=True)
    cfg.access.vehicle = "ohv_gt50"
    cfg.hunt_window.start, cfg.hunt_window.end = HUNT[0], HUNT[-1]
    out = build_access_points(ws, cfg)
    names = sorted(out["name"])
    # Both ends of the public spur qualify; the private spur's ends are dropped.
    assert names and all("FR 870" in n for n in names)
    assert all(v == "ohv_gt50" for v in out["vehicle"])


def test_landcover_picker_prefers_known_ids_and_rejects_decoys():
    from elkscout.sources import landcover as lc

    decoys = [
        "mrlc_download:NLCD_Land_Cover_Change_Count_L48_2021",
        "mrlc_download:nlcd_tcc_hawaii_2021_v2021-4",
        "mrlc_download:NLCD_2021_Land_Cover_AK",
        "mrlc_download:nlcd_tcc_PR_2021",
    ]
    with_preferred = decoys + ["mrlc_download:NLCD_2021_Land_Cover_L48", "mrlc_download:nlcd_tcc_conus_2021_v2021-4"]
    assert lc.choose_coverage(with_preferred, "landcover", lc._LANDCOVER_RE) == "mrlc_download:NLCD_2021_Land_Cover_L48"
    assert lc.choose_coverage(with_preferred, "canopy", lc._CANOPY_RE) == "mrlc_download:nlcd_tcc_conus_2021_v2021-4"
    newer = decoys + ["mrlc_download:nlcd_tcc_conus_2023_v2023-5", "mrlc_download:NLCD_2024_Land_Cover_L48"]
    assert lc.choose_coverage(newer, "landcover", lc._LANDCOVER_RE) == "mrlc_download:NLCD_2024_Land_Cover_L48"
    assert lc.choose_coverage(newer, "canopy", lc._CANOPY_RE) == "mrlc_download:nlcd_tcc_conus_2023_v2023-5"
    with pytest.raises(RuntimeError):
        lc.choose_coverage(decoys, "canopy", lc._CANOPY_RE)


def test_overpass_has_three_endpoints():
    from elkscout import endpoints

    assert len(endpoints.OVERPASS) >= 3 and any("maps.mail.ru" in u for u in endpoints.OVERPASS)
