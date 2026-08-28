"""Procedural fixture generator: a plausible mountain AOI as manual drop-ins.

make_fixtures(out_dir) writes a complete data/manual/-shaped directory
satisfying every manual key except 'boundary' (tests use --aoi-bbox synth
boundaries). The terrain is deterministic (seeded) and the vectors are derived
from the same analytic terrain functions, so roads follow valleys and creeks
run where water would actually run.

Geography: real Unit 33 country near Deadwood Reservoir, ~8 x 8 km.
North-south valleys every VALLEY_WAVE_M meters; ridges between them.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio.warp
from rasterio.crs import CRS
from shapely.geometry import LineString, Point, Polygon, box

from .config import load_config
from .grid import Grid, write_raster
from .paths import _MANUAL_FILES
from .sources.weather import CLIMATOLOGY_NOTE

AOI_BBOX = (-115.72, 44.10, -115.62, 44.17)  # lon/lat, ~8 x 7.8 km
_EPSG = 32611
_RES = 30.0
_PAD_M = 2500.0  # beyond the AOI so the buffered scoring grid is covered
VALLEY_WAVE_M = 4000.0
_SNWD_IN = 4.0
# Repo-anchored: testkit is a dev tool that lives alongside configs/.
_PROFILE = Path(__file__).resolve().parents[2] / "configs" / "unit33_oct_rifle.yaml"


def _utm_bounds() -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = rasterio.warp.transform_bounds(
        CRS.from_epsg(4326), CRS.from_epsg(_EPSG), *AOI_BBOX
    )
    return (minx - _PAD_M, miny - _PAD_M, maxx + _PAD_M, maxy + _PAD_M)


def _terrain_m(x: np.ndarray, y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Elevation in meters at UTM coords; ridges between N-S valleys, rising north."""
    b = _utm_bounds()
    xr = x - b[0]
    yr = y - b[1]
    ridge = 0.5 * (1.0 - np.cos(2.0 * np.pi * xr / VALLEY_WAVE_M))  # 0 valley, 1 ridge
    p1, p2 = rng.uniform(0, 2 * np.pi, 2)
    rough = 40.0 * np.sin(xr / 700.0 + p1) * np.cos(yr / 900.0 + p2)
    return 1800.0 + 450.0 * ridge + 0.02 * yr + rough


def _valley_xs(bounds) -> list[float]:
    """UTM x of each valley centerline inside the padded bounds."""
    xs = []
    k = 0
    while True:
        x = bounds[0] + k * VALLEY_WAVE_M
        if x > bounds[2]:
            break
        if bounds[0] + 200 < x < bounds[2] - 200:
            xs.append(x)
        k += 1
    return xs


def _to_lonlat(xs, ys):
    return rasterio.warp.transform(CRS.from_epsg(_EPSG), CRS.from_epsg(4326), list(xs), list(ys))


def _line_lonlat(xs, ys) -> LineString:
    lons, lats = _to_lonlat(xs, ys)
    return LineString(list(zip(lons, lats)))


