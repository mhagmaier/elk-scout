---
name: onx-scout
description: >
  Scout a western big-game hunt unit end to end and deliver OnX-importable
  waypoints plus a day-by-day hunt guide. Use this skill whenever the user asks
  to scout a unit or GMU, plan an elk or mule deer hunt, generate OnX waypoints,
  build a hunting map or e-scouting package, or asks where to hunt/camp/glass in
  a numbered game unit — even if they don't say "OnX" or "scout". It interviews
  the hunter (state/unit, species, weapon, dates, days, style, vehicle),
  generates a season-aware scoring profile, runs the elkscout GIS pipeline with
  security-timber analysis and near-live Sentinel-2 imagery, checks every point
  on recent aerial photos, verifies season dates, and writes the guide.
---

# OnX Scout

Turn a hunter's answers into scored, evidence-backed waypoints (GPX for OnX,
security-timber KML, interactive map, spreadsheet) and a day-by-day hunt
guide, using the `elkscout` pipeline in this repo.

## Hard rules (these override everything below)

- **Never scrape, automate, or log into OnX.** OnX has no public API and
  automation violates their ToS. The integration is files the hunter imports
  (OnX web map → My Content → Import; GPX/KML, 4 MB / 3,000 markups — the
  pipeline enforces both).
- **Never present fixture/demo/synthetic data as real scouting.** If a run used
  fixtures or `--aoi-bbox` test areas, label every artifact and message
  "DEMO DATA". A hunter will put boots on these coordinates.
- **Never assert legality.** Every statement about seasons, tags, land, or
  roads ends with a pointer to verify with the agency. The guide always carries
  the fair-chase and land-status disclaimers.
- **Don't hand-edit curve numbers.** Model math flows through
  `scripts/gen_profile.py`, `configs/adjustments.yaml`, and the state registry,
  so every number is reviewable and tested. User tweaks go through `--adjust`.
- **Say how old every picture is.** Sentinel-2 date, NAIP flight year,
  satellite capture dates — and tell the hunter to flip through OnX's own
  imagery before committing to a block, since it may be newer.

## Workflow

### 1. Interview the hunter (two AskUserQuestion rounds, max)

Round 1 — one call, four questions:
1. **Unit**: "Which state and unit/GMU?" Options: "Idaho — Unit 33 (shipped
   example)" / "Colorado — a GMU" / "Another state" (descriptions show the
   format: "e.g. 'Colorado 68 and 681' or 'Montana HD 270'"). Multiple units
   are fine; the boundary step dissolves them.
