# Why the model moves: season × style × weapon adjustments

The numeric source of truth is `configs/adjustments.yaml`; this file explains
it so you can defend any number to the hunter — and know which knob to turn
when they push back. The composition order is template → phase → style →
weapon → user `--adjust`, with factor weights renormalized to 1.0 at the end.
Styles deliberately out-rank phases on the security curve: how far the hunter
can operate from the truck beats how far game sits from roads.

## Phase derivation (from the hunt's start date)

| Species | Window | Phase | One-line why |
|---|---|---|---|
| elk | Aug 15 – Sep 30 | `rut` | Bulls with cows on high summer range, vocal, water-anchored |
| elk | Oct 1 – Nov 7 | `general` | The template: pressured post-rut elk in security timber |
| elk | Nov 8 – Dec 31 | `late` | Migration/recovery: snow pushes elk to low south-facing feed |
| mule deer | Aug 15 – Sep 30 | `high_country` | Patternable alpine bucks; a glassing game |
| mule deer | Oct 1 – Nov 3 | `transition` | The deer template: road-shy browsers mid-elevation |
| mule deer | Nov 4 – Dec 31 | `rut` | Bucks follow doe groups onto winter-range shrub |

## The cells, in plain hunter language

**Elk rut (Sept archery country).** A September bull lives within bugling
distance of cows and within a short walk of water — wallows are daily
appointments in hot weather. Pressure is a fraction of rifle season, so elk
tolerate roads better (security optimum pulls in to 0.8–3 km). That's why
water weight jumps ×1.7 with a tighter curve (full score ≤250 m), elevation
rides ~300 ft higher (summer range), WATER waypoints multiply ×1.5, SADDLE
×1.25 (travel pinches between bed and feed are calling setups), and GLASS
drops — you kill September bulls with your ears.

**Elk general (Oct rifle).** This IS the template — the profile that was built
and reviewed for Idaho unit 33: security heaviest (0.25, optimum 1.2–4 km),
dark-timber bedding, burn/meadow-edge feed. No deltas.

**Elk late (Nov+).** Feed ×1.4, water ×0.5 (snow is water), elevation
plateau 5,800–7,400 ft before state calibration. Bedding switches to south
faces **only once snow has reached the elk band** (`snow_in_band` in
snow.json): with patchy, high snow, pressured late bulls stay bedded in
north-facing dark timber — the GMU 68/681 lesson, where the unconditional
south flip put beds on the wrong slopes. GLASS ×1.5.

**Mule deer template (Oct transition).** Deer are browsers in opener country:
feed scores NLCD shrub (52) at 1.0 over grass (71) at 0.7; bedding wants
10–50% canopy on steep, broken ground (the cliff-adjacent pocket a buck backs
into), tolerated to 80% slope; water weight is only 0.08 — deer water
unpredictably; security and pressure run higher than elk because rifle deer
vacuum off roaded country fast.

**Deer high country (Sept).** Plateau 8,200–9,800 ft, nearly-open bedding
(canopy curve peaks at 5–30%), slope tolerance to 85%, GLASS ×1.6: find a
velvet buck at first light, watch him bed, stalk at midday.

**Deer rut (Nov).** Find does, find bucks: feed ×1.5 on low (5,200–7,000 ft)
south-aspect shrub, snow shift doubled, pressure ×1.2 (winter-range roads
concentrate hunters), GLASS ×1.6 — glass all day, the next buck walks through
at noon.

## Snow line, not median depth

`snow.method: snowline` (default) estimates the snow line — the lowest station
holding 6+ inches whose higher neighbors mostly agree — and pulls the band's
top down to it only when it sits below the top. When Sentinel-2 has a clear
look within three weeks, the **observed** snow line from the imagery replaces
the station estimate. On 68/681 the old median rule took 7 in. from stations
at 10,000–11,700 ft and shifted the band down 483 ft though Cochetopa Pass at
10,020 ft was bare; the snow-line rule shifts it 0.

## State calibration

The templates are central-Idaho numbers. `configs/states.yaml` carries an
`elevation_offset_ft` per state (Colorado +3,000 ft) applied after every
other layer, and the state's land-access rules. An unregistered state gets
no offset — check the band against published unit elevations.

## Security timber

`timber.py` finds blocks of dark conifer (NLCD 42/43 at or above the local
conifer 75th-percentile canopy, floor 35%) on public land, 0.5+ mi from
motorized routes, 100+ ac, after removing Sentinel-2 "dead" cells. BED
scores get ×1.15 inside blocks, hunt areas rank by mean score + 0.3 ×
(nearby block acres / max), and photo-confirmed dead blocks drop out of the
ranking. Knobs: `timber.min_road_mi`, `timber.min_acres`,
`timber.dark_canopy_pct`, `timber.rank_weight`.

## Style overlays

| Style | Security curve says | Camp logic |
|---|---|---|
| day | Optimum 0.8–2.5 km; penalize past 4 km — you can't be there at gray light | CAMP count 0; ACCESS ×1.5; the guide plans dark-o'clock trailhead starts |
| backpack | Template default (1.2–4 km) | Camp: water ≤400 m, ≤10% slope, 2.4–5.6 km in |
| horseback | Optimum 2–6 km, live to 9+ — stock resets the distance economy | Camp band pushed to 3–9 km; graze + water + trail access matter |

## Weapon overlays (waypoint emphasis, not factor weights)

Rifle is the identity — the templates already carry rifle emphasis.
Muzzleloader trims GLASS slightly and adds SADDLE (the approach matters more
than the vantage). Archery: WATER ×1.4 and SADDLE ×1.4, GLASS ×0.7 — inside
60 yards the hunt is ambushes on water, wallows, and travel pinches, and the
guide's thermals section carries the weight.

## When the hunter pushes back

| Complaint | Knob |
|---|---|
| "Too far from roads / I can't pack that deep" | style → `day`, or `--adjust factors.security.weight=<lower>` |
| "I hate crowds, go deeper" | `--adjust factors.pressure.weight=0.2` (renormalized) |
| "Too high / too low for this unit" | `--adjust factors.elevation.curve_elevation_ft=[[...]]` with shifted breakpoints |
| "I want more water sits" (archery) | counts via `--adjust waypoints.counts.WATER=<n>` |
| "Snow came early" | re-run near the hunt — SNOTEL shifts the band live; or `--adjust snow.band_shift_ft=[[...]]` |
| "Show me fewer, better points" | `--adjust waypoints.score_floor=0.55` |
| "Ranking ignores the big timber" / "too much weight on timber" | `--adjust timber.rank_weight=0.5` (or 0.1) |
| "Those aren't real security blocks" | `--adjust timber.min_road_mi=0.75` / `timber.min_acres=200` |
| "Band is wrong for this state" | fix `elevation_offset_ft` in `configs/states.yaml` (with a source), regenerate |