def make_fixtures(out_dir: Path, seed: int = 42) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    bounds = _utm_bounds()
    grid = Grid.from_bounds(bounds, _RES, _EPSG)
    xs, ys = grid.cell_centers()
    X, Y = np.meshgrid(xs, ys)
    dem = _terrain_m(X, Y, rng).astype(np.float32)
    write_raster(out / _MANUAL_FILES["dem"], grid, {"dem": dem})

    valleys = _valley_xs(bounds)
    dist_valley = np.min(np.stack([np.abs(X - vx) for vx in valleys]), axis=0)
    ridge_x = valleys[0] + VALLEY_WAVE_M / 2 if valleys else (bounds[0] + bounds[2]) / 2

    # Burn scar: NE block between the first valley and the ridge east of it.
    burn_poly_utm = Polygon(
        [
            (valleys[0] + 300, bounds[3] - 4200),
            (valleys[0] + 2600, bounds[3] - 4200),
            (valleys[0] + 2600, bounds[3] - 900),
            (valleys[0] + 300, bounds[3] - 900),
        ]
    )
    in_burn = np.zeros(grid.shape, bool)
    bx0, by0, bx1, by1 = burn_poly_utm.bounds
    in_burn[(X >= bx0) & (X <= bx1) & (Y >= by0) & (Y <= by1)] = True

    # Landcover: valley-bottom grass, burn shrub, conifer elsewhere; a lake in the SW valley.
    landcover = np.full(grid.shape, 42, dtype=np.uint8)
    landcover[dist_valley < 220] = 71
    landcover[in_burn] = 52
    lake_cx, lake_cy = valleys[0], bounds[1] + 2600
    in_lake = ((X - lake_cx) ** 2 + (Y - lake_cy) ** 2) < 350.0**2
    landcover[in_lake] = 11
    write_raster(out / _MANUAL_FILES["landcover"], grid, {"landcover": landcover}, nodata=255, dtype="uint8")

    canopy = np.full(grid.shape, 65, dtype=np.uint8)
    canopy[landcover == 71] = 5
    canopy[landcover == 52] = 10
    canopy[landcover == 11] = 0
    # Slightly thicker timber on the cooler (east-facing) side of each ridge.
    canopy[(landcover == 42) & (np.cos(2 * np.pi * (X - bounds[0]) / VALLEY_WAVE_M) < 0)] = 75
    write_raster(out / _MANUAL_FILES["canopy"], grid, {"canopy": canopy}, nodata=255, dtype="uint8")

    # Road down the first valley; a trail up a side drainage to the east ridge.
    ny = 40
    road_y = np.linspace(bounds[1] + 300, bounds[3] - 300, ny)
    road = _line_lonlat(np.full(ny, valleys[0] + 60.0), road_y)
    gpd.GeoDataFrame({"highway": ["track"], "name": ["Fixture Valley Rd"]}, geometry=[road], crs="EPSG:4326").to_file(
        out / _MANUAL_FILES["osm_motorized"], driver="GeoJSON"
    )
    th_utm = (valleys[0] + 80.0, (bounds[1] + bounds[3]) / 2)
    trail_x = np.linspace(th_utm[0], ridge_x, 30)
    trail_y = np.linspace(th_utm[1], th_utm[1] + 1800, 30)
    trail = _line_lonlat(trail_x, trail_y)
    gpd.GeoDataFrame({"highway": ["path"], "name": ["Fixture Trail"]}, geometry=[trail], crs="EPSG:4326").to_file(
        out / _MANUAL_FILES["osm_trails"], driver="GeoJSON"
    )
    th_lon, th_lat = _to_lonlat([th_utm[0]], [th_utm[1]])
    gpd.GeoDataFrame(
        {"highway": ["trailhead"], "name": ["Fixture TH"]},
        geometry=[Point(th_lon[0], th_lat[0])],
        crs="EPSG:4326",
    ).to_file(out / _MANUAL_FILES["osm_trailheads"], driver="GeoJSON")

    spring_utm_x = [ridge_x - 500, ridge_x + 600]
    spring_utm_y = [bounds[1] + 5200, bounds[1] + 6800]
    sp_lon, sp_lat = _to_lonlat(spring_utm_x, spring_utm_y)
    gpd.GeoDataFrame(
        {"natural": ["spring", "spring"], "name": [None, None]},
        geometry=[Point(lon, lat) for lon, lat in zip(sp_lon, sp_lat)],
        crs="EPSG:4326",
    ).to_file(out / _MANUAL_FILES["osm_springs"], driver="GeoJSON")

    spur_x = np.linspace(valleys[0] + 60, valleys[0] + 900, 10)
    spur_y = np.full(10, bounds[1] + 3600.0)
    gpd.GeoDataFrame({"NAME": ["Spur 100"]}, geometry=[_line_lonlat(spur_x, spur_y)], crs="EPSG:4326").to_file(
        out / _MANUAL_FILES["mvum_roads"], driver="GeoJSON"
    )

    # Creeks along every valley; the eastern one is named.
    creeks = []
    creek_names = []
    for i, vx in enumerate(valleys):
        cy = np.linspace(bounds[1] + 200, bounds[3] - 200, 40)
        creeks.append(_line_lonlat(np.full(40, vx), cy))
        creek_names.append("Fixture Creek" if i == len(valleys) - 1 else None)
    gpd.GeoDataFrame({"GNIS_NAME": creek_names}, geometry=creeks, crs="EPSG:4326").to_file(
        out / _MANUAL_FILES["water_lines"], driver="GeoJSON"
    )
    lake_lon, lake_lat = _to_lonlat([lake_cx], [lake_cy])
    lake = Point(lake_lon[0], lake_lat[0]).buffer(0.004)
    gpd.GeoDataFrame({"GNIS_NAME": ["Fixture Lake"]}, geometry=[lake], crs="EPSG:4326").to_file(
        out / _MANUAL_FILES["water_bodies"], driver="GeoJSON"
    )
    (out / _MANUAL_FILES["huc12"]).write_text('{"type": "FeatureCollection", "features": []}')

    # Ownership: everything public except a private inholding beside the road.
    all_lon = box(*AOI_BBOX).buffer(0.05)
    ph_utm = box(valleys[0] - 400, bounds[1] + 5600, valleys[0] + 500, bounds[1] + 6400)
    ph_lon, ph_lat = _to_lonlat([c[0] for c in ph_utm.exterior.coords], [c[1] for c in ph_utm.exterior.coords])
    private = Polygon(zip(ph_lon, ph_lat))
    gpd.GeoDataFrame(
        {"agency": ["USFS", "PRIVATE"], "public": [True, False]},
        geometry=[all_lon, private],
        crs="EPSG:4326",
    ).to_file(out / _MANUAL_FILES["ownership"], driver="GeoJSON")

    bp_lon, bp_lat = _to_lonlat([c[0] for c in burn_poly_utm.exterior.coords], [c[1] for c in burn_poly_utm.exterior.coords])
    gpd.GeoDataFrame(
        {"year": [2016], "fire_name": ["Fixture Fire"]},
        geometry=[Polygon(zip(bp_lon, bp_lat))],
        crs="EPSG:4326",
    ).to_file(out / _MANUAL_FILES["burns"], driver="GeoJSON")

    cfg = load_config(_PROFILE)
    curve_x = [p[0] for p in cfg.snow.band_shift_ft]
    curve_y = [p[1] for p in cfg.snow.band_shift_ft]
    (out / _MANUAL_FILES["snow"]).write_text(
        json.dumps(
            {
                "stations": [
                    {"triplet": "999:ID:SNTL", "name": "Fixture Summit", "elevation_ft": 7040,
                     "snwd_in": _SNWD_IN, "wteq_in": 1.1}
                ],
                "median_snwd_in": _SNWD_IN,
                "band_shift_ft": float(np.interp(_SNWD_IN, curve_x, curve_y)),
                "as_of": "2026-08-28",
                "no_data": False,
            },
            indent=2,
        )
    )
    (out / _MANUAL_FILES["weather"]).write_text(json.dumps({"mode": "climatology", "note": CLIMATOLOGY_NOTE}, indent=2))
