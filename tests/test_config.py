"""Config loading and validation."""

import copy

import pytest
import yaml
from pydantic import ValidationError

from elkscout.config import load_config, Config

PROFILE = "configs/unit33_oct_rifle.yaml"


def _raw():
    with open(PROFILE, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_shipped_profile_loads():
    cfg = load_config(PROFILE)
    assert cfg.profile == "rifle-october-backpack"
    assert cfg.unit == "33"
    weights = cfg.factors.weights()
    assert pytest.approx(sum(weights.values())) == 1.0
    assert weights["security"] == max(weights.values())  # rifle season: security dominates
    assert cfg.hunt_window.start.month == 10


def test_non_monotonic_curve_rejected():
    raw = copy.deepcopy(_raw())
    raw["factors"]["elevation"]["curve_elevation_ft"] = [[6000, 1.0], [5000, 0.5]]
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_curve_y_out_of_range_rejected():
    raw = copy.deepcopy(_raw())
    raw["factors"]["water"]["curve_dist_water_m"] = [[0, 1.5], [500, 0.0]]
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_negative_weight_rejected():
    raw = copy.deepcopy(_raw())
    raw["factors"]["feed"]["weight"] = -0.2
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_unknown_waypoint_type_rejected():
    raw = copy.deepcopy(_raw())
    raw["waypoints"]["counts"]["WALLOW"] = 5
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_unknown_factor_in_type_profile_rejected():
    raw = copy.deepcopy(_raw())
    raw["type_profiles"]["BED"]["moon_phase"] = 0.5
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_camp_band_must_be_ordered_pair():
    raw = copy.deepcopy(_raw())
    raw["camp"]["trailhead_km"] = [5.6, 2.4]
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_hunt_window_order_enforced():
    raw = copy.deepcopy(_raw())
    raw["hunt_window"] = {"start": "2026-10-24", "end": "2026-10-15"}
    with pytest.raises(ValidationError):
        Config.model_validate(raw)
