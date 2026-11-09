#!/usr/bin/env bash
# Offline rehearsal of the onx-scout skill's pipeline steps (profile -> run ->
# exports) on procedural fixture terrain. Everything it produces is DEMO DATA.
set -euo pipefail
cd "$(dirname "$0")/.."

WORK="${1:-$(mktemp -d)}"
echo "== onx-scout dry run =="
echo "workspace: $WORK   (DEMO DATA - procedural fixtures, not real terrain)"

mkdir -p "$WORK/manual"
python3 - "$WORK" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "src")
from elkscout.testkit import make_fixtures
make_fixtures(Path(sys.argv[1]) / "manual")
print("fixtures: ok")
PY

PROFILE="$WORK/profile.yaml"
python3 scripts/gen_profile.py --species elk --weapon rifle --style backpack \
    --state ID --unit 33 --start 2026-10-15 --end 2026-10-24 --days 5 \
    --out "$PROFILE"

python3 -m elkscout run --config "$PROFILE" --data "$WORK" --offline \
    --aoi-bbox=-115.72,44.10,-115.62,44.17

python3 scripts/export_xlsx.py --data "$WORK" --out "$WORK/out/waypoints.xlsx" \
    --demo-note "DEMO DATA: procedural fixture terrain - do not hunt these coordinates."

python3 - "$WORK" <<'PY'
import sys
from pathlib import Path

import geopandas as gpd
import gpxpy

work = Path(sys.argv[1])
out = work / "out"
required = [
    out / "elkscout_unit33_all.gpx",
    out / "elkscout_unit33.kml",
    out / "map.html",
    out / "briefing.md",
    out / "waypoints.xlsx",
    work / "work" / "waypoints.geojson",
]
for p in required:
    assert p.exists() and p.stat().st_size > 0, f"missing artifact: {p}"

gpx_path = out / "elkscout_unit33_all.gpx"
assert gpx_path.stat().st_size <= 4_000_000, "GPX exceeds the OnX 4 MB limit"
with open(gpx_path, encoding="utf-8") as fh:
    waypoints = gpxpy.parse(fh).waypoints
assert 0 < len(waypoints) <= 3000, f"GPX waypoint count {len(waypoints)} outside OnX limits"

wp = gpd.read_file(work / "work" / "waypoints.geojson")
assert len(set(wp["wp_type"])) >= 3, f"expected >=3 waypoint types, got {set(wp['wp_type'])}"
print(f"asserts: ok ({len(waypoints)} waypoints, {len(set(wp['wp_type']))} types)")
PY

echo "== DRY RUN OK - artifacts in $WORK/out (DEMO DATA) =="
