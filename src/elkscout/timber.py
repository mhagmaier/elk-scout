"""Security timber: big blocks of dark conifer far from motorized routes.

run_timber(ws, cfg) -> work/timber_blocks.geojson (EPSG:4326 polygons) + work/timber.json

"Dark timber" = NLCD evergreen/mixed forest (42/43) with tree canopy at or
above a threshold. NLCD canopy reads low in dry Rockies conifer (Colorado
68/681: conifer quartiles 27/37/44%), so a fixed 60% finds nothing; by default
the threshold is the local conifer 75th percentile on public ground in the
unit, floored at cfg.timber.min_dark_canopy_pct.

A security block is a contiguous (8-connected) patch of dark timber on public
land inside the unit, at least cfg.timber.min_road_mi from any motorized
route, of at least cfg.timber.min_acres. When Sentinel-2 change detection has
run (work/sentinel.tif band "dead"), dead/disturbed cells are removed first —
NLCD 2021 still maps beetle-killed stands as dense conifer.

Per block: id (T01.. by size), acres, center lat/lon, elevation p10-p90,
north-facing share, median canopy, median/max distance to motorized routes.
Downstream: scoring boosts BED inside blocks; waypoints rank hunt areas by
nearby block acres and cite the nearest block in each waypoint's evidence;
report writes the blocks as a KML for OnX.
"""

from __future__ import annotations

import json
import logging

import geopandas as gpd
import numpy as np
import rasterio.features
from scipy import ndimage
from shapely.geometry import shape

from .config import Config
from .factors import NODATA_U8, load_factors
from .grid import Grid, read_raster
from .paths import Workspace

log = logging.getLogger("elkscout.timber")

M_PER_MI = 1609.344
ACRE_M2 = 4046.8564
M_TO_FT = 3.28084
NLCD_CONIFER = (42, 43)


def dark_canopy_threshold(canopy: np.ndarray, conifer_public: np.ndarray, cfg: Config) -> tuple[float, bool]:
    """(threshold %, auto?) for 'dark' timber."""
    if cfg.timber.dark_canopy_pct is not None:
        return float(cfg.timber.dark_canopy_pct), False
    vals = canopy[conifer_public]
    if vals.size == 0:
        return float(cfg.timber.min_dark_canopy_pct), True
    return max(float(cfg.timber.min_dark_canopy_pct), float(np.percentile(vals, 75))), True


def _dead_mask(ws: Workspace, shape_: tuple[int, int]) -> np.ndarray:
    if not ws.sentinel_tif.exists():
        return np.zeros(shape_, dtype=bool)
    bands, _ = read_raster(ws.sentinel_tif)
    dead = bands.get("dead")
    if dead is None or dead.shape != shape_:
        return np.zeros(shape_, dtype=bool)
    return np.nan_to_num(dead, nan=0.0) > 0.5


