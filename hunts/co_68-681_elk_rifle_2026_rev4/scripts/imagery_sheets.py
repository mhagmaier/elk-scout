"""Aerial-imagery chips + contact sheets for timber blocks and waypoints.

Revision 3's script with one change: motorized routes come from the pipeline's
data/work/motorized.geojson. --kml needs a layer named Security_timber.

Sources:
  esri      Esri World Imagery (Vantor Vivid satellite), natural color; capture
            date/resolution read from the service's own metadata layers
  naip-cir  USDA NAIP (USGS NAIPPlus service) color-infrared: live vegetation
            red, dead/gray timber shows gray-green
  naip-rgb  USDA NAIP natural color

Overlays: timber blocks (yellow), OSM motorized routes (red), waypoints
(BED magenta, FEED lime, SADDLE cyan, GLASS white, WATER blue, ACCESS orange),
500 m / 1 km scale bar. North is up.

Usage:
  python3 imagery_sheets.py blocks --data data --kml <timber_blocks.kml> --out DIR [--source esri] [--ids T01,T05]
  python3 imagery_sheets.py points --data data --kml <timber_blocks.kml> --out DIR [--source esri] [--names B3-03,F5-04]
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import requests
from PIL import Image, ImageDraw, ImageFont

ESRI = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"
NAIP = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer"
UTM = 32613
COLORS = {"BED": (255, 0, 255), "FEED": (130, 255, 0), "SADDLE": (0, 230, 255), "GLASS": (255, 255, 255),
          "WATER": (70, 150, 255), "ACCESS": (255, 150, 0)}
YELLOW = (255, 230, 0)
ROAD = (255, 40, 40)
_session = requests.Session()


def font(sz: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=sz)
    except TypeError:
        return ImageFont.load_default()


def get(url: str, params: dict, tries: int = 4) -> requests.Response:
    for i in range(tries):
        try:
            r = _session.get(url, params=params, timeout=120)
            r.raise_for_status()
            return r
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))
    raise RuntimeError("unreachable")


def fetch_chip(source: str, bbox: tuple, px: int) -> Image.Image:
    xmin, ymin, xmax, ymax = bbox
    p = {"bbox": f"{xmin},{ymin},{xmax},{ymax}", "bboxSR": UTM, "imageSR": UTM, "size": f"{px},{px}",
         "format": "jpg", "f": "image"}
    if source == "esri":
        r = get(f"{ESRI}/export", p | {"transparent": "false"})
    else:
        fn = "FalseColorComposite" if source == "naip-cir" else "NaturalColor"
        r = get(f"{NAIP}/exportImage", p | {"renderingRule": json.dumps({"rasterFunction": fn})})
    if not r.headers.get("content-type", "").startswith("image"):
        raise RuntimeError(f"not an image: {r.text[:300]}")
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def capture_meta(source: str, x: float, y: float) -> tuple[str, str | None]:
    if source == "esri":
        for layer in (9, 10, 11):
            r = get(f"{ESRI}/{layer}/query", {
                "geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "inSR": UTM,
                "spatialRel": "esriSpatialRelIntersects", "returnGeometry": "false", "f": "json",
                "outFields": "SRC_DATE,SRC_RES,SRC_DESC,NICE_NAME"})
            fs = r.json().get("features", [])
            if fs:
                a = fs[0]["attributes"]
                s = str(a.get("SRC_DATE"))
                d = f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else s
                return f"Vantor {a.get('NICE_NAME') or ''} {a.get('SRC_DESC') or ''} {d}, {a.get('SRC_RES')} m".replace("  ", " "), d
        return "Esri World Imagery (date n/a)", None
    r = get(f"{NAIP}/query", {
        "where": "Category=1", "geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "inSR": UTM,
        "spatialRel": "esriSpatialRelIntersects", "outFields": "Year,acquisition_date", "returnGeometry": "false",
        "orderByFields": "Year DESC", "f": "json"})
    fs = r.json().get("features", [])
    if fs:
        a = fs[0]["attributes"]
        ad = a.get("acquisition_date")
        d = dt.datetime.fromtimestamp(ad / 1000, dt.timezone.utc).date().isoformat() if isinstance(ad, (int, float)) else str(a.get("Year"))
        return f"USDA NAIP {'color-infrared' if source == 'naip-cir' else 'natural color'} {d}, 0.6 m", d
    return "NAIP (date n/a)", None


def to_px(x, y, bbox, w, h):
    xmin, ymin, xmax, ymax = bbox
    return ((x - xmin) / (xmax - xmin) * w, (ymax - y) / (ymax - ymin) * h)


def draw_geom(dr, geom, bbox, w, h, color, width):
    gt = geom.geom_type
    if gt == "Polygon":
        for ring in [geom.exterior, *geom.interiors]:
            dr.line([to_px(x, y, bbox, w, h) for x, y in ring.coords], fill=color, width=width, joint="curve")
    elif gt == "LineString":
        pts = [to_px(x, y, bbox, w, h) for x, y in geom.coords]
        if len(pts) > 1:
            dr.line(pts, fill=color, width=width, joint="curve")
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            draw_geom(dr, g, bbox, w, h, color, width)


def overlay(img, bbox, blocks, roads, wps, focus_block=None, focus_wp=None):
    w, h = img.size
    dr = ImageDraw.Draw(img)
    win = gpd.GeoSeries.from_xy([bbox[0], bbox[2]], [bbox[1], bbox[3]], crs=UTM).total_bounds
    from shapely.geometry import box as sbox
    frame = sbox(*win)
    for _, r in roads[roads.intersects(frame)].iterrows():
        draw_geom(dr, r.geometry.intersection(frame.buffer(50)), bbox, w, h, ROAD, 2)
    for _, b in blocks[blocks.intersects(frame)].iterrows():
        draw_geom(dr, b.geometry, bbox, w, h, YELLOW, 4 if b["bid"] == focus_block else 2)
        if b["bid"] != focus_block:
            c = b.geometry.representative_point()
            if frame.contains(c):
                dr.text(to_px(c.x, c.y, bbox, w, h), b["bid"], font=font(18), fill=YELLOW, stroke_width=2, stroke_fill=(0, 0, 0), anchor="mm")
    f = font(17)
    for _, p in wps[wps.intersects(frame)].iterrows():
        x, y = to_px(p.geometry.x, p.geometry.y, bbox, w, h)
        col = COLORS.get(p["wp_type"], (255, 255, 255))
        rad = 9 if p["code"] == focus_wp else 6
        dr.ellipse([x - rad, y - rad, x + rad, y + rad], outline=(0, 0, 0), fill=col, width=2)
        dr.text((x + rad + 3, y), p["code"], font=f, fill=col, stroke_width=2, stroke_fill=(0, 0, 0), anchor="lm")
    # scale bar
    mpp = (bbox[2] - bbox[0]) / w
    span = 1000 if (bbox[2] - bbox[0]) > 3000 else (500 if (bbox[2] - bbox[0]) > 900 else 200)
    L = span / mpp
    x0, y0 = 14, h - 22
    dr.rectangle([x0 - 2, y0 - 8, x0 + L + 2, y0 + 8], fill=(0, 0, 0))
    dr.rectangle([x0, y0 - 5, x0 + L, y0 + 5], fill=(255, 255, 255))
    dr.text((x0 + L + 8, y0), f"{span if span < 1000 else span // 1000}{' m' if span < 1000 else ' km'}", font=font(16),
            fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0), anchor="lm")
    return img


def labeled(img, lines, bar_h=46):
    w, h = img.size
    out = Image.new("RGB", (w, h + bar_h), (20, 20, 20))
    out.paste(img, (0, bar_h))
    dr = ImageDraw.Draw(out)
    dr.text((8, 3), lines[0], font=font(19), fill=(255, 255, 255))
    if len(lines) > 1:
        dr.text((8, 25), lines[1], font=font(15), fill=(200, 200, 200))
    return out


def sheet(tiles, cols, gap=8):
    w, h = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    s = Image.new("RGB", (cols * w + (cols - 1) * gap, rows * h + (rows - 1) * gap), (0, 0, 0))
    for i, t in enumerate(tiles):
        s.paste(t, ((i % cols) * (w + gap), (i // cols) * (h + gap)))
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["blocks", "zoom", "points"])
    ap.add_argument("--data", default="data")
    ap.add_argument("--kml", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default="esri", choices=["esri", "naip-cir", "naip-rgb"])
    ap.add_argument("--ids", default=None)
    ap.add_argument("--names", default=None)
    ap.add_argument("--px", type=int, default=0)
    ap.add_argument("--side-m", type=float, default=700)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "chips").mkdir(parents=True, exist_ok=True)

    blocks = gpd.read_file(a.kml, layer="Security_timber").to_crs(UTM)
    blocks["bid"] = blocks["Name"].str.split().str[0]
    blocks["geometry"] = blocks.geometry.buffer(45).buffer(-45).simplify(10)
    wps = gpd.read_file(Path(a.data) / "work" / "waypoints.geojson").to_crs(UTM)
    wps["code"] = wps["name"].str.split().str[0]
    roads = gpd.read_file(Path(a.data) / "work" / "motorized.geojson").to_crs(UTM)
    roads = roads[roads.geometry.notna()]

    jobs = []
    if a.what == "zoom":
        from shapely.ops import polylabel
        sel = blocks if not a.ids else blocks[blocks["bid"].isin(a.ids.split(","))]
        for _, b in sel.iterrows():
            g = b.geometry
            big = max(getattr(g, "geoms", [g]), key=lambda q: q.area)
            c = polylabel(big, tolerance=10)
            s = a.side_m
            for src in ("esri", "naip-cir"):
                jobs.append({"key": f"{b['bid']}z", "source": src, "bbox": (c.x - s / 2, c.y - s / 2, c.x + s / 2, c.y + s / 2),
                             "center": (c.x, c.y), "title": f"{b['bid']} core  ·  {int(s)} m across", "focus_block": b["bid"], "focus_wp": None})
        px, cols, per = a.px or 760, 2, 4
    elif a.what == "blocks":
        sel = blocks if not a.ids else blocks[blocks["bid"].isin(a.ids.split(","))]
        for _, b in sel.iterrows():
            x0, y0, x1, y1 = b.geometry.bounds
            side = max(x1 - x0, y1 - y0) * 1.15
            side = max(side, 1500)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            jobs.append({"key": b["bid"], "bbox": (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2),
                         "center": (b.geometry.representative_point().x, b.geometry.representative_point().y),
                         "title": f"{b['bid']}  ·  {b['Name'].split(' ', 2)[2]}", "focus_block": b["bid"], "focus_wp": None,
                         "source": a.source})
        px, cols, per = a.px or 510, 3, 6
    else:
        sel = wps.sort_values(["area_rank", "code"])
        if a.names:
            sel = sel[sel["code"].isin(a.names.split(","))]
        for _, p in sel.iterrows():
            s = a.side_m
            jobs.append({"key": p["code"], "bbox": (p.geometry.x - s / 2, p.geometry.y - s / 2, p.geometry.x + s / 2, p.geometry.y + s / 2),
                         "center": (p.geometry.x, p.geometry.y),
                         "title": f"{p['code']}  {p['wp_type']}  {int(p['elevation_ft']):,} ft  ·  area {p['area_rank']} {p['hunt_area']}",
                         "focus_block": None, "focus_wp": p["code"], "source": a.source})
        px, cols, per = a.px or 500, 3, 9

    def run(j):
        img = fetch_chip(j["source"], j["bbox"], px)
        meta, date = capture_meta(j["source"], *j["center"])
        img = overlay(img, j["bbox"], blocks, roads, wps, j["focus_block"], j["focus_wp"])
        img.save(out / "chips" / f"{j['key']}_{j['source']}.jpg", quality=90)
        return j | {"meta": meta, "date": date, "img": labeled(img, [j["title"], meta])}

    with ThreadPoolExecutor(max_workers=4) as ex:
        done = list(ex.map(run, jobs))

    meta_out = {}
    for i in range(0, len(done), per):
        grp = done[i:i + per]
        name = f"{a.what}_{a.source if a.what != 'zoom' else 'pair'}_{i // per + 1:02d}.png"
        sheet([g["img"] for g in grp], cols).save(out / name)
        print(f"{name}: {', '.join(g['key'] for g in grp)}")
        for g in grp:
            meta_out[f"{g['key']}|{g['source']}"] = {"source": g["meta"], "date": g["date"], "sheet": name}
    mp = out / f"meta_{a.what}.json"
    old = json.loads(mp.read_text()) if mp.exists() else {}
    mp.write_text(json.dumps(old | meta_out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
