"""State registry: schema, the Idaho entry's drift-guard against endpoints constants."""

import pytest
import yaml
from pydantic import ValidationError

from elkscout import endpoints
from elkscout.registry import DEFAULT_PATH, StateEntry, load_states


def test_registry_loads_and_has_idaho():
    states = load_states()
    assert "ID" in states
    idaho = states["ID"]
    assert idaho.agency.startswith("Idaho")
    assert idaho.provenance.status == "verified"


def test_idaho_entry_matches_endpoints_constants():
    """Drift guard: the registry's Idaho service must equal the built-in default."""
    b = load_states()["ID"].boundary
    assert b.base_url == endpoints.IDFG_HUNTING
    assert b.alt_urls == [endpoints.IDFG_HUNTING_ALT]
    assert b.layer == endpoints.IDFG_GMU_LAYER
    default = endpoints.idfg_default_boundary()
    assert b.unit_field_hints == default.unit_field_hints
    assert b.unit_value_format == default.unit_value_format


def test_entry_missing_base_url_rejected():
    with pytest.raises(ValidationError):
        StateEntry.model_validate(
            {"name": "Nowhere", "agency": "X", "boundary": {"layer": 1}}
        )


def test_bad_status_rejected():
    raw = yaml.safe_load(DEFAULT_PATH.read_text())
    entry = raw["states"]["ID"]
    entry["provenance"]["status"] = "trust-me"
    with pytest.raises(ValidationError):
        StateEntry.model_validate(entry)


def test_state_codes_normalized_upper():
    states = load_states()
    assert all(code == code.upper() for code in states)
