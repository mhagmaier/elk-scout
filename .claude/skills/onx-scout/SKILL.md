---
name: onx-scout
description: >
  Scout a western big-game hunt unit end to end and deliver OnX-importable
  waypoints plus a day-by-day hunt guide. Use this skill whenever the user asks
  to scout a unit or GMU, plan an elk or mule deer hunt, generate OnX waypoints,
  build a hunting map or e-scouting package, or asks where to hunt/camp/glass in
  a numbered game unit — even if they don't say "OnX" or "scout". It interviews
  the hunter (state/unit, species, weapon, dates, days, style), generates a
  season-aware scoring profile, runs the elkscout GIS pipeline, verifies season
  dates, and writes the guide.
---

# OnX Scout

Turn a hunter's answers into scored, evidence-backed waypoints (GPX for OnX,
KML, interactive map, spreadsheet) and a day-by-day hunt guide, using the
`elkscout` pipeline in this repo.

## Hard rules (these override everything below)

- **Never scrape, automate, or log into OnX.** OnX has no public API and
  automation violates their ToS. The integration is a GPX file the hunter
  imports manually (OnX web map → My Content → Import; limits 4 MB / 3,000
  markups — the pipeline enforces both).
- **Never present fixture/demo/synthetic data as real scouting.** If a run used
  fixtures or `--aoi-bbox` test areas, label every artifact and message
  "DEMO DATA". A hunter will put boots on these coordinates.
- **Never assert legality.** Every statement about seasons, tags, or access
  ends with a pointer to verify with the state agency. The guide always carries
  the fair-chase and land-status disclaimers (ownership layers have gaps;
  fences don't read GeoJSON).
- **Don't hand-edit curve numbers.** All model math flows through
  `scripts/gen_profile.py` and `configs/adjustments.yaml`, so every number is
  reviewable and tested.

## Workflow

### 1. Interview the hunter (two AskUserQuestion rounds, max)

Round 1 — one call, four questions:
1. **Unit**: "Which state and unit/GMU?" Options: "Idaho — Unit 33 (shipped
   example)" / "Idaho — another unit" / "Another state" (descriptions show the
   expected format: "e.g. 'Colorado unit 61' or 'Montana HD 270'").
2. **Species**: Elk / Mule deer.
3. **Weapon**: Archery / Muzzleloader / Rifle — note in each description what
   it changes ("Rifle: glassing-first model", "Archery: water + ambush model").
4. **Style**: Day hunts from roads / Backpack 1+ mi / Horseback.

Round 2 — one call:
1. **Dates**: "You pick — typical <weapon> season" / "Opening week" / "I have
   exact dates". If "you pick", run the regs search (step 5) NOW and choose a
   real season window; defaults if search is unavailable: elk rifle mid-Oct,
   elk archery Sep 10–20, deer rifle third week of Oct, deer archery Sep 1–10.
2. **Days**: hunting days excluding travel (default 5).
3. **Limits** (multiSelect): none / daily travel under ~5 mi / vertical under
   ~2,000 ft/day / other. Free text maps to `--adjust` flags or a style change
   (e.g. "bad knees" → day-style security curve even with a camp).
4. **Camp preference** (backpack/horseback) or **Access preference** (day).

### 2. Resolve the unit boundary

Check `configs/states.yaml`. If the state is listed → proceed. If not → follow
`references/state-discovery.md` to find, verify, and register the state's GMU
boundary service (or set up the manual `data/manual/boundary.geojson` fallback
it describes). Never invent a service URL — only registered-and-verified or
manual.

### 3. Generate and confirm the model

```
python3 scripts/gen_profile.py \
  --species <elk|mule_deer> --weapon <archery|muzzleloader|rifle> \
  --style <day|backpack|horseback> --state <CODE> --unit <N> \
  --start YYYY-MM-DD --end YYYY-MM-DD --days <N> \
  --out configs/generated/<state>_<unit>_<species>_<weapon>.yaml
```

Show the hunter the generated `.summary.md` (weights table + adjustments),
then ONE confirmation question: "Run it" / "Adjust weights" (one loop through
`--adjust`, then re-show) / "Change dates". If they question a number, the
rationale lives in `references/model-adjustments.md`.

### 4. Doctor gate, then run

```
python3 -m elkscout doctor --config <generated.yaml> --data data
```

If the GIS endpoints are unreachable (common in cloud sandboxes), paste the
local-run commands and manual drop-in table from
`references/manual-fallbacks.md` and **stop** — do not fall back to fixtures,
do not fabricate conditions. Otherwise:

```
python3 -m elkscout run --config <generated.yaml> --data data
python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx
```

### 5. Verify regulations (web search)

Search `"<state> fish and game" <species> season unit <unit> <year>` plus the
agency's own site. Extract: season dates for the weapon, tag/draw type, and
unit-specific rules. Cite every source. Flag mismatches with the hunter's
dates plainly ("your dates start 3 days before the opener per IDFG — verify").

### 6. Write the Ultimate Guide

Follow `references/guide-template.md` exactly; write `data/out/guide.md`.
Conditions come from the run's artifacts (`snow.json`, `weather.json`,
`briefing.md`) — never invented. Every recommendation names waypoints from
`data/out/*.gpx`. The itinerary covers the hunter's N days.

### 7. Deliver

Send the hunter (SendUserFile or equivalent): `guide.md`, `briefing.md`, the
all-waypoints GPX **and** the per-area GPX files (selective import), the KML,
`map.html`, `waypoints.xlsx`. Close with a 3-line summary + OnX import steps.

## Command crib

```bash
python3 scripts/gen_profile.py --species elk --weapon rifle --style backpack \
    --state ID --unit 33 --start 2026-10-15 --end 2026-10-24 --days 5 \
    --out configs/generated/id_33_elk_rifle.yaml
python3 -m elkscout doctor --config configs/generated/id_33_elk_rifle.yaml --data data
python3 -m elkscout run --config configs/generated/id_33_elk_rifle.yaml --data data
python3 scripts/export_xlsx.py --data data --out data/out/waypoints.xlsx
python3 -m pytest -q          # sanity: the pipeline's own suite
```

Dependencies: `pip install -e ".[dev,xlsx]"` from the repo root (Python ≥3.11).

## References (read when the step needs them)

- `references/model-adjustments.md` — why each season/style/weapon delta exists;
  which knob answers which hunter complaint.
- `references/state-discovery.md` — finding + verifying + registering a new
  state's boundary service; the manual boundary fallback.
- `references/guide-template.md` — the guide's exact structure, voice, and
  itinerary logic.
- `references/manual-fallbacks.md` — the doctor-failure playbook (local-run
  commands + manual drop-in table).
