"""Photo check: sheets + review template on a real (offline, fixture) pipeline run,
verdicts flowing into GPX/KML/briefing, dead blocks dropping out of ranking."""

import json
import shutil

import geopandas as gpd
import gpxpy
import pytest

from elkscout import imagery
from elkscout.cli import main
from elkscout.config import load_config
from elkscout.paths import Workspace
from elkscout.testkit import AOI_BBOX

CONFIG = "configs/unit33_oct_rifle.yaml"
BBOX = ",".join(str(v) for v in AOI_BBOX)


@pytest.fixture(scope="module")
def run_ws(fixture_manual_dir, tmp_path_factory):
    data = tmp_path_factory.mktemp("imagery") / "data"
    (data / "manual").mkdir(parents=True)
    for f in fixture_manual_dir.iterdir():
        shutil.copy2(f, data / "manual" / f.name)
    common = ["--config", CONFIG, "--data", str(data), "--offline"]
    assert main(["fetch", *common, f"--aoi-bbox={BBOX}"]) == 0
    assert main(["score", *common]) == 0
    assert main(["waypoints", *common]) == 0
    return Workspace(data)


def _fake_fetch(net, source, bbox, px, epsg):
    from PIL import Image

    color = (40, 90, 40) if source == "esri" else (150, 20, 30)
    return Image.new("RGB", (px, px), color)


def test_waypoints_carry_stable_ids_and_model_sentence(run_ws):
    wp = gpd.read_file(run_ws.waypoints_geojson)
    assert wp["wp_id"].is_unique
    assert all("@" in i for i in wp["wp_id"])
    assert (wp["desc"] == wp["desc_model"]).all()


def test_make_sheets_writes_pages_pdf_and_review_template(run_ws, monkeypatch):
    monkeypatch.setattr(imagery, "fetch_chip", _fake_fetch)
    monkeypatch.setattr(imagery, "capture_date", lambda net, src, x, y, epsg: (f"{src} 2025-07-01", "2025-07-01"))
    cfg = load_config(CONFIG)
    from elkscout.cache import Cache
    from elkscout.net import Net

    meta = imagery.make_sheets(Net(Cache(run_ws.cache), offline=True), run_ws, cfg, px=120)
    assert meta
    pages = sorted(p.name for p in run_ws.imagery_dir.glob("*.png"))
    assert any(p.startswith("points_") for p in pages)
    assert (run_ws.imagery_dir / "imagery_check.pdf").stat().st_size > 1000
    review = json.loads(run_ws.imagery_review_json.read_text())
    wp = gpd.read_file(run_ws.waypoints_geojson)
    assert set(review["waypoints"]) == set(wp["wp_id"])
    first = next(iter(review["waypoints"].values()))
    assert first["verdict"] == "" and first["dates"]["esri"] == "2025-07-01"


def test_verdicts_flow_into_outputs_and_survive_rerun(run_ws):
    review = json.loads(run_ws.imagery_review_json.read_text())
    wp = gpd.read_file(run_ws.waypoints_geojson)
    bed = wp[wp["wp_type"] == "BED"].iloc[0]
    review["waypoints"][bed["wp_id"]]["verdict"] = "poor bed: leafless aspen edge, cover 250 m west"
    if review["blocks"]:
        first_block = next(iter(review["blocks"]))
        review["blocks"][first_block]["verdict"] = "mostly dead (gray crowns)"
    run_ws.imagery_review_json.write_text(json.dumps(review))

    common = ["--config", CONFIG, "--data", str(run_ws.root), "--offline"]
    assert main(["report", *common]) == 0
    assert main(["report", *common]) == 0  # idempotent: verdict not appended twice

    cfg = load_config(CONFIG)
    with open(run_ws.gpx_all(cfg.unit), encoding="utf-8") as fh:
        notes = {w.name: w.description for w in gpxpy.parse(fh).waypoints}
    note = notes[bed["name"]]
    assert note.count("Photos (2025-07-01): poor bed: leafless aspen edge") == 1
    assert len(note) <= cfg.outputs.desc_max_chars

    if review["blocks"]:
        kml = run_ws.timber_kml(cfg.unit).read_text()
        assert "mostly dead" in kml
        assert "mostly dead" in run_ws.briefing_md.read_text()


def test_dead_blocks_do_not_count_toward_area_ranking():
    import geopandas as gpd
    from shapely.geometry import Point, box

    from elkscout.waypoints import area_timber_acres

    wp = gpd.GeoDataFrame({"name": ["A", "A"]}, geometry=[Point(0, 0), Point(100, 0)], crs="EPSG:32613")
    blocks = gpd.GeoDataFrame(
        {"id": ["T01", "T02"], "acres": [900, 300], "imagery": ["mostly dead (gray crowns)", "dense live conifer"]},
        geometry=[box(200, 0, 600, 400), box(-600, 0, -200, 400)],
        crs="EPSG:32613",
    )
    assert area_timber_acres(wp, blocks, 3.0, 32613) == {"A": 300}


@pytest.mark.parametrize(
    ("verdict", "dead"),
    [("mostly dead (gray crowns)", True), ("dense live conifer", False),
     ("live, some dead crowns mixed in", False), ("", False), (None, False)],
)
def test_block_is_dead(verdict, dead):
    assert imagery.block_is_dead(verdict) is dead
