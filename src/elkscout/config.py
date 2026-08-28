"""Typed configuration for the scoring model (loaded from configs/*.yaml).

The YAML is the authoritative, human-argued elk model; this module only
validates shape and ranges. See configs/unit33_oct_rifle.yaml for semantics.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from .curves import validate_curve

CurvePts = list[list[float]]


def _curve_field(v: CurvePts) -> CurvePts:
    validate_curve(v)
    return v


class HuntWindow(BaseModel):
    start: _dt.date
    end: _dt.date

    @model_validator(mode="after")
    def _order(self) -> "HuntWindow":
        if self.end < self.start:
            raise ValueError("hunt_window.end before start")
        return self


class GridCfg(BaseModel):
    res_m: float = 30.0
    epsg: int = 32611
    buffer_m: float = 2000.0


class SnowCfg(BaseModel):
    band_shift_ft: CurvePts
    station_bbox_pad_deg: float = 0.25

    _v = field_validator("band_shift_ft")(classmethod(lambda cls, v: v if _shift_ok(v) else v))


def _shift_ok(v: CurvePts) -> bool:
    xs = [p[0] for p in v]
    if any(b <= a for a, b in zip(xs, xs[1:])):
        raise ValueError("snow.band_shift_ft x (inches) must be strictly increasing")
    return True


class ElevationFactor(BaseModel):
    weight: float = Field(ge=0)
    curve_elevation_ft: CurvePts

    _v = field_validator("curve_elevation_ft")(classmethod(lambda cls, v: _curve_field(v)))


class SecurityFactor(BaseModel):
    weight: float = Field(ge=0)
    curve_dist_motorized_km: CurvePts

    _v = field_validator("curve_dist_motorized_km")(classmethod(lambda cls, v: _curve_field(v)))


class BeddingFactor(BaseModel):
    weight: float = Field(ge=0)
    aspect_center_deg: float = 22.0
    aspect_exponent: float = 1.5
    curve_canopy_pct: CurvePts
    curve_slope_pct: CurvePts
    bench_bonus: float = 0.25
    slope_position_min: float = 0.5

    _v1 = field_validator("curve_canopy_pct")(classmethod(lambda cls, v: _curve_field(v)))
    _v2 = field_validator("curve_slope_pct")(classmethod(lambda cls, v: _curve_field(v)))


class FeedFactor(BaseModel):
    weight: float = Field(ge=0)
    curve_burn_age_yr: CurvePts
    edge_dist_m: float = 150.0
    interior_mult: float = Field(default=0.6, ge=0, le=1)
    aspect_center_deg: float = 135.0
    aspect_mix: float = Field(default=0.4, ge=0, le=1)

    _v = field_validator("curve_burn_age_yr")(classmethod(lambda cls, v: _curve_field(v)))


class WaterFactor(BaseModel):
    weight: float = Field(ge=0)
    curve_dist_water_m: CurvePts

    _v = field_validator("curve_dist_water_m")(classmethod(lambda cls, v: _curve_field(v)))


class PressureFactor(BaseModel):
    weight: float = Field(ge=0)
    curve_dist_trailhead_km: CurvePts

    _v = field_validator("curve_dist_trailhead_km")(classmethod(lambda cls, v: _curve_field(v)))


class FactorsCfg(BaseModel):
    elevation: ElevationFactor
    security: SecurityFactor
    bedding: BeddingFactor
    feed: FeedFactor
    water: WaterFactor
    pressure: PressureFactor

    def weights(self) -> dict[str, float]:
        return {name: getattr(self, name).weight for name in FACTOR_NAMES}


FACTOR_NAMES = ["elevation", "security", "bedding", "feed", "water", "pressure"]


class MasksCfg(BaseModel):
    public_only: bool = True
    max_slope_pct: float = 60.0


class CampCfg(BaseModel):
    max_slope_pct: float = 10.0
    max_water_dist_m: float = 400.0
    trailhead_km: list[float]

    @field_validator("trailhead_km")
    @classmethod
    def _pair(cls, v: list[float]) -> list[float]:
        if len(v) != 2 or v[0] >= v[1]:
            raise ValueError("camp.trailhead_km must be [min, max]")
        return v


class SaddleCfg(BaseModel):
    dem_downsample_m: float = 90.0
    travel_max_km: float = 2.0


class GlassCfg(BaseModel):
    viewshed_radius_km: float = 2.5
    max_candidates: int = 60


WAYPOINT_TYPES = ["BED", "FEED", "WATER", "SADDLE", "GLASS", "CAMP", "ACCESS"]


class WaypointsCfg(BaseModel):
    min_spacing_m: float = 700.0
    cross_type_spacing_m: float = 300.0
    score_floor: float = Field(default=0.45, ge=0, le=1)
    counts: dict[str, int]
    saddle: SaddleCfg = SaddleCfg()
    glass: GlassCfg = GlassCfg()

    @field_validator("counts")
    @classmethod
    def _known_types(cls, v: dict[str, int]) -> dict[str, int]:
        unknown = set(v) - set(WAYPOINT_TYPES)
        if unknown:
            raise ValueError(f"unknown waypoint types in counts: {sorted(unknown)}")
        return v


class HuntAreasCfg(BaseModel):
    min_waypoints: int = 6
    min_areas: int = 4
    max_areas: int = 8


class OutputsCfg(BaseModel):
    gpx_max_bytes: int = 4_000_000
    gpx_max_waypoints: int = 3000
    desc_max_chars: int = 450


class Config(BaseModel):
    profile: str
    unit: str
    hunt_window: HuntWindow
    grid: GridCfg = GridCfg()
    snow: SnowCfg
    factors: FactorsCfg
    masks: MasksCfg = MasksCfg()
    type_profiles: dict[str, dict[str, float]]
    camp: CampCfg
    waypoints: WaypointsCfg
    hunt_areas: HuntAreasCfg = HuntAreasCfg()
    outputs: OutputsCfg = OutputsCfg()

    @field_validator("type_profiles")
    @classmethod
    def _profiles_ok(cls, v: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        for t, weights in v.items():
            if t not in WAYPOINT_TYPES:
                raise ValueError(f"type_profiles: unknown waypoint type {t!r}")
            unknown = set(weights) - set(FACTOR_NAMES)
            if unknown:
                raise ValueError(f"type_profiles[{t}]: unknown factors {sorted(unknown)}")
            total = sum(weights.values())
            if total <= 0:
                raise ValueError(f"type_profiles[{t}]: weights sum to {total}")
        return v


def load_config(path: str | Path) -> Config:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config.model_validate(raw)
