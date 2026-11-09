# Doctor-failure playbook: run it where the data is

`elkscout doctor` failing means this machine's network can't reach the public
GIS services (cloud sandboxes usually can't). Do NOT run the pipeline against
fixtures and present the output as scouting. Give the hunter this block,
filled in with their generated profile path, and stop.

## Local-run commands (paste, with the real profile path)

```bash
git clone https://github.com/mhagmaier/LMU_Capstone
cd LMU_Capstone
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,xlsx]"

python3 -m elkscout doctor --config <generated-profile>.yaml --data data
python3 -m elkscout run    --config <generated-profile>.yaml --data data
python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx
```

Outputs land in `data/out/`. Afterwards they can either read the guide
workflow themselves or zip `data/` (or just `data/cache/`) and bring it back
to a Claude session — with a primed cache the whole pipeline re-runs here with
`--offline`, and the guide can be written against real artifacts.

## Manual drop-ins (per-source fallback)

Every source checks `data/manual/` before the network; each `OfflineMissError`
names the exact file it wants. The full table:

| File under `data/manual/` | Content | Where to get it |
|---|---|---|
| `boundary.geojson` | Unit polygon, EPSG:4326 | State agency open-data/hunt-planner portal |
| `dem.tif` | Any-CRS GeoTIFF DEM covering the unit | USGS TNM download (3DEP 1/3″) |
| `osm_motorized.geojson` | Motorized ways (lines) | Overpass export (overpass-turbo.eu) |
| `osm_trails.geojson` | Non-motorized trails (lines) | Overpass export |
| `osm_trailheads.geojson` | Trailheads/parking (points) | Overpass export |
| `osm_springs.geojson` | Springs (points) | Overpass export |
| `mvum_roads.geojson` | USFS MVUM routes (lines) | FSGeodata Clearinghouse |
| `water_lines.geojson` | Perennial flowlines | USGS NHD via TNM download |
| `water_bodies.geojson` | Lakes/reservoirs (polygons) | USGS NHD |
| `huc12.geojson` | HUC12 watersheds (polygons) | USGS WBD |
| `ownership.geojson` | Ownership polygons (`public` bool or agency field) | BLM SMA |
| `burns.geojson` | Burn perimeters with `year`, `fire_name` | MTBS |
| `landcover.tif` | NLCD land cover (any CRS) | MRLC viewer bbox download |
| `canopy.tif` | NLCD tree canopy % (any CRS) | MRLC viewer |
| `snow.json` | SNOTEL summary (schema: `src/elkscout/sources/snotel.py`) | NRCS report generator |
| `weather.json` | Forecast summary (schema: `sources/weather.py`) | optional; climatology fallback is automatic |

Snow and weather degrade gracefully on their own (zero-snow + climatology
notes); everything else either needs the network, the cache, or its file.
