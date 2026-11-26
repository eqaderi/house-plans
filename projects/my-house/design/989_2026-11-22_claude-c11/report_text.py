"""Plain-language text of index.html. Numbers in braces are filled in from the measured model."""

IDEA = [
    ("The same house as C10, now buildable.",
     "Your stair and lift core, your room sizes and your three levels stay. What changed is what 27 specialist reviewers found could not be built, "
     "was unsafe, or broke one of your rules."),
    ("Every floor stands on something.",
     "Under every part of the garage, the main floor, every terrace and every balcony there is now a wall, a column line or dug ground. "
     "No part stands over an undrawn void (rule 4.9)."),
    ("Your big arrival court.",
     "The ground west of the court and south of the forecourt is dug out. The stair from the road is at the far west, against the road: "
     "12 easy steps, a corner landing, 12 more. Court with porch: {court:.0f} + {porch:.0f} m²."),
    ("Easy stairs all the way down.",
     "From the court, 24 steps of 15 cm in three short flights take you to the garden walk at the lower floor; the walk runs on along the loggia's open front "
     "to the garden terrace, and 16 more steps of 15 cm reach the lawn. A script walks this whole route and checks every link. Every outdoor stair has landings, handrails both sides and guards."),
    ("Real walls, real services.",
     "Walls are drawn at their real thickness (0.40 m outside). The water tanks moved from the roof of the kitchen to the ground under the garage; "
     "the hob has a duct to the roof; risers, drains and terrace build-ups are designed in."),
    ("Rooms fixed.",
     "Dining seats 8 with chairs pulled out, the kitchen has 4 stools, the master's ensuite and dressing open from inside the bedroom, "
     "the laundry is compact (about 5 m²) with its own stores, and every lift door has a clear 1.5 m landing."),
]

STANDS = [
    ("The garage (road level) stands on the walls of the main floor.",
     "Under the half of the garage that stood on nothing in C10, a service room is dug down to the main floor: water tanks, booster pump and a bulk store, "
     "on solid ground. Its walls (u 0, u 2.0, v 1.1, v 2.8, v 4.6, v 7.3, the stair core on u 6.8) carry the garage slab; the garage's back wall stands on a beam on v 9.5. "
     "Road floor {s_road_plate[area]:.0f} m²: {s_road_plate[wall]:.0f} m² directly on a wall or beam, {s_road_plate[span]:.0f} m² spanning at most 7 m between them, "
     "{s_road_plate[unsupported]:.0f} m² on nothing. The roof terrace and the green roof stand on the master and living walls."),
    ("The main floor stands on the lower floor's walls and on dug ground.",
     "{s_main_plate[ground]:.0f} m² (service room, wet cluster, pantry, entry) stands on ground dug into the hill. The other {s_main_plate[wall]:.0f} + {s_main_plate[span]:.0f} m² "
     "stand on lower walls and beams: the lower north wall moved out to the north edge (v 1.1), so the master suite has the grandparents' walls under it; "
     "the whole south façade (v 13.0) sits on a beam carried by five continuous columns hidden in the children's walls, and a second beam over the south glass carries the road level; "
     "glass is never counted as a wall; "
     "the living room's corner over the loggia stands on an RC wall and beams, not on 5–6 m posts. {s_main_plate[unsupported]:.0f} m² on nothing."),
    ("The lower floor stands on the ground.",
     "{s_lower_plate[ground]:.0f} m² on dug ground with at most 1.0 m of compacted fill. Where the hill falls away under the lounge's east part, "
     "the slab is suspended between foundation walls over a ventilated crawl void (it would have needed 1.1 m of fill). Deepest dig: {deepest:.2f} m."),
    ("Every terrace and balcony.",
     "South terrace ({s_t_south[area]:.0f} m²): on the children's room walls and the v 13.0 beam, its slab set 0.25 m lower for waterproofing. "
     "East and master balconies ({s_balc_e[area]:.0f} + {s_balc_m[area]:.0f} m²): on an edge beam and five columns at u 19.6, so they are not long cantilevers. "
     "Garden terrace ({s_t_low[area]:.0f} m²): a suspended slab on four walls, with the rainwater cistern and the garden store under it. "
     "Loggia ({s_loggia[area]:.0f} m²): a suspended slab between the girls' wall and an RC wall. "
     "Forecourt: on the ground near the road, and on a deck with a pier line where fill would have been deeper than 1 m ({s_fore_deck[area]:.0f} m²)."),
]

