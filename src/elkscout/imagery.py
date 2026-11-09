"""Photo check: sub-meter imagery sheets of every security block and waypoint,
plus the review loop that writes photo verdicts back into the outputs.

    elkscout imagery --config <profile> --data data      # build sheets (network)
    -> data/out/imagery/*.png, data/out/imagery/imagery_check.pdf,
       data/work/imagery_review.json (a template to fill in)
    elkscout waypoints / report                          # apply verdicts

Sources:
- USDA NAIP via USGS (0.6 m), NEWEST flight forced with a mosaic rule. Color
  infrared is the dead-timber test: live conifer reads dark red, aspen/willow
  bright pink-red (leaf-on), dead/gray timber gray-green.
- Esri World Imagery (0.3-0.5 m natural color; capture dates vary by place
  and are read from the service's metadata layers).
Sentinel-2 (sources/sentinel.py) is the near-live layer; these photos are the
sharp-but-older layer. Neither replaces OnX's own imagery — the guide says to
flip through OnX before committing to a block.

Review loop: imagery_review.json has one entry per block id and per waypoint,
keyed by a STABLE waypoint id (type + location, not the rank-based name, which
can shift between runs). Fill "verdict" after looking at the sheets
(e.g. "dense live conifer", "mostly dead - gray crowns", "poor bed: aspen
edge"). apply_review() then appends "Photos (<date>): <verdict>." to each
waypoint note and records block verdicts; blocks judged dead stop counting
toward hunt-area ranking.
"""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path

import geopandas as gpd

from . import endpoints
from .config import Config
from .factors import _read_vec
from .grid import Grid
from .net import Net
from .paths import Workspace

log = logging.getLogger("elkscout.imagery")

SOURCE = "imagery"
COLORS = {"BED": (255, 0, 255), "FEED": (130, 255, 0), "SADDLE": (0, 230, 255), "GLASS": (255, 255, 255),
          "WATER": (70, 150, 255), "ACCESS": (255, 150, 0), "CAMP": (180, 120, 255)}
YELLOW = (255, 230, 0)
ROAD = (255, 40, 40)
POINT_SIDE_M = 700.0
BLOCK_MIN_SIDE_M = 1500.0
MAX_BLOCKS = 25
NAIP_NEWEST = {  # newest flight on top, so the picture and its metadata agree
    "mosaicMethod": "esriMosaicAttribute",
    "sortField": "Year",
    "sortValue": "2100",
    "ascending": True,
    "where": "Category = 1",
}


def wp_id(wp_type: str, lon: float, lat: float) -> str:
    """Stable waypoint key: survives re-ranking/renaming, changes only if the point moves."""
    return f"{wp_type}@{lat:.5f},{lon:.5f}"


def _pil():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:  # pragma: no cover - environment dependent
        raise RuntimeError("photo sheets need Pillow: pip install -e '.[imagery]'") from e
    return Image, ImageDraw, ImageFont


def _font(size: int):
    _, _, ImageFont = _pil()
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
              "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _validate_image(raw: bytes) -> None:
    if not (raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"expected an image, got: {raw[:160]!r}")


# -- fetching ----------------------------------------------------------------

def fetch_chip(net: Net, source: str, bbox: tuple, px: int, epsg: int):
    Image, _, _ = _pil()
    xmin, ymin, xmax, ymax = bbox
    p = {"bbox": f"{xmin:.1f},{ymin:.1f},{xmax:.1f},{ymax:.1f}", "bboxSR": epsg, "imageSR": epsg,
         "size": f"{px},{px}", "format": "jpg", "f": "image"}
    if source == "esri":
        url = f"{endpoints.ESRI_WORLD_IMAGERY}/export"
    else:
        url = f"{endpoints.NAIP_IMAGESERVER}/exportImage"
        fn = "FalseColorComposite" if source == "naip-cir" else "NaturalColor"
        p["renderingRule"] = json.dumps({"rasterFunction": fn})
        p["mosaicRule"] = json.dumps(NAIP_NEWEST)
    raw = net.fetch_bytes(url, p, source=SOURCE, ext="jpg", validate=_validate_image)
    return Image.open(io.BytesIO(raw)).convert("RGB")


