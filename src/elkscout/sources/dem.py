"""DEM: USGS 3DEP -> work/dem.tif (float32 meters, aligned to the scoring grid).

Contract:
- fetch_dem(net, ws, grid): resolution order
    1. ws.manual_path("dem") if present (GeoTIFF, any CRS/res) -> grid.warp_file_to_grid
    2. arcgis.export_image_tiles(endpoints.DEM_IMAGESERVER, bounds=grid.bounds,
       epsg=grid.epsg, res_m=grid.res) -> open each tile bytes with rasterio MemoryFile,
       mosaic with rasterio.merge.merge, warp mosaic onto the exact grid transform.
  Post-process: values <= -1000 or >= 9000 -> NaN (3DEP nodata sentinels).
  Write via grid.write_raster(ws.dem_tif, grid, {"dem": arr}) and return the array.
- load_dem(ws) -> (array, Grid): read work/dem.tif band "dem".
"""

from __future__ import annotations

import numpy as np

from ..grid import Grid, read_raster
from ..net import Net
from ..paths import Workspace


def fetch_dem(net: Net, ws: Workspace, grid: Grid) -> np.ndarray:
    raise NotImplementedError


def load_dem(ws: Workspace) -> tuple[np.ndarray, Grid]:
    bands, grid = read_raster(ws.dem_tif)
    return bands["dem"], grid
