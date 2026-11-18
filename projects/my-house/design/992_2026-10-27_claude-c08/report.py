"""index.html for C08: critique of C07 and the owner's 0109-r5, then the three options with checklists."""

from __future__ import annotations

from html import escape

from compare import section as compare_section
from engine import room_dims, zg

CSS = """
:root{--ink:#1d2f3a;--muted:#5c6a73;--line:#ddd8cc;--bg:#fbfaf6;--card:#fff;--ok:#2f7d5b;--warn:#a5671b;--bad:#b23a48;--accent:#1f6f6a}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ink:#e7ecef;--muted:#a9b4ba;--line:#3a4247;--bg:#161a1d;--card:#1e2327}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 Helvetica,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 80px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:21px;margin:40px 0 10px;border-top:1px solid var(--line);padding-top:24px}
h3{font-size:16px;margin:22px 0 8px;color:var(--accent)}
.sub{color:var(--muted)}.notice{background:#fff4e0;color:#5b4210;border:1px solid #ecd3a3;padding:10px 14px;border-radius:6px;margin:16px 0}
table{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:13.5px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600}.pass{color:var(--ok);font-weight:700}.manual{color:var(--muted);font-weight:700}.open{color:var(--warn);font-weight:700}.FAIL{color:var(--bad);font-weight:700}
img{width:100%;border:1px solid var(--line);border-radius:6px;background:#fbfaf6;margin:6px 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
nav a{margin-right:14px;color:var(--accent)}ul{padding-left:20px}li{margin:3px 0}
"""

C07_CRITIQUE = [
    "Rooms are rectangles pushed into a grid, and the grid comes first. Living, dining and lounge sizes come out as whatever was left over (Garden Lounge 37 m², Family Hall 31.8 m², Boys 22 m²).",
    "The west court is an L-shaped slot running along the garage. You reach the 'front door' through it, which is the 'strange passage' you rejected (stmt-021).",
    "Labels overlap the walls and each other. Green 'PASS / All 30 issues resolved' text is printed on the drawing, while defects stay visible: the dress is a 2.9 m² sliver, and the parents' bedroom sits under the garage (I15).",
    "Dimension lines are missing, doors are hard to read, and the drawings sit in the parcel frame, not grid north. Nothing tells you how the house sits on the slope.",
]

OWNER_KEEP = [
    "Owner's north stair core with REST 1.40 and the lift beside it, stacked on all three floors.",
    "Owner's 4-part screened WC / shower / wudu / lobby cluster.",
    "Owner's south row of boys and girls rooms at 4.3 × 4.8 m, each with 2 beds, 2 desks and 2 wardrobes.",
    "Owner's road-level sequence: two cars on the west, core in the middle, office at the east looking onto the roof.",
    "Owner's levels: road 1677.50, main 1673.60, lower 1670.00, the main and lower floors stepping east with the hill.",
]

OWNER_FIX = [
    ("Living is 21–23 m² in A, B and C, a strip between the dining and the prayer bay.", "Living is 43–46 m² and 5.5–6 m wide. The sofa corner in the NE is closed to the north. Only option 2 is a true L; options 1 and 3 are 5.7 × 7.7 m rooms (rules 3.1 and 3.3)."),
    ("B's kitchen is 11 m² and its pantry sits away from the fridge (I26).", "Kitchen is 15 m² with an island, and the pantry is next to it or within 2.3 m (rule 1.5)."),
    ("B has three hall fragments (family hall, family link, screened kitchen arrival).", "One family hall per floor (rules 2.2 and 2.3)."),
    ("B's parents' suite is SW, next to the public south terrace (I30) and under the garage (I15).", "Master suite on the quiet north (rule 6.5), with its own lobby, under the core and roof deck, not the cars."),
    ("No pedestrian door at road level. On the main floor you enter under the garage slab.", "Road level: a west front door opens into a straight hall towards the stair and lift. Main floor: a west door opens off an open-sky SW court (rule 2.6)."),
    ("Garage is 5.2 m deep, so the LC300 barely fits. The car-door zone clashes with the cabinet (I09). No workbench.", "Garage is 6.8 × 8.4 m (57 m²), with two 3.35 m shutters, 4.2 m bays and a workbench and bike wall (rule 5.5)."),
    ("Lower guest room has no seated WC (I10). Laundry is 7 m² (I12).", "Seated, step-free guest ensuite with a 1.5 m turning circle; laundry and drying 13 m² beside the store."),
    ("House ends at u ≈ 17.8 on the main floor (rule 4.2).", "Main floor reaches u 18.6–19.2, lower floor u 21.6–22.2, then a garden terrace and the lawn."),
]

