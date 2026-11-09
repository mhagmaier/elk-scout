"""Species templates: validity, curve sanity, documented elk/deer differences."""

import pytest

from elkscout.config import FACTOR_NAMES, load_config
from elkscout.curves import validate_curve

ELK = "configs/templates/elk.yaml"
DEER = "configs/templates/mule_deer.yaml"
UNIT33 = "configs/unit33_oct_rifle.yaml"

CURVE_KEYS = {
    "elevation": ["curve_elevation_ft"],
    "security": ["curve_dist_motorized_km"],
    "bedding": ["curve_canopy_pct", "curve_slope_pct"],
    "feed": ["curve_burn_age_yr"],
    "water": ["curve_dist_water_m"],
    "pressure": ["curve_dist_trailhead_km"],
}


@pytest.mark.parametrize("path", [ELK, DEER])
def test_template_is_a_valid_complete_profile(path):
    cfg = load_config(path)
    assert pytest.approx(sum(cfg.factors.weights().values()), abs=1e-6) == 1.0
    for factor, keys in CURVE_KEYS.items():
        for key in keys:
            validate_curve(getattr(getattr(cfg.factors, factor), key))


def test_elk_template_numerically_matches_unit33():
    t = load_config(ELK).model_dump()
    u = load_config(UNIT33).model_dump()
    for volatile in ("profile", "unit"):
        t.pop(volatile)
        u.pop(volatile)
    assert t == u


def test_deer_differs_from_elk_in_the_documented_ways():
    elk = load_config(ELK)
    deer = load_config(DEER)
    # Browsers: shrub over grass.
    assert deer.factors.feed.landcover_scores[52] > deer.factors.feed.landcover_scores[71]
    assert elk.factors.feed.landcover_scores[52] == elk.factors.feed.landcover_scores[71] == 1.0
    # Less water-dependent, more road-shy.
    assert deer.factors.water.weight < elk.factors.water.weight
    assert deer.factors.security.weight > elk.factors.security.weight
    # Open, rocky, steeper bedding: canopy optimum starts far lower.
    deer_canopy = dict((x, y) for x, y in deer.factors.bedding.curve_canopy_pct)
    assert deer_canopy[10] == 1.0  # scores full at 10% canopy
    elk_canopy = dict((x, y) for x, y in elk.factors.bedding.curve_canopy_pct)
    assert elk_canopy[60] == 1.0 and elk_canopy[45] < 1.0
    # Steeper tolerance via the cliff mask too.
    assert deer.masks.max_slope_pct > elk.masks.max_slope_pct
