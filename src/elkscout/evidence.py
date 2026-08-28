"""Per-waypoint evidence: sampled physical facts + a human-readable sentence.

Contract:
- build_evidence(row, col, wp_type, grid, dem, terrain, factors, vectors) -> dict
  with keys (None where unknown):
    elevation_ft (int), aspect_deg (float|None), aspect_compass ("N".."NW"|None),
    slope_pct (int), tpi_class ("bench"|"saddle"|"knob"|"slope"|"valley"),
    canopy_pct (int|None), dist_motorized_mi (float, 1dp),
    dist_trailhead_mi (float|None), dist_water_mi (float, 2dp),
    burn_name (str|None), burn_year (int|None),
    nearest_water_name (str|None — GNIS_NAME of nearest water_lines feature
    within 2 km, if named), agency (str|None), huc12_name (str|None).
  vectors is a dict of loaded GeoDataFrames: {"water_lines", "burns",
  "ownership", "huc12"} (any may be empty).
  tpi_class from terrain: bench if |tpi300|<sigma and tpi1000>0; saddle/knob
  are assigned by the caller for SADDLE/GLASS types (pass wp_type through);
  else slope (tpi300<...) — keep the rule simple and documented in code.

- render_sentence(ev: dict, wp_type: str) -> str, e.g.:
    BED:  "North-facing bench at 7,410 ft, 62% canopy, 24% slope; 1.8 mi from
           nearest motorized route, 0.4 mi to water."
    FEED: "...edge of 2016 Pioneer Fire burn..." when burn_name/year present.
    Include burn/water names when available; omit clauses whose data is None.
  ASCII only. No trailing whitespace. <= ~400 chars.

- short_tag(ev, wp_type) -> terse name fragment used in waypoint names:
  BED->"N-bench"/"NE-timber", FEED->"burn-edge"/"meadow", WATER->"spring"/"creek",
  SADDLE->"saddle", GLASS->"glass", CAMP->"camp", ACCESS->"TH". <= 10 chars.
"""

from __future__ import annotations


def build_evidence(row, col, wp_type, grid, dem, terrain, factors, vectors) -> dict:
    raise NotImplementedError


def render_sentence(ev: dict, wp_type: str) -> str:
    raise NotImplementedError


def short_tag(ev: dict, wp_type: str) -> str:
    raise NotImplementedError
