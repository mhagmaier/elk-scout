"""Sentinel-2 near-live imagery: STAC paging/cloud filter, snow composite and
observed snow line, greenness-loss (dead timber) detection, offline behavior.

Scenes are synthetic local GeoTIFFs standing in for the S3-hosted COGs.
"""

import datetime as dt
import json

import numpy as np
import pytest
import rasterio
from affine import Affine

from elkscout.cache import Cache
from elkscout.config import load_config
from elkscout.grid import Grid, write_raster
from elkscout.net import Net
from elkscout.paths import Workspace
from elkscout.sources import sentinel

CFG = load_config("configs/templates/elk.yaml")
N = 60  # 60x60 cells at 30 m = 1.8 km


def _grid():
    return Grid.from_bounds((400020, 4200000, 400020 + N * 30, 4200000 + N * 30), 30, 32613)


def _tif(path, arr, res=20.0):
    """Write a band covering the grid footprint at a finer resolution (exercises warping)."""
    h, w = arr.shape
    tr = Affine(res, 0, 400020, 0, -res, 4200000 + N * 30)
    with rasterio.open(path, "w", driver="GTiff", width=w, height=h, count=1, dtype="uint16",
                       crs="EPSG:32613", transform=tr, nodata=0) as dst:
        dst.write(arr.astype("uint16"), 1)
    return str(path)


def _item(tmp_path, name, date, cloud=5.0, **bands):
    assets = {}
    for key, arr in bands.items():
        href = _tif(tmp_path / f"{name}_{key}.tif", arr)
        rb = [{"scale": 1.0, "offset": 0.0}] if key == "scl" else [{"scale": 1e-4, "offset": 0.0}]
        assets[key] = {"href": href, "raster:bands": rb}
    return {"id": name, "properties": {"datetime": f"{date}T18:00:00Z", "eo:cloud_cover": cloud}, "assets": assets}


FINE = 90  # 90x90 at 20 m covers the 1.8 km grid


def _rows():
    return np.arange(FINE)[:, None].repeat(FINE, axis=1)


def test_snow_composite_and_observed_snowline(tmp_path):
    grid = _grid()
    rows = _rows()
    # Top 40% of the scene (north = high ground) is snow: high green, low SWIR.
    snow_mask = rows < 36
    green = np.where(snow_mask, 8000, 900)
    swir = np.where(snow_mask, 1000, 2500)
    scl = np.where(snow_mask, 11, 4)
    it = _item(tmp_path, "s1", "2026-11-12", green=green, swir16=swir, scl=scl)
    snow, date, used = sentinel.snow_composite([it], grid, 24)
    assert date == "2026-11-12" and used == 1
    assert snow[:20].mean() == 1.0 and snow[-20:].mean() == 0.0

    # DEM rises to the north: 2,700 m (8,858 ft) south edge -> 3,300 m (10,827 ft) north edge.
    dem = np.linspace(3300, 2700, N)[:, None].repeat(N, axis=1).astype(np.float32)
    line = sentinel.observed_snowline(snow, dem, np.ones(grid.shape))
    assert line is not None
    assert 10000 <= line <= 10600  # snow covers roughly the top 40% of the slope


def test_clouds_skipped_and_newest_wins(tmp_path):
    grid = _grid()
    bare_g, bare_s = np.full((FINE, FINE), 900), np.full((FINE, FINE), 2500)
    snow_g, snow_s = np.full((FINE, FINE), 8000), np.full((FINE, FINE), 1000)
    cloudy = _item(tmp_path, "new", "2026-11-14", green=snow_g, swir16=snow_s, scl=np.full((FINE, FINE), 9))
    older = _item(tmp_path, "old", "2026-11-09", green=bare_g, swir16=bare_s, scl=np.full((FINE, FINE), 4))
    snow, date, _ = sentinel.snow_composite([cloudy, older], grid, 24)
    assert np.nanmean(snow) == 0.0  # cloud-flagged newest scene ignored
    assert date == "2026-11-09"


