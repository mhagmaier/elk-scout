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


class BoundarySource(BaseModel):
    """Where a unit's boundary polygon comes from (an ArcGIS feature service).

    Carried inside generated configs so a profile is self-contained; when a
    config has no `boundary:` block, sources.boundary falls back to the
    built-in Idaho Fish & Game service.
    """

    base_url: str  # ArcGIS REST service URL (…/MapServer), no trailing /query
    alt_urls: list[str] = []
    layer: int | None = None  # explicit layer id; None -> discover via layer_hint
    layer_hint: str | None = None  # substring match on layer name (case-insensitive)
    unit_field: str | None = None  # exact field name; None -> discovery
    unit_field_hints: list[str] = []  # tried (as substrings) before the generic heuristic
    unit_value_format: str = "{unit}"  # e.g. "{unit:0>2}" for zero-padded unit numbers


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
    # How snow moves the elevation band:
    #   snowline - estimate the snow line from the stations (lowest elevation
    #              holding >= snowline_depth_in, confirmed by stations above
    #              it) and pull the band's top down to it only when snow has
    #              actually reached the elk band. Robust when the stations sit
    #              far above the band (common in Colorado).
    #   median   - the original rule: median depth -> band_shift_ft curve.
    method: str = "snowline"
    snowline_depth_in: float = 6.0

    _v = field_validator("band_shift_ft")(classmethod(lambda cls, v: v if _shift_ok(v) else v))

    @field_validator("method")
    @classmethod
    def _method_ok(cls, v: str) -> str:
        if v not in ("snowline", "median"):
            raise ValueError(f"snow.method must be snowline|median, got {v!r}")
        return v


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
    # Aspect preference once snow has reached the elk band (late-season
    # thermal bedding on sunny faces). None = never switch.
    snow_aspect_center_deg: float | None = None

    _v1 = field_validator("curve_canopy_pct")(classmethod(lambda cls, v: _curve_field(v)))
    _v2 = field_validator("curve_slope_pct")(classmethod(lambda cls, v: _curve_field(v)))


class FeedFactor(BaseModel):
    weight: float = Field(ge=0)
    curve_burn_age_yr: CurvePts
    edge_dist_m: float = 150.0
    interior_mult: float = Field(default=0.6, ge=0, le=1)
    aspect_center_deg: float = 135.0
    aspect_mix: float = Field(default=0.4, ge=0, le=1)
    # Per-NLCD-class feed quality in [0,1]; default reproduces the original
    # binary behavior (every feed class scores 1.0). Lets species profiles
    # weight browse (52 shrub) over grass (71) etc.
    landcover_scores: dict[int, float] = Field(
        default_factory=lambda: {52: 1.0, 71: 1.0, 90: 1.0, 95: 1.0}
    )

    _v = field_validator("curve_burn_age_yr")(classmethod(lambda cls, v: _curve_field(v)))

    @field_validator("landcover_scores")
    @classmethod
    def _scores_ok(cls, v: dict[int, float]) -> dict[int, float]:
        for code, score in v.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(f"landcover_scores[{code}] must be in [0,1], got {score}")
        return v


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


class LandAccessCfg(BaseModel):
    """Which surface-management agencies count as huntable public land.

    Codes are BLM SMA ADMIN_AGENCY_CODE values (BLM, USFS, BOR, STATE, LG,
    NPS, FWS, DOD, BIA, PVT, ...). State trust land is closed by default —
    states where it's open (e.g. Idaho endowment land) opt in via the
    registry. Polygons in the `public_access` drop-in (walk-in programs,
    enrolled trust parcels) are always open.
    """

    open_agencies: list[str] = Field(default_factory=lambda: ["BLM", "USFS", "BOR"])
    notes: str = ""

    @field_validator("open_agencies")
    @classmethod
    def _upper(cls, v: list[str]) -> list[str]:
        return [s.strip().upper() for s in v]


# Hunter's vehicle -> (MVUM "allowed" field, MVUM "dates open" field).
# Field names are matched case-insensitively against the MVUM layers.
VEHICLE_FIELDS: dict[str, tuple[str, str]] = {
    "passenger": ("passengervehicle", "passengervehicle_datesopen"),
    "high_clearance": ("highclearancevehicle", "highclearancevehicle_datesopen"),
    "ohv_gt50": ("other_ohv_gt50inches", "other_ohv_gt50_datesopen"),
    "ohv_lt50": ("other_ohv_lt50inches", "other_ohv_lt50_datesopen"),
    "atv": ("atv", "atv_datesopen"),
    "motorcycle": ("motorcycle", "motorcycle_datesopen"),
}


class AccessCfg(BaseModel):
    vehicle: str = "high_clearance"  # what the hunter drives to the jump-off
    max_unit_dist_mi: float = 1.0  # access points may sit this far outside the unit

    @field_validator("vehicle")
    @classmethod
    def _vehicle_ok(cls, v: str) -> str:
        if v not in VEHICLE_FIELDS:
            raise ValueError(f"access.vehicle must be one of {sorted(VEHICLE_FIELDS)}, got {v!r}")
        return v


class TimberCfg(BaseModel):
    """Security timber: big blocks of dark conifer far from motorized routes."""

    # Canopy % that counts as "dark". None = auto: the local conifer 75th
    # percentile, floored at min_dark_canopy_pct (NLCD canopy reads low in
    # dry Rockies conifer, so a fixed 60% finds nothing in Colorado).
    dark_canopy_pct: float | None = None
    min_dark_canopy_pct: float = 35.0
    min_road_mi: float = 0.5
    min_acres: float = 100.0
    bed_bonus: float = 0.15  # BED score multiplier bonus inside a block
    rank_weight: float = 0.3  # hunt-area ranking weight on nearby timber acres
    rank_radius_mi: float = 3.0


class ImageryCfg(BaseModel):
    """Sentinel-2 near-live imagery: current snow cover + timber mortality."""

    enabled: bool = True
    recent_days: int = 21  # look-back window for the current-conditions composite
    max_cloud_pct: float = 40.0
    leafon_months: list[int] = Field(default_factory=lambda: [7, 8, 9])
    baseline_years_back: int = 4  # compare latest summer vs this many years earlier
    dead_dndvi: float = -0.15  # greenness loss that flags dead/disturbed timber
    max_scenes: int = 6


class Config(BaseModel):
    profile: str
    unit: str
    hunt_window: HuntWindow
    state: str | None = None  # registry code, e.g. "ID", "CO"
    boundary: BoundarySource | None = None  # None -> built-in IDFG default
    land_access: LandAccessCfg = LandAccessCfg()
    access: AccessCfg = AccessCfg()
    timber: TimberCfg = TimberCfg()
    imagery: ImageryCfg = ImageryCfg()
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
