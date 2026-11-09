"""Near-live imagery from Sentinel-2: current snow cover + timber mortality.

fetch_sentinel(net, ws, grid, cfg) -> dict  (writes work/sentinel.tif + work/sentinel.json)

Why: NLCD land cover/canopy is a 2021 snapshot and the photo services are
2017-2025 mosaics. Beetle kill, new burns, and logging since then turn "dense
live conifer" into gray snags, and the week-of-hunt snow line decides where
elk are. Sentinel-2 (10-20 m, a pass every ~5 days, free, no key) can't show
single trees, but it sees both of those things.

Products (on the scoring grid):
- snow_now   1 snow / 0 bare / NaN no clear look, from the newest clear-sky
             observation per cell within cfg.imagery.recent_days (SCL snow
             class or NDSI > 0.4). Gives an OBSERVED snow line that replaces
             the station-interpolated one in snow.json.
- ndvi_now   greenest-pixel NDVI over the latest leaf-on window
- dndvi      ndvi_now minus the same composite cfg.imagery.baseline_years_back
             years earlier
- dead       1 where dndvi <= cfg.imagery.dead_dndvi on cells that were green
             (baseline NDVI >= min_baseline_ndvi): likely dead/disturbed
             timber. timber.py removes these cells before drawing blocks.

Imagery is an enhancer: offline runs, unreachable hosts, or no clear scenes
log a warning and write sentinel.json {"available": false, ...} — the
pipeline continues on NLCD alone.
"""

from __future__ import annotations

import datetime as dt
import json
import logging

import numpy as np
import rasterio
import rasterio.warp
from rasterio.enums import Resampling

from .. import endpoints
from ..config import Config
from ..grid import Grid, read_raster, write_raster
from ..net import Net
from ..paths import Workspace

log = logging.getLogger("elkscout.sentinel")

SOURCE = "sentinel"
M_TO_FT = 3.28084
NDSI_SNOW = 0.4
SNOWLINE_BIN_FT = 200.0
SNOWLINE_MIN_CELLS = 50
# Scene Classification Layer: 0 nodata, 1 saturated, 3 cloud shadow,
# 8/9 cloud, 10 cirrus are unusable; 11 is snow/ice.
SCL_BAD = (0, 1, 3, 8, 9, 10)
SCL_SNOW = 11

ASSET_KEYS = {
    "green": ("green", "B03"),
    "red": ("red", "B04"),
    "nir": ("nir", "B08"),
    "swir16": ("swir16", "B11"),
    "scl": ("scl", "SCL"),
}


# -- STAC --------------------------------------------------------------------

def search_items(net: Net, bbox4326, start: dt.date, end: dt.date, cfg: Config) -> list[dict]:
    """STAC items over the AOI in [start, end], under the cloud cap, newest first."""
    url = f"{endpoints.STAC_EARTH_SEARCH}/search"
    params = {
        "collections": endpoints.SENTINEL2_COLLECTION,
        "bbox": ",".join(f"{v:.5f}" for v in bbox4326),
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "limit": 100,
    }
    items: list[dict] = []
    for _ in range(5):  # page cap
        page = net.fetch_json(url, params, source=SOURCE)
        items.extend(page.get("features") or [])
        nxt = next((l for l in page.get("links") or [] if l.get("rel") == "next" and l.get("href")), None)
        if not nxt:
            break
        url, params = nxt["href"], None
    clear = [
        it for it in items
        if float((it.get("properties") or {}).get("eo:cloud_cover", 100.0)) <= cfg.imagery.max_cloud_pct
    ]
    clear.sort(key=lambda it: (it.get("properties") or {}).get("datetime", ""), reverse=True)
    return clear


def _asset(item: dict, band: str) -> tuple[str, float, float] | None:
    """(href, scale, offset) for a logical band, or None if the item lacks it."""
    assets = item.get("assets") or {}
    for key in ASSET_KEYS[band]:
        a = assets.get(key)
        if a and a.get("href"):
            rb = (a.get("raster:bands") or [{}])[0]
            scale = float(rb.get("scale", 1.0 if band == "scl" else 1e-4))
            # Earth Search v1 L2A COGs are already harmonized to the pre-PB04.00
            # scale (reflectance = DN * 1e-4) - dense timber reads red ~250 DN,
            # NIR ~1,650 DN whatever `earthsearch:boa_offset_applied` says - yet
            # their raster:bands still list the -0.1 BOA offset. Applying it again
            # drives dark-forest bands negative: NDVI lands far outside [-1, 1]
            # (garbage dead-timber mask) and NDSI flags dark conifer as snow.
            offset = 0.0
            return a["href"], scale, offset
    return None


