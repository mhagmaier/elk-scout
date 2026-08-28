"""GPX/KML writers: round-trip, OnX limits, name safety."""

import xml.etree.ElementTree as ET

import geopandas as gpd
import gpxpy
import pytest
from shapely.geometry import Point, box

from elkscout.config import load_config
from elkscout.outputs.gpx_writer import SYMBOLS, write_gpx_files
from elkscout.outputs.kml_writer import KML_NS, write_kml
from elkscout.paths import Workspace

CFG = load_config("configs/unit33_oct_rifle.yaml")


def _workspace(tmp_path, names=None):
    ws = Workspace(tmp_path / "data")
    ws.ensure_dirs()
    rows = [
        ("B1-01 N-bench 7410", "BED", "north", 1),
        ("F1-01 burn-edge 7100", "FEED", "north", 1),
        ("W1-01 creek 6800", "WATER", "north", 1),
        ("B2-01 NE-timber 7300", "BED", "south", 2),
        ("G2-01 glass 7600", "GLASS", "south", 2),
        ("C2-01 camp 6900", "CAMP", "south", 2),
    ]
    if names:
        rows = [(names[i] if i < len(names) else r[0], *r[1:]) for i, r in enumerate(rows)]
    wp = gpd.GeoDataFrame(
        {
            "wp_type": [r[1] for r in rows],
            "name": [r[0] for r in rows],
            "score": [0.8, 0.7, 0.65, 0.75, 0.6, 0.55],
            "desc": [f"Reason for {r[0]}" for r in rows],
            "evidence_json": ["{}"] * 6,
            "hunt_area": [r[2].title() for r in rows],
            "area_slug": [r[2] for r in rows],
            "area_rank": [r[3] for r in rows],
            "elevation_ft": [7410, 7100, 6800, 7300, 7600, 6900],
        },
        geometry=[Point(-115.65 + i * 0.01, 44.12 + (i % 2) * 0.01) for i in range(6)],
        crs="EPSG:4326",
    )
    wp.to_file(ws.waypoints_geojson, driver="GeoJSON")
    areas = gpd.GeoDataFrame(
        {
            "name": ["North", "South"],
            "slug": ["north", "south"],
            "rank": [1, 2],
            "n_waypoints": [3, 3],
            "mean_score": [0.717, 0.633],
        },
        geometry=[box(-115.7, 44.115, -115.55, 44.2), box(-115.7, 44.05, -115.55, 44.115)],
        crs="EPSG:4326",
    )
    areas.to_file(ws.hunt_areas_geojson, driver="GeoJSON")
    return ws


def test_gpx_roundtrip_and_per_area_files(tmp_path):
    ws = _workspace(tmp_path)
    paths = write_gpx_files(ws, CFG)
    assert [p.name for p in paths] == [
        "elkscout_unit33_all.gpx",
        "elkscout_unit33_north.gpx",
        "elkscout_unit33_south.gpx",
    ]
    with open(paths[0], encoding="utf-8") as fh:
        parsed = gpxpy.parse(fh)
    assert len(parsed.waypoints) == 6
    symbols = {w.name: w.symbol for w in parsed.waypoints}
    assert symbols["B1-01 N-bench 7410"] == SYMBOLS["BED"]
    assert symbols["G2-01 glass 7600"] == SYMBOLS["GLASS"]
    for w in parsed.waypoints:
        assert w.description and -180 <= w.longitude <= 180 and -90 <= w.latitude <= 90
        assert w.elevation and 2000 < w.elevation < 2400  # meters
    with open(paths[1], encoding="utf-8") as fh:
        assert len(gpxpy.parse(fh).waypoints) == 3


def test_gpx_rejects_non_ascii_name(tmp_path):
    ws = _workspace(tmp_path, names=["B1-01 séjour 7410"])
    with pytest.raises(ValueError, match="OnX-safe"):
        write_gpx_files(ws, CFG)


def test_gpx_enforces_waypoint_limit(tmp_path):
    ws = _workspace(tmp_path)
    cfg = CFG.model_copy(deep=True)
    cfg.outputs.gpx_max_waypoints = 2
    with pytest.raises(ValueError, match="exceeds OnX limit"):
        write_gpx_files(ws, cfg)


def test_kml_placemark_count(tmp_path):
    ws = _workspace(tmp_path)
    out = write_kml(ws, CFG)
    root = ET.parse(out).getroot()
    placemarks = root.findall(f".//{{{KML_NS}}}Placemark")
    assert len(placemarks) == 6 + 2  # waypoints + area outlines
    styles = {s.get("id") for s in root.findall(f".//{{{KML_NS}}}Style")}
    assert {"style-BED", "style-GLASS", "style-area"}.issubset(styles)
