"""index.html for C10: one design, shown first in 3D on the field, then floor by floor, then checked."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import engine as E
import shots
from shapely.ops import unary_union
from sitemap import meets_ground

CSS = """
:root{--ink:#1d2f3a;--muted:#5c6a73;--line:#ddd8cc;--bg:#fbfaf6;--card:#fff;--ok:#2f7d5b;--warn:#a5671b;--bad:#b23a48;--accent:#1f6f6a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Helvetica,Arial,sans-serif}
main{max-width:1320px;margin:0 auto;padding:0 18px 90px}
header{padding:30px 0 6px}
h1{font-size:32px;margin:0 0 6px;line-height:1.2}
h2{font-size:24px;margin:56px 0 12px;border-top:2px solid var(--line);padding-top:26px;scroll-margin-top:60px}
h3{font-size:17px;margin:26px 0 8px;color:var(--accent)}
.sub{color:var(--muted)}
.notice{background:#fff4e0;color:#5b4210;border:1px solid #ecd3a3;padding:10px 14px;border-radius:6px;margin:14px 0;font-size:14.5px}
nav{position:sticky;top:0;background:rgba(251,250,246,.96);border-bottom:1px solid var(--line);padding:9px 0;z-index:5;margin:0 -18px;padding-left:18px}
nav a{margin-right:16px;color:var(--accent);text-decoration:none;font-weight:600;font-size:14.5px;white-space:nowrap}
nav a:hover{text-decoration:underline}
table{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:14.5px}
th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600}
.pass{color:var(--ok);font-weight:700}.manual{color:var(--muted);font-weight:700}.open{color:var(--warn);font-weight:700}.FAIL{color:var(--bad);font-weight:700}
figure{margin:10px 0 18px}
figure img{width:100%;border:1px solid var(--line);border-radius:8px;background:#fbfaf6;display:block}
figcaption{font-size:14px;color:var(--muted);margin-top:6px}
figcaption b{color:var(--ink)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.split{display:grid;grid-template-columns:3fr 2fr;gap:22px;align-items:start}
@media (max-width:900px){.two,.split{grid-template-columns:1fr}}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.card b{display:block;font-size:24px;line-height:1.2}
.card span{color:var(--muted);font-size:13.5px}
ul{padding-left:22px}li{margin:5px 0}
.big li{margin:9px 0}
iframe{width:100%;height:780px;border:1px solid var(--line);border-radius:8px;background:#eef1f2;display:block}
details{margin:10px 0}summary{cursor:pointer;color:var(--accent);font-weight:600}
.btn{display:inline-block;background:var(--accent);color:#fff;border-radius:6px;padding:7px 13px;text-decoration:none;font-weight:600;font-size:14.5px}
.q{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warn);border-radius:6px;padding:10px 14px;margin:10px 0}
.q b{display:block}
"""

IDEA = [
    ("Three floors step down the hill.", "Road level: garage, front door, office. Main floor: kitchen, dining, living and the parents. "
     "Lower floor: children, grandparents, lounge and the garden. One stair and one lift join all three."),
    ("Each floor sits further east than the one above.", "So the roof of one floor is the terrace of the next, and the deepest dig is about 4 m."),
    ("Rooms are placed by the ground, not by a grid.", "Your field falls two ways. Where the ground is at or below a floor, that floor gets "
     "bedrooms, living rooms and terraces. Where the floor is buried, it gets the stair, bathrooms, laundry and stores."),
    ("South and east are for living.", "Kitchen with its south terrace, dining, living, every bedroom and the lounge face south or east. Nothing but service rooms faces the hill."),
    ("The garden follows the hill too.", "One level play lawn lies along the contour, where the hill already has that height. Below it the slope stays as it is and carries the trees."),
]

CHANGES = [
    ("Boys' and girls' rooms", "On the south from u 5.0. The boys' south wall was 0.3 to 1.8 m under ground and its window faced a dug trench.",
     "Moved 1.8 m east. Both south windows clear the ground: at most {win:+.2f} m against the floor at one end of the boys' window (sill 0.9 m)."),
    ("Digging", "Lower-floor pit {c9dig:.0f} m³, deepest cut {c9cut:.2f} m. A bathroom and a riser room were dug into the deepest corner.",
     "Lower-floor pit {dig:.0f} m³, deepest cut {cut:.2f} m. Those two rooms are not dug. The bathroom moved beside the family hall."),
    ("Master suite", "C09-1: bedroom 19 m², dressing 2.8 m², ensuite 4.1 m². C09-2 had the bigger suite but no outdoor space.",
     "Bedroom {mb:.0f} m² in the NE corner, dressing {md:.1f} m², ensuite {me:.1f} m², own balcony, bed facing the view. A bookshelf wall separates it from the living room."),
    ("Main-floor terraces", "64 m². East balcony 1.4 m deep, not joined to the south terrace.",
     "{terr:.0f} m². East balcony 1.6 m deep, wrapping the SE corner into the south terrace."),
    ("Roof terrace (road level)", "Reached only through the office.", "Reached from the core lobby through a glass door. That door also gives the entrance hall a view."),
    ("Lower-floor bathroom", "One family bathroom, entered from the foot of the stair.", "Separate WC, separate shower and twin basins, entered from the family hall."),
    ("Grandparents", "Room behind a vestibule. The bed stood across the garden door.", "Door from the hall straight into the room, 2 m from the lift. Bed on the north wall, garden door free."),
    ("Garden", "Paved terrace, then two lawns (71 + 38 m²) on up to 2.6 m of fill, split by a line square to the house.",
     "Terrace and covered loggia at floor level, then one level lawn of {lawn:.0f} m² along the contour (fill up to {lawnfill:.1f} m), then a natural tree bank."),
    ("Doors and furniture", "By the new test, furniture stood in 22 doorways or door swings: a counter across the kitchen terrace door, the fridge in the kitchen opening, a sofa across the lounge door.",
     "All {ndoors} doors and openings are tested with their swings. None is blocked."),
]

DECISIONS = [
    ("Lawn size or wall height?", "The lawn is {lawn:.0f} m² on one level, with a wall of about {lawnwall:.1f} m on its downhill side and a natural tree bank below. "
     "Taking the lawn out to the 1 m setback line adds about {bank:.0f} m², but then a wall of about 2 m stands near the east boundary and the trees go. C09 had 109 m² of lawn, on two levels."),
    ("The lawn is 14 steps below the terrace.", "The lift serves the lower floor, the garden terrace and the loggia without a step. It does not reach the lawn. "
     "A lawn level with the lounge would need walls of 3 to 4 m. Is a terrace and loggia without steps enough for the grandparents?"),
    ("Everyday meals for eight.", "You asked for everyday meals in the kitchen and for a kitchen of 15–17 m² (rules 1.4, 1.5). At that size the island seats three or four. "
     "The dining table for six to eight is one step away through the opening. If all eight must eat inside the kitchen, it has to grow to about 22 m² (my estimate) and the living room gives up the space."),
    ("Main-floor court door: two turns to the stair (rule 2.6).", "Unchanged from C09. The daily front door is on the road level and is straight. "
     "A straight court door would sit under the garage slab, the passage you rejected."),
    ("Main family hall, 10.5 × 2.1 m (rule 2.2).", "Unchanged from C09. It is open to the stair, the dining room and the living room, with rooms on one side only. Acceptable?"),
    ("Parents' suite on the main floor (rules 6.5 and 6.7).", "Kept on the main floor, north side, as in stmt-018. Your own options A and C had it on the lower floor."),
    ("Family hall downstairs has no window of its own.", "It gets daylight through the 2.2 m opening to the lounge. A glazed lounge wall or a roof light over the stair would add more."),
]

LIMITS = [
    "Exploratory concept. Nothing here is stored in the project record, and nothing is validated.",
    "The site is still unconfirmed: UTM zone, datum and the legal boundary. All heights come from the survey TIN, 27 surveyed points with straight interpolation between them.",
    "Setbacks are the 1 m south and east lines already in the project. No setback is assumed on the north and west. Local rules are not checked.",
    "Not engineered. Retaining walls (forecourt about 3 m, garden terrace about 2.4 m), foundations, the 1.6 m balcony, drainage behind buried walls and the stair need professionals.",
    "Not permit-ready, not construction-ready, not checked against any building code.",
    "Pantry, the wudu and WC group and the lower-floor bathroom have no windows. They need mechanical ventilation.",
]


def area(lv, rid: str) -> float:
    return E.room_dims(lv.room(rid))[2]


def schedule(lv) -> str:
    rows = []
    for r in lv.rooms:
        if not r.name or r.kind in ("stair", "lift", "merge"):
            continue
        w, d, a = E.room_dims(r)
        rect = r.geom.area > 0.97 * r.geom.envelope.area
        rows.append(f"<tr><td>{escape(r.name.title())}</td><td>{f'{w:.1f} × {d:.1f}' if rect else 'L-shaped'}</td><td>{a:.1f}</td></tr>")
    for t in lv.terraces:
        if t.name and t.kind != "stair":
            rows.append(f"<tr><td>{escape(t.name.title())} <span class='sub'>(outside)</span></td><td></td><td>{t.geom.area:.0f}</td></tr>")
    return "<table><tr><th>Room</th><th>Clear size (m)</th><th>Area (m²)</th></tr>" + "".join(rows) + "</table>"


def checklist(report: dict) -> str:
    label = {"pass": "PASS · measured", "manual": "designer's judgement", "open": "YOUR DECISION", "FAIL": "FAIL"}
    names = {"doors.clear": "Doors clear of furniture", "ground.openings": "Windows and doors clear the ground", "daylight.rooms": "Daylight in every main room"}
    rows = []
    for c in report["rules"]:
        if c["id"].startswith("geom."):
            continue
        rid = c["id"]
        for k, v in names.items():
            if rid.startswith(k):
                rid = f"{v} · {rid.rsplit('.', 1)[1]} floor"
        rows.append(f"<tr><td>{escape(rid)}</td><td class='{c['status']}'>{label[c['status']]}</td><td>{escape(c['evidence'])}</td></tr>")
    g = [c for c in report["rules"] if c["id"].startswith("geom.")]
    geo = "all clear" if all(c["status"] == "pass" for c in g) else "; ".join(c["evidence"] for c in g if c["status"] != "pass")
    lc = {k: v for k, v in report["label_collisions"].items() if v}
    return ("<table><tr><th>Rule</th><th>Status</th><th>Evidence</th></tr>" + "".join(rows) + "</table>"
            f"<p class='sub'>Geometry checks on all three floors (no overlapping rooms, everything inside the parcel and the 1 m setbacks, no enclosed leftover holes): {escape(geo)}. "
            f"Overlapping labels on the drawings: {escape(str(lc) if lc else 'none')}.</p>")


def fig(src: str, caption: str, link: str | None = None) -> str:
    img = f"<img src='{src}' alt='{escape(caption[:80], quote=True)}' loading='lazy'>"
    if link:
        img = f"<a href='{link}'>{img}</a>"
    return f"<figure>{img}<figcaption>{caption}</figcaption></figure>"


def build(opt: E.Option, gm: E.GroundModel, report: dict, model: dict, here: Path) -> None:
    shots.write_page(here, model)
    taken = shots.take(here)
    L = opt.levels
    main, lower = L["main"], L["lower"]
    ew = report["earthworks"]
    gross = {k: lv.footprint.area for k, lv in L.items()}
    covered = unary_union([lv.footprint for lv in L.values()]).area
    garden = E.ENVELOPE.intersection(E.R(lower.footprint.bounds[2], -1, 40, 19)).area
    terr = {t.id: t for lv in L.values() for t in lv.terraces}
    pits = [r for r in ew["rows"] if r["kind"] == "pit"]
    deepest = max(r["max_cut_m"] for r in pits)
    lawn_row = next(r for r in ew["rows"] if r["zone"].startswith("Play Lawn"))
    c9 = {"dig": 240.4, "cut": 4.38}
    c9_file = here.parent / "991_2026-10-27_claude-c09" / "c09-1" / "checks.json"
    if c9_file.exists():
        rows9 = json.loads(c9_file.read_text())["earthworks"]["rows"]
        low9 = next(r for r in rows9 if r["zone"].startswith("LOWER"))
        c9 = {"dig": low9["cut_m3"], "cut": low9["max_cut_m"]}
    win = max(E.zg_safe(u, 16.8) for u in (8.9, 9.4, 9.9, 10.4, 10.9)) - lower.z
    nums = dict(win=win, c9dig=c9["dig"], c9cut=c9["cut"], dig=next(r["cut_m3"] for r in pits if r["zone"].startswith("Lower")), cut=deepest,
                mb=area(main, "master"), md=area(main, "dress"), me=area(main, "ens"),
                terr=sum(t.geom.area for t in main.terraces if t.kind == "terrace"), lawn=terr["lawn"].geom.area,
                lawnfill=lawn_row["max_fill_m"], lawnwall=lawn_row["max_fill_m"], bank=terr["bank"].geom.area,
                ndoors=sum(len(lv.doors) for lv in L.values()))
    fails = [c for c in report["rules"] if c["status"] == "FAIL"]
    n_pass = sum(c["status"] == "pass" for c in report["rules"])
    mn, ms = meets_ground(lower.z, 2.8), meets_ground(lower.z, 16.4)
    z = {k: E.zg_safe(*p) for k, p in {"nw": (0.3, 0.3), "ne": (30.5, 0.3), "sw": (-9.4, 17.9), "se": (22.0, 17.9)}.items()}

    p: list[str] = []
    a = p.append
    a(f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
      f"<title>My House · C10</title><style>{CSS}</style></head><body><main>")
    a("<header><h1>My House · C10<br>One design, fitted to both slopes of the field</h1>"
      "<p class='sub'>Claude Code (Fable) · 18 Nov 2026 · based on your own 0109-r5 layouts through C08 and C09 · your request: stmt-026</p></header>")
    a("<nav><a href='#idea'>The idea</a><a href='#3d'>3D model</a><a href='#field'>The field</a><a href='#road'>Road level</a>"
      "<a href='#main'>Main floor</a><a href='#lower'>Lower floor + garden</a><a href='#sections'>Sections + digging</a>"
      "<a href='#changes'>What changed</a><a href='#rules'>Rule check</a><a href='#decisions'>Your decisions</a></nav>")
    a("<div class='notice'><b>Exploratory concept.</b> Nothing here is stored in the project record or validated. The site is still unconfirmed. "
      "Nothing is engineered or ready for a permit. <a href='#limits'>All limits</a>.</div>")

    # ---- the idea
    a("<h2 id='idea'>The idea in one minute</h2><div class='split'><div>")
    if "house-se" in taken:
        a(fig("views/house-se.png", "<b>The house on your field, seen from the south-east.</b> Road at the top left, garden at the bottom right. "
              "The red line is your boundary; the red tags give the height of each corner.", "3d.html"))
    a("</div><div><ul class='big'>" + "".join(f"<li><b>{escape(h)}</b> {escape(t)}</li>" for h, t in IDEA) + "</ul></div></div>")
    a("<div class='cards'>"
      f"<div class='card'><b>{sum(gross.values()):.0f} m²</b><span>floor area on three floors, garage included (road {gross['road']:.0f}, main {gross['main']:.0f}, lower {gross['lower']:.0f})</span></div>"
      f"<div class='card'><b>{100 * covered / E.PARCEL.area:.0f}%</b><span>of the 600 m² field is under the house ({covered:.0f} m²)</span></div>"
      f"<div class='card'><b>{garden:.0f} m²</b><span>of garden east of the house: terrace, lawn of {nums['lawn']:.0f} m², tree bank</span></div>"
      f"<div class='card'><b>{nums['terr']:.0f} m²</b><span>of terraces on the main floor, plus a {terr['deck-r'].geom.area:.0f} m² roof terrace</span></div>"
      f"<div class='card'><b>{deepest:.1f} m</b><span>deepest dig (your limit: about 4.5 m). Dig ≈ {ew['total_cut_m3']:.0f} m³, fill ≈ {ew['total_fill_m3']:.0f} m³</span></div>"
      f"<div class='card'><b>{n_pass} of {n_pass + len(fails)}</b><span>measured rule checks pass. {sum(c['status'] == 'open' for c in report['rules'])} rules wait for your decision</span></div>"
      "</div>")
    if fails:
        a("<div class='notice'><b>Failing checks:</b> " + escape("; ".join(c["id"] for c in fails)) + "</div>")

    # ---- 3D
    a("<h2 id='3d'>The 3D model: turn it, open it, look inside</h2>"
      "<p>This is the real model, in true scale. Drag to turn it and scroll to zoom. The buttons along the top change what you see: "
      "the whole house, the bare field, the digging, or one floor with everything above it lifted off. "
      "<a class='btn' href='3d.html'>Open the 3D model full screen</a></p>"
      "<iframe src='3d.html' title='3D model of the field and the house'></iframe>"
      "<p class='sub'>If the box stays empty, your browser has 3D switched off. The still pictures on this page come from the same model.</p>")

    # ---- the field
    a("<h2 id='field'>Your field, and how the house sits on it</h2>")
    a("<ul class='big'>"
      f"<li><b>Main slope, west → east.</b> The road side is at about {z['nw']:.1f} m. The east boundary is at about {z['ne']:.1f} m. "
      f"The field falls about {z['nw'] - z['ne']:.0f} m over 30 m: more than 1 m down for every 3 m forward.</li>"
      f"<li><b>Cross slope, north → south.</b> Along any line across the field the south side is about 2.5 to 3 m lower than the north side. "
      f"So the lowest corner is the south-east ({z['se']:.1f} m) and the most buried corner of any floor is its north-west.</li>"
      f"<li><b>What that does to a floor.</b> The lower floor is at 1670.00. On the north side the ground only drops to that height {mn:.1f} m from the west. "
      f"On the south side it gets there after {ms:.1f} m. The line between those two points runs diagonally through the house, and the plan follows it.</li>"
      "<li><b>Directions.</b> As in all earlier drawings, “east” means down the hill, along your north boundary. By the compass that is east-north-east, "
      "so the “south” side really faces south-south-east. Good for sun.</li></ul>")
    a("<div class='two'>")
    if "field" in taken:
        a(fig("views/field.png", "<b>The bare field, coloured by height.</b> Red is the road side, blue is the lowest corner. "
              "The two black arrows are the two slopes. The thin frame is where the house will stand."))
    a(fig("drawings/site.png", "<b>The house on the field, from above.</b> The dashed blue and brown lines show where the ground is exactly at the main-floor "
          "and lower-floor levels. West of a line that floor is under ground.", "drawings/site.svg"))
    a("</div><div class='two'>")
    if "house-south" in taken:
        a(fig("views/house-south.png", "<b>Seen from the south: the main slope.</b> Road on the left, garden on the right. "
              "Each floor comes out of the hill further to the right than the one above."))
    if "house-east" in taken:
        a(fig("views/house-east.png", "<b>Seen from the east, from below: the cross slope.</b> The ground on the right (north) is higher than on the left (south). "
              "Lounge and grandparents open onto the terrace; the lawn and the trees are below."))
    a("</div>")

    # ---- floors
    shots_of = {"road": "open-road", "main": "open-main", "lower": "open-lower"}
    intro = {
        "road": "You arrive here, by car or on foot. Floor at 1677.50, level with the road.",
        "main": "The family's day floor, one level below the road. Floor at 1673.60.",
        "lower": "The children's and grandparents' floor, level with the garden terrace. Floor at 1670.00.",
    }
    for key in ("road", "main", "lower"):
        lv = L[key]
        a(f"<h2 id='{key}'>{escape(lv.title.title())}</h2><p>{intro[key]}</p><div class='split'><div>")
        if shots_of[key] in taken:
            a(fig(f"views/{shots_of[key]}.png", f"<b>{escape(lv.title.title())} in 3D,</b> with everything above it lifted off. Walls are cut at 1.3 m so you can see in."))
        a("</div><div><h3>How this floor works</h3><ul>" + "".join(f"<li>{escape(n)}</li>" for n in lv.notes) + "</ul></div></div>")
        a(fig(f"drawings/{key}.png", f"<b>{escape(lv.title.title())} plan.</b> North is up. Click for the full-size drawing.", f"drawings/{key}.svg"))
        a("<details><summary>Room sizes on this floor</summary>" + schedule(lv) + "</details>")
        if key == "road" and "house-road" in taken:
            a(fig("views/house-road.png", "<b>Seen from the road.</b> Two garage doors and the front door. From here the house is one storey high; the other two floors are below."))

    # ---- sections
    a("<h2 id='sections'>Sections through the hill, and the digging</h2>"
      "<p>Four cuts through the house and the ground, drawn in true scale. Two run west → east and two run north → south, so you can see both slopes. "
      "The cut lines A–A to D–D are marked on the plan of the field above.</p>")
    a(fig("drawings/sections.png", "<b>Sections.</b> Brown line: the ground today. Light brown hatch over rooms: that part of the house is below today's ground. "
          "Green hatch: filled ground. Green line: finished garden and court levels. Grey: walls that hold the ground.", "drawings/sections.svg"))
    a("<div class='split'><div>")
    if "dig" in taken:
        a(fig("views/dig.png", "<b>Digging and filling, with the house lifted off.</b> The yellow skin is today's ground. "
              "Where it floats above a floor, that floor is dug in. Where a flat area rises through it, that area is filled."))
    a("</div><div><h3>Earthwork</h3><table><tr><th>Where</th><th>Area</th><th>Dig</th><th>Fill</th></tr>")
    for r in ew["rows"]:
        nm = r["zone"].split(" (")[0].replace(" + Garden", "")
        dig = f"{r['cut_m3']:.0f} m³, up to {r['max_cut_m']:.1f} m" if r["cut_m3"] >= 1 else "–"
        fill = f"{r['fill_m3']:.0f} m³, up to {r['max_fill_m']:.1f} m" if r["fill_m3"] >= 1 else "–"
        a(f"<tr><td>{escape(nm)}</td><td>{r['area_m2']:.0f} m²</td><td>{dig}</td><td>{fill}</td></tr>")
    a(f"<tr><th>Total</th><th></th><th>≈ {ew['total_cut_m3']:.0f} m³</th><th>≈ {ew['total_fill_m3']:.0f} m³</th></tr></table>"
      f"<p class='sub'>How measured: {escape(ew['method'])} Status: inferred from the survey TIN, not a soil survey.</p>"
      f"<p>About half of what is dug out can be used again on the field as fill. The rest, roughly {ew['total_cut_m3'] - ew['total_fill_m3']:.0f} m³, has to be taken away.</p></div></div>")

    # ---- changes
    a("<h2 id='changes'>What changed from C09</h2><p>C10 keeps what you liked in C08 and C09: your stair and lift core, your room sizes, the levels, the house ending 18 m from the west. "
      "It changes these points.</p><table><tr><th></th><th>C09</th><th>C10</th></tr>"
      + "".join(f"<tr><td><b>{escape(t)}</b></td><td>{escape(o.format(**nums))}</td><td>{escape(n.format(**nums))}</td></tr>" for t, o, n in CHANGES)
      + "</table>")

    # ---- rules
    a("<h2 id='rules'>Rule check (OWNER_DESIGN_RULES.md, rule 8.1)</h2>"
      "<p>Each of your rules, with how it was checked. “Measured” means a script tested the geometry. “Designer's judgement” means I looked and decided. "
      "“Your decision” means the rule is not clearly met or not clearly broken, and you should choose.</p>" + checklist(report))

    # ---- decisions
    a("<h2 id='decisions'>Your decisions</h2><p>These are the points where I could not give you everything at once. Tell me which way to go on any of them.</p>")
    for k, (h, t) in enumerate(DECISIONS, 1):
        a(f"<div class='q'><b>{k}. {escape(h)}</b>{escape(t.format(**nums))}</div>")
    a("<h2 id='limits'>Limits of this study</h2><ul>" + "".join(f"<li>{escape(x)}</li>" for x in LIMITS) + "</ul>")
    a("<p class='sub'>Rebuild: <code>.venv/bin/python projects/my-house/design/990_2026-11-18_claude-c10/build.py</code>. "
      "Geometry is in design.py; plans, sections, the 3D model and the checks are all drawn from it.</p>")
    a("</main></body></html>")
    (here / "index.html").write_text("".join(p))
