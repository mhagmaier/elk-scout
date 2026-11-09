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

| station | elevation ft | snow depth in | SWE in |
|---|---|---|---|
| Cochetopa Pass | 10,020 | 0.0 | 0.2 |
| Hayden Pass | 10,700 | 8.0 | 2.2 |
| Porphyry Creek | 10,790 | 8.0 | 2.3 |
| Moon Pass | 11,110 | 0.0 | 0.0 |
| Middle Creek | 11,260 | 20.0 | 7.2 |
| Sargents Mesa | 11,490 | 5.0 | 1.8 |
| Rat Creek | 11,680 | 22.0 | 7.9 |

**Forecast (Open-Meteo, pulled Nov 9, 9–13 days out):** colder and windier than the Nov 8 pull. Light snow Nov 20 behind a front, then calm and cold Nov 21–22.

| date | high °F | low °F | precip in | snow in | max wind mph | wind from |
|---|---|---|---|---|---|---|
| Wed Nov 18 | 34 | 18 | 0.012 | 0.0 | 17 | W (273°) |
| Thu Nov 19 | 34 | 18 | 0.0 | 0.0 | 22 | SSE (167°) |
| Fri Nov 20 | 28 | 13 | 0.071 | 0.331 | 19 | WNW (301°) |
| Sat Nov 21 | 36 | 12 | 0.0 | 0.0 | 8 | NNW (327°) |
| Sun Nov 22 | 32 | 20 | 0.0 | 0.0 | 7 | NE (55°) |

**What it means.** Snow sits above the elk, so expect bulls bedded in north-facing dark timber and feeding in the openings beside it at first and last light. The Nov 20 front is light, about a third of an inch of snow in the forecast. The calm, cold day behind it (Nov 21) is the best glassing day of the week. The forecast is 9–13 days out, so re-run snow, weather and Sentinel-2 two or three days before you leave (section 12).

## 3. Regulations check