DECISIONS = [
    ("NEW · Should the walls that hold the hill stay part of the house?",
     "Three reviewers (seismic, geotechnics, structure) say the north and west walls hold 3.6–4.5 m of hill and push the house downhill, and that the house would twist in an earthquake. "
     "C11 already detached the north pile wall. Detaching the west and core walls too means a second wall line with a drained gap: about 0.6 m off the service room and the court side, more digging and cost.",
     "Ask a structural engineer after the boreholes; keep the plan as it is until then (the rooms do not change)."),
    ("NEW · The front door: in the porch's side wall, or on the entry's south wall facing the court?",
     "Now it opens from the covered porch, facing a wall 2 m away, and needs two turns to the stair. On the south wall it would face the court and lead straight to the hall, but it would lose the cover.",
     "Move it to the south wall under a 1.5 m canopy, if you prefer a door you see as you come down the stair."),
    ("NEW · Size: 510 m² on the grid lines, 552 m² to the outside wall faces",
     "Your rule 4.7 calls 525–555 m² too big. C11 grew from C10's 459 m² (grid) because the service room under the garage and the north strip under the master suite now have floors: "
     "they are what the garage and the master suite stand on. The east garden is still 147 m².",
     "Keep it: the extra area is buried storage and structure, not a bigger-looking house. Or turn the service room into a ventilated void (saves no digging)."),
    ("NEW · Privacy along the garden walk",
     "The walk from the court to the garden passes the children's windows at their floor level. Guests coming down from the court would use it too.",
     "Translucent glass from the sill to 1.75 m on those windows (in SPECIFICATION.md), and a gate at the head of the court stair."),
    ("NEW · Room sizes the owner did not set",
     "The master suite (27 m² bedroom with its dressing zone) and the grandparents' room (27 m²) are larger than the children's rooms (19 m²), because the north strip had to become rooms.",
     "Keep the grandparents' sitting bay (they spend their days there); or make the north part of their room a store."),
    ("NEW · The play lawn is 61 m², smaller than C10's 74 m²",
     "The lawn stair and the stair walls take about 8 m². A one-level garden at 1669.85 (Q4) would give a bigger flat area with a 3 m wall over the neighbour.",
     "Keep the lower lawn; the pocket under the east balcony is now a covered play corner."),
    ("Q1 Wudu: are the feet washed or wiped?", "C11 designs for both: two seated stations, a floor trough with a drain, a standing basin.", "Keep both."),
    ("Q2 Largest gathering: 15, 30–35 or 60 people?", "C11 is designed for 15 seated (your recorded answer). 30–35 fit on one sofreh through the dining and living with the tables cleared.",
     "Keep 15 unless large gatherings are regular."),
    ("Q3 Bring back a study/play room?", "C11 adds no room: homework at the bedroom desks, games in the lounge, the hall kept clear for the lift landing.", "No new room."),
    ("Q4 Garden: one level at 1669.85, or the garden terrace at 1669.98 plus a lawn at 1667.60?",
     "C11 keeps the lawn at 1667.60 with a 16-step stair. One level would need a 3 m wall above the downhill neighbour and 2.6 times the fill.", "Keep the lower lawn."),
    ("Q5 Master balcony: start it 1.5 m south of the north edge, or keep it to the edge behind a 1.8 m screen?",
     "C11 starts it at v 2.6, so it looks east only, not into the north neighbour.", "Keep v 2.6."),
    ("Q6 Raise the road floor to 1677.65 for drainage?", "C11 keeps 1677.50: the forecourt falls to a channel at the boundary. The road edge has never been surveyed.",
     "Survey the road crown and gutter every 3 m first; decide after."),
    ("Q7 Walled hayat: a street wall and a lockable pedestrian gate at the stair head, the shutters as vehicle gates?",
     "C11 assumes yes: a 1.2 m sliding gate with intercom and parcel niche at the stair head, a 0.7 m RC parapet and rail on the road edge, no wall between court and terrace. "
     "But the court stair runs along the open south footpath, so without Q8's fence or a gate at the court stair the hayat is not closed.",
     "Yes, and add a gate at the head of the court stair (see the walk privacy decision)."),
    ("Q8 A fence or gate on the shared south footpath?", "None until the footpath's ownership is known.", "Wait for the title documents."),
    ("Q9 A direct stair from the main terraces down to the garden terrace?", "No: the route is terrace → court → court stair → garden walk.", "No."),
    ("Q10 Glazed sliders to close the kitchen while frying?", "No doors (your rule 1.3); a ducted hood with make-up air instead.", "No."),
    ("Q11 A squat pan somewhere, or WC pans turned strictly away from the qibla?",
     "Western pans with a shattaf, set square to the walls (43–47° off the qibla, not facing it).", "Keep, unless you want the strict reading."),
    ("Q12 Where is the family prayer place?",
     "The reviewers suggested the NE living corner, but that is your sheltered sofa corner (rule 3.1). C11 puts the prayer place (2 mats on the qibla) in the SE living corner, by the south window.",
     "SE living corner, as drawn."),
    ("Q13 Will the house ever grow upward, or the lower floor become a flat?", "No. C11 adds only door lintels and a knock-out panel for later.", "No."),
    ("Q14 A second WC downstairs for the morning rush?", "No: the family bathroom has a separate WC and shower.", "No."),
    ("Q15 Plan the children's block for 3 rooms later?", "No: the columns at u 11.1 make that costly.", "No."),
    ("Main family hall, 10.6 m long (rule 2.2)", "Unchanged since C10: open 2.6 m to the stair, 2.2 m to the entry, 1.6 m to the dining. It reads as a hall with rooms off it, not a corridor.",
     "Accept it."),
    ("Arrival court: {court:.0f} + {porch:.0f} m² instead of the reviewers' 51.6 m²",
     "Real walls inside the parcel and the setback cost about 7 m². The only way to win it back is a wall on the road edge itself, which needs the road authority.",
     "Accept the smaller court."),
    ("Road stair: first flight 164 mm risers", "The forecourt level (1677.47) sets it. 13 risers of 152 mm would need 0.32 m more run, taken from the court.",
     "Keep 164 mm (well under the 175 mm limit)."),
    ("Grandparents' room 28 m² clear", "The room grew because the lower north wall moved out to carry the master suite; the north part is a sitting area with a window to the garden.",
     "Keep the sitting area; or ask for a store there instead."),
    ("Quiet office 9.8 m² clear", "Inside real walls on the grid u 9.4–12.6. A 12.6 m² office would push the road level onto the roof terrace.", "Keep, with the fold-down bed."),
]

