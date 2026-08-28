"""Land ownership (public vs private) -> work/ownership.geojson (EPSG:4326).

Contract — fetch_ownership(net, ws, bbox4326):
1. ws.manual_path("ownership") if present.
2. endpoints.BLM_SMA: pick the polygon layer (from ?f=json, the layer whose
   name contains 'Surface Management Agency'; if ambiguous use layer 1's parent
   behavior — discover, don't hardcode). Query bbox, out_fields '*',
   max_allowable_offset ~0.0003 deg (SMA polygons are huge).
3. Normalize: add a string column `agency` from the first existing field among
   ADMIN_AGENCY_CODE / ADMIN_UNIT_NAME / ADMIN_DEPT_CODE / MGMT_AGNCY / SMA
   (fall back to 'UNKNOWN'), and a boolean column `public` — True unless agency
   text (uppercased) contains 'PRIVATE' or equals 'PVT'.
4. Write ws.ownership_geojson.

factors.py treats cells with no ownership polygon at all as PRIVATE=False?
No — as public=True (federal land dominates unit 33 and SMA has slivers of
no-data); the README documents this default and hunters must verify parcels.
Offline miss -> OfflineMissError("ownership", ws).
"""

from __future__ import annotations

from ..net import Net
from ..paths import Workspace


def fetch_ownership(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float]) -> None:
    raise NotImplementedError
