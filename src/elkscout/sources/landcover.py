"""NLCD land cover + percent tree canopy -> work/landcover.tif, work/canopy.tif
(uint8, aligned to the scoring grid; 255 = nodata).

Contract — fetch_landcover(net, ws, grid):
- Each raster resolves independently: manual drop-in ("landcover"/"canopy",
  any CRS/res GeoTIFF, warped nearest onto the grid) first, else MRLC WCS.
- WCS path: GetCapabilities (cached) -> coverage names; land cover = newest id
  matching land-cover naming (excluding change/confidence/etc products);
  canopy = newest tree-canopy id. GetCoverage 1.0.0 in EPSG:5070 (NLCD native)
  over the grid bounds + margin, read via rasterio MemoryFile, warped nearest
  onto the grid.
- Written via grid write_raster, band names "landcover"/"canopy", uint8,
  nodata 255.

NLCD classes used downstream: 11 open water; 41/42/43 forest; 52 shrub;
71 grassland; 90 woody wetland; 95 herbaceous wetland.
Offline miss -> OfflineMissError("landcover"/"canopy", ws).
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import numpy as np
import rasterio
import rasterio.warp
from rasterio.enums import Resampling
from rasterio.io import MemoryFile

from .. import endpoints
from ..grid import Grid, write_raster
from ..net import Net, OfflineError, validate_tiff_body
from ..paths import OfflineMissError, Workspace

log = logging.getLogger("elkscout.landcover")

SOURCE = "landcover"
_NLCD_EPSG = 5070
_MARGIN_M = 1000.0

_LANDCOVER_RE = re.compile(r"(lndcov|land_?cover)", re.IGNORECASE)
_CANOPY_RE = re.compile(r"(tcc|tree_?canopy)", re.IGNORECASE)
_EXCLUDE_RE = re.compile(
    r"(change|confidence|descriptor|count|index|fct|fractional|impervious|science|shrub|herbaceous"
    r"|hawaii|alaska|puerto|(^|[_:\-])(hi|ak|pr)([_\-]|$))",
    re.IGNORECASE,
)
# Lower-48 coverage only: names must carry one of these tokens.
_L48_RE = re.compile(r"(l48|conus)", re.IGNORECASE)
# Known-good ids, tried first (verified against MRLC's catalog on the GMU
# 68/681 run, Nov 2026 — the regex picker had chosen a change-count product
# and a Hawaii canopy layer).
PREFERRED = {
    "landcover": ["mrlc_download:NLCD_2021_Land_Cover_L48"],
    "canopy": ["mrlc_download:nlcd_tcc_conus_2021_v2021-4"],
}


def fetch_landcover(net: Net, ws: Workspace, grid: Grid) -> None:
    _fetch_one(net, ws, grid, key="landcover", pattern=_LANDCOVER_RE, out=ws.landcover_tif, band="landcover")
    _fetch_one(net, ws, grid, key="canopy", pattern=_CANOPY_RE, out=ws.canopy_tif, band="canopy")


def choose_coverage(names: list[str], key: str, pattern: re.Pattern) -> str:
    """Preferred id if the catalog has it, else the newest lower-48 match."""
    for pid in PREFERRED.get(key, []):
        if pid in names:
            return pid
    candidates = [n for n in names if pattern.search(n) and _L48_RE.search(n) and not _EXCLUDE_RE.search(n)]
    if not candidates:
        raise RuntimeError(f"no lower-48 MRLC coverage matches {pattern.pattern} among {len(names)} names")

    def year(name: str) -> int:
        ys = [int(y) for y in re.findall(r"((?:19|20)\d{2})", name)]
        return max(ys) if ys else 0

    return max(candidates, key=year)


def _fetch_one(net: Net, ws: Workspace, grid: Grid, *, key: str, pattern: re.Pattern, out, band: str) -> None:
    manual = ws.manual_path(key)
    if manual.exists():
        log.info("landcover: using manual drop-in %s", manual)
        arr = grid.warp_file_to_grid(manual, resampling=Resampling.nearest)
    else:
        try:
            coverage = _pick_coverage(net, pattern, key)
            arr = _get_coverage(net, coverage, grid)
        except OfflineError as e:
            raise OfflineMissError(key, ws) from e
    u8 = np.where(np.isfinite(arr), arr, 255).astype("uint8")
    write_raster(out, grid, {band: u8}, nodata=255, dtype="uint8")
    valid = int(np.count_nonzero(u8 != 255))
    log.info("landcover: %s -> %s (%.1f%% valid)", band, out, 100.0 * valid / u8.size)


def _pick_coverage(net: Net, pattern: re.Pattern, key: str) -> str:
    raw = net.fetch_bytes(
        endpoints.MRLC_WCS,
        {"service": "WCS", "version": "1.0.0", "request": "GetCapabilities"},
        source=SOURCE,
        ext="xml",
    )
    best = choose_coverage(_coverage_names(raw), key, pattern)
    log.info("landcover: selected coverage %r for %s", best, key)
    return best


def _coverage_names(capabilities_xml: bytes) -> list[str]:
    root = ET.fromstring(capabilities_xml)
    names: list[str] = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag in ("name", "CoverageId") and el.text:
            names.append(el.text.strip())
    return names


def _get_coverage(net: Net, coverage: str, grid: Grid) -> np.ndarray:
    minx, miny, maxx, maxy = rasterio.warp.transform_bounds(
        grid.crs, rasterio.crs.CRS.from_epsg(_NLCD_EPSG), *grid.bounds
    )
    minx -= _MARGIN_M
    miny -= _MARGIN_M
    maxx += _MARGIN_M
    maxy += _MARGIN_M
    width = max(1, int(round((maxx - minx) / 30.0)))
    height = max(1, int(round((maxy - miny) / 30.0)))
    raw = net.fetch_bytes(
        endpoints.MRLC_WCS,
        {
            "service": "WCS",
            "version": "1.0.0",
            "request": "GetCoverage",
            "coverage": coverage,
            "bbox": f"{minx},{miny},{maxx},{maxy}",
            "crs": f"EPSG:{_NLCD_EPSG}",
            "response_crs": f"EPSG:{_NLCD_EPSG}",
            "width": width,
            "height": height,
            "format": "GeoTIFF",
        },
        source=SOURCE,
        ext="tif",
        validate=validate_tiff_body,
    )
    try:
        with MemoryFile(raw) as mem, mem.open() as src:
            return grid.warp_to_grid(
                src.read(1), src.transform, src.crs, resampling=Resampling.nearest, src_nodata=src.nodata
            )
    except rasterio.errors.RasterioIOError as e:
        snippet = raw[:200].decode("utf-8", "replace")
        raise RuntimeError(
            f"MRLC GetCoverage for {coverage!r} did not return a GeoTIFF "
            f"(response starts: {snippet!r}); clear data/cache/{SOURCE}/ and retry"
        ) from e
