# GMU 68 + 681 bull elk, rifle — Nov 18–22, 2026

> **Note (Nov 2026):** the helper scripts in this folder have since been folded
> into the pipeline — state land rules (`configs/states.yaml`), the SNOTEL fix
> and snow-line model, the NLCD picker fix, legal OHV access points
> (`--vehicle ohv_gt50`), security timber (`elkscout` score stage), Sentinel-2
> imagery, and the photo check (`elkscout imagery`). This folder stays as the
> record of the revision-3 package as delivered.

E-scouting package for Colorado GMUs 68 and 681 (fourth rifle season), built with the elkscout pipeline in this repo plus the helper scripts in this folder. This is revision 3: bedding in north-facing dark timber, mapped security timber blocks, and an imagery check of every block and waypoint.

**Start here: [out/guide.md](out/guide.md).** It covers conditions, the regulations check, the model, timber cover, the imagery check, hunt areas, a day-by-day plan, the waypoint index and OnX import steps.

These are modeled scouting points, not elk sightings. Verify season dates, your hunt code, land status and road rules with CPW and the land agencies before hunting.

## What's here

| folder | contents |
|---|---|
| [`out/`](out/) | The delivered package: the guide, OnX GPX files (all 40 points plus one file per hunt area), the security-timber KML, the Google Earth KML, `imagery_check.pdf`, `waypoints.xlsx`, `map.html`, the pipeline briefing, and the model's QA maps in `out/qa/` |
| [`scripts/`](scripts/) | Helper scripts for the steps the pipeline couldn't do on its own here. Run them from the repo root; each docstring has its usage |
| [`templates/`](templates/) | The guide template that `fill_guide.py` fills |
| [`inputs/`](inputs/) | The manual data drop-ins this run used (`data/manual/`), plus the two source files behind them |
| [`work/`](work/) | Small intermediates: waypoints, hunt areas, weather, snow, MVUM roads, water, timber stats, QA context, guide snippets and imagery capture dates |

Not included:
- The model's rasters (`data/work/*.tif`, about 400 MB). Two are over GitHub's 100 MB file limit, and `elkscout run` rebuilds them from `inputs/`.
- The individual imagery chips and sheets. Every sheet is in `out/imagery_check.pdf`.
- Revisions 1 and 2, which revision 3 replaces.

## Scripts

| script | what it does |
|---|---|
| `make_dropins.py` | NLCD 2021 land cover and tree canopy (the pipeline's automatic pick chose the wrong layers), and OpenStreetMap layers through an Overpass mirror (the main servers refused connections) |
| `make_snow.py` | SNOTEL snow depth from Colorado stations (the pipeline's query returned stations nationwide) |
| `make_access.py` | ACCESS candidates: ends of Forest Service routes open to OHVs over 50 in on every hunt day, plus public trailheads |
| `qa_context.py` | Per-point land status and packout distances; per-area drain direction and nearby MVUM routes |
| `timber_cover.py` | Dark-timber stats, the 21 security timber blocks and the timber KML |
| `imagery_sheets.py` | Satellite (Esri World Imagery) and NAIP color-infrared photo sheets of the blocks and waypoints |
| `apply_imagery.py` | Writes the imagery verdicts into the GPX, KML, spreadsheet, map and briefing; builds the guide snippets and `imagery_check.pdf` |
| `fill_guide.py` | Fills the guide template from the run's data |

A few files came from one-off commands rather than these scripts, and are included as built:
- `inputs/ownership.geojson`: the BLM surface-management layer (BLM, Forest Service and Bureau of Reclamation land open; State Trust and local-government land closed), with CPW public-access properties (`inputs/cpw_public_access.geojson`) open.
- `inputs/osm_trailheads_public.geojson`: OpenStreetMap trailheads on public land, the input to `make_access.py`.
- `work/timber_table.md`, `work/dark_acres.txt` and `work/n_blocks.txt`: built from `work/timber_v2.json` and the MVUM roads.

The imagery verdicts in `apply_imagery.py` were written by eye from the sheets this run produced. A re-run that moves the points needs a fresh look at the new sheets; the script stops if the waypoint names don't match.

## Re-running

From the repo root:

```bash
H=hunts/co_68-681_elk_rifle_2026
CFG=configs/generated/co_68-681_elk_rifle.yaml
mkdir -p data/manual && cp $H/inputs/* data/manual/   # this run's drop-ins

# Optional: refresh the drop-ins instead of reusing them
python3 $H/scripts/make_dropins.py landcover --data data
python3 $H/scripts/make_dropins.py osm --data data --overpass <Overpass mirror URL>
python3 $H/scripts/make_snow.py --config $CFG --data data
python3 $H/scripts/make_access.py --data data --start 2026-11-18 --end 2026-11-22 \
  --trailheads $H/inputs/osm_trailheads_public.geojson

# Model, waypoints, GPX/KML/map/briefing, spreadsheet
python3 -m elkscout run --config $CFG --data data
python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx

# Timber blocks and QA context
python3 $H/scripts/timber_cover.py --data data --out $H/work/timber_v2.json \
  --kml data/out/elkscout_unit68-681_timber_blocks.kml --dark-canopy 45
python3 $H/scripts/qa_context.py --data data --out $H/work/qa_context.json

# Imagery sheets (data/ is git-ignored, so they stay out of the repo)
IMG=data/imagery; KML=data/out/elkscout_unit68-681_timber_blocks.kml
python3 $H/scripts/imagery_sheets.py blocks --data data --kml $KML --out $IMG --source esri
python3 $H/scripts/imagery_sheets.py blocks --data data --kml $KML --out $IMG --source naip-cir
python3 $H/scripts/imagery_sheets.py zoom   --data data --kml $KML --out $IMG
python3 $H/scripts/imagery_sheets.py points --data data --kml $KML --out $IMG --source esri
python3 $H/scripts/imagery_sheets.py points --data data --kml $KML --out $IMG --source naip-cir \
  --names B1-01,B2-01,B2-02,B3-01,B3-02,B3-03,B4-01,B4-02

# Imagery verdicts into the outputs, then the guide
python3 $H/scripts/apply_imagery.py --out data/out --imagery $IMG --data data \
  --timber-table $H/work/timber_table.md --snippets $H/work/snippets
N=$H/work/snippets
python3 $H/scripts/fill_guide.py --data data --config $CFG \
  --template $H/templates/guide_template_v3.md --out data/out/guide.md \
  --extra TIMBER_TABLE=$N/timber_table_v3.md --extra DARK_ACRES=$H/work/dark_acres.txt \
  --extra N_BLOCKS=$H/work/n_blocks.txt --extra BED_TABLE=$N/bed_table.md \
  --extra BLOCK_DATES=$N/block_dates.md --extra N_NOV=$N/n_nov.txt \
  --extra SAT_RANGE=$N/sat_range.txt --imagery-notes $N/imagery_notes.json
```

Imagery credit: Esri World Imagery (Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community); USDA NAIP via USGS The National Map.
