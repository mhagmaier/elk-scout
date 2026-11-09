"""SNOTEL: state-wildcard query + local bbox filter, snow-line model, offline fallbacks."""

import json

import pytest

from elkscout.cache import Cache
from elkscout.config import load_config
from elkscout.net import Net
from elkscout.paths import Workspace
from elkscout.sources import snotel

ELK = "configs/templates/elk.yaml"

# Your GMU 68/681 stations, Nov 8 2026 (from the hunt guide).
CO_ROWS = [
    {"name": "Cochetopa Pass", "elevation_ft": 10020, "snwd_in": 0.0},
    {"name": "Hayden Pass", "elevation_ft": 10700, "snwd_in": 9.0},
    {"name": "Porphyry Creek", "elevation_ft": 10790, "snwd_in": 7.0},
    {"name": "Moon Pass", "elevation_ft": 11110, "snwd_in": 0.0},
    {"name": "Middle Creek", "elevation_ft": 11260, "snwd_in": 20.0},
    {"name": "Sargents Mesa", "elevation_ft": 11490, "snwd_in": 5.0},
    {"name": "Rat Creek", "elevation_ft": 11680, "snwd_in": 22.0},
]


def _co_cfg(band_top: float):
    cfg = load_config(ELK).model_copy(deep=True)
    cfg.state = "CO"
    cfg.factors.elevation.curve_elevation_ft = [[band_top - 2500, 0.0], [band_top - 1600, 1.0], [band_top, 1.0], [band_top + 1100, 0.0]]
    return cfg


def test_snowline_from_colorado_stations():
    assert snotel.estimate_snowline(CO_ROWS, 6.0) == 10700


def test_high_snowline_does_not_drag_band_down():
    """The 68/681 lesson: snow at 10,700+ ft must not shift a band topping at 10,400."""
    out = snotel._summarize(CO_ROWS, _co_cfg(10400))
    assert out["median_snwd_in"] == 7.0  # the old rule shifted -483 ft off this number
    assert out["snowline_ft"] == 10700
    assert out["band_shift_ft"] == 0.0
    assert out["snow_in_band"] is False


def test_low_snowline_pulls_band_down_and_flags_snow_in_band():
    rows = [dict(r, snwd_in=(r["snwd_in"] + 15)) for r in CO_ROWS]  # big storm: every station deep
    out = snotel._summarize(rows, _co_cfg(10400))
    assert out["snowline_ft"] == 10020
    assert out["band_shift_ft"] == pytest.approx(10020 - 10400)
    assert out["snow_in_band"] is True


def test_shift_bounded_by_profile_curve():
    cfg = _co_cfg(10400)
    rows = [{"name": "Low", "elevation_ft": 6000, "snwd_in": 30.0}]
    out = snotel._summarize(rows, cfg)
    assert out["band_shift_ft"] == min(p[1] for p in cfg.snow.band_shift_ft)


def test_median_method_preserved():
    cfg = load_config(ELK).model_copy(deep=True)
    cfg.snow.method = "median"
    out = snotel._summarize([{"elevation_ft": 7000, "snwd_in": 12.0}], cfg)
    assert out["band_shift_ft"] == -900.0  # [[0,0],[6,-400],[12,-900],[24,-1500]]


def test_no_reporting_stations():
    out = snotel._summarize([], load_config(ELK))
    assert out["no_data"] is True and out["band_shift_ft"] == 0.0 and out["snowline_ft"] is None


def _seed(net, url, params, payload):
    key = Cache.key("GET", url, params, None)
    net.cache.put("snow", key, "json", json.dumps(payload).encode(), url, params)


def test_fetch_filters_nationwide_list_locally(tmp_path, monkeypatch):
    """AWDB ignores bbox params; stations outside the padded AOI must never reach /data."""
    import datetime as dt

    from elkscout import endpoints

    ws = Workspace(tmp_path)
    ws.ensure_dirs()
    net = Net(Cache(ws.cache), offline=True)
    cfg = _co_cfg(10400)
    stations = [
        {"stationTriplet": "1:CO:SNTL", "name": "Inside", "elevation": 10700, "latitude": 38.2, "longitude": -106.3},
        {"stationTriplet": "2:CO:SNTL", "name": "Far away", "elevation": 9000, "latitude": 40.5, "longitude": -105.6},
    ]
    _seed(net, f"{endpoints.AWDB}/stations", {"stationTriplets": "*:CO:SNTL", "activeOnly": "true"}, stations)
    today = dt.date.today()
    data_params = {
        "stationTriplets": "1:CO:SNTL",  # ONLY the inside station
        "elements": "SNWD,WTEQ",
        "duration": "DAILY",
        "beginDate": (today - dt.timedelta(days=7)).isoformat(),
        "endDate": today.isoformat(),
    }
    data = [{"stationTriplet": "1:CO:SNTL", "data": [
        {"stationElement": {"elementCode": "SNWD"}, "values": [{"value": 8.0}]},
    ]}]
    _seed(net, f"{endpoints.AWDB}/data", data_params, data)

    out = snotel.fetch_snow(net, ws, (-106.6, 38.0, -106.0, 38.4), cfg)
    assert [s["name"] for s in out["stations"]] == ["Inside"]
    assert out["snowline_ft"] == 10700
    assert json.loads(ws.snow_json.read_text())["band_shift_ft"] == 0.0
