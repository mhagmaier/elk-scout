"""Suitability scoring: measurement rasters -> [0,1] factor scores -> composites.

Inputs: work/dem.tif, work/terrain.tif, work/canopy.tif, work/factors.tif,
work/snow.json. Outputs:

- work/composite.tif: bands composite, f_elevation, f_security, f_bedding,
  f_feed, f_water, f_pressure, hard_mask
- work/type_scores.tif: bands BED, FEED, WATER, CAMP (per-type re-weighted
  composites; SADDLE/GLASS/ACCESS are candidate-driven in waypoints.py)
- QA grayscale PNGs per band under data/out/qa/

Factor semantics are defined by the curves in the YAML profile; see
configs/unit33_oct_rifle.yaml. The elevation optimum shifts DOWN by the
SNOTEL-derived band_shift_ft. Hard mask: inside unit, public (if configured),
slope below the cliff threshold, not open water.
"""

from __future__ import annotations

import json
import logging
import warnings

import numpy as np
import rasterio

from .config import Config
from .curves import apply_curve, aspect_score, shift_curve_x
from .factors import NODATA_U8, load_factors
from .grid import Grid, read_raster, write_raster
from .paths import Workspace
from .sources.dem import load_dem
from .terrain import load_terrain

log = logging.getLogger("elkscout.scoring")

M_TO_FT = 3.28084
COMPOSITE_BANDS = [
    "composite",
    "f_elevation",
    "f_security",
    "f_bedding",
    "f_feed",
    "f_water",
    "f_pressure",
    "hard_mask",
]
TYPE_BANDS = ["BED", "FEED", "WATER", "CAMP"]


def _geometric_mean(parts: list[np.ndarray]) -> np.ndarray:
    stack = np.stack([np.clip(p, 1e-6, 1.0) for p in parts])
    return np.exp(np.mean(np.log(stack), axis=0)).astype(np.float32)


def _factor_scores(ws: Workspace, cfg: Config) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], Grid]:
    dem, grid = load_dem(ws)
    terrain, _ = load_terrain(ws)
    fx, _ = load_factors(ws)
    canopy_u8 = read_raster(ws.canopy_tif)[0]["canopy"]
    canopy = np.where(canopy_u8 == NODATA_U8, np.nan, canopy_u8.astype(np.float32))
    snow = json.loads(ws.snow_json.read_text())

    shift = float(snow.get("band_shift_ft", 0.0))
    elev_curve = shift_curve_x(cfg.factors.elevation.curve_elevation_ft, shift)
    f_elevation = apply_curve(dem * M_TO_FT, elev_curve)

    f_security = apply_curve(fx["dist_motorized_m"] / 1000.0, cfg.factors.security.curve_dist_motorized_km)

    b = cfg.factors.bedding
    aspect_center = b.aspect_center_deg
    if b.snow_aspect_center_deg is not None:
        if snow.get("snow_in_band"):
            aspect_center = b.snow_aspect_center_deg
            log.info("scoring: snow has reached the elk band -> bedding aspect %.0f deg (sunny slopes)", aspect_center)
        else:
            log.info("scoring: snow not in the elk band -> bedding stays on %.0f deg (dark timber)", aspect_center)
    aspect_sub = aspect_score(terrain["aspect_deg"], aspect_center, b.aspect_exponent)
    aspect_sub = np.where(np.isnan(aspect_sub), 0.5, aspect_sub)  # flat/no-data -> neutral
    canopy_sub = np.nan_to_num(apply_curve(canopy, b.curve_canopy_pct), nan=0.0)
    slope_sub = np.nan_to_num(apply_curve(terrain["slope_pct"], b.curve_slope_pct), nan=0.0)
    bedding = _geometric_mean([aspect_sub, canopy_sub, slope_sub])
    tpi300 = terrain["tpi300"]
    unit_mask = fx["unit"] > 0
    sigma = float(np.nanstd(tpi300[unit_mask])) if unit_mask.any() else float(np.nanstd(tpi300))
    bench = (np.abs(np.nan_to_num(tpi300, nan=np.inf)) < sigma) & (np.nan_to_num(terrain["tpi1000"], nan=-1) > 0)
    # Scale the bench bonus by the canopy sub-score: a bench amplifies real
    # dark-timber bedding, it must not create a bedding floor in treeless cells.
    bedding = np.clip(bedding + b.bench_bonus * bench * canopy_sub, 0.0, 1.0)
    f_bedding = np.where(terrain["slope_pos"] < b.slope_position_min, 0.5 * bedding, bedding).astype(np.float32)

    f = cfg.factors.feed
    burn_score = np.nan_to_num(apply_curve(fx["burn_age_yr"], f.curve_burn_age_yr), nan=0.0)
    base = np.maximum.reduce([fx["feed_class"], burn_score, fx["riparian"]])
    edge_mult = np.where(fx["edge_dist_m"] <= f.edge_dist_m, 1.0, f.interior_mult)
    aspect_feed = aspect_score(terrain["aspect_deg"], f.aspect_center_deg)
    aspect_feed = np.where(np.isnan(aspect_feed), 0.7, aspect_feed)
    aspect_mult = (1.0 - f.aspect_mix) + f.aspect_mix * aspect_feed
    f_feed = np.clip(base * edge_mult * aspect_mult, 0.0, 1.0).astype(np.float32)

    f_water = apply_curve(fx["dist_water_m"], cfg.factors.water.curve_dist_water_m)
    f_pressure = apply_curve(fx["dist_trailhead_m"] / 1000.0, cfg.factors.pressure.curve_dist_trailhead_km)

    scores = {
        "elevation": f_elevation,
        "security": f_security,
        "bedding": f_bedding,
        "feed": f_feed,
        "water": f_water,
        "pressure": f_pressure,
    }
    return scores, fx, grid


