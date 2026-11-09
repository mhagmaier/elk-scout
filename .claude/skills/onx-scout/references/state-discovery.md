# Finding, verifying, and registering a state's unit-boundary service

`configs/states.yaml` maps a state code to the ArcGIS feature service that
serves its game-unit polygons. The pipeline only needs this once per state —
generated profiles carry their own `boundary:` block. Idaho ships verified.
Everything here is best-effort discovery for the other states: never guess a
URL into the registry, and never mark anything `verified` you didn't actually
query.

## 1. Search

Try, in order (WebSearch):
- `"<state>" "game management unit" OR "hunt unit" OR "hunt district" boundaries ArcGIS REST MapServer`
- `<state> <agency name> hunt unit GIS open data` (agency names: "Fish and
  Game", "Fish, Wildlife & Parks", "Parks and Wildlife", "Game and Fish",
  "Department of Wildlife Resources" — varies by state)
- The state's ArcGIS Open Data hub (`data-<agency>.opendata.arcgis.com` or
  `hub.arcgis.com` search)

You are looking for a REST **feature/map service** URL ending in `/MapServer`
or `/FeatureServer`, not a web viewer page. Montana calls units "hunting
districts"; Wyoming "hunt areas"; Colorado/Nevada/Arizona "GMUs"; adjust
search terms and `unit_field_hints` accordingly.

## 2. Verify (all checks must pass before `status: verified`)

Run these as plain GETs (curl or WebFetch) and confirm:

1. `{service}?f=json` → valid JSON with a `layers` array.
2. For the candidate layer: `{service}/{id}?f=json` → `"geometryType":
   "esriGeometryPolygon"` and a plausible unit field among its `fields`
   (look for: UNIT, GMU, NAME, HUNT_UNIT, DISTRICT, UNIT_ID, HUNTUNIT, GMUNIT).
3. `{service}/{id}/query?where=1%3D1&returnCountOnly=true&f=json` → a sane
   statewide count (roughly 10–500 units).
4. The hunter's actual unit returns a feature:
   `{service}/{id}/query?where=<FIELD>%3D'<unit>'&returnCountOnly=true&f=json` → count ≥ 1.

## 3. Register

Append to `configs/states.yaml` (append a new mapping under `states:`, don't
rewrite the file — it carries comments):

```yaml
  MT:
    name: Montana
    agency: Montana Fish, Wildlife & Parks
    unit_system: "Hunting District (numbered, e.g. 270)"
    boundary:
      base_url: "<the verified /MapServer or /FeatureServer URL>"
      alt_urls: []
      layer: <verified layer id>
      layer_hint: "district"
      unit_field: "<exact field if check 4 used it, else null>"
      unit_field_hints: ["DISTRICT", "HUNT", "NAME"]
      unit_value_format: "{unit}"
    provenance:
      verified: "<today, if all 4 checks passed>"
      status: verified
      notes: "<which checks ran, count returned, date>"
```

If egress is blocked here (checks can't run), you may still register the entry
with `verified: null` and `status: provisional` — and tell the hunter plainly
that it must be confirmed from a networked machine before trusting it.
`scripts/gen_profile.py` surfaces provisional status in the model summary.

Run `python3 -m pytest tests/test_registry.py -q` after editing — the schema
test catches malformed entries.

## 4. When discovery fails

Some states don't publish a queryable service. The pipeline's manual fallback
takes any unit polygon:

1. Hunter exports the unit from the state's hunt-planner/open-data portal as
   **GeoJSON, EPSG:4326** (most portals: the unit's page → Download/Export).
2. Save it as `data/manual/boundary.geojson`.
3. Generate the profile with `--no-boundary`; the fetch stage picks the manual
   file up automatically (it checks `data/manual/` before any network).

## Worked example: the Idaho entry

Idaho's entry wraps the service elkscout has used since v1:
`gisportal-idfg.idaho.gov/hosting/rest/services/Hunting/MapServer`, layer 3
(GMU polygons), alternate host `gis.idfg.idaho.gov/server/...`, unit field
discovered at runtime from hints NAME/UNIT/GMU. It was verified during the
original unit-33 build (checks 1–4 all passed on 2026-08-28).
