"""index.html for C08: critique of C07 and the owner's 0109-r5, then the three options with checklists."""

from __future__ import annotations

from html import escape

from compare import section as compare_section
from engine import room_dims, zg
from shapely.ops import unary_union

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

C08_TO_C09 = [
    ("Too big: 525–553 m² gross, the house covering 48–51% of the field.", "452–463 m² gross, covering 39–40% (stmt-023)."),
    ("Lower floor ran to u 21.6–22.2. East lawn only 35–43 m².", "Lower floor ends at u 18.0. 151 m² of east garden inside the setbacks: a paved terrace, then two lawns stepping down the hill. Plus a 21 m² SE terrace (stmt-024)."),
    ("SE garden terrace and path crossed the parcel line (my checker missed it).", "Every terrace and path is checked against the 1 m setbacks."),
    ("Living 43–46 m², separate dining 14 m².", "Living 34 m² (5.2 × 6.8 m, sofa corner closed to the north). The dining opens 3 m wide into it, making one L-shaped day room (stmt-024)."),
    ("Stair 3.2 m wide.", "Same dog-leg with REST 1.40, flights 1.15 m: stair box 2.6 m wide."),
    ("Lower floor had a family hall of 30–34 m² plus a lounge, and a WC/shower cluster.", "Square 18 m² family hall, a 22 m² garden lounge with tea bar (kept, as you chose), and one family bathroom."),
    ("Deepest cut 4.2 m.", "Deepest cut 4.4 m, still within your 4.5 m (survey TIN, inferred)."),
]

WHY_TWO = ("Why two options, not three. With the house ending at u 18, the core, the master suite on the north (6.5), "
           "a ≥5 m wide living room in the SE (3.3), the kitchen on the south terrace (1.1) and dining opening into the living (stmt-024) "
           "allow one day-floor layout. C08-3's dining-kitchen-living order no longer works once the dining joins the living. "
           "What can still vary is the master suite (mid-north with a private NE terrace, or the NE corner) and the lower floor "
           "(grandparents NE with the lounge east, or the reverse). A third set would only shuffle these. Say if you want one anyway.")

QUESTIONS = [
    "<b>Parents' suite (rules 6.5 vs 6.7)</b> is still open. Both options keep it on the north, per 6.5.",
    "<b>Main-floor entry (2.6)</b>: two turns from the west door to the stair. A straight route would put the door under the garage slab.",
    "<b>Main hall (2.2)</b> is 10.5 × 2.1 m, open to the stair and the dining room. Acceptable?",
    "<b>Master suite size.</b> The ensuite is 4–6 m² and the dressing room 3–7 m². Standard, but no longer 'grand'.",
    "<b>Garden levels.</b> Paved terrace 1669.98, upper lawn 1668.60, lower lawn 1667.30 with low retaining steps. One flat lawn would need about 3 m of fill at the east boundary.",
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
             f"<title>My House C09</title><style>{CSS}</style></head><body><main>"]
    parts.append("<h1>My House · C09 compact options</h1><p class='sub'>Claude Code · 27 Oct 2026 · C08 shrunk to fit the field and free the east garden (stmt-023, stmt-024)</p>")
    parts.append("<div class='notice'>EXPLORATORY concept sketches. Nothing here is stored in the project record or validated. The site is unconfirmed. "
                 "Nothing is permit-ready, structurally engineered or geotechnically verified. Retaining walls, drainage and the stair geometry need professionals.</div>")
    parts.append("<nav><a href='#compare'><b>Compare</b></a>" + "".join(f"<a href='#{o.code}'>{o.code}</a>" for o, _ in results)
                 + "<a href='#questions'>Questions</a></nav>")
    parts.append(compare_section(results, out))
    parts.append("<h2>The field</h2><ul>" + "".join(f"<li>{escape(x)}</li>" for x in slope_facts()) + "</ul>")
    parts.append("<h2>What changed from C08</h2><table><tr><th>C08</th><th>C09</th></tr>"
                 + "".join(f"<tr><td>{escape(a)}</td><td>{escape(b)}</td></tr>" for a, b in C08_TO_C09) + "</table>")
    parts.append(f"<p>{escape(WHY_TWO)}</p>")
    parts.append("<h2>The options at a glance</h2><table><tr><th></th>" + "".join(f"<th>{o.code}</th>" for o, _ in results) + "</tr>")

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
    parts.append(row("Ground covered by house", lambda o, r: f"{unary_union([lv.footprint for lv in o.levels.values()]).area:.0f} m² of 600"))
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
