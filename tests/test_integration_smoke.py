"""Full pipeline, fully offline, on the procedural fixture AOI."""

import json
import shutil

import geopandas as gpd
import gpxpy
import pytest

from elkscout.cli import main
from elkscout.config import load_config
from elkscout.paths import Workspace
from elkscout.testkit import AOI_BBOX

CONFIG = "configs/unit33_oct_rifle.yaml"
BBOX = ",".join(str(v) for v in AOI_BBOX)


@pytest.fixture(scope="session")
def pipeline_ws(fixture_manual_dir, tmp_path_factory):
    data = tmp_path_factory.mktemp("smoke") / "data"
    (data / "manual").mkdir(parents=True)
    for f in fixture_manual_dir.iterdir():
        shutil.copy2(f, data / "manual" / f.name)
    common = ["--config", CONFIG, "--data", str(data), "--offline"]
    # note: value starts with '-', so it must be attached with '='
    assert main(["fetch", *common, f"--aoi-bbox={BBOX}"]) == 0
    assert main(["score", *common]) == 0
    assert main(["waypoints", *common]) == 0
    assert main(["report", *common]) == 0
    return Workspace(data)


def test_stage_artifacts_exist(pipeline_ws):
    ws = pipeline_ws
    for p in (
        ws.boundary_geojson, ws.grid_json, ws.dem_tif, ws.terrain_tif,
        ws.landcover_tif, ws.canopy_tif, ws.factors_tif, ws.composite_tif,
        ws.type_scores_tif, ws.snow_json, ws.weather_json,
        ws.waypoints_geojson, ws.hunt_areas_geojson,
    ):
        assert p.exists(), f"missing artifact {p}"


def test_waypoints_substantive(pipeline_ws):
    wp = gpd.read_file(pipeline_ws.waypoints_geojson)
    assert len(wp) >= 8
    assert len(set(wp["wp_type"])) >= 3
    assert wp["name"].is_unique
    assert wp["desc"].str.len().gt(20).all()
    # Snow shift from the fixture (4" SNWD) must have been applied.
    snow = json.loads(pipeline_ws.snow_json.read_text())
    assert snow["band_shift_ft"] == pytest.approx(-266.7, abs=1.0)


def test_gpx_outputs_valid(pipeline_ws):
    cfg = load_config(CONFIG)
    gpx_all = pipeline_ws.gpx_all(cfg.unit)
    assert gpx_all.exists()
    with open(gpx_all, encoding="utf-8") as fh:
        parsed = gpxpy.parse(fh)
    wp = gpd.read_file(pipeline_ws.waypoints_geojson)
    assert len(parsed.waypoints) == len(wp)
    assert gpx_all.stat().st_size <= cfg.outputs.gpx_max_bytes
    per_area = list(pipeline_ws.out.glob(f"elkscout_unit{cfg.unit}_*.gpx"))
    assert len(per_area) >= 2  # the all-file plus at least one area file


def test_map_and_briefing(pipeline_ws):
    cfg = load_config(CONFIG)
    assert pipeline_ws.map_html.stat().st_size > 50_000
    html = pipeline_ws.map_html.read_text(errors="ignore")
    assert "Habitat score" in html and "Waypoints" in html
    briefing = pipeline_ws.briefing_md.read_text()
    assert "Wind and thermals" in briefing
    assert "| waypoint | type |" in briefing
    wp = gpd.read_file(pipeline_ws.waypoints_geojson)
    assert "Fixture Fire" in briefing or (wp["wp_type"] == "FEED").any()
    assert pipeline_ws.kml(cfg.unit).exists()
