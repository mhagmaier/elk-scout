"""gen_profile.py: golden identity, phase derivation, 54-combo validity, determinism."""

import datetime as dt
import importlib.util
import itertools
import sys
from pathlib import Path

import pytest
import yaml

from elkscout.config import FACTOR_NAMES, load_config

REPO = Path(__file__).resolve().parents[1]
UNIT33 = REPO / "configs" / "unit33_oct_rifle.yaml"


def _gen(tmp_path, *args: str) -> Path:
    spec = importlib.util.spec_from_file_location("gen_profile", REPO / "scripts" / "gen_profile.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = tmp_path / "out.yaml"
    rc = mod.main([*args, "--out", str(out)])
    assert rc == 0
    return out


GOLDEN_ARGS = [
    "--species", "elk", "--weapon", "rifle", "--style", "backpack",
    "--state", "ID", "--unit", "33", "--start", "2026-10-15", "--end", "2026-10-24",
]


def test_golden_identity_reproduces_unit33(tmp_path):
    """elk + Oct rifle + backpack + ID/33 == the shipped unit-33 profile."""
    out = _gen(tmp_path, *GOLDEN_ARGS)
    gen = load_config(out).model_dump()
    ref = load_config(UNIT33).model_dump()
    # Expected differences only:
    assert gen.pop("profile") == "elk-general-rifle-backpack"
    ref.pop("profile")
    assert gen.pop("boundary") is not None  # injected Idaho block
    ref.pop("boundary")
    # Registry-injected state context (unit33 predates it and uses defaults).
    assert gen.pop("state") == "ID"
    ref.pop("state")
    assert "STATE" in gen.pop("land_access")["open_agencies"]  # Idaho endowment land open
    ref.pop("land_access")
    assert gen.pop("access")["vehicle"] == "high_clearance"
    ref.pop("access")
    assert gen["unit"] == ref["unit"] == "33"
    assert gen.pop("hunt_window") == ref.pop("hunt_window")  # same dates chosen
    assert gen == ref


def test_golden_summary_written(tmp_path):
    out = _gen(tmp_path, *GOLDEN_ARGS)
    summary = out.with_suffix(".summary.md").read_text()
    assert "Model summary" in summary
    assert "general" in summary
    assert "| security | 0.25 |" in summary


@pytest.mark.parametrize(
    ("species", "start", "phase"),
    [
        ("elk", "2026-09-30", "rut"),
        ("elk", "2026-10-01", "general"),
        ("elk", "2026-11-07", "general"),
        ("elk", "2026-11-08", "late"),
        ("mule_deer", "2026-09-15", "high_country"),
        ("mule_deer", "2026-11-03", "transition"),
        ("mule_deer", "2026-11-04", "rut"),
    ],
)
def test_phase_derivation_boundaries(tmp_path, species, start, phase):
    end = (dt.date.fromisoformat(start) + dt.timedelta(days=7)).isoformat()
    out = _gen(
        tmp_path, "--species", species, "--weapon", "rifle", "--style", "backpack",
        "--state", "ID", "--unit", "33", "--start", start, "--end", end,
    )
    assert load_config(out).profile == f"{species}-{phase}-rifle-backpack"


PHASE_START = {
    "rut_elk": "2026-09-10", "general": "2026-10-15", "late": "2026-11-20",
    "high_country": "2026-09-10", "transition": "2026-10-15", "rut_deer": "2026-11-15",
}


def test_every_matrix_combo_validates(tmp_path):
    """All species x phase x weapon x style combos produce a valid profile."""
    combos = []
    for species, phases in (("elk", ["rut", "general", "late"]),
                            ("mule_deer", ["high_country", "transition", "rut"])):
        for phase, weapon, style in itertools.product(
            phases, ["archery", "muzzleloader", "rifle"], ["day", "backpack", "horseback"]
        ):
            combos.append((species, phase, weapon, style))
    assert len(combos) == 54

    for i, (species, phase, weapon, style) in enumerate(combos):
        start = PHASE_START[f"{phase}_elk" if phase == "rut" and species == "elk"
                            else f"{phase}_deer" if phase == "rut" else phase]
        end = (dt.date.fromisoformat(start) + dt.timedelta(days=7)).isoformat()
        out = _gen(
            tmp_path / str(i), "--species", species, "--weapon", weapon, "--style", style,
            "--phase", phase, "--state", "ID", "--unit", "33", "--start", start, "--end", end,
        )
        cfg = load_config(out)
        assert pytest.approx(sum(cfg.factors.weights().values()), abs=1e-3) == 1.0
        assert sum(cfg.waypoints.counts.values()) <= cfg.outputs.gpx_max_waypoints
        if style == "day":
            assert cfg.waypoints.counts["CAMP"] == 0
        # Elevation curve x values stay in the sanity band.
        assert all(3000 <= x <= 11500 for x, _ in cfg.factors.elevation.curve_elevation_ft)


def test_determinism(tmp_path):
    a = _gen(tmp_path / "a", *GOLDEN_ARGS).read_bytes()
    b = _gen(tmp_path / "b", *GOLDEN_ARGS).read_bytes()
    assert a == b


def test_unknown_state_fails_helpfully(tmp_path):
    with pytest.raises(SystemExit):
        _gen(
            tmp_path, "--species", "elk", "--weapon", "rifle", "--style", "backpack",
            "--state", "ZZ", "--unit", "1", "--start", "2026-10-15", "--end", "2026-10-20",
        )


def test_no_boundary_skips_injection(tmp_path):
    out = _gen(
        tmp_path, "--species", "elk", "--weapon", "rifle", "--style", "backpack",
        "--unit", "270", "--start", "2026-10-15", "--end", "2026-10-20", "--no-boundary",
    )
    assert load_config(out).boundary is None


def test_user_adjust_applied_then_renormalized(tmp_path):
    out = _gen(tmp_path, *GOLDEN_ARGS, "--adjust", "factors.pressure.weight=0.3")
    cfg = load_config(out)
    weights = cfg.factors.weights()
    assert pytest.approx(sum(weights.values()), abs=1e-3) == 1.0
    assert weights["pressure"] > weights["water"]  # the bump survived renormalization


def test_adjustments_matrix_schema():
    """Every key the matrix touches exists in the templates it will be applied to."""
    adjustments = yaml.safe_load((REPO / "configs" / "adjustments.yaml").read_text())
    templates = {
        "elk": yaml.safe_load((REPO / "configs" / "templates" / "elk.yaml").read_text()),
        "mule_deer": yaml.safe_load((REPO / "configs" / "templates" / "mule_deer.yaml").read_text()),
    }

    def check_cell(cell, docs):
        for factor in (cell.get("weights") or {}):
            assert factor in FACTOR_NAMES, factor
        for curve_key in (cell.get("curves") or {}):
            factor, curve = curve_key.split(".", 1)
            for doc in docs:
                assert curve in doc["factors"][factor], curve_key
        for dotted in (cell.get("set") or {}):
            for doc in docs:
                node = doc
                for part in dotted.split("."):
                    assert part in node, f"{dotted} missing {part}"
                    node = node[part]
        for wp_type in (cell.get("counts") or {}):
            for doc in docs:
                assert wp_type in doc["waypoints"]["counts"], wp_type

    for species, phases in adjustments["phases"].items():
        for cell in phases.values():
            check_cell(cell, [templates[species]])
    for cell in adjustments["styles"].values():
        check_cell(cell, list(templates.values()))
    for cell in adjustments["weapons"].values():
        check_cell(cell, list(templates.values()))


CO_ARGS = [
    "--species", "elk", "--weapon", "rifle", "--style", "day", "--vehicle", "ohv_gt50",
    "--state", "CO", "--unit", "681", "--start", "2026-11-18", "--end", "2026-11-22",
]


def test_colorado_calibration_and_land_rules(tmp_path):
    """The lessons from the GMU 68/681 run are now automatic for Colorado."""
    out = _gen(tmp_path, *CO_ARGS)
    cfg = load_config(out)
    assert cfg.profile == "elk-late-rifle-day"
    assert cfg.state == "CO"
    assert cfg.access.vehicle == "ohv_gt50"
    # State trust land closed unless enrolled (enrolled parcels come from the overlay).
    assert "STATE" not in cfg.land_access.open_agencies
    assert "BLM" in cfg.land_access.open_agencies
    # Elevation curve raised +3,000 ft from the Idaho template's late band.
    xs = [x for x, _ in cfg.factors.elevation.curve_elevation_ft]
    plateau = [x for x, y in cfg.factors.elevation.curve_elevation_ft if y == 1.0]
    assert min(plateau) == 5800 + 3000 and max(plateau) == 7400 + 3000
    assert xs == sorted(xs)
    # Late-season south bedding is snow-gated, not unconditional.
    assert cfg.factors.bedding.aspect_center_deg == 22
    assert cfg.factors.bedding.snow_aspect_center_deg == 180
    summary = out.with_suffix(".summary.md").read_text()
    assert "state calibration (CO)" in summary and "+3000 ft" in summary


def test_unknown_state_with_manual_boundary_gets_safe_defaults(tmp_path):
    out = _gen(
        tmp_path, "--species", "elk", "--weapon", "rifle", "--style", "backpack",
        "--state", "MT", "--unit", "270", "--start", "2026-10-25", "--end", "2026-10-30", "--no-boundary",
    )
    cfg = load_config(out)
    assert cfg.boundary is None
    assert cfg.land_access.open_agencies == ["BLM", "USFS", "BOR"]
    assert "no registry entry" in out.with_suffix(".summary.md").read_text()