def capture_date(net: Net, source: str, x: float, y: float, epsg: int) -> tuple[str, str | None]:
    """(human label, ISO date or None) for the imagery under a point."""
    if source == "esri":
        for layer in (9, 10, 11):
            try:
                r = net.fetch_json(f"{endpoints.ESRI_WORLD_IMAGERY}/{layer}/query", {
                    "geometry": f"{x:.1f},{y:.1f}", "geometryType": "esriGeometryPoint", "inSR": epsg,
                    "spatialRel": "esriSpatialRelIntersects", "returnGeometry": "false", "f": "json",
                    "outFields": "SRC_DATE,SRC_RES,SRC_DESC,NICE_NAME"}, source=SOURCE)
            except Exception:  # noqa: BLE001 - metadata is best-effort
                continue
            fs = r.get("features") or []
            if fs:
                a = fs[0].get("attributes") or {}
                s = str(a.get("SRC_DATE"))
                d = f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else s
                return f"satellite {d}, {a.get('SRC_RES')} m", d
        return "satellite (date n/a)", None
    try:
        r = net.fetch_json(f"{endpoints.NAIP_IMAGESERVER}/query", {
            "where": "Category=1", "geometry": f"{x:.1f},{y:.1f}", "geometryType": "esriGeometryPoint",
            "inSR": epsg, "spatialRel": "esriSpatialRelIntersects", "outFields": "Year,acquisition_date",
            "returnGeometry": "false", "orderByFields": "Year DESC", "f": "json"}, source=SOURCE)
    except Exception:  # noqa: BLE001
        return "NAIP (date n/a)", None
    fs = r.get("features") or []
    if not fs:
        return "NAIP (date n/a)", None
    a = fs[0].get("attributes") or {}
    ad = a.get("acquisition_date")
    if isinstance(ad, (int, float)):
        import datetime as dt

        d = dt.datetime.fromtimestamp(ad / 1000, dt.timezone.utc).date().isoformat()
    else:
        d = str(a.get("Year"))
    kind = "color-infrared" if source == "naip-cir" else "natural color"
    return f"NAIP {kind} {d}, 0.6 m", d


# -- drawing -------------------------------------------------------------------

def _to_px(x, y, bbox, w, h):
    xmin, ymin, xmax, ymax = bbox
    return ((x - xmin) / (xmax - xmin) * w, (ymax - y) / (ymax - ymin) * h)


def _draw_geom(dr, geom, bbox, w, h, color, width):
    gt = geom.geom_type
    if gt == "Polygon":
        for ring in [geom.exterior, *geom.interiors]:
            dr.line([_to_px(x, y, bbox, w, h) for x, y in ring.coords], fill=color, width=width)
    elif gt == "LineString":
        pts = [_to_px(x, y, bbox, w, h) for x, y in geom.coords]
        if len(pts) > 1:
            dr.line(pts, fill=color, width=width)
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            _draw_geom(dr, g, bbox, w, h, color, width)


def overlay(img, bbox, blocks, roads, wps, focus_block=None, focus_wp=None):
    """Blocks (yellow), motorized routes (red), waypoints by type, scale bar. North up."""
    from shapely.geometry import box as sbox

    _, ImageDraw, _ = _pil()
    w, h = img.size
    dr = ImageDraw.Draw(img)
    frame = sbox(*bbox)
    if roads is not None and len(roads):
        for geom in roads[roads.intersects(frame)].geometry:
            _draw_geom(dr, geom.intersection(frame.buffer(50)), bbox, w, h, ROAD, 2)
    if blocks is not None and len(blocks):
        for _, b in blocks[blocks.intersects(frame)].iterrows():
            _draw_geom(dr, b.geometry, bbox, w, h, YELLOW, 4 if b["id"] == focus_block else 2)
    f = _font(16)
    if wps is not None and len(wps):
        for _, p in wps[wps.intersects(frame)].iterrows():
            x, y = _to_px(p.geometry.x, p.geometry.y, bbox, w, h)
            col = COLORS.get(p["wp_type"], (255, 255, 255))
            rad = 9 if p["code"] == focus_wp else 6
            dr.ellipse([x - rad, y - rad, x + rad, y + rad], outline=(0, 0, 0), fill=col, width=2)
            dr.text((x + rad + 3, y - 8), p["code"], font=f, fill=col)
    span = 1000 if (bbox[2] - bbox[0]) > 3000 else (500 if (bbox[2] - bbox[0]) > 900 else 200)
    bar = span / ((bbox[2] - bbox[0]) / w)
    x0, y0 = 14, h - 22
    dr.rectangle([x0 - 2, y0 - 8, x0 + bar + 2, y0 + 8], fill=(0, 0, 0))
    dr.rectangle([x0, y0 - 5, x0 + bar, y0 + 5], fill=(255, 255, 255))
    dr.text((x0 + bar + 8, y0 - 9), f"{span} m" if span < 1000 else "1 km", font=_font(15), fill=(255, 255, 255))
    return img


