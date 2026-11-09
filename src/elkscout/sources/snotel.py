"""SNOTEL snow state -> work/snow.json.

Contract — fetch_snow(net, ws, bbox4326, cfg) -> dict:
1. ws.manual_path("snow") if present (same schema) -> copied to ws.snow_json.
2. NRCS AWDB REST: /stations with a state-wildcard triplet ("*:CO:SNTL", or
   "*:*:SNTL" when the profile has no state) — AWDB v1 IGNORES bbox params and
   returns every station nationwide, which then blows the /data URL past its
   length limit (HTTP 414). Stations are filtered to the padded bbox locally,
   then /data (SNWD, WTEQ, DAILY, last 7 days) in batches.
3. Summary: median_snwd_in, an estimated snow line, and band_shift_ft:
   - snow.method "snowline" (default): snowline_ft = lowest reporting station
     holding >= snowline_depth_in whose higher neighbors mostly agree; the
     band shift pulls the elevation optimum's top down to the snow line ONLY
     when the snow line sits below it. Stations far above the elk band no
     longer drag the band down (the GMU 68/681 lesson).
   - snow.method "median": the original median-depth -> band_shift_ft curve.
   snow_in_band says whether snow has reached the elk band (it gates the
   late-season sunny-slope bedding switch in scoring).

Written schema:
  {"stations": [{"triplet","name","elevation_ft","snwd_in","wteq_in"}...],
   "median_snwd_in": float, "snowline_ft": float|null, "band_top_ft": float,
   "band_shift_ft": float, "snow_in_band": bool, "method": str,
   "as_of": "YYYY-MM-DD", "no_data": bool}

Snow is an enhancer, not a required layer: offline misses and HTTP failures
degrade to the zero-snow dict with no_data=true (with a warning), never raise.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging

import numpy as np
import requests

from .. import endpoints
from ..config import Config
from ..net import Net, OfflineError
from ..paths import Workspace

log = logging.getLogger("elkscout.snotel")

SOURCE = "snow"


def fetch_snow(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float], cfg: Config) -> dict:
    manual = ws.manual_path(SOURCE)
    if manual.exists():
        log.info("snotel: using manual drop-in %s", manual)
        result = json.loads(manual.read_text())
    else:
        try:
            result = _fetch(net, bbox4326, cfg)
        except OfflineError:
            # The /data cache key embeds today's date, so an offline run days
            # after priming misses the cache — reuse the last fetched summary
            # rather than silently degrading to zero snow.
            if ws.snow_json.exists():
                log.info("snotel: offline; reusing previously fetched %s", ws.snow_json)
                return json.loads(ws.snow_json.read_text())
            log.warning("snotel: offline with no prior data; assuming zero snow")
            result = _summarize([], cfg)
        except (requests.RequestException, RuntimeError, ValueError, KeyError) as e:
            log.warning("snotel: unavailable (%s); assuming zero snow", e)
            result = _summarize([], cfg)
    ws.snow_json.parent.mkdir(parents=True, exist_ok=True)
    ws.snow_json.write_text(json.dumps(result, indent=2))
    log.info(
        "snotel: median SNWD %.1f in over %d station(s) -> elevation shift %+.0f ft",
        result["median_snwd_in"],
        len(result["stations"]),
        result["band_shift_ft"],
    )
    return result


def _in_bbox(s: dict, bbox: tuple[float, float, float, float], pad: float) -> bool:
    lat, lon = s.get("latitude"), s.get("longitude")
    if lat is None or lon is None:
        return False
    minlon, minlat, maxlon, maxlat = bbox
    return (minlat - pad) <= lat <= (maxlat + pad) and (minlon - pad) <= lon <= (maxlon + pad)


_DATA_BATCH = 40  # stations per /data call; keeps the URL far below AWDB's limit


def _fetch(net: Net, bbox4326: tuple[float, float, float, float], cfg: Config) -> dict:
    state = (cfg.state or "*").upper()
    payload = net.fetch_json(
        f"{endpoints.AWDB}/stations",
        {"stationTriplets": f"*:{state}:SNTL", "activeOnly": "true"},
        source=SOURCE,
    )
    if not isinstance(payload, list):
        raise RuntimeError(f"unexpected /stations payload: {type(payload).__name__}")
    stations = [s for s in payload if s.get("stationTriplet") and _in_bbox(s, bbox4326, cfg.snow.station_bbox_pad_deg)]
    log.info("snotel: %d station(s) returned for %s, %d inside the padded AOI", len(payload), state, len(stations))
    if not stations:
        return _summarize([], cfg)

    today = _dt.date.today()
    latest: dict[str, dict] = {s["stationTriplet"]: {} for s in stations}
    triplets = list(latest)
    for i in range(0, len(triplets), _DATA_BATCH):
        data = net.fetch_json(
            f"{endpoints.AWDB}/data",
            {
                "stationTriplets": ",".join(triplets[i : i + _DATA_BATCH]),
                "elements": "SNWD,WTEQ",
                "duration": "DAILY",
                "beginDate": (today - _dt.timedelta(days=7)).isoformat(),
                "endDate": today.isoformat(),
            },
            source=SOURCE,
        )
        for entry in data if isinstance(data, list) else []:
            triplet = entry.get("stationTriplet")
            for element in entry.get("data") or []:
                code = ((element.get("stationElement") or {}).get("elementCode") or "").upper()
                values = [v.get("value") for v in element.get("values") or [] if v.get("value") is not None]
                if triplet in latest and code in ("SNWD", "WTEQ") and values:
                    latest[triplet][code] = float(values[-1])

    rows = [
        {
            "triplet": s["stationTriplet"],
            "name": s.get("name"),
            "elevation_ft": s.get("elevation"),
            "snwd_in": latest[s["stationTriplet"]].get("SNWD"),
            "wteq_in": latest[s["stationTriplet"]].get("WTEQ"),
        }
        for s in stations
    ]
    return _summarize(rows, cfg)


def band_top_ft(cfg: Config) -> float:
    """Top of the elevation optimum (highest breakpoint scoring 1.0)."""
    curve = cfg.factors.elevation.curve_elevation_ft
    tops = [float(x) for x, y in curve if float(y) >= 1.0]
    return max(tops) if tops else max(float(x) for x, _ in curve)


def estimate_snowline(rows: list[dict], depth_in: float) -> float | None:
    """Lowest station elevation holding >= depth_in, where at least half of the
    stations above it agree. None = no confirmed snow line at station elevations
    (snow, if any, is patchy or above every station)."""
    pts = sorted(
        (float(r["elevation_ft"]), float(r["snwd_in"]))
        for r in rows
        if r.get("snwd_in") is not None and r.get("elevation_ft") is not None
    )
    for i, (elev, depth) in enumerate(pts):
        if depth < depth_in:
            continue
        above = pts[i + 1 :]
        if not above or sum(d >= depth_in for _, d in above) >= len(above) / 2:
            return elev
    return None


def _summarize(rows: list[dict], cfg: Config) -> dict:
    reporting = [r["snwd_in"] for r in rows if r.get("snwd_in") is not None]
    median = float(np.median(reporting)) if reporting else 0.0
    xs = [p[0] for p in cfg.snow.band_shift_ft]
    ys = [p[1] for p in cfg.snow.band_shift_ft]
    top = band_top_ft(cfg)
    snowline = estimate_snowline(rows, cfg.snow.snowline_depth_in)
    if cfg.snow.method == "median":
        shift = float(np.interp(median, xs, ys))
        in_band = median >= 2 * cfg.snow.snowline_depth_in
    else:
        floor = min(ys)  # never shift further than the profile's own curve allows
        shift = max(floor, min(0.0, snowline - top)) if snowline is not None else 0.0
        in_band = snowline is not None and snowline <= top
    return {
        "stations": rows,
        "median_snwd_in": median,
        "snowline_ft": snowline,
        "band_top_ft": top,
        "band_shift_ft": float(shift),
        "snow_in_band": bool(in_band),
        "method": cfg.snow.method,
        "as_of": _dt.date.today().isoformat(),
        "no_data": not reporting,
    }


def load_snow(ws: Workspace) -> dict:
    return json.loads(ws.snow_json.read_text())
