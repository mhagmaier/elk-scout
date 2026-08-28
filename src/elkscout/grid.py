"""The scoring grid: one canonical 30 m raster lattice in EPSG:32611.

Every raster artifact in the pipeline is aligned to this grid (same transform,
shape, CRS) so factor math is plain numpy. Vectors are stored in EPSG:4326 and
projected here on use.

Raster conventions: float32, NaN nodata (uint8 rasters use 255), north-up
transform (row 0 = northern edge).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
from affine import Affine
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.enums import Resampling

from .config import GridCfg


@dataclass(frozen=True)
class Grid:
    transform: Affine  # north-up: (res, 0, minx, 0, -res, maxy)
    width: int
    height: int
    epsg: int

    # -- construction ------------------------------------------------------
    @classmethod
    def from_bounds(cls, bounds: tuple[float, float, float, float], res_m: float, epsg: int) -> "Grid":
        """Grid covering `bounds` (minx,miny,maxx,maxy in `epsg`), snapped outward to the res lattice."""
        minx, miny, maxx, maxy = bounds
        minx = math.floor(minx / res_m) * res_m
        miny = math.floor(miny / res_m) * res_m
        maxx = math.ceil(maxx / res_m) * res_m
        maxy = math.ceil(maxy / res_m) * res_m
        width = int(round((maxx - minx) / res_m))
        height = int(round((maxy - miny) / res_m))
        transform = Affine(res_m, 0.0, minx, 0.0, -res_m, maxy)
        return cls(transform=transform, width=width, height=height, epsg=epsg)

    @classmethod
    def from_boundary(cls, boundary_gdf, cfg: GridCfg) -> "Grid":
        """Grid over a boundary GeoDataFrame (any CRS), buffered by cfg.buffer_m."""
        gdf = boundary_gdf.to_crs(epsg=cfg.epsg)
        minx, miny, maxx, maxy = gdf.total_bounds
        b = cfg.buffer_m
        return cls.from_bounds((minx - b, miny - b, maxx + b, maxy + b), cfg.res_m, cfg.epsg)

    # -- basics ------------------------------------------------------------
    @property
    def crs(self) -> CRS:
        return CRS.from_epsg(self.epsg)

    @property
    def res(self) -> float:
        return float(self.transform.a)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        minx = self.transform.c
        maxy = self.transform.f
        maxx = minx + self.width * self.res
        miny = maxy - self.height * self.res
        return (minx, miny, maxx, maxy)

    def bbox4326(self, pad_deg: float = 0.0) -> tuple[float, float, float, float]:
        """Grid bounds in EPSG:4326 (lon/lat), densified along edges for correctness."""
        minx, miny, maxx, maxy = rasterio.warp.transform_bounds(self.crs, CRS.from_epsg(4326), *self.bounds)
        return (minx - pad_deg, miny - pad_deg, maxx + pad_deg, maxy + pad_deg)

    def cell_centers(self) -> tuple[np.ndarray, np.ndarray]:
        """1D arrays of x (per column) and y (per row) cell-center coordinates."""
        xs = self.transform.c + (np.arange(self.width) + 0.5) * self.res
        ys = self.transform.f - (np.arange(self.height) + 0.5) * self.res
        return xs, ys

    def xy(self, row: np.ndarray | int, col: np.ndarray | int) -> tuple[np.ndarray, np.ndarray]:
        """Cell-center projected coordinates for (row, col)."""
        x = self.transform.c + (np.asarray(col) + 0.5) * self.res
        y = self.transform.f - (np.asarray(row) + 0.5) * self.res
        return x, y

    def rowcol(self, x: np.ndarray | float, y: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
        col = np.floor((np.asarray(x) - self.transform.c) / self.res).astype(int)
        row = np.floor((self.transform.f - np.asarray(y)) / self.res).astype(int)
        return row, col

    def xy_to_lonlat(self, x: np.ndarray | float, y: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
        tr = Transformer.from_crs(self.crs, CRS.from_epsg(4326), always_xy=True)
        return tr.transform(x, y)

    # -- vector -> raster --------------------------------------------------
    def rasterize(
        self,
        geoms: Iterable,
        values: float | Iterable[float] = 1.0,
        fill: float = 0.0,
        all_touched: bool = True,
        dtype: str = "float32",
    ) -> np.ndarray:
        """Burn shapely geometries (already in grid CRS) onto the grid."""
        geoms = list(geoms)
        if not geoms:
            return np.full(self.shape, fill, dtype=dtype)
        if np.isscalar(values):
            shapes = [(g, values) for g in geoms]
        else:
            shapes = list(zip(geoms, values))
        return rasterio.features.rasterize(
            shapes,
            out_shape=self.shape,
            transform=self.transform,
            fill=fill,
            all_touched=all_touched,
            dtype=dtype,
        )

    def rasterize_gdf(self, gdf, **kw) -> np.ndarray:
        """Rasterize a GeoDataFrame in any CRS (reprojected here first)."""
        if gdf is None or len(gdf) == 0:
            return np.full(self.shape, kw.get("fill", 0.0), dtype=kw.get("dtype", "float32"))
        g = gdf.to_crs(epsg=self.epsg)
        return self.rasterize(g.geometry.values, **kw)

    # -- raster -> grid ----------------------------------------------------
    def warp_to_grid(
        self,
        src_array: np.ndarray,
        src_transform: Affine,
        src_crs,
        resampling: Resampling = Resampling.bilinear,
        src_nodata: float | None = None,
        dst_dtype: str = "float32",
    ) -> np.ndarray:
        """Reproject/resample an arbitrary raster onto this grid."""
        dst = np.full(self.shape, np.nan, dtype=dst_dtype)
        rasterio.warp.reproject(
            source=src_array.astype(dst_dtype),
            destination=dst,
            src_transform=src_transform,
            src_crs=src_crs,
            src_nodata=src_nodata,
            dst_transform=self.transform,
            dst_crs=self.crs,
            dst_nodata=np.nan,
            resampling=resampling,
        )
        return dst

    def warp_file_to_grid(self, path: str | Path, resampling: Resampling = Resampling.bilinear) -> np.ndarray:
        with rasterio.open(path) as src:
            return self.warp_to_grid(
                src.read(1), src.transform, src.crs, resampling=resampling, src_nodata=src.nodata
            )

    # -- persistence -------------------------------------------------------
    def to_json(self) -> dict:
        return {
            "transform": list(self.transform)[:6],
            "width": self.width,
            "height": self.height,
            "epsg": self.epsg,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_json(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "Grid":
        d = json.loads(Path(path).read_text())
        return cls(transform=Affine(*d["transform"]), width=d["width"], height=d["height"], epsg=d["epsg"])


# -- on-grid raster file IO -------------------------------------------------

def write_raster(
    path: str | Path,
    grid: Grid,
    bands: dict[str, np.ndarray] | np.ndarray,
    nodata: float | None = None,
    dtype: str | None = None,
) -> None:
    """Write on-grid array(s) as GeoTIFF. dict keys become band descriptions."""
    if isinstance(bands, np.ndarray):
        bands = {"band_1": bands}
    names = list(bands)
    first = bands[names[0]]
    dtype = dtype or str(first.dtype)
    if nodata is None:
        nodata = float("nan") if np.issubdtype(np.dtype(dtype), np.floating) else 255
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=grid.height,
        width=grid.width,
        count=len(names),
        dtype=dtype,
        crs=grid.crs,
        transform=grid.transform,
        nodata=nodata,
        compress="deflate",
        tiled=True,
    ) as dst:
        for i, name in enumerate(names, start=1):
            arr = bands[name]
            if arr.shape != grid.shape:
                raise ValueError(f"band {name!r} shape {arr.shape} != grid {grid.shape}")
            dst.write(arr.astype(dtype), i)
            dst.set_band_description(i, name)


def read_raster(path: str | Path) -> tuple[dict[str, np.ndarray], Grid]:
    """Read an on-grid GeoTIFF back into {band_name: array} plus its Grid."""
    with rasterio.open(path) as src:
        grid = Grid(
            transform=src.transform,
            width=src.width,
            height=src.height,
            epsg=src.crs.to_epsg(),
        )
        out: dict[str, np.ndarray] = {}
        for i in range(1, src.count + 1):
            name = src.descriptions[i - 1] or f"band_{i}"
            arr = src.read(i)
            if src.nodata is not None and not math.isnan(src.nodata):
                arr = np.where(arr == src.nodata, np.nan, arr) if np.issubdtype(arr.dtype, np.floating) else arr
            out[name] = arr
        return out, grid


def sample_at_points(grid: Grid, array: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Sample an on-grid array at projected (grid-CRS) coordinates; out-of-grid -> NaN."""
    row, col = grid.rowcol(xs, ys)
    row = np.atleast_1d(row)
    col = np.atleast_1d(col)
    ok = (row >= 0) & (row < grid.height) & (col >= 0) & (col < grid.width)
    out = np.full(row.shape, np.nan, dtype="float64")
    out[ok] = array[row[ok], col[ok]]
    return out
