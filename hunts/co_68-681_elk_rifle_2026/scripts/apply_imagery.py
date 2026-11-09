"""Write the imagery-check results into the delivered package.

- GPX (all + per-area), waypoint KML, map.html popups, briefing.md rows:
  append "Imagery: ..." to each waypoint note
- timber-block KML: imagery verdict + capture dates in each description;
  mostly-dead blocks get "(mostly dead)" in the name
- waypoints.xlsx: "Imagery" column, About sheet fixed for this run
- snippets for the guide: timber table with an imagery column, bed table,
  block capture dates, count of November block captures
- imagery_check.pdf: cover page + every sheet that was reviewed

Idempotent: re-running does not double-append.

Usage (repo root): python3 apply_imagery.py --out data/out --imagery <dir>
                   --timber-table <md> --snippets <dir>
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from copy import copy
from datetime import date
from html import escape as hesc
from pathlib import Path
from xml.sax.saxutils import escape

import geopandas as gpd
import openpyxl
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw, ImageFont

# What the imagery shows at each waypoint (reviewed by eye, sheet by sheet).
POINTS = {
    "B1-01": "inside a band of live conifer, moderate density, openings on both sides",
    "F1-01": "open park, grass between scattered trees",
    "F1-02": "open grass and shrub slope beside timber",
    "S1-01": "open ground with scattered trees",
    "S1-02": "mixed open ground and timber",
    "B2-01": "edge of a live conifer stand, meadow to the NW",
    "B2-02": "live conifer of moderate density; denser timber 100-150 m NW",
    "F2-01": "open meadow at a timber edge",
    "F2-02": "open grass and sage with scattered trees; two-track to the SE",
    "G2-01": "at a timber edge, so the view may be blocked; open slope just south",
    "S2-01": "open slope with scattered trees; timber patch to the north",
    "S2-02": "meadow and timber edge",
    "S2-03": "open ground with scattered trees",
    "W2-01": "inside dense timber; the creek runs along its north edge",
    "A3-01": "road end in the Middle Creek bottom; a track continues north (check the MVUM before driving it)",
    "B3-01": "poor bed: edge of an aspen clone, leafless in November; dense conifer about 250 m west",
    "B3-02": "poor bed: west edge of a timber island of about 10 acres in open sage",
    "B3-03": "inside dense dark timber (block T12)",
    "A4-01": "road end in a meadow between timber stands",
    "A4-02": "road end in open sage with scattered trees",
    "A4-03": "road end at a drainage, open ground",
    "A4-04": "Stone Cellar campground loop by the creek",
    "B4-01": "poor bed: broken rock with scattered trees, not continuous cover",
    "B4-02": "timber edge; a dense conifer band starts 50-100 m north",
    "F4-01": "open grass among timber stringers and rock",
    "F4-02": "meadow edge against dense timber near Fourmile Creek",
    "A5-01": "on FR 874 in open timber",
    "F5-01": "open grassy slope, timber to the north",
    "F5-02": "open grass and sage with scattered trees",
    "F5-03": "open grassland with scattered conifers",
    "F5-04": "open slope right beside a dense conifer stringer",
    "F5-05": "open grass, timber to the north",
    "G5-01": "timberline with scattered trees; check the view",
    "G5-02": "open alpine slope",
    "G5-03": "open alpine meadow ringed by timber",
    "G5-04": "open alpine summit",
    "G5-05": "open alpine slope",
    "G5-06": "open talus summit",
    "S5-01": "scattered timber",
    "W5-01": "moderately dense conifer, meadow to the NW",
}

# Bed points for the guide table: (code, verdict, what the photos show).
BEDS = [
    ("B3-03", "good", "inside dense dark timber (T12)"),
    ("B1-01", "good", "inside a band of live conifer, moderate density, openings on both sides"),
    ("B2-02", "good", "live conifer of moderate density; denser timber 100–150 m NW"),
    ("B2-01", "edge", "edge of a live conifer stand, meadow to the NW; the cover is the stand behind it"),
    ("B4-02", "edge", "timber edge; the cover is the dense conifer band that starts 50–100 m north"),
    ("B3-01", "**poor**", "edge of an aspen clone, leafless in November; the cover is dense conifer about 250 m west"),
    ("B3-02", "**poor**", "west edge of a timber island of about 10 acres in open sage; skip it"),
    ("B4-01", "**poor**", "broken rock with scattered trees; skip it"),
]

BLOCKS = {
    "T01": "dense live conifer",
    "T02": "dense live conifer (satellite image cloudy; color-infrared clear)",
    "T03": "live, moderately dense",
    "T04": "dense live conifer, small parks inside",
    "T05": "dense live conifer, aspen pockets",
    "T06": "live, moderately dense",
    "T07": "live, some dead crowns mixed in",
    "T08": "live, some dead crowns mixed in",
    "T09": "mostly dead (gray crowns), not dark timber",
    "T10": "mostly dead (gray crowns), not dark timber",
    "T11": "dense young regrowth, roads and cuts at its edges",
    "T12": "dense live dark timber",
    "T13": "dense live conifer, aspen on its east edge",
    "T14": "dense live conifer, aspen and willow creek bottom",
    "T15": "live, moderately dense",
    "T16": "live, moderately dense",
    "T17": "mixed live and dead",
    "T18": "dense live core",
    "T19": "live, moderately dense",
    "T20": "live, moderately dense",
    "T21": "live pocket inside dead timber",
}
DEAD = {"T09", "T10"}


def font(sz: int, bold: bool = False):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        return ImageFont.truetype(p, sz)
    except OSError:
        return ImageFont.load_default()


def nice(d: str) -> str:
    x = date.fromisoformat(d)
    m = "Sept" if x.month == 9 else x.strftime("%b")
    return f"{m} {x.day}, {x.year}"


def patch_notes(text: str, tag_name: str, tag_desc: str, codes: dict) -> tuple[str, int]:
    """Append 'Imagery: ...' to the <desc>/<description> that follows each <name>CODE ...</name>.
    A trailing '(score X)' stays last."""
    n = 0

    def repl(m: re.Match) -> str:
        nonlocal n
        code = m.group(2).split()[0]
        if code not in codes or "Imagery:" in m.group(5):
            return m.group(0)
        n += 1
        note = f"Imagery: {escape(codes[code])}."
        body = m.group(5)
        sm = re.match(r"^(.*?)(\s*\(score [0-9.]+\))$", body, re.S)
        body = f"{sm.group(1)} {note}{sm.group(2)}" if sm else f"{body} {note}"
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{body}{m.group(6)}"

    pat = re.compile(rf"(<{tag_name}>)([^<]+)(</{tag_name}>)(\s*<{tag_desc}>)([^<]*)(</{tag_desc}>)")
    return pat.sub(repl, text), n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--imagery", required=True)
    ap.add_argument("--timber-table", required=True)
    ap.add_argument("--snippets", required=True)
    ap.add_argument("--data", default="data")
    a = ap.parse_args()
    out, img, snip = Path(a.out), Path(a.imagery), Path(a.snippets)
    snip.mkdir(parents=True, exist_ok=True)
    mp = json.loads((img / "meta_points.json").read_text())
    mz = json.loads((img / "meta_zoom.json").read_text())

    wp = gpd.read_file(Path(a.data) / "work" / "waypoints.geojson")
    codes = {r["name"].split()[0] for _, r in wp.iterrows()}
    assert codes == set(POINTS), (codes ^ set(POINTS))

    sat = {k: mp[f"{k}|esri"]["date"] for k in POINTS}
    pnotes = {k: f"{v} (satellite {sat[k]})" for k, v in POINTS.items()}

    # GPX + waypoint KML
    for f in sorted(out.glob("*.gpx")) + [out / "elkscout_unit68-681.kml"]:
        t, n = patch_notes(f.read_text(), "name", "desc" if f.suffix == ".gpx" else "description", pnotes)
        f.write_text(t)
        print(f"{f.name}: {n} notes added")

    # map.html popups and briefing.md rows
    mh, br = (out / "map.html").read_text(), (out / "briefing.md").read_text()
    nm = nb = 0
    for _, r in wp.iterrows():
        code, d = r["name"].split()[0], r["desc"]
        tag = f"<br><i>Imagery: {hesc(pnotes[code])}.</i>"
        if mh.count(d) == 1 and d + "<br><i>Imagery:" not in mh:
            mh = mh.replace(d, d + tag); nm += 1
        if br.count(d) == 1 and d + " Imagery:" not in br:
            br = br.replace(d, f"{d} Imagery: {pnotes[code]}."); nb += 1
    (out / "map.html").write_text(mh)
    (out / "briefing.md").write_text(br)
    print(f"map.html: {nm} popups, briefing.md: {nb} rows")

    # timber KML
    bnotes = {}
    for b, v in BLOCKS.items():
        bnotes[b] = (f"{v} (core checked on satellite {mz[f'{b}z|esri']['date']} and "
                     f"NAIP color-infrared {mz[f'{b}z|naip-cir']['date']})")
    f = out / "elkscout_unit68-681_timber_blocks.kml"
    t, n = patch_notes(f.read_text(), "name", "description", bnotes)
    for b in DEAD:
        t = re.sub(rf"<name>({b} timber \d+ ac)</name>", r"<name>\1 (mostly dead)</name>", t)
        assert len(re.findall(rf"<name>{b} timber \d+ ac \(mostly dead\)</name>", t)) == 1, b
    f.write_text(t)
    print(f"{f.name}: {n} notes added")

    # xlsx
    wb = openpyxl.load_workbook(out / "waypoints.xlsx")
    ws = wb["Waypoints"]
    hdr = [c.value for c in ws[1]]
    col = hdr.index("Imagery") + 1 if "Imagery" in hdr else ws.max_column + 1
    src = col - 1
    ws.cell(1, col, "Imagery")._style = copy(ws.cell(1, src)._style)
    for r in range(2, ws.max_row + 1):
        code = str(ws.cell(r, 1).value).split()[0]
        c = ws.cell(r, col, pnotes[code])
        c._style = copy(ws.cell(r, src)._style)
    ws.column_dimensions[get_column_letter(col)].width = 70
    ws.auto_filter.ref = f"A1:{get_column_letter(col)}{ws.max_row}"
    ab = wb["About"]
    ab.cell(7, 1).value = "Regenerate:"
    ab.cell(8, 1).value = "  1. python3 -m elkscout run --config configs/generated/co_68-681_elk_rifle.yaml --data data"
    ab.cell(9, 1).value = "  2. python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx"
    ab.cell(11, 1).value = ("Data sources: USGS 3DEP, NHD, NLCD, MTBS, BLM SMA, OSM/USFS MVUM, NRCS SNOTEL, Open-Meteo. "
                            "Verify land status and current Colorado Parks and Wildlife rules before hunting.")
    ab.cell(13, 1).value = ("Imagery column: what the photos show at each point, checked by eye on Esri World Imagery "
                            "satellite (Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community; capture "
                            "date in parentheses) and, for bed points, USDA NAIP color-infrared flown September 2019. "
                            "Nothing after those dates shows.")
    ab.cell(13, 1)._style = copy(ab.cell(11, 1)._style)
    wb.save(out / "waypoints.xlsx")
    print("waypoints.xlsx: Imagery column", get_column_letter(col))

    # guide snippets
    lines = Path(a.timber_table).read_text().strip().splitlines()
    new = [lines[0] + " imagery |", lines[1] + "---|"]
    for ln in lines[2:]:
        b = ln.split("|")[1].strip()
        new.append(ln + (f" **{BLOCKS[b]}** |" if b in DEAD else f" {BLOCKS[b]} |"))
    (snip / "timber_table_v3.md").write_text("\n".join(new) + "\n")

    rows = ["| bed | photos show | verdict | satellite | color-infrared |", "|---|---|---|---|---|"]
    for code, verdict, txt in BEDS:
        rows.append(f"| {code} | {txt} | {verdict} | {mp[code + '|esri']['date']} | {mp[code + '|naip-cir']['date']} |")
    (snip / "bed_table.md").write_text("\n".join(rows) + "\n")

    parts = []
    for srcname, label in (("esri", "Satellite"), ("naip-cir", "Color-infrared")):
        g = defaultdict(list)
        for k, v in mz.items():
            bid, s = k.split("|")
            if s == srcname:
                g[v["date"]].append(bid[:-1])
        parts.append(f"- **{label}:** " + " · ".join(f"{nice(d)}: {', '.join(sorted(v))}" for d, v in sorted(g.items())))
    (snip / "block_dates.md").write_text("**Capture dates of the block close-ups:**\n" + "\n".join(parts) + "\n")
    n_nov = sum(1 for k, v in mz.items() if k.endswith("|esri") and v["date"][5:7] == "11")
    (snip / "n_nov.txt").write_text(str(n_nov))
    (snip / "imagery_notes.json").write_text(json.dumps(pnotes, indent=1))
    alld = sorted({v["date"] for v in list(mp.values()) + list(mz.values()) if "naip" not in v["source"].lower()})
    (snip / "sat_range.txt").write_text(f"{nice(alld[0])} to {nice(alld[-1])}")
    print("snippets:", sorted(p.name for p in snip.iterdir()), "| November block captures:", n_nov, "| range:", alld[0], alld[-1])

    # PDF
    order = (sorted(img.glob("blocks_esri_*.png")) + sorted(img.glob("blocks_naip-cir_*.png")) +
             sorted(img.glob("zoom_pair_*.png")) + sorted(img.glob("points_esri_*.png")) +
             sorted(img.glob("points_naip-cir_*.png")))
    cnt = lambda pat: len(list(img.glob(pat)))  # noqa: E731
    W, H = 1600, 1200
    cover = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(cover)
    y = 70
    d.text((70, y), "GMU 68 + 681 — imagery check", font=font(46, True), fill=(20, 20, 20))
    y += 90
    body = [
        ("Every security timber block (T01–T21) and all 40 waypoints, checked by eye.", False),
        ("", False),
        ("Satellite, natural color: Esri World Imagery. Source: Esri, Vantor, Earthstar Geographics,", False),
        (f"and the GIS User Community. 0.31–0.5 m; captured {(snip / 'sat_range.txt').read_text()}, date printed on each image.", False),
        ("Color-infrared: USDA NAIP via USGS The National Map, flown Sept 9–22, 2019, 0.6 m.", False),
        ("In color-infrared, live conifer is dark red, aspen and willow bright pink-red, dead trees gray-green.", False),
        ("", False),
        ("Overlays: yellow = timber blocks, red = OpenStreetMap motorized routes. Waypoints:", False),
        ("BED magenta, FEED green, SADDLE cyan, GLASS white, WATER blue, ACCESS orange. North is up.", False),
        ("", False),
        (f"Pages: block overviews in natural color ({cnt('blocks_esri_*.png')}) and color-infrared ({cnt('blocks_naip-cir_*.png')});", False),
        (f"700 m close-ups of each block's core, satellite | color-infrared ({cnt('zoom_pair_*.png')});", False),
        (f"700 m squares around every waypoint ({cnt('points_esri_*.png')}); the bed points in color-infrared ({cnt('points_naip-cir_*.png')}).", False),
        ("", False),
        ("Findings: T09 and T10 are mostly dead timber. B3-01, B3-02 and B4-01 are poor bedding cover.", True),
        ("Every verdict is in guide.md section 5 and in each waypoint and block note.", False),
        ("", False),
        ("Nothing after the printed dates shows: beetle kill, blowdown, logging or fire since then won't be here.", False),
        ("This is not OnX or Google Earth imagery; theirs may be newer.", False),
    ]
    for ln, bold in body:
        d.text((70, y), ln, font=font(26, bold), fill=(40, 40, 40))
        y += 42
    assert y < H - 40, y
    pages = [cover]
    for p in order:
        im = Image.open(p).convert("RGB")
        if im.width > 1600:
            im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
        pages.append(im)
    pdf = out / "imagery_check.pdf"
    pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=150, quality=72)
    print(f"{pdf.name}: {len(pages)} pages, {pdf.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
