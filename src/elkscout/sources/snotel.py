"""SNOTEL snow state -> work/snow.json.

Contract — fetch_snow(net, ws, bbox4326, cfg):
1. ws.manual_path("snow") if present (same JSON schema as below) -> copy to
   ws.snow_json and return it parsed.
2. NRCS AWDB REST (endpoints.AWDB):
   - GET /stations with params networkCds=SNTL, activeOnly=true and the bbox
     params minLatitude/maxLatitude/minLongitude/maxLongitude (bbox4326 padded
     by cfg.snow.station_bbox_pad_deg). Response: list of station dicts with
     stationTriplet, name, elevation (ft), latitude, longitude.
   - GET /data with stationTriplets=<comma-joined>, elements=SNWD,WTEQ,
     duration=DAILY, beginDate/endDate = today-7d..today (format YYYY-MM-DD),
     periodRef=END. Take each station's most recent non-null SNWD (inches).
3. Compute median_snwd_in over stations (0.0 if no stations/data — with a
   "no_data" flag) and band_shift_ft = interp on cfg.snow.band_shift_ft
   (clamped; note shift values are <= 0).
4. Write ws.snow_json:
   {"stations": [{"triplet","name","elevation_ft","snwd_in","wteq_in"}...],
    "median_snwd_in": float, "band_shift_ft": float, "as_of": "YYYY-MM-DD",
    "no_data": bool}
   and return the dict.
Offline miss -> write the zero-snow fallback dict with no_data=true INSTEAD of
raising (snow is an enhancer, not a required layer) — but only when offline;
online HTTP failures should retry then fall back the same way with a warning.
"""

from __future__ import annotations

from ..config import Config
from ..net import Net
from ..paths import Workspace


def fetch_snow(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float], cfg: Config) -> dict:
    raise NotImplementedError
