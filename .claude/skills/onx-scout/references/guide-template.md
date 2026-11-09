# The Ultimate Guide: structure, voice, itinerary logic

Write `data/out/guide.md` with EXACTLY this section order. Everything factual
comes from the run's artifacts (`data/work/snow.json`, `data/work/weather.json`,
`data/out/briefing.md`, `data/work/waypoints.geojson`, the generated profile's
`.summary.md`) or a cited web search. If an artifact is missing, write "not
available" — never invent a condition, a temperature, or a season date.

## Section skeleton

```
# <Unit> <Species> Hunt — <dates> (<N> days)
```

1. **Header block** — state/unit, species/weapon/style, dates, generation
   date. If the run used fixtures or a test AOI: a bold DEMO DATA banner,
   first. Then the three standing disclaimers (fair chase; land status —
   "ownership layers have gaps, confirm access on OnX and with the agency";
   regulations — "verify with <agency> before hunting").
2. **Conditions** — SNOTEL snow state and the elevation shift applied;
   forecast table or the climatology note, verbatim from the artifacts; one
   paragraph on what it means ("4 inches at the stations pulled the band down
   ~270 ft — hunt the 6,200–7,900 shelf, not the ridgetops").
3. **Regulations check** — the cited findings from the web search, a table of
   season dates vs. the hunter's dates, mismatches flagged in bold. End with
   the verify-with-agency line.
4. **The model** — the weights table and top-3 adjustments from `.summary.md`,
   two sentences on what the model rewards in this configuration.
5. **Hunt areas, ranked** — one subsection per area (from `hunt_areas` +
   `briefing.md`): why it scores (quote 2–3 waypoint evidence sentences
   verbatim), access route, and the area's wind/thermal plan tied to its
   drainage orientation.
6. **Wind and thermals** — the doctrine section (morning downslope until the
   sun works, upslope mid-morning through afternoon, downslope again at dusk;
   SW prevailing ahead of fronts; hunt from above in the morning, from below
   in the evening). For archery, expand: approach routes, milkweed checks,
   when to back out rather than push a marginal wind.
7. **Day-by-day itinerary** — one block per hunting day for the hunter's N days:
   - Day 1: travel + afternoon/evening glassing from a named GLASS point near
     access; no killing ambitions, just inventory.
   - Allocate dawn sessions to areas by rank — the best area gets the most
     mornings. Each day: dawn plan (named GLASS/FEED points), midday plan
     (still-hunt toward named BED benches as thermals switch, or move camp),
     evening plan (named FEED edges, WATER, SADDLE ambushes).
   - Weather pivots: "if the front lands Day 3, drop to Area 2's feed edges
     and glass the snow line."
   - Packout contingency per area: distance/vertical from the kill zone to the
     nearest ACCESS point, quarters math (elk: 4–5 trips solo; deer: 1–2),
     stock notes if horseback.
8. **Waypoint index** — table: name, type, lat/lon, elevation, evidence
   sentence (from `waypoints.geojson` properties).
9. **Import instructions** — OnX web map → My Content → Import → the GPX;
   per-area files for selective import; KML for Google Earth; the xlsx for
   planning at the kitchen table.

## Voice

Write like a seasoned hunting partner, not a consultant: terse, imperative,
concrete. "Be on G1-01 at gray light" beats "it is recommended to arrive
early." Distances in miles, elevations in feet. No hedging filler; hedge only
where the data genuinely is uncertain (then say why). Every claim must trace
to a named waypoint, an artifact, or a cited source — if you can't trace it,
cut it.
