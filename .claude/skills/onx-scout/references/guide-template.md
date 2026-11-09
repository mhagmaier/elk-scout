# The Ultimate Guide: structure, voice, itinerary logic

Write `data/out/guide.md` with this section order. Everything factual comes
from the run's artifacts — `data/work/snow.json`, `sentinel.json`,
`weather.json`, `timber.json`, `timber_blocks.geojson`, `waypoints.geojson`,
`hunt_areas.geojson`, `imagery_review.json`, `data/out/briefing.md`, the
profile's `.summary.md` — or a cited web search. If an artifact is missing,
write "not available"; never invent a condition, a date, or a distance.

## Section skeleton

```
# <Units> <Species> Hunt — <dates> (<N> days)
```

1. **Header** — state/units, species/weapon/style/vehicle, dates, run date.
   DEMO DATA banner first if the run used fixtures. Standing disclaimers:
   fair chase; land status ("ownership layers have gaps; confirm on OnX and
   with the agency; closed agencies in this state: …"); regulations.
2. **Conditions** — snow: the snow line and where it came from (Sentinel-2
   date if `snowline_source` says so, else the SNOTEL estimate), whether snow
   has reached the elk band (`snow_in_band`) and what that did to bedding;
   station table; forecast table or climatology note, verbatim.
3. **Regulations check** — cited table vs. the hunter's plan; mismatches in
   bold; nonresident OHV permit; rules of each public-access parcel in play.
4. **The model** — weights and top adjustments from `.summary.md`, including
   state calibration and land rules, in two or three sentences.
5. **Security timber** — the threshold used (`timber.json`), block count and
   acres, how many acres Sentinel-2 removed as dead, and a table of blocks:
   id, acres, elevation, north-facing share, road distance, nearest legal
   road for the hunter's vehicle, photo verdict. Point to the timber KML.
6. **Imagery** — what was looked at and how old it is: Sentinel-2 snow date
   and leaf-on years compared; NAIP flight year(s) and satellite date range
   (from `imagery_review.json` dates). Block and bed-point verdicts; anything
   the photos overturned. What photos can't show (since-capture change,
   understory, gates) and the OnX-imagery check.
7. **Hunt areas, ranked** — one subsection per area: security timber acres
   within reach, why it scores (quote 2–3 waypoint notes verbatim), access on
   roads legal for the hunter's vehicle, wind/thermal plan from the drainage
   direction, packout.
8. **Wind and thermals** — downslope at gray light, upslope mid-morning to
   afternoon, downslope at dusk; hunt timber from above once the air lifts,
   edges from below at evening. Archery: expand approach routes and when to
   back out of a marginal wind.
9. **Day-by-day** — see the itinerary rules below.
10. **Waypoint index** — name, type, area, lat/lon, elevation, land, note.
11. **Import** — OnX: delete earlier imports of this hunt first (names repeat
    across revisions), then the all-points GPX or per-area GPX files, and the
    security-timber KML; Google Earth KML; `waypoints.xlsx`; `map.html`;
    `imagery_check.pdf`.
12. **Still unverified** — every item the run couldn't confirm (license valid
    units, CWD, BLM/county road OHV status, since-capture changes), plus
    "re-run snow, weather, and imagery 2–3 days before you leave"
    (`elkscout fetch --only snow,weather,sentinel`, then score, waypoints,
    report — keep the current files to compare).

## Itinerary rules

- **Pressured seasons (any rifle season after earlier general seasons; OTC
  units; any unit the agency flags for crowding): open in the biggest
  photo-confirmed LIVE security timber.** Opening-day pressure pushes elk into
  it; be on its edges at gray light. Don't open in an area with no security
  timber just because its mean score is high. Hunt-area ranks already include
  timber; cross-check against the photo verdicts.
- Allocate the remaining dawns by rank; the best timber country gets the most
  mornings. Edge-and-feed areas without security timber are weather pivots
  and backups.
- Each day: dawn (named GLASS/FEED points against the timber), mid-morning
  (still-hunt the block from above as thermals lift, toward named BED points
  the photos confirmed), evening (low-side edge or FEED/WATER/SADDLE).
- Skip any point the photos called poor or dead; name the better cover the
  verdict points to.
- Weather pivots: a front with snow → first-light tracks on the lowest feed;
  wind wrong for an area → the next block over.
- **Packout decision before the opener.** For each area: distance and climb
  from the likely kill zone to the nearest legal road; elk 4–5 loads solo
  (deer 1–2) = round-trip miles. If the best timber is 2+ mi from a road and
  the hunter is solo, say it plainly: bring help, or cap solo shots at about a
  mile from the road. Note any parcel that bans motorized retrieval.

## Voice

Write like a seasoned hunting partner: terse, imperative, concrete. "Be on
the T05 edge at gray light" beats "it is recommended to arrive early."
Distances in miles, elevations in feet. Hedge only where the data is
genuinely uncertain, and say why. Every claim traces to a named waypoint, a
block, an artifact, or a cited source — if it can't, cut it.