def run_timber(ws: Workspace, cfg: Config) -> gpd.GeoDataFrame:
    grid = Grid.load(ws.grid_json)
    fx, _ = load_factors(ws)
    lc = read_raster(ws.landcover_tif)[0]["landcover"]
    can = read_raster(ws.canopy_tif)[0]["canopy"]
    terrain, _ = read_raster(ws.terrain_tif)
    dem = read_raster(ws.dem_tif)[0]["dem"]
    aspect = terrain["aspect_deg"]
    dmot = fx["dist_motorized_m"]
    pub = (fx["public"] > 0.5) & (fx["unit"] > 0.5)

    can_ok = can != NODATA_U8
    conifer = np.isin(lc, NLCD_CONIFER) & can_ok
    thr, auto = dark_canopy_threshold(can, conifer & pub, cfg)
    dead = _dead_mask(ws, grid.shape)
    dark = conifer & (can >= thr) & ~dead
    cell_ac = grid.res * grid.res / ACRE_M2

    secure = dark & pub & (dmot >= cfg.timber.min_road_mi * M_PER_MI)
    lab, n = ndimage.label(secure, structure=np.ones((3, 3), bool))
    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) if n else np.array([])
    keep = [i + 1 for i, s in enumerate(sizes) if s * cell_ac >= cfg.timber.min_acres]

    records = []
    for bid in keep:
        m = lab == bid
        polys = [shape(g) for g, v in rasterio.features.shapes(m.astype("uint8"), mask=m, transform=grid.transform) if v == 1]
        geom = gpd.GeoSeries(polys, crs=grid.crs).union_all()
        rr, cc = np.nonzero(m)
        aa = aspect[rr, cc]
        aa = aa[np.isfinite(aa)]
        elev_ft = dem[rr, cc] * M_TO_FT
        elev_ft = elev_ft[np.isfinite(elev_ft)]
        c = geom.representative_point()
        lon, lat = grid.xy_to_lonlat(c.x, c.y)
        records.append({
            "acres": int(round(float(m.sum() * cell_ac))),
            "center_lat": round(float(lat), 5),
            "center_lon": round(float(lon), 5),
            "elev_lo_ft": int(np.percentile(elev_ft, 10)) if elev_ft.size else None,
            "elev_hi_ft": int(np.percentile(elev_ft, 90)) if elev_ft.size else None,
            "north_share": round(float(np.mean((aa >= 315) | (aa < 45))), 2) if aa.size else 0.0,
            "median_canopy": int(np.median(can[rr, cc])),
            "road_mi_median": round(float(np.median(dmot[rr, cc])) / M_PER_MI, 2),
            "road_mi_max": round(float(dmot[rr, cc].max()) / M_PER_MI, 2),
            "geometry": geom,
        })
    records.sort(key=lambda r: -r["acres"])
    for i, r in enumerate(records):
        r["id"] = f"T{i + 1:02d}"

    if records:
        blocks = gpd.GeoDataFrame(records, geometry="geometry", crs=grid.crs).to_crs(epsg=4326)
        blocks = blocks[["id", *[k for k in records[0] if k not in ("id", "geometry")], "geometry"]]
    else:
        blocks = gpd.GeoDataFrame({"id": [], "acres": []}, geometry=gpd.GeoSeries([], dtype="geometry"), crs="EPSG:4326")

    ws.timber_blocks_geojson.unlink(missing_ok=True)
    if len(blocks):
        blocks.to_file(ws.timber_blocks_geojson, driver="GeoJSON")
    else:
        ws.timber_blocks_geojson.write_text(json.dumps({"type": "FeatureCollection", "features": []}))

    conifer_pub = can[conifer & pub]
    stats = {
        "dark_canopy_pct": round(thr, 1),
        "dark_canopy_auto": auto,
        "conifer_canopy_quartiles": [int(np.percentile(conifer_pub, q)) for q in (25, 50, 75)] if conifer_pub.size else None,
        "public_acres": int(round(float(pub.sum() * cell_ac))),
        "dark_public_acres": int(round(float((dark & pub).sum() * cell_ac))),
        "dead_conifer_acres_removed": int(round(float((conifer & (can >= thr) & dead & pub).sum() * cell_ac))),
        "min_road_mi": cfg.timber.min_road_mi,
        "min_acres": cfg.timber.min_acres,
        "n_blocks": len(blocks),
        "block_acres_total": int(sum(r["acres"] for r in records)),
    }
    ws.timber_json.write_text(json.dumps(stats, indent=2))
    log.info(
        "timber: dark >= %.0f%% canopy (%s); %d security block(s), %d ac total; %d dead-conifer ac removed",
        thr, "auto" if auto else "fixed", len(blocks), stats["block_acres_total"], stats["dead_conifer_acres_removed"],
    )
    return blocks


def load_blocks(ws: Workspace) -> gpd.GeoDataFrame:
    if not ws.timber_blocks_geojson.exists():
        return gpd.GeoDataFrame({"id": [], "acres": []}, geometry=gpd.GeoSeries([], dtype="geometry"), crs="EPSG:4326")
    g = gpd.read_file(ws.timber_blocks_geojson)
    return g.set_crs("EPSG:4326") if g.crs is None else g


def block_mask(ws: Workspace, grid: Grid) -> np.ndarray:
    """Boolean on-grid mask of security timber."""
    blocks = load_blocks(ws)
    if len(blocks) == 0:
        return np.zeros(grid.shape, dtype=bool)
    return grid.rasterize_gdf(blocks, dtype="uint8", all_touched=False).astype(bool)