| item | what CPW / the source says | your plan | status |
|---|---|---|---|
| 2026 fourth rifle season | Nov 18–22 ([CPW 2026 Big Game Brochure](https://spl.cde.state.co.us/artemis/nrserials/nr1431internet/nr14312026internet.pdf)) | Nov 18–22 | **match** |
| Hunt code / valid units | Not confirmed: the brochure's elk hunt-code tables (pp. 41–52) didn't come through any copy reachable from here | 68 + 681 | **verify your license lists both 68 and 681** |
| CWD sampling | Mandatory head submission from elk taken in rifle seasons on *selected* hunt codes; over-the-counter elk codes are excluded; no mandatory deer testing in 2026. The selected codes are on brochure pp. 41–52 ([CPW CWD page](https://cpw.state.co.us/activities/hunting/big-game/chronic-wasting-disease)) | — | **check whether your hunt code is selected** |
| Hunter orange or pink | Firearm big-game hunters must wear fluorescent orange or pink; camo orange/pink doesn't count ([Kiowa County Press, CPW 2026 rules](https://kiowacountypress.net/content/colorado-hunting-seasons-open-new-regulations-2026)) | — | comply |
| Side-by-side | Nonresident OHVs need a Colorado OHV permit ($26.25) displayed on public-land roads and designated trails; buying online gives a 45-day temporary authorization number ([CPW](https://cpw.state.co.us/register-off-highway-vehicle)) | 64-in RZR | **buy before you go** |
| Forest Service roads | ACCESS points are ends of routes the USFS Motor Vehicle Use Map shows open to OHVs over 50 in on all five hunt days (USFS EDW MVUM) | 64-in RZR | verify on the current MVUM |
| State Trust Land in play | Each CPW-enrolled parcel below is open Sept 1 – end of Feb with elk listed; everyone 16+ needs a valid hunting or fishing license to enter ([CPW State Trust Lands](https://cpw.state.co.us/state-trust-lands/middle-creek)) | — | comply; parcel rules below |

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
| elevation | 0.15 |
| security | 0.22 |
| bedding | 0.17 |
| feed | 0.24 |
| water | 0.04 |
| pressure | 0.17 |

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
- The run drew **28 blocks totaling 10,468 acres**. The photos call **9,404 acres live** and **1,064 acres mostly dead**.
- The dead ones are T08, T09, T15, T21 and T25, high-elevation timber in the La Garita Mountains on the west side. They were already gray in the 2019 color-infrared, before Sentinel-2's 2022 baseline, so its comparison couldn't flag them; the photos did. OnX puts that country in and around the **La Garita Wilderness (no motorized use)**.

**Middle Creek holds the live timber:**
- The core is T01 (1,482 ac), T03 (1,188), T04 (907) and T05 (835), plus T13, T14 and T19: 4,919 acres within 3 mi of the Middle Creek points.
- T01, T04, T05 and T13 are dense live conifer on the satellite and color-infrared photos, and Google Earth agrees for T01, T04 and T05 (Sept 2023 – Oct 2024).
- **Carnero** has the next most: T07, T12 and T28 (749 acres) with five BED points in or beside them, all live with some dead crowns mixed in.

`elkscout_unit68-681_timber_blocks.kml` has every outline for OnX; each note carries the photo verdict.

| block | acres | elevation ft | north-facing | from roads, median (max) | nearest road legal for your RZR | waypoints within 1 mi | photos | satellite / color-infrared |
|---|---|---|---|---|---|---|---|---|
| T01 | 1,482 | 9,446–10,861 | 33% | 1.59 mi (2.42 mi) | FR 870 Middle Cr, 0.6 mi | A1-01, B1-02 | dense live conifer (also Google Earth, Oct 2024) | 2025-05-11 / 2019-09-22 |
| T02 | 1,230 | 10,197–11,041 | 4% | 0.77 mi (1.25 mi) | FR 782.2A Antelope Park, 0.5 mi | — | dense live conifer, aspen in the draws (Google Earth, Oct 2025) | 2023-11-10 / 2019-09-22 |
| T03 | 1,188 | 9,812–10,731 | 2% | 0.84 mi (1.61 mi) | FR 7578 Milk Creek, 1.6 mi | — | live conifer, moderately dense, open parks inside | 2021-11-16 / 2019-09-22 |
| T04 | 907 | 9,648–10,991 | 54% | 1.44 mi (2.07 mi) | FR 880.2B Antora Meadows, 0.7 mi | A1-01 | dense live conifer, small parks inside (Google Earth, Sept 2023) | 2025-05-11 / 2019-09-22 |
| T05 | 835 | 9,647–10,693 | 21% | 0.97 mi (1.48 mi) | FR 870 Middle Cr, 0.5 mi | A1-01, B1-01, B1-02, F1-01, F1-02 | dense live conifer, aspen pockets on its edges (Google Earth, Oct 2024) | 2021-11-16 / 2019-09-22 |
| T06 | 802 | 10,086–11,077 | 29% | 0.73 mi (1.13 mi) | FR 880 Findley Gulch, 0.6 mi | G4-04, G4-05 | live conifer with scattered dead crowns and aspen patches (Google Earth, Sept 2023) | 2021-11-16 / 2019-09-22 |
| T07 | 441 | 9,778–10,660 | 73% | 0.79 mi (1.20 mi) | FR 620 Fullerton Park, 0.5 mi | B2-01, B2-04 | live conifer, some dead crowns mixed in | 2018-11-09 / 2019-09-09 |
| T08 | 327 | 10,472–11,120 | 71% | 0.71 mi (1.33 mi) | FR 776.1A Table Mtn, 0.5 mi | — | **mostly dead (gray crowns), not dark timber** | 2023-11-10 / 2019-09-12 |
| T09 | 316 | 11,376–11,811 | 78% | 2.92 mi (3.36 mi) | FR 600 Pool Table, 2.4 mi | — | **mostly dead (gray crowns), not dark timber** | 2025-04-09 / 2019-09-12 |
| T10 | 250 | 10,035–10,420 | 63% | 1.07 mi (1.50 mi) | FR 680 North Carnero, 1.5 mi | — | live conifer, moderately dense | 2017-10-30 / 2019-09-09 |
| T11 | 248 | 10,397–10,738 | 6% | 0.67 mi (0.93 mi) | FR 810.1C Spanish Bear, 0.5 mi | — | dense young regrowth, roads and cuts at its edges | 2023-11-10 / 2019-09-09 |
| T12 | 207 | 9,741–10,491 | 87% | 0.71 mi (1.09 mi) | FR 709 Antelope, 0.5 mi | B2-02, B2-03, B2-05 | live conifer, some dead crowns mixed in | 2018-11-09 / 2019-09-09 |
| T13 | 190 | 9,617–10,045 | 52% | 1.28 mi (1.59 mi) | FR 7578 Milk Creek, 1.9 mi | — | dense live dark timber | 2021-11-16 / 2019-09-22 |
| T14 | 177 | 9,616–10,588 | 0% | 0.70 mi (1.09 mi) | FR 7578 Milk Creek, 0.9 mi | — | dense live conifer, aspen on its edges | 2021-11-16 / 2019-09-22 |
| T15 | 176 | 10,896–11,405 | 86% | 1.87 mi (2.50 mi) | FR 787 Saguache Park, 1.3 mi | — | **mostly dead (gray crowns), not dark timber** | 2025-04-09 / 2019-09-12 |
| T16 | 172 | 9,984–10,562 | 57% | 1.12 mi (1.56 mi) | FR 680.2A North Carnero, 0.8 mi | — | live conifer, moderately dense, between meadows | 2017-10-30 / 2019-09-09 |
| T17 | 172 | 9,714–10,477 | 76% | 0.69 mi (1.05 mi) | FR 690.2A Storm King Cg, 0.5 mi | B2-06 | live conifer, moderately dense to dense; meadow to the north | 2023-11-08 / 2019-09-09 |
| T18 | 142 | 9,733–10,191 | 25% | 0.70 mi (0.88 mi) | FR 685 Cecilia Cr, 0.5 mi | S2-01 | live conifer, moderately dense, open parks around it | 2023-11-08 / 2019-09-09 |
| T19 | 140 | 10,271–10,557 | 1% | 0.73 mi (1.00 mi) | FR 860 Indian Park, 0.5 mi | F1-02 | dense live core in a draw | 2018-11-09 / 2019-09-22 |
| T20 | 134 | 9,987–10,279 | 2% | 0.69 mi (0.93 mi) | FR 782.2A Antelope Park, 0.5 mi | — | dense live conifer; old cutting units on its east side | 2021-11-14 / 2019-09-22 |
| T21 | 126 | 11,125–11,606 | 82% | 2.63 mi (3.01 mi) | FR 744 Middle Fork Saguache, 2.2 mi | — | **mostly dead (gray crowns), not dark timber** | 2025-04-09 / 2019-09-12 |
| T22 | 125 | 9,297–10,531 | 56% | 0.71 mi (1.09 mi) | FR 888 Greenback, 0.6 mi | F4-01 | live conifer, moderately dense (satellite image cloudy) | 2023-08-31 / 2019-09-22 |
| T23 | 121 | 10,545–10,888 | 37% | 0.91 mi (1.44 mi) | FR 744 Middle Fork Saguache, 0.5 mi | — | mixed live and dead: live patches inside gray timber | 2025-04-09 / 2019-09-12 |
| T24 | 119 | 9,896–10,441 | 51% | 0.68 mi (1.02 mi) | FR 842 Saguache Peak, 0.5 mi | — | live conifer, moderately dense, meadow to the east | 2018-11-09 / 2019-09-09 |
| T25 | 119 | 11,243–11,771 | 89% | 1.90 mi (2.49 mi) | FR 600 Pool Table, 1.5 mi | — | **mostly dead (gray crowns), not dark timber** | 2025-04-09 / 2019-09-12 |
| T26 | 113 | 10,276–10,963 | 63% | 1.33 mi (1.77 mi) | FR 874 Peterson Cr, 0.9 mi | G4-01, G4-02, G4-03 | dense live conifer, aspen along its north edge | 2023-08-31 / 2019-09-22 |
| T27 | 108 | 9,214–9,879 | 73% | 0.81 mi (1.03 mi) | FR 852.4A Studhorse Cr, 0.5 mi | — | dense live conifer | 2018-11-09 / 2019-09-09 |
| T28 | 101 | 9,713–10,047 | 94% | 0.65 mi (0.84 mi) | FR 709 Antelope, 0.5 mi | B2-02, B2-03 | live conifer, some dead crowns mixed in | 2023-11-08 / 2019-09-09 |

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

| bed | block | what the photos show | satellite | color-infrared | nearest legal road end | packout with a partner |
|---|---|---|---|---|---|---|
| B1-01 | T05 | inside dense live conifer (block T05) | 2021-11-16 | 2019-09-22 | FR 870 Middle Cr, 1.2 mi, 1,381 ft down to the truck | 2–3 loads each, 5–7 round-trip mi apiece |
| B1-02 | T05 | edge of the T05 timber, live conifer of moderate density | 2021-11-16 | 2019-09-22 | FR 870 Middle Cr, 0.5 mi, 770 ft down to the truck | 2–3 loads each, 2–3 round-trip mi apiece |
| B2-01 | T07 | inside live conifer (T07) with some dead crowns; opening 150 m west | 2018-11-09 | 2019-09-09 | FR 704 South Tracy, 1.9 mi, 947 ft down to the truck | 2–3 loads each, 8–11 round-trip mi apiece |
| B2-02 | T12 | inside dense live conifer (T12); small park just northeast | 2018-11-09 | 2019-09-09 | FR 709 Antelope, 0.9 mi, 563 ft down to the truck | 2–3 loads each, 4–5 round-trip mi apiece |
| B2-03 | T12 | inside dense live conifer; meadow 200 m southwest | 2018-11-09 | 2019-09-09 | FR 709 Antelope, 1.1 mi, 913 ft down to the truck | 2–3 loads each, 4–7 round-trip mi apiece |
| B2-04 | T07 | dense conifer edge (T07); open slope and aspen to the west | 2018-11-09 | 2019-09-09 | FR 704 South Tracy, 1.5 mi, 1,347 ft down to the truck | 2–3 loads each, 6–9 round-trip mi apiece |
| B2-05 | T12 | live conifer of moderate density; openings and aspen to the south | 2018-11-09 | 2019-09-09 | FR 709 Antelope, 0.9 mi, 293 ft down to the truck | 2–3 loads each, 4–5 round-trip mi apiece |
| B2-06 | T17 | inside dense live conifer (T17) | 2023-11-08 | 2019-09-09 | FR 690.2A Storm King Cg, 0.9 mi, 1,016 ft down to the truck | 2–3 loads each, 4–5 round-trip mi apiece |

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
- B1-01: "North-facing valley at 10,273 ft, 54% canopy, 36% slope; 1.2 mi from the nearest motorized route, 1.12 mi to water, inside security timber T05 (835 ac). Photos (2021-11-16): inside dense live conifer (block T05)."
- F1-01: "Feed on a southeast-facing bench at 10,019 ft, 40% canopy, 21% slope; 1.1 mi from the nearest motorized route, 0.28 mi to water, 0.7 mi to security timber T05 (835 ac). Photos (2021-11-16): open meadow against a dense timber edge."

**Timber:**
- T05 holds both beds, and T01, T03, T04, T13, T14 and T19 are within reach.
- B1-01 is inside dense live conifer; B1-02 is on T05's edge.

**Access on roads legal for your RZR:**
- A1-01, the FR 870 Middle Creek road end. B1-02 is 0.5 mi from the FR 870 Middle Cr road end, 770 ft above it, and B1-01 is 1.2 mi from the FR 870 Middle Cr road end, 1,381 ft above it.
- F1-01 is 1.1 mi from the FR 856.1A Bull Bear road end, 6 ft below it.

**Wind:** gray-light air drains ESE down Middle Creek. Glass F1-01 and T05's openings from the low side. When thermals lift WNW, get above T05 and still-hunt down toward B1-01. At dusk, sit F1-01.

**Packout from B1-01:** 1.2 mi and 1,381 ft down to the FR 870 Middle Cr road end: 2–3 loads each with your partner, about 5–7 round-trip miles apiece (solo it would be 10–12).

### Area 2 — Mill Creek · 15 waypoints · 2,849 ac within 3 mi · drains NE

This area merges several watersheds; its points run 26 mi north to south. Treat it as four pockets:

1. **Carnero north (the timber):** B2-01–B2-05 in T07, T12 and T28, plus F2-01.
   - B2-02 is 0.9 mi from the FR 709 Antelope road end, 563 ft above it, and B2-03 is 1.1 mi from the FR 709 Antelope road end, 913 ft above it.
   - B2-05 is 0.6 mi off FR 620 Fullerton Park; B2-01 is 0.8 mi off FR 620 Fullerton Park.
   - F2-01 is 0.6 mi off FR 619 Lake Mtn.
2. **Carnero south:** B2-06 inside T17 is 0.9 mi from the FR 690.2A Storm King Cg road end, 1,016 ft above it. The S2-01 saddle by T18 is 0.5 mi off FR 41G Carnero.
3. **Burro Springs State Trust Land:** G2-01 and S2-04. No OHV game retrieval (section 3).
4. **Low feed and saddles:**
   - F2-03, on Spring Gulch State Trust Land: walk in from Rd 708.
   - F2-02 and S2-02, on BLM land.
   - S2-03.
   - W2-01, far northwest near T02.

**Why it scores:**
- B2-02: "Northeast-facing slope at 10,250 ft, 46% canopy, 38% slope; 0.8 mi from the nearest motorized route, 1.19 mi to Mill Creek, inside security timber T12 (207 ac). Photos (2018-11-09): inside dense live conifer (T12); small park just northeast."
- F2-01: "Feed on a southeast-facing knob at 10,450 ft, 51% canopy, 16% slope; 0.6 mi from the nearest motorized route, 0.13 mi to water. Photos (2023-11-08): tip of an open meadow (small pond) against dense timber."

**Wind:** air drains NE. At gray light, glass F2-01 and the meadow 200 m southwest of B2-03 from the low side. As thermals lift, still-hunt T12 and T07 from above. Evenings, sit the meadow edges.

**Packout from B2-02:** 0.9 mi and 563 ft down to the FR 709 Antelope road end: 2–3 loads each with your partner, about 4–5 round-trip miles apiece (solo it would be 7–9). F2-02 and S2-02 are on BLM land; BLM and county roads aren't on the Forest Service map, so check their OHV status.

### Area 3 — Ford Creek · 4 waypoints · 1,709 ac within 3 mi · drains S

**Why it scores:**
- F3-02: "Feed on a southeast-facing knob at 10,301 ft, 32% canopy, 20% slope; 0.7 mi from the nearest motorized route, 0.31 mi to water. Photos (2021-11-16): open grass between timber stringers."
- F3-01: "Feed on a southeast-facing knob at 10,136 ft, 36% canopy, 30% slope; 1.6 mi from the nearest motorized route, 0.16 mi to Baxter Creek. Photos (2025-05-11): open grass with scattered young conifers."

**Timber:** no BED points. This is the feed near Baxter Creek, south of T04 and T06 (1,709 acres within 3 mi).

**Access:** F3-02 is 0.7 mi off FR 880.2A Phantom Cr; F3-01, F3-03 and W3-01 are 1.4–1.6 mi off FR 880.2A Phantom Creek. All of them sit **below** the nearest legal road end, so the packout climbs.

**Wind:** gray-light air drains S. Glass the F3 openings from below at first light, then work up the timber stringers as the air lifts.

**Packout from F3-02:** 1.3 mi and 262 ft up to the FR 880 Findley Gulch road end: 2–3 loads each with your partner, about 5–8 round-trip miles apiece (solo it would be 10–13). If you park along FR 880.2A Phantom Cr instead, it's 0.7 mi to the nearest stretch of it.

### Area 4 — Cottonwood Creek–Kerber Creek · 9 waypoints · 4,844 ac within 3 mi · drains SSE

**Why it scores:**
- F4-02: "Feed on a southeast-facing knob at 9,548 ft, 27% canopy, 30% slope; 0.5 mi from the nearest motorized route, 0.20 mi to Little Kerber Creek. Photos (2018-11-09): open grassy slope, timber to the north."
- F4-01: "Feed on a southeast-facing knob at 9,772 ft, 32% canopy, 22% slope; 0.8 mi from the nearest motorized route, 0.25 mi to Cottonwood Creek, 0.4 mi to security timber T22 (125 ac). Photos (2025-05-11): open grass park between conifer stands (satellite cloudy; Google Earth Aug 2025)."

**Timber:**
- T06 (live, with scattered dead crowns in the 2023 image) sits below G4-04 and G4-05.
- T22 (live, moderately dense) is 0.4 mi from F4-01, and T26 (dense live conifer) is under G4-01–G4-03.

**Access:**
- F4-02 is 0.5 mi off FR 857 Little Kerber, and F4-01 is 1.3 mi off FR 873 Kelly.
- G4-05 is 0.4 mi off FR 880 Findley Gulch, and G4-04 is 0.4 mi off FR 880.2B Antora Meadows.
- The G4 knobs are 11,763–12,739 ft and had snow on Nov 6, so use them only if those roads are passable.

**Wind:** air drains SSE. Glass F4-02 and F4-01 from the low side at gray light, work T22 or T06 from above once thermals lift, and sit the feed at dusk.

**Packout from F4-01:** 1.3 mi and 719 ft down to the FR 873 Kelly road end: 2–3 loads each with your partner, about 5–8 round-trip miles apiece (solo it would be 10–13).

### Area 5 — Trough Creek–Saguache Creek · 7 waypoints · 121 ac of live timber within 3 mi · drains ENE

**Why it scores:**
- F5-01: "Feed on an east-facing slope at 10,488 ft, 37% canopy, 25% slope; 1.2 mi from the nearest motorized route, 0.21 mi to Bear Creek. Photos (2025-04-09): open meadow and shrub park between timber; snow on north slopes in the April image."

This is the road-end country: five ACCESS points (A5-01–A5-05) and little live security timber. The photos dropped T08 and T21, which leaves T23, live patches inside gray timber. It's a backup, not a timber area.

- F5-01 is 1.2 mi off FR 675 South Carnero.
- S5-01 is 1.5 mi off FR 744 Middle Fork Saguache.

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

**Day 1 — Wed Nov 18 (opener): Middle Creek, Area 1.** Forecast 18–34°F, W wind to 17 mph, 0.012 in of precipitation.
- **Gray light:** F1-01, an open meadow against a dense timber edge (1.1 mi from the FR 856.1A Bull Bear road end, 6 ft below it). Glass it from its low, south side, along with T05's edges 0.7 mi north-northwest.
- **Mid-morning:** the W wind blows down T05, so coming from above puts your scent on the beds. Come at B1-01 (dense live conifer) from the east, sidehilling along its slope with the wind in your face. Get to its level east of it before you turn in, whether you walk over from F1-01 (1.65 mi) or climb from A1-01 (1.2 mi, 1,381 ft). If the wind dies, come from above on the rising air.
- **Evening:** F1-01 from its southeast corner, below and downwind of the meadow, or below B1-02 (0.5 mi from the FR 870 Middle Cr road end, 770 ft above it). The sinking air and the W wind both carry your scent away from the timber there.
- **Skip F1-02:** thin timber, not a meadow.

**Day 2 — Thu Nov 19: Carnero north, Area 2.** Forecast 18–34°F, SSE wind to 22 mph, dry.
- **Gray light:** F2-01, a meadow tip against dense timber (0.6 mi off FR 619 Lake Mtn).
- **Mid-morning:** the SSE wind blows down over T12's north-facing beds, so don't come from above. Come in from FR 709 on the block's northwest side and sidehill east along the slope toward B2-03, then B2-02 (0.9 mi from the FR 709 Antelope road end, 563 ft above it), with the wind quartering into your face. A 22 mph wind swirls on this lee side of the ridge, so check it with a puffer and give the beds room.
- **Evening:** F2-01 from its low, northwest side. The sinking air and the SSE wind both carry your scent off the meadow there. Skip the meadow 200 m southwest of B2-03 tonight: it sits about 170 ft above the beds, and the sinking air would carry your scent down into them.

**Day 3 — Fri Nov 20: front with snow, Kerber side, Area 4.** Forecast 13–28°F, WNW wind to 19 mph, 0.331 in of snow.
- **First light:** look for fresh tracks on the low feed: F4-02 (0.5 mi off FR 857 Little Kerber) and F4-01 (1.3 mi off FR 873 Kelly). The other low feed is F2-03 at 8,698 ft on Spring Gulch State Trust Land and F2-02 at 9,279 ft on BLM land, if the tracks point there.
- **Mid-morning:** come at T22 from F4-01's side. Drop through the drainage between them and still-hunt in from the northeast with the WNW wind on your right. Don't come in from FR 888 to the northwest: the wind carries your scent from there into the block. Fresh snow shows where elk crossed between the feed and the timber.
- **Evening:** F4-01 from its low, southeast side.

**Day 4 — Sat Nov 21: behind the front, Middle Creek from the south.** Forecast 12–36°F, NNW wind to 8 mph, dry. Cold and calm: the best glassing day.
- **Gray light:** glass from F3-02 (0.7 mi off FR 880.2A Phantom Cr), or from G4-05 over T06 (0.4 mi off FR 880 Findley Gulch) if FR 880 is passable.
- **Mid-morning:** still-hunt T04, dense live conifer with small parks, from above. The light NNW wind and the rising air both blow uphill there. Come down from FR 880.2B Antora Meadows, 0.7 mi away and about 860 ft above the block. There the road runs near 11,700 ft, above the Nov 6 snow line. If it isn't passable, don't come at T04 from below, where the rising air would carry your scent up into it.
- **Evening:** F3-02 or F3-03.

**Day 5 — Sun Nov 22: back to whatever showed elk.** Forecast 20–32°F, NE wind to 7 mph, dry.
- Return to whichever block or area showed elk.
- **If nothing showed,** run Carnero south: B2-06, inside dense live conifer in T17 (0.9 mi from the FR 690.2A Storm King Cg road end, 1,016 ft above it). The light NE wind and the rising air both blow uphill there, so come from above. Sit the S2-01 saddle at T18 for the evening.

## 10. Waypoint index

| waypoint | type | area | lat | lon | elev ft | land | note |
|---|---|---|---|---|---|---|---|
| A1-01 TH 8892 | ACCESS | 1 Middle Creek | 38.27984 | -106.30139 | 8,892 | USFS | Access point at 8,892 ft, 25% canopy, 25% slope; 0.0 mi from the nearest motorized route, 0.04 mi to Middle Creek, 0.5 mi to security timber T05 (835 ac). Photos (2021-11-16): road end in the Middle Creek bottom; a track continues north (check the MVUM before driving it). |
| B1-01 N-timber 10273 | BED | 1 Middle Creek | 38.27959 | -106.32368 | 10,273 | USFS | North-facing valley at 10,273 ft, 54% canopy, 36% slope; 1.2 mi from the nearest motorized route, 1.12 mi to water, inside security timber T05 (835 ac). Photos (2021-11-16): inside dense live conifer (block T05). |
| B1-02 NE-bench 9662 | BED | 1 Middle Creek | 38.28000 | -106.31134 | 9,662 | USFS | Northeast-facing bench at 9,662 ft, 52% canopy, 29% slope; 0.5 mi from the nearest motorized route, 0.45 mi to water, inside security timber T05 (835 ac). Photos (2021-11-16): edge of the T05 timber, live conifer of moderate density. |
| F1-01 meadow 10019 | FEED | 1 Middle Creek | 38.25626 | -106.33011 | 10,019 | USFS | Feed on a southeast-facing bench at 10,019 ft, 40% canopy, 21% slope; 1.1 mi from the nearest motorized route, 0.28 mi to water, 0.7 mi to security timber T05 (835 ac). Photos (2021-11-16): open meadow against a dense timber edge. |
| F1-02 meadow 10229 | FEED | 1 Middle Creek | 38.25990 | -106.34286 | 10,229 | USFS | Feed on a southeast-facing knob at 10,229 ft, 34% canopy, 28% slope; 0.7 mi from the nearest motorized route, 0.20 mi to water, 0.5 mi to security timber T05 (835 ac). Photos (2018-11-09): weak feed: thin timber, not a meadow; small opening 100 m southeast (NAIP 2019). |
| B2-01 NE-timber 10175 | BED | 2 Mill Creek | 38.02607 | -106.31637 | 10,175 | USFS | Northeast-facing valley at 10,175 ft, 47% canopy, 22% slope; 0.8 mi from the nearest motorized route, 0.70 mi to water, inside security timber T07 (441 ac). Photos (2018-11-09): inside live conifer (T07) with some dead crowns; opening 150 m west. |
| B2-02 NE-timber 10250 | BED | 2 Mill Creek | 38.03866 | -106.35009 | 10,250 | USFS | Northeast-facing slope at 10,250 ft, 46% canopy, 38% slope; 0.8 mi from the nearest motorized route, 1.19 mi to Mill Creek, inside security timber T12 (207 ac). Photos (2018-11-09): inside dense live conifer (T12); small park just northeast. |
| B2-03 N-timber 10600 | BED | 2 Mill Creek | 38.03883 | -106.35898 | 10,600 | USFS | North-facing knob at 10,600 ft, 44% canopy, 37% slope; 1.0 mi from the nearest motorized route, 1.24 mi to water, inside security timber T12 (207 ac). Photos (2018-11-09): inside dense live conifer; meadow 200 m southwest. |
| B2-04 N-timber 10576 | BED | 2 Mill Creek | 38.02616 | -106.30782 | 10,576 | USFS | North-facing knob at 10,576 ft, 53% canopy, 25% slope; 1.2 mi from the nearest motorized route, 1.16 mi to water, inside security timber T07 (441 ac). Photos (2018-11-09): dense conifer edge (T07); open slope and aspen to the west. |
| B2-05 NE-timber 9980 | BED | 2 Mill Creek | 38.03880 | -106.33847 | 9,980 | USFS | Northeast-facing knob at 9,980 ft, 50% canopy, 25% slope; 0.6 mi from the nearest motorized route, 0.59 mi to Mill Creek, inside security timber T12 (207 ac). Photos (2018-11-09): live conifer of moderate density; openings and aspen to the south. |
| B2-06 N-bench 10396 | BED | 2 Mill Creek | 37.95327 | -106.41511 | 10,396 | USFS | North-facing bench at 10,396 ft, 49% canopy, 38% slope; 0.9 mi from the nearest motorized route, 0.96 mi to Middle Fork Carnero Creek, inside security timber T17 (172 ac). Photos (2023-11-08): inside dense live conifer (T17). |
| F2-01 meadow 10450 | FEED | 2 Mill Creek | 38.01868 | -106.39450 | 10,450 | USFS | Feed on a southeast-facing knob at 10,450 ft, 51% canopy, 16% slope; 0.6 mi from the nearest motorized route, 0.13 mi to water. Photos (2023-11-08): tip of an open meadow (small pond) against dense timber. |
| F2-02 meadow 9279 | FEED | 2 Mill Creek | 38.16468 | -106.22468 | 9,279 | BLM | Feed on a southeast-facing knob at 9,279 ft, 27% canopy, 21% slope; 0.5 mi from the nearest motorized route, 0.21 mi to water. Photos (2025-07-03): open park, grass between scattered trees. |
| F2-03 meadow 8698 | FEED | 2 Mill Creek | 38.10518 | -106.37287 | 8,698 | Spring Gulch STL | Feed on an east-facing slope at 8,698 ft, 35% canopy, 18% slope; 0.5 mi from the nearest motorized route, 0.11 mi to water. Photos (2023-11-10): open meadow against a timber stringer. |
| G2-01 glass 10369 | GLASS | 2 Mill Creek | 37.90474 | -106.33399 | 10,369 | Burro Springs STL | Glassing knob at 10,369 ft, 34% canopy, 15% slope; 0.3 mi from the nearest motorized route, 2.52 mi to Carnero Creek, 1.4 mi to security timber T10 (250 ac). Photos (2017-10-30): at a timber edge, so the view may be blocked; open slope just south. |
| S2-01 saddle 9597 | SADDLE | 2 Mill Creek | 37.93277 | -106.43384 | 9,597 | USFS | Travel saddle at 9,597 ft, 22% canopy, 29% slope; 0.5 mi from the nearest motorized route, 0.24 mi to water, 0.7 mi to security timber T18 (142 ac). Photos (2021-11-14): open saddle; timber edge to the north. |
| S2-02 saddle 9341 | SADDLE | 2 Mill Creek | 38.00053 | -106.25372 | 9,341 | BLM | Travel saddle at 9,341 ft, 25% canopy, 41% slope; 0.6 mi from the nearest motorized route, 0.96 mi to water. Photos (2018-11-09): open ground with scattered trees. |
| S2-03 saddle 9342 | SADDLE | 2 Mill Creek | 38.08397 | -106.26336 | 9,342 | USFS | Travel saddle at 9,342 ft, 24% canopy, 24% slope; 1.6 mi from the nearest motorized route, 1.14 mi to water. Photos (2025-07-03): mixed open ground and timber. |
| S2-04 saddle 9115 | SADDLE | 2 Mill Creek | 37.87139 | -106.34260 | 9,115 | Burro Springs STL | Travel saddle at 9,115 ft, 23% canopy, 39% slope; 0.5 mi from the nearest motorized route, 0.57 mi to Carnero Creek. Photos (2017-10-30): open ground with scattered trees and rock outcrops. |
| W2-01 creek 9600 | WATER | 2 Mill Creek | 38.25376 | -106.49292 | 9,600 | USFS | Water hole at 9,600 ft, 43% canopy, 20% slope; 0.5 mi from the nearest motorized route, 0.15 mi to Sheep Creek. Photos (2023-11-10): inside dense conifer; creek bottom 150 m northeast, meadow 300 m south. |
| F3-01 meadow 10136 | FEED | 3 Ford Creek | 38.25901 | -106.25267 | 10,136 | USFS | Feed on a southeast-facing knob at 10,136 ft, 36% canopy, 30% slope; 1.6 mi from the nearest motorized route, 0.16 mi to Baxter Creek. Photos (2025-05-11): open grass with scattered young conifers. |
| F3-02 meadow 10301 | FEED | 3 Ford Creek | 38.25917 | -106.23724 | 10,301 | USFS | Feed on a southeast-facing knob at 10,301 ft, 32% canopy, 20% slope; 0.7 mi from the nearest motorized route, 0.31 mi to water. Photos (2021-11-16): open grass between timber stringers. |
| F3-03 meadow 10018 | FEED | 3 Ford Creek | 38.25149 | -106.24774 | 10,018 | USFS | Feed on a southeast-facing bench at 10,018 ft, 27% canopy, 29% slope; 1.4 mi from the nearest motorized route, 0.31 mi to Baxter Creek. Photos (2025-05-11): open grass at a timber edge (timber to the west). |
| W3-01 creek 10104 | WATER | 3 Ford Creek | 38.25581 | -106.24850 | 10,104 | USFS | Water hole at 10,104 ft, 42% canopy, 29% slope; 1.4 mi from the nearest motorized route, 0.13 mi to Baxter Creek. Photos (2025-05-11): moderately dense conifer by a drainage. |
| F4-01 meadow 9772 | FEED | 4 Cottonwood Creek-Kerber Creek | 38.26461 | -106.06862 | 9,772 | USFS | Feed on a southeast-facing knob at 9,772 ft, 32% canopy, 22% slope; 0.8 mi from the nearest motorized route, 0.25 mi to Cottonwood Creek, 0.4 mi to security timber T22 (125 ac). Photos (2025-05-11): open grass park between conifer stands (satellite cloudy; Google Earth Aug 2025). |
| F4-02 meadow 9548 | FEED | 4 Cottonwood Creek-Kerber Creek | 38.19884 | -106.13446 | 9,548 | USFS | Feed on a southeast-facing knob at 9,548 ft, 27% canopy, 30% slope; 0.5 mi from the nearest motorized route, 0.20 mi to Little Kerber Creek. Photos (2018-11-09): open grassy slope, timber to the north. |
| G4-01 glass 11974 | GLASS | 4 Cottonwood Creek-Kerber Creek | 38.28841 | -106.09710 | 11,974 | USFS | Glassing knob at 11,974 ft, 17% canopy, 19% slope; 1.5 mi from the nearest motorized route, 0.41 mi to water, snow on the ground (2026-11-06), 0.3 mi to security timber T26 (113 ac). Photos (2019-06-29): timberline with scattered trees; check the view. |
| G4-02 glass 12011 | GLASS | 4 Cottonwood Creek-Kerber Creek | 38.29732 | -106.09826 | 12,011 | USFS | Glassing knob at 12,011 ft, 11% canopy, 18% slope; 1.3 mi from the nearest motorized route, 0.49 mi to Kelly Creek, snow on the ground (2026-11-06), 0.5 mi to security timber T26 (113 ac). Photos (2019-06-29): open alpine slope. |
| G4-03 glass 11763 | GLASS | 4 Cottonwood Creek-Kerber Creek | 38.30875 | -106.09020 | 11,763 | USFS | Glassing knob at 11,763 ft, 35% slope; 0.9 mi from the nearest motorized route, 0.38 mi to Kelly Creek, snow on the ground (2026-11-06), 1.0 mi to security timber T26 (113 ac). Photos (2019-06-29): open alpine meadow ringed by timber. |
| G4-04 glass 12739 | GLASS | 4 Cottonwood Creek-Kerber Creek | 38.31077 | -106.21478 | 12,739 | USFS | Glassing knob at 12,739 ft, 7% slope; 0.3 mi from the nearest motorized route, 0.35 mi to Antora Creek, snow on the ground (2026-11-06), 0.5 mi to security timber T06 (802 ac). Photos (2021-11-16): open alpine summit. |
| G4-05 glass 12059 | GLASS | 4 Cottonwood Creek-Kerber Creek | 38.27524 | -106.19979 | 12,059 | USFS | Glassing knob at 12,059 ft, 13% slope; 0.4 mi from the nearest motorized route, 0.74 mi to Flagstaff Creek, snow on the ground (2026-11-06), 0.5 mi to security timber T06 (802 ac). Photos (2021-11-16): open alpine slope. |
| G4-06 glass 12059 | GLASS | 4 Cottonwood Creek-Kerber Creek | 38.27457 | -106.10306 | 12,059 | USFS | Glassing knob at 12,059 ft, 30% slope; 0.6 mi from the nearest motorized route, 0.68 mi to Cottonwood Creek, snow on the ground (2026-11-06), 1.0 mi to security timber T26 (113 ac). Photos (2019-06-29): open talus summit. |
| S4-01 saddle 9402 | SADDLE | 4 Cottonwood Creek-Kerber Creek | 38.24338 | -106.05425 | 9,402 | USFS | Travel saddle at 9,402 ft, 27% canopy, 35% slope; 0.8 mi from the nearest motorized route, 0.71 mi to Cottonwood Creek, 1.1 mi to security timber T22 (125 ac). Photos (2025-05-11): scattered timber. |
| A5-01 TH 10619 | ACCESS | 5 Trough Creek-Saguache Creek | 38.04908 | -106.63679 | 10,619 | USFS | Access point at 10,619 ft, 33% canopy, 2% slope; 0.0 mi from the nearest motorized route, 0.80 mi to Saguache Creek. Photos (2023-11-10): road end at a meadow edge in timber; a two-track continues. |
| A5-02 TH 9303 | ACCESS | 5 Trough Creek-Saguache Creek | 38.05152 | -106.57701 | 9,303 | USFS | Access point at 9,303 ft, 5% slope; 0.0 mi from the nearest motorized route, 0.29 mi to Saguache Creek. Photos (2023-11-10): road end in a meadow between timber stands. |
| A5-03 TH 9016 | ACCESS | 5 Trough Creek-Saguache Creek | 38.13231 | -106.51885 | 9,016 | USFS | Access point at 9,016 ft, 11% canopy, 13% slope; 0.0 mi from the nearest motorized route, 0.43 mi to Luders Creek. Photos (2025-07-26): road end in open sage with scattered trees. |
| A5-04 TH 10206 | ACCESS | 5 Trough Creek-Saguache Creek | 38.03688 | -106.71514 | 10,206 | USFS | Access point at 10,206 ft, 6% canopy, 18% slope; 0.0 mi from the nearest motorized route, 0.68 mi to water. Photos (2023-11-10): road end at a meadow edge against timber. |
| A5-05 TH 9318 | ACCESS | 5 Trough Creek-Saguache Creek | 38.05100 | -106.61495 | 9,318 | USFS | Access point at 9,318 ft, 11% slope; 0.0 mi from the nearest motorized route, 0.30 mi to Saguache Creek. Photos (2023-11-10): road end at a drainage, open ground. |
| F5-01 meadow 10488 | FEED | 5 Trough Creek-Saguache Creek | 37.97219 | -106.64465 | 10,488 | USFS | Feed on an east-facing slope at 10,488 ft, 37% canopy, 25% slope; 1.2 mi from the nearest motorized route, 0.21 mi to Bear Creek. Photos (2025-04-09): open meadow and shrub park between timber; snow on north slopes in the April image. |
| S5-01 saddle 10946 | SADDLE | 5 Trough Creek-Saguache Creek | 37.98336 | -106.76889 | 10,946 | USFS | Travel saddle at 10,946 ft, 35% canopy, 17% slope; 1.3 mi from the nearest motorized route, 0.21 mi to Lake Fork, snow on the ground (2026-11-06). Photos (2025-04-09): open saddle at a timber edge. |

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
