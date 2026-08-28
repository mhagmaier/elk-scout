"""Waypoint extraction, typing, and hunt-area clustering.

Contract — run_waypoints(ws, cfg):
Inputs: Grid (ws.grid_json), dem, terrain, factors, composite + type scores,
vectors (trailheads, huc12, burns, ownership, water), snow.json (only passed
through to evidence? no — evidence samples rasters itself).

Extraction:
- BED / FEED / WATER / CAMP: on each band of ws.type_scores_tif —
  candidate cells = local maxima (scipy.ndimage.maximum_filter, ~5-cell window)
  with value >= cfg.waypoints.score_floor. WATER candidates additionally must
  have dist_water_m <= 300. Order all candidates by score desc, greedy-select
  up to cfg.waypoints.counts[t] with same-type spacing >=
  cfg.waypoints.min_spacing_m and cross-type spacing >=
  cfg.waypoints.cross_type_spacing_m (checked against ALL already-selected
  waypoints of every type, SADDLE/GLASS/ACCESS included — select those first?
  No: selection order is BED, FEED, WATER, SADDLE, GLASS, CAMP, ACCESS, greedy
  within each).
- SADDLE: downsample dem to cfg.waypoints.saddle.dem_downsample_m (block mean);
  ridge mask = top decile of tpi1000 (downsampled); skeletonize
  (skimage.morphology.skeletonize); candidates = skeleton cells that are local
  minima of dem along the skeleton (min of dem among skeleton cells in a 3x3
  neighborhood); require composite >= score_floor * 0.6 at the cell AND both a
  BED-score cell >= 0.5 and a FEED-score cell >= 0.5 within
  cfg.waypoints.saddle.travel_max_km. Score = composite at cell.
- GLASS: candidates = top cfg.waypoints.glass.max_candidates knobs by tpi1000
  (downsampled grid, spaced >= 500 m); for each, radial line-of-sight viewshed
  on the downsampled dem out to viewshed_radius_km (e.g. 48 azimuths, observer
  +2 m): glass_score = mean FEED type-score over visible cells; keep by
  glass_score. Store the score.
- ACCESS: trailhead points ranked by mean composite within 2 km. If no
  trailheads exist, skip the type.

All selected cells -> point geometries at cell centers (grid.xy), then
EPSG:4326 via grid.xy_to_lonlat.

Hunt areas:
- Assign each waypoint its HUC12 polygon (spatial join); waypoints outside any
  HUC12 join to the nearest one. Aggregate HUC12s by waypoint count; merge any
  HUC12 with < cfg.hunt_areas.min_waypoints into its most-waypoint-heavy
  neighbor (fallback: nearest); rank merged areas by mean waypoint score; keep
  at most max_areas (drop the weakest areas AND their waypoints — log the drop);
  if fewer than min_areas exist, that's fine (small AOIs).
- Area name = HUC12 `name` of the dominant member (title case); slug =
  lowercase-hyphenated. If huc12 layer is empty (synth fixtures), fall back to
  a 2x2 quadrant split of the AOI named NW/NE/SW/SE.

Naming: type codes B/F/W/S/G/C/A; name = f"{code}{area_rank}-{seq:02d} {tag} {elev_ft}"
where tag is a terse descriptor from evidence (e.g. "N-bench", "burn-edge",
"saddle", "glass", "spring", "camp", "TH") and seq counts within (area, type)
by score. Names must stay <= 32 chars, ASCII.

Evidence: for each waypoint call evidence.build_evidence(...) then
evidence.render_sentence(...); store the dict as a JSON string in property
"evidence_json" and the sentence in "desc" (truncated to
cfg.outputs.desc_max_chars).

Outputs:
- ws.waypoints_geojson (EPSG:4326 points), properties EXACTLY:
  wp_type, name, score (float, 3dp), desc, evidence_json, hunt_area,
  area_slug, area_rank (int), elevation_ft (int).
- ws.hunt_areas_geojson (EPSG:4326 polygons), properties:
  name, slug, rank, n_waypoints, mean_score.
"""

from __future__ import annotations

from .config import Config
from .paths import Workspace


def run_waypoints(ws: Workspace, cfg: Config) -> None:
    raise NotImplementedError
