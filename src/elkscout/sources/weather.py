"""Hunt-window weather -> work/weather.json.

Contract — fetch_weather(net, ws, points_lonlat, cfg) -> dict:
- Manual key "weather" first (same schema).
- Open-Meteo per point (16-day horizon). If the hunt window lies fully beyond
  the horizon, or any failure occurs (offline included), degrade to a
  climatology note — never raise.

Schemas written:
  {"mode": "forecast", "points": [{"lon","lat","daily": {...}}],
   "window_days_covered": int}
  {"mode": "climatology", "note": "..."}
"""

from __future__ import annotations

import datetime as _dt
import json
import logging

import requests

from .. import endpoints
from ..config import Config
from ..net import Net, OfflineError
from ..paths import Workspace

log = logging.getLogger("elkscout.weather")

SOURCE = "weather"

_DAILY_VARS = (
    "temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,"
    "wind_speed_10m_max,wind_direction_10m_dominant"
)

CLIMATOLOGY_NOTE = (
    "Hunt window is beyond the forecast horizon; plan on October climatology for "
    "central Idaho at elevation: hard frosts most mornings (teens to 20s F), "
    "afternoons in the 40s-50s, and a real chance of the season's first tracking "
    "snow above 6,500 ft. Fronts ride in on southwest wind; the day behind a front "
    "is cold, still, and the best glassing of the week. Re-run the pipeline inside "
    "16 days of your hunt for a real forecast."
)


def fetch_weather(net: Net, ws: Workspace, points_lonlat: list[tuple[float, float]], cfg: Config) -> dict:
    manual = ws.manual_path(SOURCE)
    if manual.exists():
        log.info("weather: using manual drop-in %s", manual)
        result = json.loads(manual.read_text())
    else:
        result = _fetch(net, points_lonlat, cfg)
    ws.weather_json.parent.mkdir(parents=True, exist_ok=True)
    ws.weather_json.write_text(json.dumps(result, indent=2))
    log.info("weather: mode=%s", result.get("mode"))
    return result


def _fetch(net: Net, points_lonlat: list[tuple[float, float]], cfg: Config) -> dict:
    today = _dt.date.today()
    horizon = today + _dt.timedelta(days=15)
    if cfg.hunt_window.start > horizon:
        return {"mode": "climatology", "note": CLIMATOLOGY_NOTE}
    try:
        points = []
        for lon, lat in points_lonlat:
            payload = net.fetch_json(
                endpoints.OPEN_METEO,
                {
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "daily": _DAILY_VARS,
                    "timezone": "America/Boise",
                    "forecast_days": 16,
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                    "precipitation_unit": "inch",
                },
                source=SOURCE,
            )
            points.append({"lon": lon, "lat": lat, "daily": payload.get("daily") or {}})
        covered = sum(
            1
            for d in (points[0]["daily"].get("time") or [])
            if cfg.hunt_window.start <= _dt.date.fromisoformat(d) <= cfg.hunt_window.end
        )
        return {"mode": "forecast", "points": points, "window_days_covered": covered}
    except (OfflineError, requests.RequestException, RuntimeError, ValueError) as e:
        log.warning("weather: unavailable (%s); using climatology note", e)
        return {"mode": "climatology", "note": CLIMATOLOGY_NOTE}


def load_weather(ws: Workspace) -> dict:
    return json.loads(ws.weather_json.read_text())
