"""State registry: which ArcGIS service provides each state's unit boundaries.

configs/states.yaml is consumed only at profile-generation time
(scripts/gen_profile.py) — generated configs carry their own `boundary:` block,
so pipeline fetches never read the registry. The onx-scout skill appends new
states after verifying a service (see the skill's state-discovery reference).
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator

from .config import BoundarySource

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "configs" / "states.yaml"


class Provenance(BaseModel):
    verified: _dt.date | None = None
    status: str = "provisional"
    notes: str = ""

    @field_validator("status")
    @classmethod
    def _status_ok(cls, v: str) -> str:
        if v not in ("verified", "provisional"):
            raise ValueError(f"provenance.status must be verified|provisional, got {v!r}")
        return v


class StateEntry(BaseModel):
    name: str
    agency: str
    unit_system: str = ""
    boundary: BoundarySource
    provenance: Provenance = Provenance()


def load_states(path: str | Path | None = None) -> dict[str, StateEntry]:
    p = Path(path) if path else DEFAULT_PATH
    with open(p, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    states = raw.get("states") or {}
    return {code.upper(): StateEntry.model_validate(entry) for code, entry in states.items()}
