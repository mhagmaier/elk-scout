"""Land-access rules: state trust land closed by default, overlays reopen it."""

import geopandas as gpd
import numpy as np
from shapely.geometry import box

from elkscout.config import LandAccessCfg
from elkscout.sources.ownership import _normalize, canonical_agency


def _gdf(codes):
    return gpd.GeoDataFrame(
        {"ADMIN_AGENCY_CODE": codes},
        geometry=[box(i, 0, i + 1, 1) for i in range(len(codes))],
        crs="EPSG:4326",
    )


def test_default_rules_close_state_trust_and_local_land():
    out = _normalize(_gdf(["BLM", "USFS", "BOR", "STATE", "LG", "PVT", "NPS", "FWS"]), LandAccessCfg())
    status = dict(zip(out["agency"], out["public"]))
    assert status == {
        "BLM": True, "USFS": True, "BOR": True,
        "STATE": False, "LG": False, "PVT": False, "NPS": False, "FWS": False,
    }


def test_state_can_open_trust_land():
    out = _normalize(_gdf(["STATE", "PVT"]), LandAccessCfg(open_agencies=["blm", "usfs", "state"]))
    assert list(out["public"]) == [True, False]


def test_aliases_canonicalized():
    assert canonical_agency("Forest Service") == "USFS"
    assert canonical_agency(" fs ") == "USFS"
    assert canonical_agency("Private Land") == "PVT"
    assert canonical_agency("Bureau of Land Management") == "BLM"


def test_explicit_public_column_wins():
    g = _gdf(["STATE"])
    g["public"] = [True]  # e.g. a hunter's hand-checked drop-in
    assert bool(_normalize(g, LandAccessCfg()).iloc[0]["public"]) is True


def test_public_access_overlay_reopens_closed_cells(tmp_path):
    """factors.run_factors: overlay polygons force public=1 over closed trust land."""
    from elkscout.paths import Workspace
    from elkscout.sources.ownership import _copy_public_access

    ws = Workspace(tmp_path)
    ws.ensure_dirs()
    overlay = gpd.GeoDataFrame({"name": ["Enrolled STL"]}, geometry=[box(-106.3, 38.0, -106.2, 38.1)], crs="EPSG:4326")
    overlay.to_file(ws.manual_path("public_access"), driver="GeoJSON")
    _copy_public_access(ws)
    back = gpd.read_file(ws.public_access_geojson)
    assert len(back) == 1 and np.isclose(back.total_bounds[0], -106.3)
