"""SNOTEL snow state -> work/snow.json.

Contract — fetch_snow(net, ws, bbox4326, cfg) -> dict:
1. ws.manual_path("snow") if present (same schema) -> copied to ws.snow_json.
2. NRCS AWDB REST: /stations (networkCds=SNTL, activeOnly=true, bbox padded by
   cfg.snow.station_bbox_pad_deg), then /data (elements SNWD,WTEQ, DAILY, last
   7 days); most recent non-null value per station.
3. median_snwd_in over reporting stations (0.0 + no_data flag when none), and
   band_shift_ft interpolated from cfg.snow.band_shift_ft (values <= 0).

Written schema:
  {"stations": [{"triplet","name","elevation_ft","snwd_in","wteq_in"}...],
   "median_snwd_in": float, "band_shift_ft": float, "as_of": "YYYY-MM-DD",
   "no_data": bool}

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


def _fetch(net: Net, bbox4326: tuple[float, float, float, float], cfg: Config) -> dict:
    pad = cfg.snow.station_bbox_pad_deg
    minlon, minlat, maxlon, maxlat = bbox4326
    stations = net.fetch_json(
        f"{endpoints.AWDB}/stations",
        {
            "networkCds": "SNTL",
            "activeOnly": "true",
            "minLatitude": minlat - pad,
            "maxLatitude": maxlat + pad,
            "minLongitude": minlon - pad,
            "maxLongitude": maxlon + pad,
        },
        source=SOURCE,
    )
    if not isinstance(stations, list):
        raise RuntimeError(f"unexpected /stations payload: {type(stations).__name__}")
    triplets = [s["stationTriplet"] for s in stations if s.get("stationTriplet")]
    if not triplets:
        return _summarize([], cfg)

    today = _dt.date.today()
    data = net.fetch_json(
        f"{endpoints.AWDB}/data",
        {
            "stationTriplets": ",".join(triplets),
            "elements": "SNWD,WTEQ",
            "duration": "DAILY",
            "beginDate": (today - _dt.timedelta(days=7)).isoformat(),
            "endDate": today.isoformat(),
        },
        source=SOURCE,
    )
    latest = {t: {} for t in triplets}
    for entry in data if isinstance(data, list) else []:
        triplet = entry.get("stationTriplet")
        for element in entry.get("data") or []:
            code = ((element.get("stationElement") or {}).get("elementCode") or "").upper()
            values = [v.get("value") for v in element.get("values") or [] if v.get("value") is not None]
            if triplet in latest and code in ("SNWD", "WTEQ") and values:
                latest[triplet][code] = float(values[-1])

    rows = []
    for s in stations:
        t = s.get("stationTriplet")
        rows.append(
            {
                "triplet": t,
                "name": s.get("name"),
                "elevation_ft": s.get("elevation"),
                "snwd_in": latest.get(t, {}).get("SNWD"),
                "wteq_in": latest.get(t, {}).get("WTEQ"),
            }
        )
    return _summarize(rows, cfg)


def _summarize(rows: list[dict], cfg: Config) -> dict:
    reporting = [r["snwd_in"] for r in rows if r.get("snwd_in") is not None]
    median = float(np.median(reporting)) if reporting else 0.0
    xs = [p[0] for p in cfg.snow.band_shift_ft]
    ys = [p[1] for p in cfg.snow.band_shift_ft]
    shift = float(np.interp(median, xs, ys))
    return {
        "stations": rows,
        "median_snwd_in": median,
        "band_shift_ft": shift,
        "as_of": _dt.date.today().isoformat(),
        "no_data": not reporting,
    }


def load_snow(ws: Workspace) -> dict:
    return json.loads(ws.snow_json.read_text())