def _labeled(img, title: str, sub: str, bar_h: int = 46):
    Image, ImageDraw, _ = _pil()
    w, h = img.size
    out = Image.new("RGB", (w, h + bar_h), (20, 20, 20))
    out.paste(img, (0, bar_h))
    dr = ImageDraw.Draw(out)
    dr.text((8, 3), title, font=_font(18), fill=(255, 255, 255))
    dr.text((8, 25), sub, font=_font(14), fill=(200, 200, 200))
    return out


def _sheet(tiles, cols: int, gap: int = 8):
    Image, _, _ = _pil()
    w, h = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    s = Image.new("RGB", (cols * w + (cols - 1) * gap, rows * h + (rows - 1) * gap), (0, 0, 0))
    for i, t in enumerate(tiles):
        s.paste(t, ((i % cols) * (w + gap), (i // cols) * (h + gap)))
    return s


# -- jobs ----------------------------------------------------------------------

def plan_jobs(blocks_g: gpd.GeoDataFrame, wps_g: gpd.GeoDataFrame) -> list[dict]:
    """Every chip to fetch: each block (extent + core, satellite + CIR), each waypoint
    (satellite; BED also CIR — the bed cover question is the one CIR answers)."""
    from shapely.ops import polylabel

    jobs: list[dict] = []
    for _, b in blocks_g.sort_values("acres", ascending=False).head(MAX_BLOCKS).iterrows():
        x0, y0, x1, y1 = b.geometry.bounds
        side = max(max(x1 - x0, y1 - y0) * 1.15, BLOCK_MIN_SIDE_M)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        big = max(getattr(b.geometry, "geoms", [b.geometry]), key=lambda q: q.area)
        core = polylabel(big, tolerance=10)
        title = f"{b['id']}  {int(b['acres']):,} ac  {b['elev_lo_ft']:,}-{b['elev_hi_ft']:,} ft"
        for src in ("esri", "naip-cir"):
            jobs.append({"group": "blocks", "key": b["id"], "kind": "block", "source": src, "focus_block": b["id"],
                         "bbox": (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2),
                         "center": (core.x, core.y), "title": title})
            s = POINT_SIDE_M
            jobs.append({"group": "block_cores", "key": b["id"], "kind": "block", "source": src, "focus_block": b["id"],
                         "bbox": (core.x - s / 2, core.y - s / 2, core.x + s / 2, core.y + s / 2),
                         "center": (core.x, core.y), "title": f"{b['id']} core, {int(s)} m across"})
    for _, p in wps_g.sort_values(["area_rank", "code"]).iterrows():
        s = POINT_SIDE_M
        srcs = ("esri", "naip-cir") if p["wp_type"] == "BED" else ("esri",)
        for src in srcs:
            jobs.append({"group": "points", "key": p["wp_id"], "kind": "waypoint", "source": src,
                         "focus_wp": p["code"], "name": p["name"],
                         "bbox": (p.geometry.x - s / 2, p.geometry.y - s / 2, p.geometry.x + s / 2, p.geometry.y + s / 2),
                         "center": (p.geometry.x, p.geometry.y),
                         "title": f"{p['code']}  {p['wp_type']}  {int(p['elevation_ft']):,} ft  area {p['area_rank']}"})
    return jobs


def make_sheets(net: Net, ws: Workspace, cfg: Config, px: int = 500) -> dict:
    """Fetch chips, draw overlays, write sheets + PDF + a review template."""
    from concurrent.futures import ThreadPoolExecutor

    grid = Grid.load(ws.grid_json)
    epsg = grid.epsg
    blocks = _read_vec(ws.timber_blocks_geojson)
    blocks_g = blocks.to_crs(epsg=epsg) if len(blocks) else blocks
    wps = gpd.read_file(ws.waypoints_geojson)
    wps_g = wps.to_crs(epsg=epsg)
    wps_g["code"] = wps_g["name"].str.split().str[0]
    roads = _read_vec(ws.motorized_geojson)
    roads_g = roads.to_crs(epsg=epsg) if len(roads) else None

    jobs = plan_jobs(blocks_g, wps_g)
    out = ws.imagery_dir
    out.mkdir(parents=True, exist_ok=True)

    def run(j):
        img = fetch_chip(net, j["source"], j["bbox"], px, epsg)
        label, date = capture_date(net, j["source"], *j["center"], epsg)
        img = overlay(img, j["bbox"], blocks_g, roads_g, wps_g, j.get("focus_block"), j.get("focus_wp"))
        return j | {"label": label, "date": date, "img": _labeled(img, j["title"], label)}

    with ThreadPoolExecutor(max_workers=4) as ex:
        done = list(ex.map(run, jobs))

    pages = []
    meta: dict[str, dict] = {}
    for group, cols, per in (("blocks", 2, 4), ("block_cores", 2, 4), ("points", 3, 9)):
        tiles = [d for d in done if d["group"] == group]
        for i in range(0, len(tiles), per):
            grp = tiles[i : i + per]
            page = _sheet([g["img"] for g in grp], cols)
            name = f"{group}_{i // per + 1:02d}.png"
            page.save(out / name)
            pages.append(page)
            for g in grp:
                meta.setdefault(g["key"], {})[g["source"]] = {"date": g["date"], "label": g["label"], "sheet": name}
    if pages:
        pdf = out / "imagery_check.pdf"
        pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=110)
    (out / "imagery_meta.json").write_text(json.dumps(meta, indent=1))
    _write_review_template(ws, blocks, wps, meta)
    log.info("imagery: %d chips -> %d sheet pages in %s; review template %s",
             len(done), len(pages), out, ws.imagery_review_json)
    return meta


def _write_review_template(ws: Workspace, blocks, wps, meta: dict) -> None:
    """Keep any verdicts already written; add new keys with empty verdicts."""
    old = json.loads(ws.imagery_review_json.read_text()) if ws.imagery_review_json.exists() else {}
    review = {
        "_how": "Look at data/out/imagery/*.png (or imagery_check.pdf) and fill each 'verdict'. "
                "Blocks: 'dense live conifer' / 'live, moderately dense' / 'mostly dead (gray crowns)'. "
                "Waypoints: what the photos show at the point, e.g. 'inside dense live conifer', "
                "'poor bed: leafless aspen edge, cover 250 m west'. Leave blank to skip. "
                "Then re-run `elkscout waypoints` (if any block is dead) and `elkscout report`.",
        "blocks": {},
        "waypoints": {},
    }
    for _, b in blocks.iterrows() if len(blocks) else []:
        prev = (old.get("blocks") or {}).get(b["id"], {})
        review["blocks"][b["id"]] = {
            "verdict": prev.get("verdict", ""),
            "dates": {s: v.get("date") for s, v in meta.get(b["id"], {}).items()},
        }
    for _, p in wps.iterrows():
        prev = (old.get("waypoints") or {}).get(p["wp_id"], {})
        review["waypoints"][p["wp_id"]] = {
            "name": p["name"],
            "verdict": prev.get("verdict", ""),
            "dates": {s: v.get("date") for s, v in meta.get(p["wp_id"], {}).items()},
        }
    ws.imagery_review_json.write_text(json.dumps(review, indent=1))


# -- applying verdicts ---------------------------------------------------------

def apply_review(ws: Workspace, cfg: Config) -> int:
    """Write photo verdicts into waypoint notes and block attributes. Idempotent:
    notes are rebuilt from the model sentence (desc_model) every time."""
    if not ws.imagery_review_json.exists():
        return 0
    review = json.loads(ws.imagery_review_json.read_text())
    n = 0

    wps = gpd.read_file(ws.waypoints_geojson)
    if "desc_model" in wps.columns:
        limit = cfg.outputs.desc_max_chars
        notes = []
        for _, p in wps.iterrows():
            base = str(p["desc_model"])
            entry = (review.get("waypoints") or {}).get(str(p.get("wp_id")), {})
            verdict = str(entry.get("verdict") or "").strip()
            if verdict:
                n += 1
                date = (entry.get("dates") or {}).get("esri") or (entry.get("dates") or {}).get("naip-cir")
                tag = f" Photos ({date}): {verdict}." if date else f" Photos: {verdict}."
                base = base + tag if len(base) + len(tag) <= limit else base[: max(0, limit - len(tag) - 3)].rstrip() + "..." + tag
            notes.append(base)
        wps["desc"] = notes
        wps["imagery"] = [
            str(((review.get("waypoints") or {}).get(str(i), {}) or {}).get("verdict") or "") for i in wps["wp_id"]
        ]
        ws.waypoints_geojson.unlink(missing_ok=True)
        wps.to_file(ws.waypoints_geojson, driver="GeoJSON")

    blocks = _read_vec(ws.timber_blocks_geojson)
    if len(blocks):
        verdicts = {k: str((v or {}).get("verdict") or "").strip() for k, v in (review.get("blocks") or {}).items()}
        blocks["imagery"] = [verdicts.get(str(b), "") for b in blocks["id"]]
        n += sum(1 for v in blocks["imagery"] if v)
        ws.timber_blocks_geojson.unlink(missing_ok=True)
        blocks.to_file(ws.timber_blocks_geojson, driver="GeoJSON")
    log.info("imagery: applied %d photo verdict(s)", n)
    return n


def block_is_dead(verdict) -> bool:
    v = str(verdict or "").lower()
    return "dead" in v and "live" not in v.replace("dead", "")