def test_greenness_loss_flags_dead_timber(tmp_path):
    grid = _grid()
    red_live, nir_live = np.full((FINE, FINE), 300), np.full((FINE, FINE), 3000)   # NDVI ~0.82
    red_now, nir_now = red_live.copy(), nir_live.copy()
    red_now[:, 45:] = 1200
    nir_now[:, 45:] = 1900                                                          # NDVI ~0.23 (gray snags)
    scl = np.full((FINE, FINE), 4)
    base = _item(tmp_path, "base", "2022-08-10", red=red_live, nir=nir_live, scl=scl)
    cur = _item(tmp_path, "cur", "2026-08-12", red=red_now, nir=nir_now, scl=scl)
    nb, _ = sentinel.greenest_ndvi([base], grid, 24)
    nc, _ = sentinel.greenest_ndvi([cur], grid, 24)
    dndvi = nc - nb
    dead = (dndvi <= CFG.imagery.dead_dndvi) & (nb >= CFG.imagery.min_baseline_ndvi)
    assert dead[:, 35:].mean() > 0.9   # east half died
    assert dead[:, :25].mean() == 0.0  # west half still green


def test_leafon_years():
    cfg = CFG.model_copy(deep=True)
    cfg.hunt_window.start = dt.date(2026, 11, 18)
    assert sentinel.leafon_years(cfg) == (2026, 2022)
    cfg.hunt_window.start = dt.date(2026, 9, 5)  # September hunt: this summer isn't over
    assert sentinel.leafon_years(cfg) == (2025, 2021)


def test_search_items_pages_and_filters_clouds(tmp_path):
    from elkscout import endpoints

    ws = Workspace(tmp_path)
    ws.ensure_dirs()
    net = Net(Cache(ws.cache), offline=True)
    url = f"{endpoints.STAC_EARTH_SEARCH}/search"
    start, end = dt.date(2026, 10, 22), dt.date(2026, 11, 12)
    bbox = (-106.4, 38.2, -106.2, 38.4)
    params = {
        "collections": endpoints.SENTINEL2_COLLECTION,
        "bbox": ",".join(f"{v:.5f}" for v in bbox),
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "limit": 100,
    }
    page1 = {"features": [
        {"id": "a", "properties": {"datetime": "2026-11-01T18:00:00Z", "eo:cloud_cover": 10}},
        {"id": "cloudy", "properties": {"datetime": "2026-11-11T18:00:00Z", "eo:cloud_cover": 95}},
    ], "links": [{"rel": "next", "href": "https://example.test/page2"}]}
    page2 = {"features": [{"id": "b", "properties": {"datetime": "2026-11-06T18:00:00Z", "eo:cloud_cover": 20}}], "links": []}
    for u, p, payload in ((url, params, page1), ("https://example.test/page2", None, page2)):
        key = Cache.key("GET", u, p, None)
        net.cache.put("sentinel", key, "json", json.dumps(payload).encode(), u, p)
    items = sentinel.search_items(net, bbox, start, end, CFG)
    assert [i["id"] for i in items] == ["b", "a"]  # cloudy dropped, newest first


