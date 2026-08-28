"""Wildfire burn perimeters (MTBS) -> work/burns.geojson (EPSG:4326).

Contract — fetch_burns(net, ws, bbox4326, hunt_year):
1. ws.manual_path("burns") if present.
2. endpoints.MTBS layer MTBS_LAYER (63, all-years perimeters). Query bbox with
   max_allowable_offset ~0.0003. Field names vary by vintage; discover:
   - year: first existing of FIRE_YEAR / Fire_Year / YEAR / Ig_Date-derived
     (Ig_Date may be epoch-ms or 'YYYY-MM-DD' — handle both).
   - name: first existing of FIRE_NAME / Fire_Name / INCIDENT / Event_ID.
3. Filter to hunt_year - 22 <= year <= hunt_year - 1 (the burn-age curve spans
   2-20 yr; fetch a little wide, scoring clips).
4. Normalize to columns: `year` (int), `fire_name` (str, title-cased).
5. Write ws.burns_geojson. Empty is allowed (no burns near AOI).
Offline miss -> OfflineMissError("burns", ws).
"""

from __future__ import annotations

from ..net import Net
from ..paths import Workspace


def fetch_burns(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float], hunt_year: int) -> None:
    raise NotImplementedError