QUESTIONS = [
    "<b>Your rules disagree on where the parents' suite goes.</b> Rule 6.5 (stmt-018) says the main floor, quiet north side. Rule 6.7 also names your own B arrangement, with the parents' suite SW/W on the main floor. All three options follow 6.5. Do you want a version with B's SW suite?",
    "<b>Kitchen size.</b> Rule 1.5 (stmt-021, the later statement) says 15–17 m², and rule 6.7 mentions ~18–22 m². These options use 15–15.3 m² plus a pantry, because stmt-021 says kitchens were too big.",
    "<b>East lawn.</b> stmt-018 hoped for a ~10 m flat lawn with the lower floor ending at u 20. The 42 m² living room you asked for pushes the main floor to u 18.6–19.2 and the lower floor to u 21.6–22.2. That leaves a 3 m garden terrace at 1669.98 plus a lawn of 35–45 m² at 1668.60. A larger lawn needs a smaller living room or a narrower garden terrace.",
    "<b>Main hall length (rule 2.2).</b> The family hall is 2.1 m wide and about 9 m from the entry to the living room. It is open to the stair and the dining room, but it is long. Say if you would rather trade some dining or hall area for a shorter hall.",
    "<b>Main-floor entry route (rule 2.6).</b> The west door is open to the sky, with no passage, but you turn twice to reach the stair: into the entry, north, then east. Putting the door on the hall axis would put it under the garage slab, which is the passage you rejected. Is the two-turn entry acceptable?",
    "<b>Downstairs family hall.</b> It is 30–34 m² because it also serves as the children's sitting room with the tea bar. It could shrink if the garden lounge takes that role.",
    "<b>North terrace (rule 4.3).</b> Only 1.1 m separates the house from the north boundary, so options 1–2 have no north terrace. Option 3 has a private NE master terrace.",
]


def slope_facts() -> list[str]:
    z = {k: zg(*p) for k, p in {"nw": (0.5, 0.5), "ne": (30.0, 0.5), "sw": (0.5, 17.0), "se": (21.0, 17.0)}.items()}
    return [
        f"Ground falls {z['nw'] - z['ne']:.1f} m from the road side (west, {z['nw']:.1f}) to the east boundary ({z['ne']:.1f}), "
        f"about {100 * (z['nw'] - z['ne']) / 29.5:.0f}%.",
        f"It also falls north → south: {z['nw'] - z['sw']:.1f} m along the west side and about 1.5–3 m across the middle, roughly 10–25%.",
        "So the house steps down to the east. Its buried NW corner holds the stores, wet rooms and core; day rooms and bedrooms take the open south and east.",
        "All levels come from the stored survey TIN. The site is still SITE_NEEDS_VERIFICATION, with UTM zone, datum and legal boundary unconfirmed.",
    ]


def schedule(opt) -> str:
    rows = []
    for key, lv in opt.levels.items():
        for r in lv.rooms:
            if not r.name or r.kind in ("stair", "lift", "merge"):
                continue
            w, d, a = room_dims(r)
            rows.append(f"<tr><td>{escape(lv.title.title())}</td><td>{escape(r.name.title())}</td><td>{w:.2f} × {d:.2f}</td><td>{a:.1f}</td></tr>")
    return ("<table><tr><th>Level</th><th>Room</th><th>Clear bounding (m)</th><th>Clear area (m²)</th></tr>"
            + "".join(rows) + "</table>")


def checklist(report) -> str:
    rows = []
    for c in report["rules"]:
        if c["id"].startswith("geom."):
            continue
        st = c["status"]
        lab = {"pass": "PASS · checked", "manual": "designer judgement", "open": "YOUR DECISION", "FAIL": "FAIL"}[st]
        rows.append(f"<tr><td>{escape(c['id'])}</td><td class='{st}'>{lab}</td><td>{escape(c['evidence'])}</td></tr>")
    g = [c for c in report["rules"] if c["id"].startswith("geom.")]
    geo = "all clear" if all(c["status"] == "pass" for c in g) else "; ".join(c["evidence"] for c in g if c["status"] != "pass")
    lc = {k: v for k, v in report["label_collisions"].items() if v}
    return ("<table><tr><th>Rule</th><th>Status</th><th>Evidence</th></tr>" + "".join(rows) + "</table>"
            f"<p class='sub'>Geometry checks (no overlaps, inside the 1 m S/E setback envelope, no enclosed leftover holes): {escape(geo)}. "
            f"Label collisions: {escape(str(lc) if lc else 'none')}.</p>")


