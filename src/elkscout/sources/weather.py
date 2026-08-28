"""Hunt-window weather -> work/weather.json.

Contract — fetch_weather(net, ws, points_lonlat, cfg):
- points_lonlat: [(lon, lat), ...] representative points (unit centroid et al).
- Manual key "weather" first (same schema) -> copy to ws.weather_json.
- Open-Meteo (endpoints.OPEN_METEO) per point: daily=temperature_2m_max,
  temperature_2m_min,precipitation_sum,snowfall_sum,wind_speed_10m_max,
  wind_direction_10m_dominant, timezone=America/Boise, forecast_days=16.
- If the hunt window (cfg.hunt_window) is fully beyond the 16-day horizon,
  DON'T fail: write {"mode": "climatology"} with a fixed October-climatology
  note (cold mornings ~20s F, afternoons 50s, chance of first tracking snow,
  prevailing SW winds ahead of fronts) — the briefing renders that instead.
- Otherwise write {"mode": "forecast", "points": [{"lon","lat","daily": {...}}],
  "window_days_covered": int}. Any HTTP failure degrades to the climatology
  dict with a warning rather than failing the pipeline (offline too).
Always returns the dict written.
"""

from __future__ import annotations

from ..config import Config
from ..net import Net
from ..paths import Workspace


def fetch_weather(net: Net, ws: Workspace, points_lonlat: list[tuple[float, float]], cfg: Config) -> dict:
    raise NotImplementedError