LIMITS = [
    "Exploratory concept. Nothing is stored in the project record, and nothing is validated.",
    "The site is unconfirmed (UTM zone, datum, legal boundary). Heights come from a 27-point survey TIN; true north and the qibla are inferred from the owner-supplied point.",
    "Not engineered. The structure shown (columns, beams, RC and retaining walls, spans up to 7 m) is a geometric consistency check for an engineer to design, "
    "after boreholes, a frost-depth, groundwater and radon survey, and a road survey. Seismic design (Standard 2800) is not done.",
    "Not permit-ready, not construction-ready, not code-checked. The permit regime, coverage and height rules are unknown (F5).",
    "The foul sewer outfall is unknown: space is reserved for a pumped connection to the road, a gravity drain downhill, or a holding tank.",
    "Earthwork volumes are inferred from the TIN, without footings, batters or bulking.",
]


FIXES = [
    "Both ensuite doors were blocked by a service riser: the riser moved; both doors are now clear (checked against risers and columns).",
    "The garden walk did not reach the loggia: it now runs on along the loggia's open front, and a new check walks the whole route road → court → garden walk → loggia → garden terrace → lawn.",
    "The guard check could never fail: rewritten. It now probes every edge of every terrace, roof, court, walk and stair, and re-checks independently; 237 m of guards are drawn, including a parapet on the road edge above the road stair.",
    "Glass was counted as a wall in the support check: no longer. A beam now carries the road level over the south glass, and lintel beams sit over the other large openings.",
    "The north pile wall overlapped the house wall and was too shallow: moved 0.45 m north with a drained gap, toes deepened to 1664.5–1669.0, caps stepped with the ground.",
    "Lower outer walls over the falling ground now have foundation walls down to sound ground; the SE corner has a column; the lawn-stair landings and the east garden walk are slabs on walls, not deep fill.",
    "The accessible WC now has a 1.5 m turning circle; the wudu bench no longer blocks the shower; the lower WC pan is out of sight of the hall.",
    "Living room: a 2.1 m bookcase screen with the TV now stands opposite the hall opening, so the sofa corner is sheltered (rule 3.1).",
    "Plant room enlarged to 5.0 × 1.7 m with its own flue; workbench 4.1 m; shutters lined up with the car lanes; the forecourt deck covers the whole strip behind the court wall.",
    "Gas (LPG) moved out of the sunk court to open air at road level; a refuge with bollards and a sliding gate at the road-stair head.",
    "Everything the drawings cannot show (build-ups, services, safety, materials) is written out in SPECIFICATION.md; the ledger's six overstated rows are corrected.",
]
