# GMU 68 + 681 bull elk, rifle — Nov 18–22, 2026 (revision 4)

E-scouting package for Colorado GMUs 68 and 681 (fourth rifle season), rebuilt on the updated elkscout pipeline. Every step that revision 3 needed helper scripts for now runs in the pipeline: Colorado's land rules and elevation calibration (`configs/states.yaml`), road ends legal for a 64-in RZR (`--vehicle ohv_gt50`), security timber blocks, the Sentinel-2 snow line and timber mortality, and the photo check (`elkscout imagery`). Revision 3 stays in [`../co_68-681_elk_rifle_2026/`](../co_68-681_elk_rifle_2026/).

**Start here: [out/guide.md](out/guide.md).** It covers conditions, the regulations check, the model, security timber, the photo check, hunt areas, wind, a day-by-day plan, the waypoint index and OnX import steps.

These are modeled scouting points, not elk sightings. Verify season dates, your hunt code, land status and road rules with CPW and the land agencies before hunting.

## What changed from revision 3

- **Snow line:** observed by Sentinel-2 at about 10,800 ft on Nov 6, 2026, instead of estimated from SNOTEL. It sits above the elk band (which tops out at 10,400 ft), so bedding stays in north-facing dark timber.
- **Security timber:** 28 blocks (10,468 ac) from the pipeline's timber stage. The photo check found 22 live, T23 mixed, and 5 mostly dead (T08, T09, T15, T21, T25; 1,064 ac), which leaves 9,404 ac of live or partly live timber. Dead blocks no longer count toward the hunt-area ranking.
- **Access:** the 120 Forest Service road ends open to OHVs over 50 in on every hunt day, with the distance and climb from each waypoint to its nearest one.
- **Photo check:** a verdict for every block and waypoint, from the pipeline's Esri and NAIP sheets, Google Earth Web, and OnX Recent Imagery (viewed only, nothing imported or exported, with the hunter's approval).
- **Hunting with a partner:** the packout math is 2–3 loads each.
- **Wind:** each day's approach notes are checked against that day's forecast wind and the slope direction at each target (`scripts/day_plan_geometry.py`).

## Pipeline fixes made during this run

Each fix has a test in `tests/`.

- **Sentinel-2 reflectance** (`src/elkscout/sources/sentinel.py`): Earth Search's L2A files are already harmonized, so applying the catalog's offset again pushed dark-forest bands negative. NDVI landed outside [-1, 1], and dark conifer read as snow and as dead timber.
- **Duplicate MVUM routes** (`src/elkscout/sources/mvum.py`): routes published in two layers were counted twice, which left zero legal road ends. `dedupe_routes` drops the copies.
- **Feed-point wording** (`src/elkscout/evidence.py`): notes read "Feed on a East-facing slope".

## Gaps worked around, not fixed

- **Multi-unit boundary:** the boundary query for "68-681" fails (HTTP 400), so the run used CPW's boundary of the two units (`inputs/boundary.geojson`).
- **Map projection:** `gen_profile.py` defaults to EPSG 32611 (Idaho); the run passed `--adjust grid.epsg=32613`.
- **Weather:** `weather.py`'s climatology note is written for Idaho. Open-Meteo stalled through this sandbox's proxy, so the forecast was downloaded separately (`inputs/weather.json`).
- **Overpass:** the main and kumi servers hung from the sandbox, so the run put the VK Maps mirror first.
- **Photo sheets:** `elkscout imagery` stops at 25 blocks. T26–T28 got supplement sheets from `scripts/imagery_sheets.py`, along with a natural-color check of F1-02 and F4-01, appended as the last three pages of `out/imagery_check.pdf`.

## What's here

