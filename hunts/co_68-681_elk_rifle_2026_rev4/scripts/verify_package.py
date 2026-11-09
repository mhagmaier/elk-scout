"""Check the delivered package before it goes out (read-only on data/out and data/work).

OnX import limits and markup counts for every GPX/KML, a photo verdict and date in every
point note, every waypoint code and timber block the guide names exists, no unfilled
placeholders, consistent table shapes, the bed-distance summary matches the data, and the
spreadsheet and photo-check PDF open. Prints PASS/FAIL per check.

Usage (repo root): python3 verify_package.py work/guide_context.json
"""

import json, re, sys, xml.etree.ElementTree as ET
from pathlib import Path
import geopandas as gpd
out, w = Path("data/out"), Path("data/work")
ok = True
def check(cond, msg):
    global ok
    print(("PASS " if cond else "FAIL ") + msg); ok &= bool(cond)
wp = gpd.read_file(w / "waypoints.geojson"); bl = gpd.read_file(w / "timber_blocks.geojson")
codes = {n.split()[0] for n in wp["name"]}; blocks = set(bl["id"])
# GPX / KML: well-formed, OnX limits, counts, verdicts in notes
for f in sorted(out.glob("*.gpx")) + sorted(out.glob("*.kml")):
    root = ET.parse(f).getroot()
    tag = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    marks = root.findall(f".//{tag}wpt") if f.suffix == ".gpx" else root.findall(f".//{tag}Placemark")
    size = f.stat().st_size
    check(size < 4_000_000 and len(marks) < 3000, f"{f.name}: {len(marks)} markups, {size/1e3:.0f} KB (OnX limits 4 MB / 3,000)")
    if f.suffix == ".gpx":
        descs = [(m.findtext(f"{tag}name"), m.findtext(f"{tag}desc") or "") for m in marks]
        check(all("Photos (" in d for _, d in descs), f"{f.name}: every point note carries its photo verdict and date")
        check(all(len(n) <= 32 for n, _ in descs), f"{f.name}: names fit 32 chars")
gpx_all = ET.parse(out / "elkscout_unit68-681_all.gpx").getroot()
ns = gpx_all.tag.split("}")[0] + "}"
check(len(gpx_all.findall(f".//{ns}wpt")) == len(wp) == 40, "all-points GPX has all 40 waypoints")
area_total = sum(len(ET.parse(f).getroot().findall(f".//{ns}wpt")) for f in out.glob("*_*-*.gpx") if not f.name.endswith("_all.gpx"))
per_area = [f for f in out.glob("elkscout_unit68-681_*.gpx") if not f.name.endswith("_all.gpx")]
check(sum(len(ET.parse(f).getroot().findall(f".//{ns}wpt")) for f in per_area) == 40 and len(per_area) == 5, "5 per-area GPX files hold the 40 points between them")
tk = ET.parse(out / "elkscout_unit68-681_timber_blocks.kml").getroot(); kns = tk.tag.split("}")[0] + "}"
pm = tk.findall(f".//{kns}Placemark")
check(len(pm) == 28, f"timber KML has 28 blocks ({len(pm)})")
rev = json.loads((w / "imagery_review.json").read_text())
check(all(rev["blocks"].get(b, {}).get("verdict") for b in blocks), "every block has a photo verdict")
check(all(v.get("verdict") for v in rev["waypoints"].values()) and len(rev["waypoints"]) >= 40, "every waypoint has a photo verdict")
# guide references
g = (out / "guide.md").read_text()
check("{{" not in g and "}}" not in g, "guide has no unfilled placeholders")
used_codes = set(re.findall(r"\b([ABFGSW]\d-\d{2})\b", g)); used_blocks = set(re.findall(r"\b(T\d{2})\b", g))
check(used_codes <= codes, f"every waypoint named in the guide exists ({sorted(used_codes - codes) or 'none missing'})")
check(used_blocks <= blocks, f"every block named in the guide exists ({sorted(used_blocks - blocks) or 'none missing'})")
check(not re.search(r"\ba [aeiou]\w*-facing|on a [A-Z]", g), "no 'a east-facing' / capitalized aspect mid-sentence")
check(not re.search(r"\b(this week|yesterday|last week|recently)\b", g, re.I), "no relative-time words")
for line in g.splitlines():
    if line.startswith("|") and not set(line) <= set("|-: "):
        pass
rows = [l for l in g.splitlines() if l.startswith("|")]
# table shape: consecutive table rows share a column count
blocks_of_rows, cur = [], []
for l in g.splitlines():
    if l.startswith("|"): cur.append(l.count("|"))
    elif cur: blocks_of_rows.append(cur); cur = []
check(all(len(set(b)) == 1 for b in blocks_of_rows), f"all {len(blocks_of_rows)} guide tables have consistent column counts")
# bed numbers quoted in the day plan
ctx = json.loads(Path(sys.argv[1]).read_text())
beds = {k: v for k, v in ctx["waypoints"].items() if k.startswith("B")}
rmin, rmax = min(v["route_mi"] for v in beds.values()), max(v["route_mi"] for v in beds.values())
emin, emax = min(v["end_mi"] for v in beds.values()), max(v["end_mi"] for v in beds.values())
claim = f"Every bed is {rmin}–{rmax} mi from a road legal for your RZR, and {emin}–{emax} mi from a road end. That's about {round(2*2*emin)}–{round(3*2*emax)} round-trip miles apiece"
check(claim in g, f"bed distance summary matches the data: {claim[:90]}...")
# xlsx
import openpyxl
wb = openpyxl.load_workbook(out / "waypoints.xlsx", read_only=True)
ws = wb[wb.sheetnames[0]]
n = sum(1 for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0])
check(n == 40, f"waypoints.xlsx opens; first sheet '{wb.sheetnames[0]}' has {n} rows; sheets {wb.sheetnames}")
from pypdf import PdfReader
pages = len(PdfReader(str(out / "imagery" / "imagery_check.pdf")).pages)
check(pages == 35, f"imagery_check.pdf opens: {pages} pages")
b = (out / "briefing.md").read_text()
check("DEMO" not in b and "DEMO" not in g and "fixture" not in g.lower(), "no demo/fixture labels (real run)")
print("ALL PASS" if ok else "SOME CHECKS FAILED")
