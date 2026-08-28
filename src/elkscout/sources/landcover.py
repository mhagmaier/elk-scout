"""NLCD land cover + percent tree canopy -> work/landcover.tif, work/canopy.tif
(uint8, aligned to the scoring grid; 255 = nodata).

Contract — fetch_landcover(net, ws, grid):
1. Manual drop-ins first: manual keys "landcover" and "canopy" (GeoTIFFs, any
   CRS/res) -> grid.warp_file_to_grid(..., resampling=Resampling.nearest) each.
2. MRLC GeoServer WCS (endpoints.MRLC_WCS):
   - GetCapabilities (cached) -> list coverage ids; choose land cover coverage:
     the newest id matching r'(Annual_)?NLCD.*(Land_?Cover|LndCov).*(L48|CONUS)'
     (Annual NLCD ids look like 'mrlc_download__Annual_NLCD_LndCov_2023_CU_C1V0');
     canopy: newest matching r'NLCD.*(Tree_?Canopy|TCC).*' .
   - WCS 2.0.1 GetCoverage with coverageId, format=image/tiff and
     SUBSET=X(minx,maxx)&SUBSET=Y(miny,maxy) in the coverage's native CRS
     (EPSG:5070 for NLCD; reproject grid bounds there with a safety margin) —
     read result with rasterio MemoryFile, warp to grid (nearest).
3. Write both rasters via grid write_raster with band names "landcover"/"canopy",
   dtype uint8, nodata 255.

NLCD classes used downstream (factors.py): 11 open water; 41/42/43 forest;
52 shrub; 71 grassland; 90 woody wetland; 95 herbaceous wetland.
Offline miss -> OfflineMissError("landcover", ws) (canopy analogously).
"""

from __future__ import annotations

from ..grid import Grid
from ..net import Net
from ..paths import Workspace


def fetch_landcover(net: Net, ws: Workspace, grid: Grid) -> None:
    raise NotImplementedError
