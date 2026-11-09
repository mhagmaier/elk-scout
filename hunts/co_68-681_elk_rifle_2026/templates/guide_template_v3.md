# GMU 68 + 681 Bull Elk Hunt — Nov 18–22, 2026 (5 days)

**Colorado GMUs 68 and 681** (CPW elk herd E-26, Saguache) · bull elk · rifle · day hunts from a base, side-by-side for access · hunt days Wed Nov 18 – Sun Nov 22, 2026 · elkscout pipeline run Sun Nov 8, 2026 on live data (not a demo) · imagery check Mon Nov 9, 2026.

**Revision 3 — imagery check.** This replaces the first two packages.
- **Revision 2** moved bedding into north-facing dark timber and mapped the security timber blocks (section 4, and `elkscout_unit68-681_timber_blocks.kml` for OnX).
- **Revision 3** checks every timber block and all 40 waypoints on satellite and color-infrared aerial photos (section 5; the photos are in `imagery_check.pdf`):
  - The Middle Creek blocks the plan leans on (T01, T04, T05, T12) are dense live conifer.
  - T09 and T10 are mostly dead timber. Neither is in the plan.
  - B3-01, B3-02 and B4-01 are poor bedding cover. The day plan now works around them.
- Waypoint names match revision 2, but every note now ends with what the photos show. Delete earlier imports before loading these (section 10).

**Standing disclaimers:**
- **Fair chase.** These are scouting points, not elk. Boots, glass, wind and judgment decide the hunt.
- **Land status.** Ownership layers have gaps; confirm access on OnX and with the agency. Fences don't read GeoJSON. Unenrolled State Trust Land and local-government land are treated as closed here; CPW-enrolled State Trust Land is open under each property's own rules (section 2).
- **Regulations.** Verify everything with Colorado Parks and Wildlife (CPW) before hunting: season, hunt code, valid units, property rules.

## 1. Conditions

**Snow (NRCS SNOTEL, as of {{SNOW_ASOF}}):** median depth **{{SNOW_MEDIAN}} in** over {{SNOW_N}} stations, so the model pulled its elevation band down **{{SNOW_SHIFT}} ft**. Full elevation score now runs about **{{BAND_LO}}–{{BAND_HI}} ft** (ramping to zero at {{BAND_ZERO_LO}} and {{BAND_ZERO_HI}} ft).

{{SNOW_TABLE}}

**Forecast (Open-Meteo, fetched {{SNOW_ASOF}}, hunt days only):**

{{FORECAST_TABLE}}

**What it means.** Snow is patchy and high: bare at Cochetopa Pass (10,020 ft) and Moon Pass (11,110 ft), 20–22 in at Middle Creek (11,260 ft) and Rat Creek (11,680 ft). Elk haven't been pushed out of the timber. Expect them bedded in dark timber and feeding in the openings next to it at first and last light. That's why the plan beds them in timber.

The forecast is mild and mostly dry, with a trace of precipitation Nov 21–22. It was pulled 10–14 days out, so have the pipeline re-run two or three days before you leave to refresh snow and weather.

## 2. Regulations check