2. **Species**: Elk / Mule deer.
3. **Weapon**: Archery / Muzzleloader / Rifle — say what each changes ("Rifle:
   glassing-first model", "Archery: water + ambush model").
4. **Style**: Day hunts from roads or a base camp / Backpack 1+ mi / Horseback.

Round 2 — one call:
1. **Dates**: "You pick — typical <weapon> season" / "Opening week" / "I have
   exact dates". If "you pick", run the regs search (step 6) NOW and choose a
   real season window.
2. **Days**: hunting days excluding travel (default 5).
3. **Vehicle** (decides which Forest Service roads are legal access on the
   hunt dates): Truck/SUV (`high_clearance`) / Side-by-side over 50 in
   (`ohv_gt50`, e.g. a 64-in RZR) / ATV or side-by-side under 50 in
   (`atv` / `ohv_lt50`) / Passenger car (`passenger`).
4. **Limits & preferences** (multiSelect): daily travel under ~5 mi /
   vertical under ~2,000 ft per day / hunting with a partner (changes packout
   advice) / avoid crowds even if farther / other. Free text maps to
   `--adjust` flags or a style change.

### 2. Resolve the unit boundary and the state's rules

Check `configs/states.yaml`. A listed state brings its boundary service, its
**land-access rules** (which agencies are huntable — e.g. Colorado State Trust
Land is closed, Idaho endowment land is open), and its **elevation
calibration** (the templates are tuned on central Idaho; Colorado is +3,000 ft).
If the state isn't listed, follow `references/state-discovery.md` to register
all three. If the state has a walk-in / enrolled-trust program, put its
polygons in `data/manual/public_access.geojson` — those parcels count as open
(their own rules go in the guide).

### 3. Generate and confirm the model

```
python3 scripts/gen_profile.py \
  --species <elk|mule_deer> --weapon <archery|muzzleloader|rifle> \
  --style <day|backpack|horseback> --vehicle <high_clearance|ohv_gt50|...> \
  --state <CODE> --unit <N> --start YYYY-MM-DD --end YYYY-MM-DD --days <N> \
  --out configs/generated/<state>_<unit>_<species>_<weapon>.yaml
```

Show the hunter the `.summary.md` (weights, adjustments, state calibration,
land rules), then ONE confirmation question: "Run it" / "Adjust weights" (one
loop through `--adjust`, then re-show) / "Change dates". If the summary says
the state has no elevation calibration, check the band against published unit
elevation ranges before running. Rationale for any number:
`references/model-adjustments.md`.

### 4. Doctor gate, then run

```
python3 -m elkscout doctor --config <generated.yaml> --data data
```

If the GIS endpoints are unreachable (common in cloud sandboxes), paste the
local-run commands from `references/manual-fallbacks.md` and **stop** — do not
fall back to fixtures, do not fabricate conditions. Otherwise:

```
python3 -m elkscout run --config <generated.yaml> --data data
python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx
```

`run` now includes: legal road ends for the hunter's vehicle, security timber
blocks, and Sentinel-2 near-live imagery (observed snow line + timber that has
lost its greenness since the baseline year). Read `data/work/sentinel.json` —
if `available` is false, say so in the guide (the run used NLCD alone).

### 5. Photo check — look at the ground

```
python3 -m elkscout imagery --config <generated.yaml> --data data
```

This writes sheets to `data/out/imagery/` (every security block's extent and
core, every waypoint; BED points also in color-infrared) from the newest NAIP
flight and Esri satellite, plus `data/work/imagery_review.json`. **Open each
PNG sheet and look at it** (the Read tool shows images). In color-infrared,
live conifer is dark red, aspen/willow bright pink-red, dead timber gray-green.
For every block and waypoint, write a short verdict into the review file:
"dense live conifer", "mostly dead (gray crowns)", "poor bed: leafless aspen
edge, cover 250 m west", "open meadow against dense timber". Then:

```
python3 -m elkscout waypoints --config <generated.yaml> --data data   # only if any block is dead
python3 -m elkscout report    --config <generated.yaml> --data data
python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx
```

Verdicts land in every GPX/KML note, the timber KML, the map, and the
briefing; dead blocks stop counting toward hunt-area ranking. Plan the days
around the photo verdicts, not just the scores.

### 6. Verify regulations (web search)

Search `"<state> fish and game" <species> season unit <unit> <year>` plus the
agency's own brochure. Extract: season dates for the weapon, the hunt code's
valid units, orange/pink rules, OHV permits for nonresidents, CWD sampling,
and the rules of any public-access parcels in play. Cite every source. Flag
mismatches plainly. What you can't confirm goes in the guide's "still
unverified" list.

### 7. Write the Ultimate Guide

Follow `references/guide-template.md`; write `data/out/guide.md`. Conditions
come from artifacts (`snow.json`, `sentinel.json`, `weather.json`,
`timber.json`, `briefing.md`) — never invented. Every recommendation names
waypoints or timber blocks. The day plan follows the template's itinerary
rules — in pressured seasons the opener goes to the biggest **photo-confirmed
live** security timber, not simply the top-scoring area.

### 8. Deliver

Send the hunter (SendUserFile or equivalent): `guide.md`, `briefing.md`, the
all-waypoints GPX **and** per-area GPX files, the security-timber KML, the
Google Earth KML, `map.html`, `waypoints.xlsx`, and
`imagery/imagery_check.pdf`. Close with a 3-line summary + OnX import steps.

## Command crib

```bash
python3 scripts/gen_profile.py --species elk --weapon rifle --style day --vehicle ohv_gt50 \
    --state CO --unit 681 --start 2026-11-18 --end 2026-11-22 --days 5 \
    --out configs/generated/co_681_elk_rifle.yaml
python3 -m elkscout doctor  --config configs/generated/co_681_elk_rifle.yaml --data data
python3 -m elkscout run     --config configs/generated/co_681_elk_rifle.yaml --data data
python3 -m elkscout imagery --config configs/generated/co_681_elk_rifle.yaml --data data
#   ...fill data/work/imagery_review.json after looking at data/out/imagery/*.png...
python3 -m elkscout waypoints --config configs/generated/co_681_elk_rifle.yaml --data data
python3 -m elkscout report    --config configs/generated/co_681_elk_rifle.yaml --data data
python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx
python3 -m elkscout fetch --only snow,weather,sentinel --config <cfg> --data data   # 2-3 days before leaving
```

Dependencies: `pip install -e ".[dev,xlsx,imagery]"` from the repo root (Python ≥3.11).

## References (read when the step needs them)

- `references/model-adjustments.md` — why each season/style/weapon delta
  exists, the snow-line and timber logic, and which knob answers which
  hunter complaint.
- `references/state-discovery.md` — registering a new state: boundary
  service, land-access rules, elevation calibration, public-access programs.
- `references/guide-template.md` — the guide's structure, voice, itinerary
  rules, and packout math.
- `references/manual-fallbacks.md` — the doctor-failure playbook (local-run
  commands + manual drop-in table).
