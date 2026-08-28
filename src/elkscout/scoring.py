"""Suitability scoring: measurements -> [0,1] factor scores -> composites.

Contract — run_scoring(ws, cfg):
Inputs: dem (sources.dem.load_dem), terrain (terrain.load_terrain),
factors (factors.load_factors), snow (json at ws.snow_json).

1. Factor scores, each float32 in [0,1] (NaN allowed outside data), using
   curves.apply_curve / curves.aspect_score and cfg.factors:

   - elevation: dem_ft = dem * 3.28084; curve = cfg.factors.elevation
     .curve_elevation_ft with every x SHIFTED by snow["band_shift_ft"]
     (a value <= 0) via curves.shift_curve_x.
   - security: curve_dist_motorized_km on dist_motorized_m / 1000.
   - bedding: geometric mean of [aspect_score(aspect_deg, center, exponent)
     with NaN(flat)->0.5, curve_canopy_pct(canopy), curve_slope_pct(slope_pct)],
     then +bench_bonus where bench (|tpi300| < std(tpi300 over unit) AND
     tpi1000 > 0), then *0.5 where slope_pos < slope_position_min, clip [0,1].
   - feed: base = max(feed_class, curve_burn_age_yr(burn_age_yr) [NaN->0],
     riparian); edge_mult = 1.0 where edge_dist_m <= edge_dist_m cfg else
     interior_mult; aspect_mult = (1-aspect_mix) + aspect_mix *
     aspect_score(aspect_deg, feed.aspect_center_deg) [flat->0.7];
     feed = clip(base * edge_mult * aspect_mult, 0, 1).
   - water: curve_dist_water_m on dist_water_m.
   - pressure: curve_dist_trailhead_km on dist_trailhead_m / 1000.

2. hard_mask = unit * public * (slope_pct <= cfg.masks.max_slope_pct)
   * (1 - open_water); (public only if cfg.masks.public_only).

3. composite = (sum w_i * f_i / sum w_i) * hard_mask, NaN->0 outside data.

4. Type scores (float32): for each type in cfg.type_profiles, the re-weighted
   sum * hard_mask. Plus "CAMP": composite-based utility = mean(security,
   water score) * hard_mask, ZEROED where slope_pct > cfg.camp.max_slope_pct
   or dist_water_m > cfg.camp.max_water_dist_m or dist_trailhead_m/1000
   outside cfg.camp.trailhead_km band.

5. Write:
   - ws.composite_tif: bands {"composite", "f_elevation", "f_security",
     "f_bedding", "f_feed", "f_water", "f_pressure", "hard_mask"}.
   - ws.type_scores_tif: bands {"BED","FEED","WATER","CAMP"}.
   - QA PNGs (one per band above) into ws.qa via save_qa_png (simple
     matplotlib-free rendering: normalize -> PIL? No PIL dep — use
     folium-free approach: write with rasterio to PNG driver, 0-255 scaled).

load_scores(ws) -> ((composite_bands, type_bands), Grid).
"""

from __future__ import annotations

import numpy as np

from .config import Config
from .grid import Grid, read_raster
from .paths import Workspace


def run_scoring(ws: Workspace, cfg: Config) -> None:
    raise NotImplementedError


def load_scores(ws: Workspace) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], Grid]:
    comp, grid = read_raster(ws.composite_tif)
    types, _ = read_raster(ws.type_scores_tif)
    return comp, types, grid