def build(results, out) -> None:
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>My House C08</title><style>{CSS}</style></head><body><main>"]
    parts.append("<h1>My House · C08 plan options</h1><p class='sub'>Claude Code · 27 Oct 2026 · three reworked versions of the owner's own 0109-r5 plans (A, B, C)</p>")
    parts.append("<div class='notice'>EXPLORATORY concept sketches. Nothing here is stored in the project record or validated. The site is unconfirmed. "
                 "Nothing is permit-ready, structurally engineered or geotechnically verified. Retaining walls, drainage and the stair geometry need professionals.</div>")
    parts.append("<nav><a href='#compare'><b>Compare</b></a>" + "".join(f"<a href='#{o.code}'>{o.code}</a>" for o, _ in results)
                 + "<a href='#questions'>Questions</a></nav>")
    parts.append(compare_section(results, out))
    parts.append("<h2>The field</h2><ul>" + "".join(f"<li>{escape(x)}</li>" for x in slope_facts()) + "</ul>")
    parts.append("<h2>Why C07 felt robotic</h2><ul>" + "".join(f"<li>{escape(x)}</li>" for x in C07_CRITIQUE) + "</ul>")
    parts.append("<h2>Your 0109-r5 designs: kept and fixed</h2><h3>Kept</h3><ul>" + "".join(f"<li>{escape(x)}</li>" for x in OWNER_KEEP) + "</ul>")
    parts.append("<h3>Problems found → what C08 does</h3><table><tr><th>In 0109-r5</th><th>In C08</th></tr>"
                 + "".join(f"<tr><td>{escape(a)}</td><td>{escape(b)}</td></tr>" for a, b in OWNER_FIX) + "</table>")
    parts.append("<h2>The three options at a glance</h2><table><tr><th></th>" + "".join(f"<th>{o.code}</th>" for o, _ in results) + "</tr>")

    def row(label, fn):
        return f"<tr><td>{label}</td>" + "".join(f"<td>{escape(fn(o, r))}</td>" for o, r in results) + "</tr>"

    def area(o, rid, lv="main"):
        return f"{room_dims(o.levels[lv].room(rid))[2]:.1f} m²"

    parts.append(row("Derived from", lambda o, r: o.source))
    parts.append(row("Idea", lambda o, r: o.idea))
    parts.append(row("Living", lambda o, r: area(o, "living")))
    parts.append(row("Kitchen / dining", lambda o, r: f"{area(o, 'kitchen')} / {area(o, 'dining')}"))
    parts.append(row("Master bedroom", lambda o, r: area(o, "master")))
    parts.append(row("Main / lower east edge", lambda o, r: f"u {o.levels['main'].footprint.bounds[2]:.1f} / u {o.levels['lower'].footprint.bounds[2]:.1f}"))
    parts.append(row("Gross floor (road+main+lower)", lambda o, r: f"{sum(lv.footprint.area for lv in o.levels.values()):.0f} m²"))
    parts.append(row("Earthwork (TIN, inferred)", lambda o, r: f"cut ≈ {r['earthworks']['total_cut_m3']:.0f} m³ · fill ≈ {r['earthworks']['total_fill_m3']:.0f} m³"))
    parts.append(row("Checked rules failing", lambda o, r: str(sum(c['status'] == 'FAIL' for c in r['rules']))))
    parts.append(row("Open owner decisions", lambda o, r: str(sum(c['status'] == 'open' for c in r['rules']))))
    parts.append(row("Shared by all three", lambda o, r: "road level, SW arrival, core, wet cluster, kids' rooms"))
    parts.append("</table>")
    for o, r in results:
        d = o.code.lower()
        parts.append(f"<h2 id='{o.code}'>{o.code} · {escape(o.title)}</h2><p>{escape(o.idea)}</p>")
        for key in ("road", "main", "lower"):
            parts.append(f"<h3>{escape(o.levels[key].title.title())}</h3><img src='{d}/{key}.png' alt='{o.code} {key} plan'>")
        parts.append(f"<h3>Sections and earthwork</h3><img src='{d}/sections.png' alt='{o.code} sections'>")
        parts.append("<h3>Rule checklist (OWNER_DESIGN_RULES.md, rule 8.1)</h3>" + checklist(r))
        parts.append("<h3>Room schedule</h3>" + schedule(o))
    parts.append("<h2 id='questions'>Your decisions</h2><ul>" + "".join(f"<li>{q}</li>" for q in QUESTIONS) + "</ul>")
    parts.append("</main></body></html>")
    (out / "index.html").write_text("".join(parts))