| item | what CPW / the source says | your plan | status |
|---|---|---|---|
| 2026 fourth rifle season | Nov 18–22 ([CPW 2026 Big Game Brochure](https://spl.cde.state.co.us/artemis/nrserials/nr1431internet/nr14312026internet.pdf)) | Nov 18–22 | **match** |
| Hunt code / valid units | Not confirmed: the brochure's elk hunt-code tables didn't extract | 68 + 681 | **verify your license lists both 68 and 681** |
| Hunter orange or pink | Firearm big-game hunters must wear fluorescent orange or pink; camo orange/pink doesn't count ([Kiowa County Press, CPW 2026 rules](https://kiowacountypress.net/content/colorado-hunting-seasons-open-new-regulations-2026)) | — | comply |
| Side-by-side | Nonresident OHVs need a Colorado OHV permit ($26.25) displayed on the vehicle on public-land roads and designated trails; buying online gives a 45-day temporary authorization number ([CPW](https://cpw.state.co.us/register-off-highway-vehicle)) | RZR | **buy before you go** |
| Forest Service roads | Every ACCESS point and every FR-numbered route named below is on the USFS Motor Vehicle Use Map as open to OHVs over 50 in on all five hunt days (USFS EDW MVUM) | 64-in RZR | verify on the current MVUM |
| CWD sampling | Some elk rifle GMUs require CWD samples; list is on brochure p. 41, which didn't extract | — | **check p. 41** |
| Burro Springs STL (G2-01) | Open May 1 – end of Feb; motorized only on designated roads; **OHVs may not be used to retrieve big game**; camping and fires prohibited; access 1.5 hr before sunrise to 1.5 hr after sunset in big-game season ([CPW](https://cpw.state.co.us/state-trust-lands/burro-springs)) | — | comply |
| Spring Gulch STL (F2-01) | Open Sept 1 – end of Feb; elk listed; drive USFS Rd 708, park at the old road, walk N 0.6 mi to the boundary ([CPW](https://cpw.state.co.us/state-trust-lands/spring-gulch)) | — | comply |

**Herd context (E-26, [CPW herd plan adjustment, 2026](https://cpw.state.co.us/sites/default/files/dam/sftwgsxane/item.20.17_consent_e26_hmpadjustment_2026.pdf)):** GMUs 68 + 681 cover about 1,047 sq mi, about 88% public. The 2024 post-hunt estimate was 5,500 elk. CPW's previous 5- and 3-year observed averages were about 15 bulls per 100 cows (14 observed in 2021; 18 averaged since 1987). It has been an over-the-counter bull unit since 1987, so your season follows the OTC second and third rifle seasons, and CPW lists overcrowding as a concern. Winter range covers about 601 sq mi.

Verify season dates, your hunt code's valid units and every property rule with CPW before hunting.

## 3. The model

Late-season rifle, day hunts (`elk-late-rifle-day`), 30 m grid over both units.

| factor | weight |
|---|---|
{{WEIGHTS_ROWS}}

**Top adjustments:**
1. **Bedding in dark timber.** North-northeast-facing benches in the densest conifer this unit has. Full canopy score starts at 45%: the template's 60% dark-timber threshold dropped 15 points, because NLCD canopy reads low here (conifer median 38%, highest pixel anywhere 74%). This replaces the late-season default of sunny south-slope thermal bedding, which assumes snow has pushed elk out of the timber; it hasn't.
2. **Late phase:** feed ×1.4, water ×0.5, elevation ×1.15. **Day style:** security peaks 0.5–1.6 mi from motorized routes and fades past 2.5 mi; no camp points.
3. **Colorado calibration** (set with your OK):
   - Elevation band up 3,000 ft, to a best band of 8,800–10,400 ft before the snow shift. That lines the Idaho template up with goHUNT's 9,000–11,000 ft range for [unit 681](https://gohunt.com/insider/units/colorado-big-game-unit-681); it's an informed estimate, not a CPW figure.
   - No doubled snow shift, because these SNOTEL sites sit at 10,000–11,700 ft.
   - UTM zone 13 grid, 40 waypoints, hunt areas grouped at 4+ waypoints.

The model beds elk on north and northeast benches in the heaviest conifer, at 37–52% canopy and 9,370–9,900 ft. It puts feed on southeast-facing shrub and grass openings near timber edges at 8,700–9,900 ft, half a mile to a mile and a half off roads.

By NLCD canopy, half the BED points sit in dense conifer (B1-01, B2-01, B2-02, B3-03) and the rest on timber edges (37–39% canopy). The photos (section 5) sharpen that:
- **In live conifer:** B1-01, B2-02 and B3-03.
- **On timber edges:** B2-01 (the live stand is right behind it) and B4-02 (a dense band starts 50–100 m north).
- **Poor bedding cover:** B3-01 (leafless aspen), B3-02 (a 10-acre timber island) and B4-01 (broken rock).

**Data notes, so you know what's under the points:**
- **OpenStreetMap** roads, trails and springs came through the VK Maps Overpass mirror, because the main Overpass servers refused this sandbox.
- **Land cover** is NLCD 2021 and **canopy** is NLCD 2021 tree canopy. The pipeline's automatic layer pick grabbed a change-count layer and a Hawaii canopy layer, so both were set by hand.
- **SNOTEL** came from a corrected station query.
- **Ownership:** unenrolled state and local land is masked out; CPW public-access properties are open.
- **ACCESS points** are road ends of Forest Service routes open to OHVs over 50 in on all five days, plus public trailheads.
- **Timber blocks** in section 4 are computed from the same NLCD rasters the model used.
- **Imagery:** Esri World Imagery satellite and USDA NAIP color-infrared, checked by eye (section 5).

## 4. Timber cover

**Method:** "dark timber" here is NLCD evergreen or mixed forest with NLCD tree canopy of 45% or more. That's the densest quarter of conifer in these units: conifer canopy quartiles are 27 / 37 / 44%.

**What's out there:**
- There are {{DARK_ACRES}} public acres of it, about 10% of the public ground, mostly between 9,600 and 11,000 ft.
- Only about a third of it is half a mile or more from a road.
- **Security timber** means a contiguous block of at least 100 acres on public land, at least 0.5 mi from any mapped motorized route. There are {{N_BLOCKS}} blocks; the table below lists all of them, and `elkscout_unit68-681_timber_blocks.kml` has the outlines for OnX.

**Middle Creek holds the timber.**
- **T01, 1,386 ac:** the most secure big block in either unit, with a median of 1.6 mi and up to 2.4 mi from any road. On the photos it's also the best: uniformly dense live conifer.
- **Around it:** T03 (1,142 ac), T05 (799 ac) and T04 (816 ac, 56% north-facing, between Middle and Ford creeks), plus T12, T13 and T18. All are dense live conifer on the photos except T03, which is live but moderately dense.
- That's about 4,600 acres of security timber within a few miles of the FR 870 road end, A3-01.
- **Carnero** has several smaller blocks, mostly north-facing (T15, T16, T19, T20), all live and moderately dense on the photos. **Luders Creek** has none within 5 mi of its hunting points.

**Checked on photos.** NLCD is 30 m data from 2021, so every block was also checked on satellite and color-infrared imagery (section 5; the verdicts are in the table's last column). Two don't hold up: T09 and T10 are mostly standing dead timber that NLCD still maps as dense conifer. T07, T08 and T17 have dead crowns mixed in. None of those five is in the day plan.

{{TIMBER_TABLE}}

**How the plan uses timber:**
- **Gray light and last light:** glass the openings and feed points that touch these blocks.
- **Once the thermals lift:** still-hunt the downhill edges of the block from above.
- **When the air falls at dusk:** sit the edge on the low side.
- **If a block gets pushed:** move to the next block over, not into the open.

## 5. Imagery check

Revisions 1 and 2 came straight out of the GIS model; nobody had looked at the ground. This revision does: every timber block and all 40 waypoints were checked by eye, and the pages are in `imagery_check.pdf`.

**Sources:**
- **Satellite, natural color:** Esri World Imagery (Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community), 0.31–0.5 m per pixel. The capture date changes from spot to spot, anywhere from {{SAT_RANGE}}. {{N_NOV}} of the 21 block close-ups were shot in November, the same time of year as your hunt.
- **Color-infrared:** USDA NAIP via USGS The National Map, 0.6 m, flown Sept 9–22, 2019. Live conifer shows dark red, aspen and willow bright pink-red (still in leaf in September), and dead trees gray-green. That's the clearest way to tell live timber from beetle kill.
- **Not OnX or Google Earth.** OnX has no public API, so its imagery can't be pulled from here, and Google Earth isn't available in this workspace. Either may have newer imagery than these dates.

**What photos can't show:** anything after the capture date (beetle kill, blowdown, logging or fire since then), what's under the canopy, and fences or gates.

**How it was checked:**
- Each block got an overview, then a 700 m close-up of its core, side by side in satellite and color-infrared.
- Each waypoint got a 700 m square on satellite, and the eight bed points got a second look in color-infrared.
- Overlays: block outlines in yellow, OpenStreetMap motorized routes in red, waypoints colored by type.

**Timber blocks:**
- **Dense live conifer:**
  - T01, the best block, uniformly dark red in color-infrared.
  - T02 (its satellite image is cloudy, but color-infrared is clear).
  - T04, with small parks inside.
  - T05, fine-textured (probably lodgepole), with aspen pockets.
  - T11, dense young even-aged regrowth, with roads and cuts at its edges.
  - T12, which holds B3-03.
  - T13, with aspen on its east edge.
  - T14, with aspen and willow in the creek bottom.
  - T18, a dense core.
- **Live, moderately dense:** T03, T06, T15 (borders a meadow), T16 (open parks around it), T19 and T20 (between two meadows).
- **Live with dead mixed in:** T07 and T08 have some dead crowns; T17 is a mix of live and dead.
- **Mostly dead:** T09 and T10 are gray in color-infrared, probably beetle kill. NLCD 2021 still maps them as dense conifer, but they aren't dark timber. Neither is in a hunt area or the day plan.
- **T21** is a live pocket inside dead timber.

{{BLOCK_DATES}}

**Bed points:**

{{BED_TABLE}}

**Everything else:**
- **Feed:** every FEED point is a real opening: grass, sage or alpine meadow. The ones against cover make the best evening sits:
  - F4-02, a meadow edge against dense timber.
  - F5-04, an open slope beside a dense conifer stringer.
  - F2-01, a meadow at a timber edge.
- **Glass:** G5-02, G5-04, G5-05 and G5-06 are open alpine summits and slopes. G5-03 is an alpine meadow ringed by timber and G5-01 is at timberline with scattered trees, so check their views. G2-01 is at a timber edge, so its view may be blocked; there's open slope just south.
- **Saddles** are open or scattered timber; S1-02 and S2-02 mix meadow and timber.
- **Water:** W2-01 is inside dense timber with the creek along its north edge. W5-01 is moderately dense conifer with a meadow to the NW.
- **Access:**
  - A3-01 is the road end in the Middle Creek bottom. A track continues north, so check the MVUM before driving past it.
  - A4-04 is the Stone Cellar campground loop.
  - A5-01, the end of FR 874, is in open timber.

Each waypoint's note in the GPX and KML files and in `waypoints.xlsx` ends with its imagery line and satellite date. Each timber block's note has its verdict and both photo dates.

## 6. Hunt areas, ranked

"Drains toward" is the overall downhill direction from a plane fit to the elevation model. Morning down-slope and evening air flows that way; mid-day thermals run the opposite way.

### Area 1 — Cold Spring–Saguache Creek (GMUs 68 + 681) · 5 waypoints · mean score 0.911 · drains SE

**Why it scores:**
- B1-01: "{{EV_B1-01}}"
- F1-02: "{{EV_F1-02}}"
- S1-02: "{{EV_S1-02}}"

**Timber:** B1-01 sits in dense conifer (45%) on a north slope. On the photos it's a band of live conifer of moderate density with openings on both sides. The patch around it is too small, or too close to a road, to be a security block; the nearest block, T07 (400 ac, 72% north-facing, live with some dead crowns), is 3 mi away.

**Access:** FR 706.3A Paradise (open to OHVs over 50 in, 05/16–03/14) is 0.9 mi from F1-02, 1.1 mi from B1-01 and 2.2 mi from S1-02. F1-01 and S1-01 (GMU 681, BLM) are a separate pair about 6 mi north, 0.5–0.6 mi off Poison–Dry Loop Road (the BLM 5275 segment; the FR 879 portion open to OHVs over 50 in is 1.6–1.8 mi away).

**Wind:** Gray-light air drains SE. Come in low and glass F1-02. When thermals lift NW, get above B1-01 and work down through the timber. At dusk, sit below F1-02.

**Packout:** 0.9–1.1 mi to FR 706.3A. Elk run 4–5 loads solo, so about 7–11 round-trip miles.

### Area 2 — North Fork Carnero Creek (GMU 68) · 9 waypoints · mean score 0.870 · drains E

**Why it scores:**
- B2-02: "{{EV_B2-02}}"
- B2-01: "{{EV_B2-01}}"
- W2-01: "{{EV_W2-01}}"

**Timber:** NLCD puts both beds in dense conifer (47–51%) on north-facing ground. On the photos:
- **B2-02** is live conifer of moderate density, with denser timber 100–150 m NW.
- **B2-01** is the edge of a live stand, with a meadow to its NW.
- **Security blocks**, all live and moderately dense: T20 (106 ac, between two meadows) is 1.4–1.9 mi from the beds; T15 (146 ac, 75% north-facing), T19 and T16 are nearby, with S2-02 within a mile of T16.

**Access:**
- **FR 620 Fullerton Park** (open to OHVs over 50 in) is 0.9 mi from B2-02 and 1.6 mi from B2-01.
- **North Carnero Road:** OpenStreetMap tags FR 680 0.5–0.6 mi from both beds. Check that segment's designation; the FR 680 segments open to your RZR are farther.
- **FR 41G Carnero** (open all year) is 0.5 mi from S2-02 and 0.6 mi from F2-01.
- **F2-01** is on Spring Gulch STL: walk in from Rd 708. **G2-01** is on Burro Springs STL: no OHV retrieval.
- **East-side BLM points:** F2-02 is 0.7 mi off Cottonwood Creek Road (BLM 5215), S2-03 is 0.6 mi off Red Rock Canyon Road, and S2-01 is 0.6 mi off CR P42. BLM and county roads aren't on the USFS map, so check their OHV status.

**Wind:** Air drains east. At gray light, stay low and east and glass the meadows on both sides of T20 and the one NW of B2-01. When thermals lift west and uphill, hunt down through the denser timber NW of B2-02 and the stand behind B2-01 from above. Evenings, sit the low (east) side of the timber edges.

**Packout:** 0.9–1.6 mi from the beds to FR 620: about 7–16 round-trip miles.

### Area 3 — Middle Creek (GMU 681) · 4 waypoints · mean score 0.851 · drains SSE

**Why it scores:**
- B3-03: "{{EV_B3-03}}"
- B3-01: "{{EV_B3-01}}"
- B3-02: "{{EV_B3-02}}"

**Timber:** This is the security timber in 68/681: T01, T03, T05 and T04, plus T12, T13 and T18 (section 4). The photos confirm it: all are dense live conifer except T03, which is live but moderately dense.
- **B3-03** sits inside T12, in dense dark timber.
- **B3-01**, 0.9 mi from T05, is a poor bed on the photos: the edge of an aspen clone that will be leafless. The cover there is the dense conifer about 250 m west of it.
- **B3-02** (BLM) is the west edge of a timber island of about 10 acres in open sage. It's left out of the plan.

**Access:** **A3-01**, the end of FR 870 Middle Creek (Middle Creek Road / CR 38F), on USFS land, open to OHVs over 50 in 05/16–03/14. A track continues north past it on the photos; check the MVUM before driving it.

| target | distance | climb |
|---|---|---|
| T05 edge | 0.5 mi off FR 870 | — |
| T01 edge | 0.6 mi off FR 870 | — |
| B3-01 (the cover is 250 m west) | 2.4 mi from A3-01 | +1,000 ft |
| B3-03 (inside T12) | 2.7 mi from A3-01 | +890 ft |

B3-02 (BLM) is 0.6 mi off FR 881 Wild Horse.

There's no FEED point in this area. The closest model feed is F5-04 (Area 5), 1.1 mi off FR 880.2A Phantom Creek and 2 mi from T04.

**Wind:** Gray-light air drains SSE down Middle Creek. Glass the openings along T05's edge from the low side. When thermals lift NNW, still-hunt T05 and T01 from above. Evenings, sit T05's lower edge.

**Packout:** Downhill to FR 870. From B3-01 or B3-03 it's 2.4–2.7 mi, so 4–5 loads is about 19–27 round-trip miles. From T05's edge it's 0.5 mi.

### Area 4 — Luders Creek (GMU 68) · 8 waypoints · mean score 0.741 · drains ESE

**Why it scores:**
- B4-02: "{{EV_B4-02}}"
- B4-01: "{{EV_B4-01}}"
- F4-02: "{{EV_F4-02}}"

**Timber:** NLCD has both beds on northeast-facing timber edges (37–38% canopy). The photos split them:
- **B4-02** is an edge, and the cover is the dense conifer band that starts 50–100 m north of it.
- **B4-01** is broken rock with scattered trees, so it's dropped from the plan.
- **F4-02** is a meadow edge against dense timber near Fourmile Creek.

No security block is within 5 mi; the nearest is T11 (203 ac, dense young regrowth with roads at its edges). Treat this as an edge-and-feed area, not a timber area.

**Access:** FR 740 Four Mile (open to OHVs over 50 in) is 0.6 mi from B4-02, 0.7 mi from B4-01, 1.1 mi from F4-02 and 1.4 mi from F4-01. The model's ACCESS road ends:
- A4-01, FR 761 Lost Spring
- A4-02, FR 750.2B Rabbit Canyon
- A4-03, FR 736 Duckfoot Creek
- A4-04, FR 787.3B1 Stone Cellar CG loop (open all year)

**Wind:** Gray-light air drains ESE. Glass F4-01 and F4-02 from the low side. When thermals lift, come down onto the dense band north of B4-02 from above. Evenings, sit F4-02 on Fourmile Creek.

**Packout:** 0.6–1.4 mi to FR 740: about 5–14 round-trip miles.

### Area 5 — Cottonwood Creek–Kerber Creek (GMU 681) · 14 waypoints · mean score 0.693 · drains ESE

**Why it scores:**
- F5-04: "{{EV_F5-04}}"
- W5-01: "{{EV_W5-01}}"
- F5-01: "{{EV_F5-01}}"

**Timber:**
- **West side (Ford Creek):** F5-04 and W5-01 (46% conifer) are 2 mi from T04, 816 ac and 56% north-facing. On the photos, F5-04 is an open slope right beside a dense conifer stringer, and W5-01 is moderately dense conifer with a meadow to its NW.
- **Under the G5 knobs:** T06 (607 ac, live and moderately dense) sits below G5-04 and G5-05. T14 (169 ac, 72% north-facing, dense live conifer with aspen and willow in the creek bottom) is within a mile of G5-05.

**Access:**
- **West:** F5-04 is 1.1 mi and W5-01 is 1.6 mi off FR 880.2A Phantom Creek. F5-03 (BLM) is 1.4 mi off FR 786 Ford Tie.
- **East:**
  - F5-01 is 0.5 mi off FR 857 Little Kerber.
  - F5-05 is 1.7 mi off FR 857. OpenStreetMap shows CR LL56 / FR 789 at 0.5 mi; check its designation.
  - F5-02 is 2.2 mi off FR 852.4A Studhorse Creek, or 0.8 mi off Werner Loop Road (BLM 5300).
  - S5-01 is 1.9 mi off FR 873 Kelly.
  - A5-01 is the end of FR 874 Peterson Creek, in open timber.
- **G5 glass knobs (11,763–12,739 ft):** G5-04 and G5-05 are 0.4 mi off FR 880.2B and FR 880 (both open 06/16–03/14), look down on T06, and are open alpine ground on the photos. Use them only if those roads are passable: Middle Creek and Rat Creek SNOTEL (11,260–11,680 ft) carried 20–22 in. The other knobs are 0.6–1.5 mi off FR 888, 892 and 875.

**Wind:** Air drains ESE. Glass the F5 openings from the low side at gray light, work the T04 and T06 timber edges from above once thermals lift, and sit the low side at dusk.

**Packout:** 0.5–2.2 mi to the nearest legal road, depending on the spot.

## 7. Wind and thermals

Thermals run the day:
- **Gray light until roughly two hours after sun hits the slope:** air pours downhill, toward each area's "drains toward" direction.
- **Mid-morning through afternoon:** it lifts and runs uphill.
- **Dusk:** it rolls back down.

Hunt timber from above once the air lifts, and edges from below in the evening. Prevailing flow swings SW ahead of fronts; the forecast shows WSW to SW on Nov 19–20 ahead of the light Nov 21–22 system.

With a rifle you'll do most of the killing off glass at first and last light, on the openings that touch timber. Thermals decide the mid-day still-hunt and whether a bedded bull is still there when you ease over the bench. If the wind is wrong for an area, go to the next block over: that's what the per-area GPX files and the timber KML are for.

## 8. Day-by-day

**Tue Nov 17 — travel (season closed).** In daylight, run FR 706.3A Paradise so the opener drive and parking are known. No GLASS point sits near a reachable road end, so there's no evening inventory sit. Gray light on Nov 18 is the first look.

**Day 1 — Wed Nov 18 (opener): Cold Spring–Saguache, Area 1.** Forecast 28–48°F, NW 6 mph max, dry.
- **Dawn:** off FR 706.3A, 0.9 mi to F1-02, an open slope beside timber; glass it and the timber edges around it.
- **Mid-morning:** when the air lifts, get above B1-01 (a band of live north-facing conifer, 1.1 mi off the road) and still-hunt down. It has openings on both sides to glass across as you go.
- **Evening:** F1-02 or the S1-02 saddle.

**Day 2 — Thu Nov 19: North Fork Carnero Creek, Area 2.** Forecast 30–52°F, WSW 9 mph max.
- **Dawn:** in on FR 620 Fullerton Park; glass the meadows on both sides of T20 and the one NW of B2-01.
- **Mid-morning:** still-hunt down through the denser timber NW of B2-02, then the stand behind B2-01.
- **Evening:** the low (east) edges, or F2-02 (BLM) on the east side.
- **Alternate:** S2-02 saddle, 0.5 mi off FR 41G, next to T16.

**Day 3 — Fri Nov 20: Middle Creek timber, Area 3.** Forecast 29–54°F, SW 6 mph max, ahead of the Nov 21 system.
- **Dawn:** from A3-01, 0.5–0.6 mi to the T05 and T01 edges; glass the openings along them.
- **Mid-morning:** with the air lifting, still-hunt T05 and T01 from above, toward B3-03 inside T12 (2.7 mi from A3-01). All three blocks are dense live conifer on the photos. Skip B3-01, an aspen edge that will be bare; if you're near it, the cover is the dense conifer about 250 m west.
- **Evening:** T05's lower edge, 0.5 mi off FR 870, for the shortest packout.

**Day 4 — Sat Nov 21: Luders Creek / Fourmile, Area 4.** Forecast 32–40°F, ESE 7 mph max, trace precipitation.
- **Dawn:** off FR 740 Four Mile; glass F4-01 and F4-02, 1.1–1.4 mi out.
- **Mid-morning:** come down onto the dense conifer band that starts 50–100 m north of B4-02, 0.6 mi off the road. Skip B4-01: on the photos it's broken rock with scattered trees.
- **Evening:** F4-02, a meadow edge against dense timber.
- **Weather pivot:** if the system brings snow, cut fresh tracks at first light on the lowest feed:
  - F2-01 (8,698 ft, Spring Gulch STL)
  - F2-02 (9,154 ft, BLM)
  - F4-02 (9,233 ft)
  - F1-01 (9,279 ft, BLM)
  - S2-01 saddle (8,535 ft, BLM)

**Day 5 — Sun Nov 22: back to whatever showed elk.** Forecast 31–44°F, NW 4 mph max, trace precipitation.
- Return to whichever area or timber block showed elk.
- **If nothing showed,** run Area 5 West:
  - **Dawn:** F5-04, 1.1 mi off FR 880.2A Phantom Creek, an open slope beside a dense conifer stringer.
  - **Mid-day:** the north-facing edges of T04.
  - **Dusk:** F5-04.

## 9. Waypoint index

{{WAYPOINT_INDEX}}

## 10. Import

- **OnX:** web map (webmap.onxmaps.com) → My Content → Import → select `elkscout_unit68-681_all.gpx` for all 40 points. A paid membership is required for imports.
- **Delete earlier imports first.** Revision 1 used different names, and revision 2 has these names with older notes, so importing on top leaves duplicates.
- **One area at a time:** import the per-area files instead:
  - `elkscout_unit68-681_cold-spring-saguache-creek.gpx`
  - `elkscout_unit68-681_north-fork-carnero-creek.gpx`
  - `elkscout_unit68-681_middle-creek.gpx`
  - `elkscout_unit68-681_luders-creek.gpx`
  - `elkscout_unit68-681_cottonwood-creek-kerber-creek.gpx`
- **Timber outlines:** import `elkscout_unit68-681_timber_blocks.kml` the same way. It holds 21 polygon outlines (T01–T21). Each note has acres, elevation, north-facing share, distance to roads, and the imagery verdict with both photo dates. T09 and T10 are labeled "(mostly dead)".
- **Waypoint names:** prefixed by type and area (`B2-01` = BED, area 2, #1). Each note carries the evidence sentence, then what the photos show and the satellite date.
- **The photos:** `imagery_check.pdf`.
- **Google Earth:** `elkscout_unit68-681.kml`.
- **Planning at the table:** `waypoints.xlsx`, now with an Imagery column.
- **Score heatmap with roads, burns and ownership:** `map.html`.

The satellite photos here run from 2017 to 2025 depending on the spot. Before you build a day around a block, flip through it on OnX's own imagery too, which may be newer, and check land status and the road you'll actually drive.