def test_fetch_end_to_end_merges_observed_snowline(tmp_path, monkeypatch):
    ws = Workspace(tmp_path / "data")
    ws.ensure_dirs()
    grid = _grid()
    grid.save(ws.grid_json)
    dem = np.linspace(3300, 2700, N)[:, None].repeat(N, axis=1).astype(np.float32)
    write_raster(ws.dem_tif, grid, {"dem": dem})
    ws.snow_json.write_text(json.dumps({"stations": [], "median_snwd_in": 7.0, "snowline_ft": None,
                                        "band_shift_ft": 0.0, "snow_in_band": False, "no_data": False}))
    rows = _rows()
    snow_mask = rows < 60  # deep storm: snow down to ~9,500 ft
    recent = [_item(tmp_path, "now", "2026-11-12",
                    green=np.where(snow_mask, 8000, 900), swir16=np.where(snow_mask, 1000, 2500),
                    scl=np.where(snow_mask, 11, 4))]
    scl = np.full((FINE, FINE), 4)
    cur = [_item(tmp_path, "cur", "2026-08-12", red=np.full((FINE, FINE), 300), nir=np.full((FINE, FINE), 3000), scl=scl)]
    base = [_item(tmp_path, "base", "2022-08-12", red=np.full((FINE, FINE), 300), nir=np.full((FINE, FINE), 3000), scl=scl)]

    def fake_search(net, bbox, start, end, cfg):
        if end.year == 2026 and end.month == 11:
            return recent
        return cur if start.year == 2026 else base

    monkeypatch.setattr(sentinel, "search_items", fake_search)
    cfg = CFG.model_copy(deep=True)
    cfg.hunt_window.start, cfg.hunt_window.end = dt.date(2026, 11, 18), dt.date(2026, 11, 22)
    cfg.factors.elevation.curve_elevation_ft = [[7800, 0.0], [8800, 1.0], [10400, 1.0], [11500, 0.0]]
    net = Net(Cache(ws.cache), offline=False)
    meta = sentinel.fetch_sentinel(net, ws, grid, cfg, today=dt.date(2026, 11, 12))
    assert meta["available"] is True and meta["snow_date"] == "2026-11-12"
    assert meta["dead_acres"] == 0
    snow = json.loads(ws.snow_json.read_text())
    assert snow["snowline_source"].startswith("Sentinel-2")
    assert snow["snowline_ft"] < 10400 and snow["snow_in_band"] is True
    assert snow["band_shift_ft"] < 0
    bands, _ = sentinel.load_sentinel(ws)
    assert set(bands) == {"snow_now", "ndvi_now", "dndvi", "dead"}


def test_offline_without_previous_imagery_degrades(tmp_path):
    ws = Workspace(tmp_path)
    ws.ensure_dirs()
    net = Net(Cache(ws.cache), offline=True)
    meta = sentinel.fetch_sentinel(net, ws, _grid(), CFG, today=dt.date(2026, 11, 12))
    assert meta["available"] is False and "offline" in meta["reason"]
    assert not ws.sentinel_tif.exists()


def test_network_failure_degrades(tmp_path, monkeypatch):
    ws = Workspace(tmp_path)
    ws.ensure_dirs()

    def boom(*a, **k):
        raise ConnectionError("proxy refused")

    monkeypatch.setattr(sentinel, "search_items", boom)
    meta = sentinel.fetch_sentinel(Net(Cache(ws.cache), offline=False), ws, _grid(), CFG, today=dt.date(2026, 11, 12))
    assert meta["available"] is False and "proxy refused" in meta["reason"]


def test_reflectance_ignores_stac_boa_offset(tmp_path):
    """Earth Search COGs are already harmonized (reflectance = DN * 1e-4) but their
    raster:bands still carry offset -0.1. Applying it pushed dense-timber red/NIR
    negative and NDVI to +/-20; the reader must use the scale alone."""
    grid = _grid()
    red = np.full((FINE, FINE), 250)    # dense conifer: ~0.025 red
    nir = np.full((FINE, FINE), 1650)   # ~0.165 NIR
    item = _item(tmp_path, "harm", "2026-09-01", red=red, nir=nir)
    for key in ("red", "nir"):
        item["assets"][key]["raster:bands"] = [{"scale": 1e-4, "offset": -0.1}]
    assert sentinel._asset(item, "red")[2] == 0.0
    r = sentinel.read_band(item, "red", grid)
    n = sentinel.read_band(item, "nir", grid)
    assert np.allclose(r, 0.025, atol=1e-4)
    ndvi = (n - r) / (n + r)
    assert np.allclose(ndvi, 0.7368, atol=1e-3)
