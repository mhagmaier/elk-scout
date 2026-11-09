# GMU 68 + 681 Bull Elk Hunt — Nov 18–22, 2026 (5 days)

**Colorado GMUs 68 and 681** (CPW elk herd E-26, Saguache) · bull elk · rifle · day hunts from a base camp · 64-in RZR (OHV over 50 in) · hunting with a partner, avoiding crowds · hunt days Wed Nov 18 – Sun Nov 22, 2026 · elkscout run and photo check Mon Nov 9, 2026, on live data (not a demo).

**Revision 4 — the updated pipeline.** This replaces revisions 1–3. Delete earlier imports before loading these (section 11).
- **New in the model:** a snow-line rule fed by Sentinel-2, security timber built into the pipeline, area ranking that counts nearby timber, access points only at Forest Service road ends legal for your RZR on all five days, and more weight on distance from trailheads (you asked to avoid crowds).
- **New photo check:** satellite and color-infrared sheets for every block and point, Google Earth on the biggest blocks, and OnX Recent Imagery over the timber country.
- **Waypoint names restart**, because the model picked a new set of points.

**Standing disclaimers:**
- **Fair chase.** These are scouting points, not elk. Boots, glass, wind and judgment decide the hunt.
- **Land status.** Ownership layers have gaps; confirm on OnX and with the agency. Fences don't read GeoJSON. Closed in this state: unenrolled State Trust Land and local-government land; CPW-enrolled State Trust Land is open under each parcel's own rules (section 3).
- **Regulations.** Verify everything with Colorado Parks and Wildlife (CPW) before hunting: season, hunt code, valid units, CWD, parcel rules.

## 1. Header notes

- **Units:** 68 and 681, dissolved into one hunt area from CPW's GMU boundary.
- **Vehicle:** side-by-side over 50 in. Every ACCESS point and every "legal road" below is a Forest Service route the Motor Vehicle Use Map shows open to that class on all five hunt days.
- **Partner:** the packout math below splits loads between two of you.

## 2. Conditions

**Snow line:** about **10,800 ft**, observed by Sentinel-2 on Nov 6, 2026 (9 scenes, 99.8% of the ground clear of cloud; snow on 14% of it). Your elk band tops out at 10,400 ft, so **snow has not reached the elk band**. The model kept bedding in north-facing dark timber and didn't shift the elevation band. Full elevation score runs 8,800–10,400 ft, falling to zero at 7,200 and 11,800 ft.

**SNOTEL, as of Nov 9:** median depth 8 in over 7 stations, patchy. Cochetopa Pass (10,020 ft) and Moon Pass (11,110 ft) are bare; Middle Creek (11,260 ft) and Rat Creek (11,680 ft) hold 20–22 in.

{{STATION_TABLE}}

**Forecast (Open-Meteo, pulled Nov 9, 9–13 days out):** colder and windier than the Nov 8 pull. Light snow Nov 20 behind a front, then calm and cold Nov 21–22.

{{FORECAST_TABLE}}

**What it means.** Snow sits above the elk, so expect bulls bedded in north-facing dark timber and feeding in the openings beside it at first and last light. The Nov 20 front is light, about a third of an inch of snow in the forecast. The calm, cold day behind it (Nov 21) is the best glassing day of the week. The forecast is 9–13 days out, so re-run snow, weather and Sentinel-2 two or three days before you leave (section 12).

## 3. Regulations check

{{REGS_TABLE}}