def read_band(item: dict, band: str, grid: Grid) -> np.ndarray | None:
    """One band warped onto the grid (GDAL picks a COG overview when downsampling)."""
    asset = _asset(item, band)
    if asset is None:
        return None
    href, scale, offset = asset
    dst = np.full(grid.shape, np.nan, dtype=np.float32)
    with rasterio.open(href) as src:
        rasterio.warp.reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_nodata=src.nodata if src.nodata is not None else 0,
            dst_transform=grid.transform,
            dst_crs=grid.crs,
            dst_nodata=np.nan,
            resampling=Resampling.nearest if band == "scl" else Resampling.average,
        )
    if band == "scl":
        return dst
    return dst * scale + offset


def _clear(scl: np.ndarray | None, shape_) -> np.ndarray:
    if scl is None:
        return np.ones(shape_, dtype=bool)
    return np.isfinite(scl) & ~np.isin(scl, SCL_BAD)


def _ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return (a - b) / (a + b)


# -- composites ----------------------------------------------------------------

def snow_composite(items: list[dict], grid: Grid, max_items: int) -> tuple[np.ndarray, str | None, int]:
    """(snow_now, newest date used, items read): newest clear observation per cell."""
    snow = np.full(grid.shape, np.nan, dtype=np.float32)
    newest = None
    used = 0
    for it in items[:max_items]:
        if np.isfinite(snow).all():
            break
        scl = read_band(it, "scl", grid)
        green = read_band(it, "green", grid)
        swir = read_band(it, "swir16", grid)
        if green is None or swir is None:
            continue
        used += 1
        ok = _clear(scl, grid.shape) & np.isfinite(green) & np.isfinite(swir) & np.isnan(snow)
        is_snow = (_ratio(green, swir) > NDSI_SNOW) | (scl == SCL_SNOW if scl is not None else False)
        snow[ok] = is_snow[ok].astype(np.float32)
        if ok.any() and newest is None:
            newest = (it.get("properties") or {}).get("datetime", "")[:10]
    return snow, newest, used


def greenest_ndvi(items: list[dict], grid: Grid, max_items: int) -> tuple[np.ndarray, int]:
    """Per-cell max NDVI over clear observations (robust to cloud and phenology)."""
    best = np.full(grid.shape, np.nan, dtype=np.float32)
    used = 0
    for it in items[:max_items]:
        red = read_band(it, "red", grid)
        nir = read_band(it, "nir", grid)
        if red is None or nir is None:
            continue
        used += 1
        scl = read_band(it, "scl", grid)
        ndvi = _ratio(nir, red)
        ok = _clear(scl, grid.shape) & np.isfinite(ndvi)
        best = np.where(ok & ~(ndvi <= best), ndvi, best)  # NaN-aware max
    return best, used


def observed_snowline(snow: np.ndarray, dem_m: np.ndarray, unit: np.ndarray) -> float | None:
    """Lowest 200-ft elevation bin that is mostly snow, with the bins above agreeing."""
    m = np.isfinite(snow) & np.isfinite(dem_m) & (unit > 0.5)
    if m.sum() < SNOWLINE_MIN_CELLS:
        return None
    elev_ft = dem_m[m] * M_TO_FT
    s = snow[m]
    lo = np.floor(elev_ft.min() / SNOWLINE_BIN_FT) * SNOWLINE_BIN_FT
    edges = np.arange(lo, elev_ft.max() + SNOWLINE_BIN_FT, SNOWLINE_BIN_FT)
    idx = np.digitize(elev_ft, edges) - 1
    fracs = []
    for b in range(len(edges) - 1):
        sel = idx == b
        if sel.sum() >= 20:
            fracs.append((edges[b], float(s[sel].mean())))
    for i, (e, f) in enumerate(fracs):
        if f < 0.5:
            continue
        above = fracs[i + 1:]
        if not above or sum(fa >= 0.5 for _, fa in above) >= len(above) / 2:
            return float(e)
    return None


def leafon_years(cfg: Config) -> tuple[int, int]:
    """(current, baseline) leaf-on years: the latest summer fully before the hunt."""
    start = cfg.hunt_window.start
    cur = start.year if start.month > max(cfg.imagery.leafon_months) else start.year - 1
    return cur, cur - cfg.imagery.baseline_years_back


def _leafon_window(year: int, months: list[int]) -> tuple[dt.date, dt.date]:
    m0, m1 = min(months), max(months)
    end = dt.date(year, m1 + 1, 1) - dt.timedelta(days=1) if m1 < 12 else dt.date(year, 12, 31)
    return dt.date(year, m0, 1), end


# -- stage ---------------------------------------------------------------------

