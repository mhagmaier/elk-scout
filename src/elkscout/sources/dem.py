"""DEM: USGS 3DEP -> work/dem.tif (float32 meters, aligned to the scoring grid).

Contract:
- fetch_dem(net, ws, grid): resolution order
    1. ws.manual_path("dem") if present (GeoTIFF, any CRS/res) -> grid.warp_file_to_grid
    2. arcgis.export_image_tiles(endpoints.DEM_IMAGESERVER, bounds=grid.bounds,
       epsg=grid.epsg, res_m=grid.res) -> open each tile bytes with rasterio
       MemoryFile, mosaic with rasterio.merge.merge (all-nodata tiles are fine),
       warp the mosaic onto the exact grid transform.
  Post-process: values <= -1000 or >= 9000 -> NaN (3DEP nodata sentinels).
  Write via grid.write_raster(ws.dem_tif, grid, {"dem": arr}) and return the array.
- load_dem(ws) -> (array, Grid): read work/dem.tif band "dem".
"""

from __future__ import annotations

import logging
from contextlib import ExitStack

import numpy as np
import rasterio.merge
from rasterio.io import MemoryFile

from .. import endpoints
from ..grid import Grid, read_raster, write_raster
from ..net import Net, OfflineError
from ..paths import OfflineMissError, Workspace
from .arcgis import export_image_tiles

log = logging.getLogger("elkscout.dem")

SOURCE = "dem"


def fetch_dem(net: Net, ws: Workspace, grid: Grid) -> np.ndarray:
    manual = ws.manual_path(SOURCE)
    if manual.exists():
        log.info("dem: using manual drop-in %s", manual)
        arr = grid.warp_file_to_grid(manual)
    else:
        try:
            tiles = export_image_tiles(
                net,
                endpoints.DEM_IMAGESERVER,
                source=SOURCE,
                bounds=grid.bounds,
                epsg=grid.epsg,
                res_m=grid.res,
            )
        except OfflineError as e:
            raise OfflineMissError(SOURCE, ws) from e
        arr = _mosaic_to_grid(tiles, grid)

    arr = arr.astype(np.float32, copy=False)
    arr[_sentinel_mask(arr)] = np.nan
    n_valid = int(np.isfinite(arr).sum())
    if n_valid == 0:
        raise RuntimeError(
            "DEM has no valid cells after nodata screening; the source did not "
            "cover the grid extent (check the AOI, or re-fetch with a clean cache)"
        )
    log.info("dem: %d/%d grid cells valid", n_valid, arr.size)
    write_raster(ws.dem_tif, grid, {"dem": arr})
    return arr


def load_dem(ws: Workspace) -> tuple[np.ndarray, Grid]:
    bands, grid = read_raster(ws.dem_tif)
    return bands["dem"], grid


# -- internals ---------------------------------------------------------------

def _mosaic_to_grid(tiles: list[bytes], grid: Grid) -> np.ndarray:
    if not tiles:
        raise RuntimeError("DEM export returned no tiles")
    with ExitStack() as stack:
        datasets = []
        for i, blob in enumerate(tiles):
            try:
                mem = stack.enter_context(MemoryFile(blob))
                datasets.append(stack.enter_context(mem.open()))
            except Exception as e:
                snippet = blob[:120].decode("utf-8", "replace")
                raise RuntimeError(
                    f"DEM tile {i + 1}/{len(tiles)} is not a readable GeoTIFF "
                    f"(starts with {snippet!r}); the cached exportImage response is "
                    f"likely a server error — clear cache/{SOURCE}/ and re-fetch"
                ) from e
        mosaic, transform = rasterio.merge.merge(datasets, nodata=np.nan, dtype="float32")
        src_crs = next((ds.crs for ds in datasets if ds.crs is not None), grid.crs)
    band = mosaic[0]
    # Clip nodata sentinels before the bilinear warp so they cannot smear into
    # neighboring valid cells during resampling.
    band[_sentinel_mask(band)] = np.nan
    log.info(
        "dem: mosaicked %d tiles into %dx%d px (%s)",
        len(tiles), band.shape[1], band.shape[0], src_crs,
    )
    return grid.warp_to_grid(band, transform, src_crs, src_nodata=np.nan)


def _sentinel_mask(arr: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return (arr <= -1000.0) | (arr >= 9000.0)
