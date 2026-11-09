# ElkScout — Terrain-Aware Elk Scouting for Idaho GMU 33

ElkScout is a Python pipeline that scores **Idaho Game Management Unit 33**
(Sawtooth Zone — Garden Valley / Lowman / Bear Valley / Deadwood country) for a
**mid-October rifle elk hunt** and produces exact, defensible waypoints:

- **GPX** files that import directly into **OnX Hunt** (web map: *My Content → Import*)
- **KML** for Google Earth
- an **interactive HTML map** (score heatmap, waypoints, roads, burns, ownership)
- a written **hunt briefing** that explains *why* every waypoint exists

Every waypoint carries its evidence, e.g.:

> `B2-03 N-bench 7410` — *"North-facing bench at 7,410 ft, 62% canopy, 24%
> slope; 1.8 mi from the nearest motorized route, 0.4 mi to a spring; edge of
> the 2016 Pioneer Fire burn."*

## Why there is no "OnX API"

OnX has no public API, and scraping it violates their Terms of Service. But
OnX's layers are built from **public data** — so ElkScout pulls the same public
sources directly, runs its own habitat model, and exports GPX *into* OnX.

## The elk model (mid-October rifle, pressured elk, backpack hunter)

A weighted sum of factor rasters on a 30 m grid (UTM 11N), each factor a
documented piecewise-linear suitability curve in
[`configs/unit33_oct_rifle.yaml`](configs/unit33_oct_rifle.yaml):

| Factor | Weight | What it encodes |
|---|---|---|
| **Security** | 0.25 | Distance from motorized routes. Rifle-season elk hold >0.8 km from wheels; the backpack sweet spot is 1.2–4 km, with a mild penalty past 6 km (packout reality). |
| **Bedding** | 0.20 | N/NE aspects × canopy >60% × 15–35% slope benches (TPI-detected) × upper-third slope position — dark-timber bedding. |
| **Feed** | 0.20 | Meadows/shrubfields, **3–15-year-old burns** (the 2016 Pioneer Fire is the big signal in this unit), riparian meadows; timber–feed *edges* score highest. |
| **Elevation** | 0.15 | Optimum ~6,000–8,200 ft, **shifted down by live SNOTEL snow depth** at run time. |
| **Water** | 0.10 | Within ~500 m of perennial streams/springs (mid-October is dry). |
| **Pressure** | 0.10 | Distance from trailheads as a hunter-density proxy. |

Hard masks: inside the unit, public land, slope <60%, not open water.

Waypoints are typed — **BED, FEED, WATER, SADDLE** (DEM-detected travel
notches), **GLASS** (viewshed-scored vantage points), **CAMP, ACCESS** — spaced
by non-max suppression, and clustered into named drainage-level **hunt areas**,
each with a morning/evening plan in the briefing.

## Quickstart

```bash
python -m pip install -e .
elkscout doctor                       # check which data endpoints you can reach
elkscout run --config configs/unit33_oct_rifle.yaml
# outputs land in data/out/:
#   elkscout_unit33_all.gpx  + one GPX per hunt area
#   elkscout_unit33.kml, map.html, briefing.md
```

Want the points as a spreadsheet too? (`pip install -e .[xlsx]` for openpyxl)

```bash
python scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx
```

## The `onx-scout` skill (use Claude as your scouting partner)

This repo ships a Claude Code project skill at `.claude/skills/onx-scout/`.
In a Claude Code session in this repo, say **"scout unit 33 for me"** (or
`/onx-scout`): Claude interviews you (state/unit, species — elk or mule deer,
weapon, dates, days, hunt style), generates a season-aware scoring profile
from the templates in `configs/templates/` + the adjustment matrix in
`configs/adjustments.yaml` (via `scripts/gen_profile.py` — deterministic and
tested, never hand-tuned), runs the pipeline, verifies current season dates by
web search, and writes a day-by-day hunt guide on top of the briefing. For
states beyond Idaho it discovers and registers the state's unit-boundary
service in `configs/states.yaml` (or walks you through the manual boundary
drop-in). Rehearse the whole flow offline with `bash scripts/skill_dryrun.sh`.

Stages can run individually (each stage persists its artifacts under `data/`):