def fetch_sentinel(net: Net, ws: Workspace, grid: Grid, cfg: Config, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    meta: dict = {"available": False}
    if not cfg.imagery.enabled:
        meta["reason"] = "disabled in profile"
        return _write_meta(ws, meta)
    if net.offline:
        if ws.sentinel_tif.exists():
            log.info("sentinel: offline; keeping existing %s", ws.sentinel_tif)
            return json.loads(ws.sentinel_json.read_text()) if ws.sentinel_json.exists() else {"available": True}
        meta["reason"] = "offline and no previous imagery"
        log.warning("sentinel: %s — continuing on NLCD only", meta["reason"])
        return _write_meta(ws, meta)

    try:
        bbox = grid.bbox4326()
        recent = search_items(net, bbox, today - dt.timedelta(days=cfg.imagery.recent_days), today, cfg)
        snow, snow_date, n_snow = snow_composite(recent, grid, cfg.imagery.max_items)

        cur_year, base_year = leafon_years(cfg)
        cur_items = search_items(net, bbox, *_leafon_window(cur_year, cfg.imagery.leafon_months), cfg)
        base_items = search_items(net, bbox, *_leafon_window(base_year, cfg.imagery.leafon_months), cfg)
        ndvi_now, n_cur = greenest_ndvi(cur_items, grid, cfg.imagery.max_items)
        ndvi_base, n_base = greenest_ndvi(base_items, grid, cfg.imagery.max_items)
    except Exception as e:  # noqa: BLE001 - imagery never fails the pipeline
        meta["reason"] = f"{type(e).__name__}: {e}"[:300]
        log.warning("sentinel: imagery unavailable (%s) — continuing on NLCD only", meta["reason"])
        return _write_meta(ws, meta)

    dndvi = ndvi_now - ndvi_base
    dead = ((dndvi <= cfg.imagery.dead_dndvi) & (ndvi_base >= cfg.imagery.min_baseline_ndvi)).astype(np.float32)
    dead[~np.isfinite(dndvi)] = np.nan
    write_raster(ws.sentinel_tif, grid, {
        "snow_now": snow, "ndvi_now": ndvi_now, "dndvi": dndvi.astype(np.float32), "dead": dead,
    })

    dem = read_raster(ws.dem_tif)[0]["dem"] if ws.dem_tif.exists() else None
    unit = grid.rasterize_gdf(_boundary(ws), dtype="float32") if ws.boundary_geojson.exists() else np.ones(grid.shape)
    snowline = observed_snowline(snow, dem, unit) if dem is not None else None
    cell_ac = grid.res * grid.res / 4046.8564
    meta = {
        "available": True,
        "snow_date": snow_date,
        "snow_items": n_snow,
        "snow_clear_share": round(float(np.isfinite(snow[unit > 0.5]).mean()), 3) if (unit > 0.5).any() else 0.0,
        "snow_cover_share": round(float(np.nanmean(snow[unit > 0.5])), 3) if np.isfinite(snow[unit > 0.5]).any() else None,
        "observed_snowline_ft": snowline,
        "leafon_current_year": cur_year,
        "leafon_baseline_year": base_year,
        "leafon_items": [n_cur, n_base],
        "dead_acres": int(round(float(np.nansum(dead[unit > 0.5]) * cell_ac))),
    }
    _merge_snowline(ws, cfg, snowline, snow_date)
    log.info(
        "sentinel: snow look %s (%d items, snow on %s of clear ground), observed snow line %s; "
        "%d ac lost greenness %d->%d",
        snow_date, n_snow, meta["snow_cover_share"], snowline, meta["dead_acres"], base_year, cur_year,
    )
    return _write_meta(ws, meta)


def _boundary(ws: Workspace):
    from .boundary import load_boundary

    return load_boundary(ws)


def _merge_snowline(ws: Workspace, cfg: Config, snowline: float | None, date: str | None) -> None:
    """An observed snow line beats the station-interpolated one: update snow.json."""
    if snowline is None or not ws.snow_json.exists():
        return
    from .snotel import band_top_ft

    snow = json.loads(ws.snow_json.read_text())
    top = band_top_ft(cfg)
    floor = min(p[1] for p in cfg.snow.band_shift_ft)
    snow.update({
        "snowline_ft": snowline,
        "snowline_source": f"Sentinel-2 {date}",
        "band_top_ft": top,
        "band_shift_ft": float(max(floor, min(0.0, snowline - top))),
        "snow_in_band": bool(snowline <= top),
    })
    ws.snow_json.write_text(json.dumps(snow, indent=2))
    log.info("sentinel: snow.json now uses the observed snow line %.0f ft (shift %+.0f ft)",
             snowline, snow["band_shift_ft"])


def _write_meta(ws: Workspace, meta: dict) -> dict:
    ws.sentinel_json.parent.mkdir(parents=True, exist_ok=True)
    ws.sentinel_json.write_text(json.dumps(meta, indent=2))
    return meta


def load_sentinel(ws: Workspace) -> tuple[dict[str, np.ndarray] | None, dict]:
    meta = json.loads(ws.sentinel_json.read_text()) if ws.sentinel_json.exists() else {"available": False}
    if not ws.sentinel_tif.exists():
        return None, meta
    bands, _ = read_raster(ws.sentinel_tif)
    return bands, meta