| folder | contents |
|---|---|
| [`out/`](out/) | The delivered package: the guide, OnX GPX files (all 40 points plus one file per hunt area), the security-timber KML, the Google Earth KML, `imagery_check.pdf` (35 pages), `waypoints.xlsx`, `map.html`, the pipeline briefing, and the model's QA maps in `out/qa/` |
| [`inputs/`](inputs/) | What this run took in by hand: the `data/manual/` drop-ins (CPW's boundary of the two units, CPW public-access parcels, the Open-Meteo forecast) and `photo_verdicts.json`, the photo verdicts written by eye |
| [`work/`](work/) | Small intermediates: waypoints, hunt areas, timber blocks and stats, the Sentinel-2 and snow summaries, the photo review as delivered, legal road ends, MVUM roads, the profile grid, and `guide_context.json` |
| [`scripts/`](scripts/) | Helper scripts for the steps the pipeline doesn't do yet. Run them from the repo root; each docstring has its usage |
| [`templates/`](templates/) | The guide template and the regulations table that `fill_guide.py` fills in |

The profile is `configs/generated/co_68-681_elk_rifle_rev4.yaml`, with its summary beside it.

Not included:
- The rasters and the larger fetched layers (ownership, OpenStreetMap, water, trails). `elkscout run` rebuilds them.
- The individual photo sheets. Every sheet is in `out/imagery_check.pdf`.

## Scripts

| script | what it does |
|---|---|
| `fill_review.py` | Writes `inputs/photo_verdicts.json` into `data/work/imagery_review.json`, matching blocks by id and waypoints by code |
| `guide_context.py` | Per waypoint: land, nearest legal road end with distance and climb, nearest legal route. Per hunt area: drain direction. Per block: nearest legal route and the waypoints within 1 mi |
| `fill_guide.py` | Fills the guide template from the run's artifacts and `work/guide_context.json` |
| `day_plan_geometry.py` | Each day's targets against that day's forecast wind, plus the bearings, distances, climbs and road positions the approach notes quote |
| `ge_checklist.py` | Every block and waypoint with coordinates, in order, for the Google Earth pass |
| `imagery_sheets.py` | Revision 3's photo-sheet script, reading the pipeline's motorized routes. It made the supplement sheets |
| `verify_package.py` | Checks the package: OnX limits, a verdict and date in every note, every waypoint and block the guide names exists, the spreadsheet and PDF open |

The photo verdicts were written by eye from this run's sheets, and `fill_review.py` matches waypoints by code. A re-run that moves the points needs a fresh look at the new sheets before the verdicts are reused. `work/imagery_review.json` is the review as delivered, including the capture dates for T26–T28 from the supplement sheets.

## Re-running

From the repo root:

```bash
H=hunts/co_68-681_elk_rifle_2026_rev4
CFG=configs/generated/co_68-681_elk_rifle_rev4.yaml
mkdir -p data/manual
cp $H/inputs/boundary.geojson $H/inputs/public_access.geojson $H/inputs/weather.json data/manual/

# The profile is committed; this is the command that made it
python3 scripts/gen_profile.py --species elk --weapon rifle --style day --vehicle ohv_gt50 \
  --state CO --unit 68-681 --start 2026-11-18 --end 2026-11-22 --days 5 \
  --adjust grid.epsg=32613 \
  --adjust 'waypoints.counts={BED: 8, FEED: 11, WATER: 2, SADDLE: 6, GLASS: 7, CAMP: 0, ACCESS: 6}' \
  --adjust hunt_areas.min_waypoints=4 --adjust hunt_areas.max_areas=10 \
  --adjust factors.pressure.weight=0.2 --out $CFG

# Model, waypoints, road ends, timber, Sentinel-2
python3 -m elkscout run --config $CFG --data data
# If the Overpass servers hang, put a mirror first (what this run did):
#   python3 -c "import sys, elkscout.endpoints as e; e.OVERPASS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter'] + [u for u in e.OVERPASS if 'mail.ru' not in u]; from elkscout.cli import main; sys.exit(main(['run', '--config', '$CFG', '--data', 'data']))"

# Photo check, then the outputs with the verdicts in them
python3 -m elkscout imagery --config $CFG --data data
python3 $H/scripts/fill_review.py --data data --verdicts $H/inputs/photo_verdicts.json
python3 -m elkscout waypoints --config $CFG --data data
python3 -m elkscout report --config $CFG --data data
python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx

# Guide
python3 $H/scripts/guide_context.py --data data --config $CFG --out $H/work/guide_context.json
python3 $H/scripts/fill_guide.py --data data --config $CFG --context $H/work/guide_context.json \
  --template $H/templates/guide_template.md --out data/out/guide.md \
  --extra REGS_TABLE=$H/templates/regs_table.md
python3 $H/scripts/day_plan_geometry.py --data data --config $CFG --context $H/work/guide_context.json
python3 $H/scripts/verify_package.py $H/work/guide_context.json
```

Two to three days before leaving, refresh the conditions and rebuild:

```bash
python3 -m elkscout fetch --only snow,weather,sentinel --config $CFG --data data
python3 -m elkscout score --config $CFG --data data
python3 -m elkscout waypoints --config $CFG --data data
python3 -m elkscout report --config $CFG --data data
```

The guide's conditions, forecast and wind notes come from the files these commands rewrite, so re-read the day plan after a refresh.