```bash
elkscout fetch     --config configs/unit33_oct_rifle.yaml   # network happens ONLY here
elkscout score     --config configs/unit33_oct_rifle.yaml   # terrain + factors + suitability
elkscout waypoints --config configs/unit33_oct_rifle.yaml
elkscout report    --config configs/unit33_oct_rifle.yaml
```

All fetches are disk-cached under `data/cache/`; after one successful `fetch`,
everything re-runs with `--offline`. On a machine that can't reach the
endpoints (locked-down networks), run `fetch` elsewhere and copy `data/cache/`
over — or drop files into `data/manual/` (below).

## Importing into OnX

1. Open the OnX **web map** (webmap.onxmaps.com) — imports need a paid membership.
2. *My Content → Import → Select from computer* → choose a `.gpx` from `data/out/`.
3. Import the per-area GPX files if you want to load areas selectively
   (OnX limits: 4 MB / 3,000 markups per file — ElkScout enforces both).
4. Waypoint notes carry the evidence sentence; names are prefixed by type and
   hunt area (`B2-03` = BED, area 2, #3).

## Data sources

| Layer | Source |
|---|---|
| GMU boundary | Idaho Fish & Game ArcGIS (`gisportal-idfg.idaho.gov`, Hunting MapServer) |
| Elevation | USGS 3DEP (`elevation.nationalmap.gov` ImageServer) |
| Roads & trails | OpenStreetMap (Overpass) ∪ USFS MVUM (`apps.fs.usda.gov` EDW) |
| Hydrography | USGS NHDPlus HR + WBD HUC12 (`hydro.nationalmap.gov`) |
| Land ownership | BLM Surface Management Agency (`gis.blm.gov`) |
| Burn perimeters | MTBS (`apps.fs.usda.gov` EDW, all-years layer) |
| Landcover & canopy | NLCD via MRLC GeoServer WCS (`mrlc.gov`) |
| Snow | NRCS SNOTEL, AWDB REST (`wcc.sc.egov.usda.gov`) |
| Forecast | Open-Meteo (no key) |

## Manual data drop-ins

If an endpoint is unreachable, place a file in `data/manual/` and the pipeline
uses it instead of the network:

| File | Content |
|---|---|
| `boundary.geojson` | Unit polygon (EPSG:4326). Export from the [IDFG open-data portal](https://data-idfggis.opendata.arcgis.com/) "Game Management Units" dataset. |
| `dem.tif` | Any-CRS GeoTIFF DEM covering the unit (e.g. TNM 1/3″ staged product); resampled automatically. |
| `osm_motorized.geojson`, `osm_trails.geojson`, `osm_trailheads.geojson`, `osm_springs.geojson` | OSM extracts (lines / lines / points / points). |
| `mvum_roads.geojson` | USFS MVUM roads (lines). |
| `water_lines.geojson`, `water_bodies.geojson`, `huc12.geojson` | NHD flowlines, waterbodies, HUC12 polygons. |
| `ownership.geojson` | Ownership polygons; a `public` boolean or agency field. |
| `burns.geojson` | Burn perimeters with `year` and `fire_name`. |
| `landcover.tif`, `canopy.tif` | NLCD land cover / tree canopy GeoTIFFs (any CRS). |
| `snow.json`, `weather.json` | See `src/elkscout/sources/snotel.py` / `weather.py` docstrings for schema. |

## Testing

```bash
python -m pytest            # unit tests + an offline end-to-end smoke run
```

The smoke test procedurally generates a realistic mountain fixture AOI
(`elkscout.testkit`) and runs the entire pipeline offline, so CI never needs
network access.

### Eyeball checklist after a real Unit 33 run

Open `data/out/map.html` and verify against known ground truth:
- The 2016 Pioneer Fire perimeter covers much of the southern/eastern unit.
- Deadwood Reservoir and Scott Mountain sit where they should.
- Security scores collapse along the Middle Fork Payette and Scott Mountain
  road corridors.
- Waypoints avoid the private ground around Garden Valley.

## Fair-chase & legal disclaimer

ElkScout is a scouting aid, not a substitute for scouting, and certainly not
for judgment. **Verify current IDFG season dates, zone rules, and tag validity**
(the Sawtooth Zone B-tag structure changes) and **verify land ownership on the
ground** — the ownership layer defaults unmapped slivers to public, and fences
don't read GeoJSON. Weather, snow, wolves, and other hunters move elk; run the
pipeline again the week of your hunt with fresh SNOTEL/forecast data.