**Parcels with waypoints on them:**
- **Spring Gulch State Trust Land (F2-03):** open Sept 1 – end of Feb; elk listed. Drive USFS Rd 708, park at the old road, and walk north 0.6 mi to the boundary ([CPW](https://cpw.state.co.us/state-trust-lands/spring-gulch)).
- **Burro Springs State Trust Land (G2-01, S2-04):**
  - Open May 1 – end of Feb.
  - Motorized travel only on designated roads, and **OHVs may not be used to retrieve big game**.
  - Camping and fires prohibited.
  - Access runs 1.5 hr before sunrise to 1.5 hr after sunset in big-game season ([CPW](https://cpw.state.co.us/state-trust-lands/burro-springs)).

**Herd context (E-26, [CPW herd plan adjustment, 2026](https://cpw.state.co.us/sites/default/files/dam/sftwgsxane/item.20.17_consent_e26_hmpadjustment_2026.pdf)):**
- GMUs 68 + 681 cover about 1,047 sq mi, about 88% of it public.
- The 2024 post-hunt estimate was 5,500 elk.
- CPW's previous 5- and 3-year observed averages were about 15 bulls per 100 cows (14 observed in 2021; 18 averaged since 1987).
- It has been an over-the-counter bull unit since 1987, so your season follows the OTC second and third rifle seasons, and CPW lists overcrowding as a concern.

Verify season dates, your hunt code's valid units, CWD selection and every parcel rule with CPW before hunting.

## 4. The model

Late-season rifle, day hunts (`elk-late-rifle-day`), 30 m grid over both units.

| factor | weight |
|---|---|
{{WEIGHTS}}

**What drives it:**
- **Phase and style:** the late phase favors feed and an elevation band, and treats snow as water. Day style peaks security 0.5–1.6 mi from motorized routes.
- **Your preference:** "avoid crowds" raised the trailhead-distance (pressure) weight to 0.17.
- **State calibration:** Colorado adds 3,000 ft to the elevation band, an informed estimate matched to goHUNT's range for unit 681, not a CPW figure.
- **Land rules:** BLM, Forest Service and Reclamation land is huntable; the other agencies count as closed.
- **Timber:** BED scores get ×1.15 inside security timber, and hunt areas rank by mean score plus nearby live security timber.

**Data notes:**
- **Boundary:** the CPW boundary for both units came in as a drop-in file, because the pipeline's boundary query can't ask for two units at once.
- **Forecast:** pulled by hand from the same Open-Meteo endpoint, because the pipeline's own request kept failing through this machine's network.
- **Sentinel-2:** read with a corrected reflectance scale. The first pass applied an offset twice and called dark timber snow; the fix ships with this revision.
- **Forest Service roads:** de-duplicated. The MVUM service lists every route twice.

## 5. Security timber

**Method.** "Dark timber" is NLCD evergreen or mixed forest at **44%+ canopy**, the densest quarter of conifer here (canopy quartiles 27 / 37 / 44%). A **security block** is 100+ contiguous public acres at least 0.5 mi from any motorized route. Before drawing blocks, Sentinel-2 removed **4,551 acres** of conifer that had lost greenness since 2022.

**What's out there:**
- There are 62,429 acres of dark timber on public land, about 11% of the public ground.
- The run drew **28 blocks totaling 10,468 acres**. The photos call **{{LIVE_AC}} acres live** and **{{DEAD_AC}} acres mostly dead**.
- The dead ones are T08, T09, T15, T21 and T25, high-elevation timber in the La Garita Mountains on the west side. They were already gray in the 2019 color-infrared, before Sentinel-2's 2022 baseline, so its comparison couldn't flag them; the photos did. OnX puts that country in and around the **La Garita Wilderness (no motorized use)**.

**Middle Creek holds the live timber:**
- The core is T01 (1,482 ac), T03 (1,188), T04 (907) and T05 (835), plus T13, T14 and T19: 4,919 acres within 3 mi of the Middle Creek points.
- T01, T04, T05 and T13 are dense live conifer on the satellite and color-infrared photos, and Google Earth agrees for T01, T04 and T05 (Sept 2023 – Oct 2024).
- **Carnero** has the next most: T07, T12 and T28 (749 acres) with five BED points in or beside them, all live with some dead crowns mixed in.

`elkscout_unit68-681_timber_blocks.kml` has every outline for OnX; each note carries the photo verdict.

{{TIMBER_TABLE}}

**How the plan uses timber:**
- **Gray light and last light:** glass the openings that touch these blocks.
- **Once thermals lift:** still-hunt the block from above toward the BED points the photos confirmed.
- **At dusk:** sit the low-side edge.
- **If a block gets pushed:** go to the next live block over, not into the open.

## 6. Imagery

**What was looked at, and how old it is:**
- **Pipeline sheets** (`imagery_check.pdf`): every block's extent and core and a 700 m square around every waypoint, on Esri World Imagery satellite (Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community). Capture dates range from **Oct 30, 2017 to Jul 26, 2025** depending on the spot; 15 of the 25 sheeted blocks were shot in November. Each block and BED point also got **USDA NAIP color-infrared**, flown **Sept 9–22, 2019**, the newest NAIP flight on the USGS service here. T26–T28 weren't in the pipeline's 25-block sheet set; their close-ups and the F1-02/F4-01 checks are the last three pages of the PDF.
- **Sentinel-2:** snow on Nov 6, 2026, and greenness compared between summers 2022 and 2026 (24 scenes each). It is 10–20 m imagery, so it sees snow and stand-scale change but not single trees.
- **Google Earth:** T01 (Oct 6, 2024), T02 (Oct 5, 2025), T03, T04 (Sept 25, 2023), T05 (Oct 6, 2024), T06 (Sept 25, 2023) and F4-01 (Aug 21, 2025).
- **OnX Recent Imagery:** the Oct 12–26, 2026 composite over Middle Creek, Carnero, Kerber and the La Garita side. It's lower resolution and was used only for change: no new burns or clearings over the timber, and no snow on it at that date.

**What the photos changed:**
- **Five blocks are mostly dead:** T08, T09, T15, T21 and T25. They no longer count toward any hunt area's ranking.
- **T23 is mixed,** with live patches inside gray timber.
- **T06** has scattered dead crowns in Google Earth's Sept 2023 image that the 2019 color-infrared doesn't show yet.
- **F1-02 isn't a meadow.** It sits in thin timber with only a small opening 100 m southeast, so the plan skips it.
- **F4-01's satellite image is cloudy;** Google Earth (Aug 21, 2025) and NAIP (Sept 2019) show an open grass park between conifer stands.

**Bed points:**

{{BED_TABLE}}

**Everything else:**
- **Feed:** every FEED point except F1-02 is a real opening. The best evening setups are the ones against cover: F1-01 (meadow against a dense timber edge), F2-01 (meadow tip with a small pond against dense timber) and F2-03 (meadow against a timber stringer).
- **Glass:** all six G4 knobs had snow on Nov 6. G4-02, G4-04, G4-05 and G4-06 are open alpine summits and slopes. G4-03 is a meadow ringed by timber and G4-01 sits at timberline, so check their views. G2-01 sits at a timber edge with open slope just south.
- **Saddles** are open or scattered timber. S2-03 mixes open ground and timber.
- **Water:** W2-01 is inside dense conifer near Sheep Creek; W3-01 is moderately dense conifer by a drainage.
- **Access:** A1-01 is the FR 870 road end in the Middle Creek bottom, where a track continues north (check the MVUM before driving it). The A5 road ends sit at meadow edges and in open sage.

**What photos can't show:** anything since the capture date (beetle kill, blowdown, logging, fire), what's under the canopy, and gates. OnX's high-resolution satellite layer doesn't show a capture date, so flip through your blocks there before committing to one.

## 7. Hunt areas, ranked

"Drains toward" is the overall downhill direction from a plane fit to the elevation model. Gray-light and evening air flows that way; mid-day thermals run the opposite way.

### Area 1 — Middle Creek · 5 waypoints · 4,919 ac of security timber within 3 mi · drains ESE

**Why it scores:**
- B1-01: "{{EV_B1-01}}"
- F1-01: "{{EV_F1-01}}"

**Timber:**
- T05 holds both beds, and T01, T03, T04, T13, T14 and T19 are within reach.
- B1-01 is inside dense live conifer; B1-02 is on T05's edge.

**Access on roads legal for your RZR:**
- A1-01, the FR 870 Middle Creek road end. B1-02 is {{TOUT_B1-02}}, and B1-01 is {{TOUT_B1-01}}.
- F1-01 is {{TOUT_F1-01}}.

**Wind:** gray-light air drains ESE down Middle Creek. Glass F1-01 and T05's openings from the low side. When thermals lift WNW, get above T05 and still-hunt down toward B1-01. At dusk, sit F1-01.

**Packout from B1-01:** {{PACK_B1-01}}

### Area 2 — Mill Creek · 15 waypoints · 2,849 ac within 3 mi · drains NE

This area merges several watersheds; its points run 26 mi north to south. Treat it as four pockets:

1. **Carnero north (the timber):** B2-01–B2-05 in T07, T12 and T28, plus F2-01.
   - B2-02 is {{TOUT_B2-02}}, and B2-03 is {{TOUT_B2-03}}.
   - B2-05 is {{ROUTE_B2-05}}; B2-01 is {{ROUTE_B2-01}}.
   - F2-01 is {{ROUTE_F2-01}}.
2. **Carnero south:** B2-06 inside T17 is {{TOUT_B2-06}}. The S2-01 saddle by T18 is {{ROUTE_S2-01}}.
3. **Burro Springs State Trust Land:** G2-01 and S2-04. No OHV game retrieval (section 3).
4. **Low feed and saddles:**
   - F2-03, on Spring Gulch State Trust Land: walk in from Rd 708.
   - F2-02 and S2-02, on BLM land.
   - S2-03.
   - W2-01, far northwest near T02.

**Why it scores:**
- B2-02: "{{EV_B2-02}}"
- F2-01: "{{EV_F2-01}}"

**Wind:** air drains NE. At gray light, glass F2-01 and the meadow 200 m southwest of B2-03 from the low side. As thermals lift, still-hunt T12 and T07 from above. Evenings, sit the meadow edges.

**Packout from B2-02:** {{PACK_B2-02}} F2-02 and S2-02 are on BLM land; BLM and county roads aren't on the Forest Service map, so check their OHV status.

### Area 3 — Ford Creek · 4 waypoints · 1,709 ac within 3 mi · drains S

**Why it scores:**
- F3-02: "{{EV_F3-02}}"
- F3-01: "{{EV_F3-01}}"

**Timber:** no BED points. This is the feed near Baxter Creek, south of T04 and T06 (1,709 acres within 3 mi).

**Access:** F3-02 is {{ROUTE_F3-02}}; F3-01, F3-03 and W3-01 are 1.4–1.6 mi off FR 880.2A Phantom Creek. All of them sit **below** the nearest legal road end, so the packout climbs.

**Wind:** gray-light air drains S. Glass the F3 openings from below at first light, then work up the timber stringers as the air lifts.

**Packout from F3-02:** {{PACK_F3-02}}

### Area 4 — Cottonwood Creek–Kerber Creek · 9 waypoints · 4,844 ac within 3 mi · drains SSE

**Why it scores:**
- F4-02: "{{EV_F4-02}}"
- F4-01: "{{EV_F4-01}}"

**Timber:**
- T06 (live, with scattered dead crowns in the 2023 image) sits below G4-04 and G4-05.
- T22 (live, moderately dense) is 0.4 mi from F4-01, and T26 (dense live conifer) is under G4-01–G4-03.

**Access:**
- F4-02 is {{ROUTE_F4-02}}, and F4-01 is {{ROUTE_F4-01}}.
- G4-05 is {{ROUTE_G4-05}}, and G4-04 is {{ROUTE_G4-04}}.
- The G4 knobs are 11,763–12,739 ft and had snow on Nov 6, so use them only if those roads are passable.

**Wind:** air drains SSE. Glass F4-02 and F4-01 from the low side at gray light, work T22 or T06 from above once thermals lift, and sit the feed at dusk.

**Packout from F4-01:** {{PACK_F4-01}}

### Area 5 — Trough Creek–Saguache Creek · 7 waypoints · 121 ac of live timber within 3 mi · drains ENE

**Why it scores:**
- F5-01: "{{EV_F5-01}}"

This is the road-end country: five ACCESS points (A5-01–A5-05) and little live security timber. The photos dropped T08 and T21, which leaves T23, live patches inside gray timber. It's a backup, not a timber area.

- F5-01 is {{ROUTE_F5-01}}.
- S5-01 is {{ROUTE_S5-01}}.

## 8. Wind and thermals

Thermals run the day:
- **Gray light until roughly two hours after sun hits the slope:** air pours downhill, toward each area's "drains toward" direction.
- **Mid-morning through afternoon:** it lifts and runs uphill.
- **Dusk:** it rolls back down.

Hunt timber from above once the air lifts, and edges from below in the evening. North-facing timber gets little sun in late November, so its air keeps draining downhill longer than open south slopes do. Check it with a puffer before you count on it having lifted.

On three hunt days the forecast wind matters more than thermals:
- **Nov 18:** W to 17 mph. It blows down T05, which faces ENE, against the rising air.
- **Nov 19:** SSE to 22 mph. It blows down over T12's north-facing beds, against the rising air.
- **Nov 20:** WNW to 19 mph, with the front. Snow and cloud keep the thermals weak, so the wind rules.

When the wind blows downhill against the rising air, don't come from above: it carries your scent straight onto the beds. Come in along the slope from the downwind side instead. A strong wind swirls in the lee of a ridge, so give beds there more room. If the wind is wrong for an area, go to the next live block over; that's what the per-area GPX files and the timber KML are for.

## 9. Day-by-day

**Opener rule:** fourth rifle season follows the OTC seasons, so open in the biggest photo-confirmed live security timber: Middle Creek.

**Packout decision before the opener:** with a partner, an elk is 2–3 loads each.
- Every bed is 0.5–1.2 mi from a road legal for your RZR, and 0.5–1.9 mi from a road end. That's about 2–11 round-trip miles apiece; the bed table in section 6 has each one.
- The Ford Creek feed is the exception: the packout climbs to the road.
- At Burro Springs, no OHV retrieval.

**Tue Nov 17 — travel (season closed).** In daylight, drive FR 870 to the A1-01 road end and find the FR 856.1A Bull Bear road end for the F1-01 approach, so both opener drives are known.

**Day 1 — Wed Nov 18 (opener): Middle Creek, Area 1.** Forecast {{FC_2026-11-18}}.
- **Gray light:** F1-01, an open meadow against a dense timber edge ({{TOUT_F1-01}}). Glass it from its low, south side, along with T05's edges 0.7 mi north-northwest.
- **Mid-morning:** the W wind blows down T05, so coming from above puts your scent on the beds. Come at B1-01 (dense live conifer) from the east, sidehilling along its slope with the wind in your face. Get to its level east of it before you turn in, whether you walk over from F1-01 (1.65 mi) or climb from A1-01 (1.2 mi, 1,381 ft). If the wind dies, come from above on the rising air.
- **Evening:** F1-01 from its southeast corner, below and downwind of the meadow, or below B1-02 ({{TOUT_B1-02}}). The sinking air and the W wind both carry your scent away from the timber there.
- **Skip F1-02:** thin timber, not a meadow.

**Day 2 — Thu Nov 19: Carnero north, Area 2.** Forecast {{FC_2026-11-19}}.
- **Gray light:** F2-01, a meadow tip against dense timber ({{ROUTE_F2-01}}).
- **Mid-morning:** the SSE wind blows down over T12's north-facing beds, so don't come from above. Come in from FR 709 on the block's northwest side and sidehill east along the slope toward B2-03, then B2-02 ({{TOUT_B2-02}}), with the wind quartering into your face. A 22 mph wind swirls on this lee side of the ridge, so check it with a puffer and give the beds room.
- **Evening:** F2-01 from its low, northwest side. The sinking air and the SSE wind both carry your scent off the meadow there. Skip the meadow 200 m southwest of B2-03 tonight: it sits about 170 ft above the beds, and the sinking air would carry your scent down into them.

**Day 3 — Fri Nov 20: front with snow, Kerber side, Area 4.** Forecast {{FC_2026-11-20}}.
- **First light:** look for fresh tracks on the low feed: F4-02 ({{ROUTE_F4-02}}) and F4-01 ({{ROUTE_F4-01}}). The other low feed is F2-03 at 8,698 ft on Spring Gulch State Trust Land and F2-02 at 9,279 ft on BLM land, if the tracks point there.
- **Mid-morning:** come at T22 from F4-01's side. Drop through the drainage between them and still-hunt in from the northeast with the WNW wind on your right. Don't come in from FR 888 to the northwest: the wind carries your scent from there into the block. Fresh snow shows where elk crossed between the feed and the timber.
- **Evening:** F4-01 from its low, southeast side.

**Day 4 — Sat Nov 21: behind the front, Middle Creek from the south.** Forecast {{FC_2026-11-21}}. Cold and calm: the best glassing day.
- **Gray light:** glass from F3-02 ({{ROUTE_F3-02}}), or from G4-05 over T06 ({{ROUTE_G4-05}}) if FR 880 is passable.
- **Mid-morning:** still-hunt T04, dense live conifer with small parks, from above. The light NNW wind and the rising air both blow uphill there. Come down from FR 880.2B Antora Meadows, 0.7 mi away and about 860 ft above the block. There the road runs near 11,700 ft, above the Nov 6 snow line. If it isn't passable, don't come at T04 from below, where the rising air would carry your scent up into it.
- **Evening:** F3-02 or F3-03.

**Day 5 — Sun Nov 22: back to whatever showed elk.** Forecast {{FC_2026-11-22}}.
- Return to whichever block or area showed elk.
- **If nothing showed,** run Carnero south: B2-06, inside dense live conifer in T17 ({{TOUT_B2-06}}). The light NE wind and the rising air both blow uphill there, so come from above. Sit the S2-01 saddle at T18 for the evening.

## 10. Waypoint index

{{WAYPOINT_INDEX}}

## 11. Import

- **OnX:** web map → My Content → Import → `elkscout_unit68-681_all.gpx` for all 40 points. **Delete earlier imports of this hunt first**, because names repeat across revisions with different locations.
- **One area at a time:** import the per-area files instead:
  - `…_middle-creek.gpx`
  - `…_mill-creek.gpx`
  - `…_ford-creek.gpx`
  - `…_cottonwood-creek-kerber-creek.gpx`
  - `…_trough-creek-saguache-creek.gpx`
- **Timber outlines:** import `elkscout_unit68-681_timber_blocks.kml` the same way. It has 28 blocks, each with its photo verdict.
- **Google Earth:** `elkscout_unit68-681.kml`.
- **At the table:** `waypoints.xlsx`, `map.html`, and `imagery_check.pdf` (every photo sheet).

## 12. Still unverified

- **Your license:** whether it lists both 68 and 681, and whether your hunt code is selected for mandatory CWD sampling (brochure pp. 41–52; [CPW CWD page](https://cpw.state.co.us/activities/hunting/big-game/chronic-wasting-disease)).
- **BLM and county roads:** their OHV status (F2-02, S2-02), because they aren't on the Forest Service map.
- **Snow on the high roads:** whether FR 880 and FR 880.2B are passable to the G4 knobs.
- **Since-capture changes:** anything after each photo date. The newest color-infrared here is from 2019.
- **The La Garita Wilderness boundary** around the dead high blocks; check it in OnX.
- **Re-run 2–3 days before you leave:** `python3 -m elkscout fetch --only snow,weather,sentinel --config configs/generated/co_68-681_elk_rifle_rev4.yaml --data data`, then `score`, `waypoints` and `report`. Keep the current files to compare.
