"""Config-driven boundary source: resolution, fallback, field discovery. No network."""

import pytest

from elkscout.config import BoundarySource, load_config
from elkscout.endpoints import IDFG_GMU_LAYER, IDFG_HUNTING, IDFG_HUNTING_ALT
from elkscout.sources.boundary import _prefer_exact, _unit_field, resolve_boundary_source

PROFILE = "configs/unit33_oct_rifle.yaml"


def test_config_without_boundary_resolves_to_idfg_default():
    cfg = load_config(PROFILE)
    assert cfg.boundary is None
    src = resolve_boundary_source(cfg)
    assert src.base_url == IDFG_HUNTING
    assert src.alt_urls == [IDFG_HUNTING_ALT]
    assert src.layer == IDFG_GMU_LAYER


def test_config_with_boundary_block_wins():
    cfg = load_config(PROFILE).model_copy(deep=True)
    cfg.boundary = BoundarySource(base_url="https://gis.example.gov/arcgis/rest/services/Hunt/MapServer")
    src = resolve_boundary_source(cfg)
    assert src.base_url.startswith("https://gis.example.gov")
    assert src.alt_urls == []
    assert src.layer is None  # discovery mode


def test_unit_value_format():
    src = BoundarySource(base_url="https://x.example/MapServer", unit_value_format="{unit:0>3}")
    assert src.unit_value_format.format(unit="7") == "007"
    default = BoundarySource(base_url="https://x.example/MapServer")
    assert default.unit_value_format.format(unit="33A") == "33A"


def _info(*field_names):
    return {"fields": [{"name": n} for n in field_names]}


def test_unit_field_explicit_match_case_insensitive():
    src = BoundarySource(base_url="https://x.example/MapServer", unit_field="gmu_code")
    assert _unit_field(src, _info("OBJECTID", "GMU_CODE", "NAME")) == "GMU_CODE"


def test_unit_field_explicit_missing_raises():
    src = BoundarySource(base_url="https://x.example/MapServer", unit_field="DISTRICT")
    with pytest.raises(RuntimeError, match="unit_field"):
        _unit_field(src, _info("OBJECTID", "NAME"))


def test_unit_field_hints_tried_before_generic_heuristic():
    # Generic heuristic would pick PLACE_NAME (contains NAME); the hint wins.
    src = BoundarySource(base_url="https://x.example/MapServer", unit_field_hints=["HUNT_DISTRICT"])
    assert _unit_field(src, _info("PLACE_NAME", "HUNT_DISTRICT")) == "HUNT_DISTRICT"


def test_unit_field_generic_fallback_order():
    src = BoundarySource(base_url="https://x.example/MapServer")
    assert _unit_field(src, _info("OBJECTID", "UNIT_ID", "GMU")) == "UNIT_ID"  # UNIT before GMU
    with pytest.raises(RuntimeError):
        _unit_field(src, _info("OBJECTID", "SHAPE_AREA"))


def test_prefer_exact_narrows_like_results():
    import geopandas as gpd
    from shapely.geometry import Point

    gdf = gpd.GeoDataFrame(
        {"NAME": ["33", "33A", "133"]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:4326",
    )
    narrowed = _prefer_exact(gdf, "NAME", "33")
    assert list(narrowed["NAME"]) == ["33"]
    # No true match -> LIKE result returned unchanged.
    untouched = _prefer_exact(gdf, "NAME", "45")
    assert len(untouched) == 3