def _hard_mask(fx: dict[str, np.ndarray], terrain_slope: np.ndarray, cfg: Config) -> np.ndarray:
    mask = fx["unit"].astype(np.float32)
    mask *= (np.nan_to_num(terrain_slope, nan=cfg.masks.max_slope_pct + 1) <= cfg.masks.max_slope_pct)
    mask *= 1.0 - fx["open_water"]
    if cfg.masks.public_only:
        mask *= fx["public"]
    return np.clip(mask, 0.0, 1.0)


def _weighted(scores: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    total = sum(weights.values())
    acc = np.zeros(next(iter(scores.values())).shape, dtype=np.float32)
    for name, w in weights.items():
        acc += w * np.nan_to_num(scores[name], nan=0.0)
    return acc / total


def run_scoring(ws: Workspace, cfg: Config) -> None:
    scores, fx, grid = _factor_scores(ws, cfg)
    terrain, _ = load_terrain(ws)
    hard = _hard_mask(fx, terrain["slope_pct"], cfg)

    composite = (_weighted(scores, cfg.factors.weights()) * hard).astype(np.float32)

    type_scores: dict[str, np.ndarray] = {}
    for t, profile in cfg.type_profiles.items():
        type_scores[t] = (_weighted(scores, profile) * hard).astype(np.float32)

    camp = 0.5 * (np.nan_to_num(scores["security"], nan=0.0) + np.nan_to_num(scores["water"], nan=0.0))
    slope = np.nan_to_num(terrain["slope_pct"], nan=999.0)
    th_km = fx["dist_trailhead_m"] / 1000.0
    camp_ok = (
        (slope <= cfg.camp.max_slope_pct)
        & (fx["dist_water_m"] <= cfg.camp.max_water_dist_m)
        & (th_km >= cfg.camp.trailhead_km[0])
        & (th_km <= cfg.camp.trailhead_km[1])
    )
    type_scores["CAMP"] = (camp * camp_ok * hard).astype(np.float32)

    comp_bands = {
        "composite": composite,
        "f_elevation": scores["elevation"],
        "f_security": scores["security"],
        "f_bedding": scores["bedding"],
        "f_feed": scores["feed"],
        "f_water": scores["water"],
        "f_pressure": scores["pressure"],
        "hard_mask": hard,
    }
    write_raster(ws.composite_tif, grid, comp_bands)
    write_raster(ws.type_scores_tif, grid, {t: type_scores[t] for t in TYPE_BANDS})

    for name, arr in {**comp_bands, **{t: type_scores[t] for t in TYPE_BANDS}}.items():
        _qa_png(ws, name, arr)
    log.info(
        "scoring: composite mean %.3f over unit (max %.3f); wrote %s, %s + QA PNGs",
        float(composite[fx["unit"] > 0].mean()) if (fx["unit"] > 0).any() else 0.0,
        float(composite.max(initial=0.0)),
        ws.composite_tif,
        ws.type_scores_tif,
    )


def _qa_png(ws: Workspace, name: str, arr: np.ndarray) -> None:
    ws.qa.mkdir(parents=True, exist_ok=True)
    u8 = (np.clip(np.nan_to_num(arr, nan=0.0), 0.0, 1.0) * 255).astype("uint8")
    path = ws.qa / f"qa_{name}.png"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", rasterio.errors.NotGeoreferencedWarning)
        with rasterio.open(
            path, "w", driver="PNG", width=u8.shape[1], height=u8.shape[0], count=1, dtype="uint8"
        ) as dst:
            dst.write(u8, 1)


def load_scores(ws: Workspace) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], Grid]:
    comp, grid = read_raster(ws.composite_tif)
    types, _ = read_raster(ws.type_scores_tif)
    return comp, types, grid
