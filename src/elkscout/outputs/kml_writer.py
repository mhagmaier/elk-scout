"""KML output for Google Earth — hand-rolled with xml.etree (no extra deps).

write_kml(ws, cfg): one Document with a shared style per waypoint type
(Google paddle icons), a Folder per hunt area (by rank) holding its
Placemarks, and a final "Hunt areas" folder with unfilled polygon outlines.
Validated by re-parsing and counting Placemarks.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from ..config import Config
from ..paths import Workspace

log = logging.getLogger("elkscout.kml")

KML_NS = "http://www.opengis.net/kml/2.2"

# Google-hosted paddle icons; href colors are baked into the icon images.
ICONS = {
    "BED": "http://maps.google.com/mapfiles/kml/paddle/blu-blank.png",
    "FEED": "http://maps.google.com/mapfiles/kml/paddle/grn-blank.png",
    "WATER": "http://maps.google.com/mapfiles/kml/paddle/ltblu-blank.png",
    "SADDLE": "http://maps.google.com/mapfiles/kml/paddle/red-blank.png",
    "GLASS": "http://maps.google.com/mapfiles/kml/paddle/ylw-blank.png",
    "CAMP": "http://maps.google.com/mapfiles/kml/paddle/purple-blank.png",
    "ACCESS": "http://maps.google.com/mapfiles/kml/paddle/wht-blank.png",
}
AREA_LINE_KML_COLOR = "ff2f2f2f"  # aabbggrr


def write_kml(ws: Workspace, cfg: Config) -> Path:
    from ..waypoints import load_waypoints

    wp, areas = load_waypoints(ws)

    ET.register_namespace("", KML_NS)
    kml = ET.Element(f"{{{KML_NS}}}kml")
    doc = ET.SubElement(kml, f"{{{KML_NS}}}Document")
    ET.SubElement(doc, f"{{{KML_NS}}}name").text = f"ElkScout Unit {cfg.unit}"

    for wp_type, icon in ICONS.items():
        style = ET.SubElement(doc, f"{{{KML_NS}}}Style", id=f"style-{wp_type}")
        icon_style = ET.SubElement(style, f"{{{KML_NS}}}IconStyle")
        ET.SubElement(ET.SubElement(icon_style, f"{{{KML_NS}}}Icon"), f"{{{KML_NS}}}href").text = icon
        line_style = ET.SubElement(style, f"{{{KML_NS}}}LineStyle")
        ET.SubElement(line_style, f"{{{KML_NS}}}width").text = "2"

    area_style = ET.SubElement(doc, f"{{{KML_NS}}}Style", id="style-area")
    ls = ET.SubElement(area_style, f"{{{KML_NS}}}LineStyle")
    ET.SubElement(ls, f"{{{KML_NS}}}color").text = AREA_LINE_KML_COLOR
    ET.SubElement(ls, f"{{{KML_NS}}}width").text = "2"
    poly = ET.SubElement(area_style, f"{{{KML_NS}}}PolyStyle")
    ET.SubElement(poly, f"{{{KML_NS}}}fill").text = "0"

    n_placemarks = 0
    for _, area in areas.sort_values("rank").iterrows():
        folder = ET.SubElement(doc, f"{{{KML_NS}}}Folder")
        ET.SubElement(folder, f"{{{KML_NS}}}name").text = f"{area['rank']}. {area['name']}"
        sub = wp[wp["area_slug"] == area["slug"]]
        for _, row in sub.iterrows():
            pm = ET.SubElement(folder, f"{{{KML_NS}}}Placemark")
            ET.SubElement(pm, f"{{{KML_NS}}}name").text = str(row["name"])
            ET.SubElement(pm, f"{{{KML_NS}}}description").text = f"{row['desc']} (score {row['score']})"
            ET.SubElement(pm, f"{{{KML_NS}}}styleUrl").text = f"#style-{row['wp_type']}"
            point = ET.SubElement(pm, f"{{{KML_NS}}}Point")
            ET.SubElement(point, f"{{{KML_NS}}}coordinates").text = (
                f"{row.geometry.x:.6f},{row.geometry.y:.6f},0"
            )
            n_placemarks += 1

    area_folder = ET.SubElement(doc, f"{{{KML_NS}}}Folder")
    ET.SubElement(area_folder, f"{{{KML_NS}}}name").text = "Hunt areas"
    for _, area in areas.sort_values("rank").iterrows():
        pm = ET.SubElement(area_folder, f"{{{KML_NS}}}Placemark")
        ET.SubElement(pm, f"{{{KML_NS}}}name").text = str(area["name"])
        ET.SubElement(pm, f"{{{KML_NS}}}styleUrl").text = "#style-area"
        geom = area.geometry
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        multi = ET.SubElement(pm, f"{{{KML_NS}}}MultiGeometry")
        for p in polys:
            polygon = ET.SubElement(multi, f"{{{KML_NS}}}Polygon")
            outer = ET.SubElement(polygon, f"{{{KML_NS}}}outerBoundaryIs")
            ring = ET.SubElement(outer, f"{{{KML_NS}}}LinearRing")
            coords = " ".join(f"{x:.6f},{y:.6f},0" for x, y in p.exterior.coords)
            ET.SubElement(ring, f"{{{KML_NS}}}coordinates").text = coords
        n_placemarks += 1

    tree = ET.ElementTree(kml)
    ET.indent(tree)
    out = ws.kml(cfg.unit)
    out.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out, encoding="utf-8", xml_declaration=True)

    reparsed = ET.parse(out)
    found = len(reparsed.getroot().findall(f".//{{{KML_NS}}}Placemark"))
    if found != n_placemarks:
        raise ValueError(f"{out.name}: re-parse found {found} placemarks, expected {n_placemarks}")
    log.info("kml: wrote %s (%d placemarks)", out, n_placemarks)
    return out
