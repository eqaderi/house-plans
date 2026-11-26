"""index.html for C11: the idea, what stands on what, the drawings, the comparison with C10, the checks, the decisions."""

from __future__ import annotations

from html import escape
from pathlib import Path

import design as D
import engine as E
import shots
from report_text import DECISIONS, FIXES, IDEA, LIMITS, STANDS
from shapely.ops import unary_union

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
nav a{margin-right:14px;color:var(--accent);text-decoration:none;font-weight:600;font-size:14px;white-space:nowrap}
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
.ans{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;padding:10px 14px;margin:10px 0}
.ans b{display:block;font-size:17px}
"""


def schedule(lv) -> str:
    rows = []
    for r in lv.rooms:
        if not r.name or r.kind in ("stair", "lift", "merge", "riser"):
            continue
        w, d, a = E.room_dims(r)
        rect = r.geom.area > 0.97 * r.geom.envelope.area
        u0, v0, u1, v1 = r.geom.bounds
        rows.append(f"<tr><td>{escape(r.name.title())}</td><td>{f'{u1 - u0:.1f} × {v1 - v0:.1f}' if rect else 'L-shaped'}</td>"
                    f"<td>{f'{w:.2f} × {d:.2f}' if rect else ''}</td><td>{a:.1f}</td></tr>")
    for t in lv.terraces:
        if t.name and t.kind not in ("stair", "bank"):
            rows.append(f"<tr><td>{escape(t.name.title())} <span class='sub'>(outside)</span></td><td></td><td></td><td>{t.geom.area:.0f}</td></tr>")
    return ("<table><tr><th>Room</th><th>On the grid (m)</th><th>Clear inside the walls (m)</th><th>Clear area (m²)</th></tr>"
            + "".join(rows) + "</table>")


def checklist(report: dict, group: str) -> str:
    label = {"pass": "PASS · measured", "manual": "designer's judgement", "open": "YOUR DECISION", "FAIL": "FAIL"}
    names = {"doors.clear": "Doors clear of furniture", "daylight.rooms": "Daylight in every main room", "2.3.voids": "2.3 no leftover holes"}
    rows = []
    for c in report["rules"]:
        if c["group"] != group:
            continue
        rid = c["id"]
        for k, v in names.items():
            if rid.startswith(k):
                rid = f"{v} · {rid.rsplit('.', 1)[1]}"
        rows.append(f"<tr><td>{escape(rid)}</td><td class='{c['status']}'>{label[c['status']]}</td><td>{escape(c['evidence'])}</td></tr>")
    return "<table><tr><th>Check</th><th>Status</th><th>Evidence</th></tr>" + "".join(rows) + "</table>"


def review_section(here: Path) -> str:
    """The reviewers' scorecard, read from the 28 review files, and the fix round."""
    import re

    rdir = here.parent.parent / "reviews" / "c11-expert-review-2026-11-22"
    rows, tot = [], {}
    for f in sorted(rdir.glob("[0-2][0-9]-*.md")):
        m = re.search(r"SCORECARD:\s*([^\n`]*)", f.read_text())
        if not m:
            continue
        vals = dict(kv.split("=") for kv in m.group(1).split())
        nn = f.name[:2]
        if nn != "28":
            for k, v in vals.items():
                tot[k] = tot.get(k, 0) + int(v)
        rows.append((f.name, vals))
    keys = ("fixed", "partly", "not_fixed", "worse", "new_blocker", "new_major", "new_minor")
    h = ["<h2 id='review'>What 28 reviewers found, and the fix round</h2>",
         "<p>After C11 was drawn, 28 specialist reviewers checked it: the same 27 specialties as for C10, plus one who checked C11 against your own words "
         "and audited the corrections ledger line by line. Their reports and the merged result are in "
         "<a href='../../reviews/c11-expert-review-2026-11-22/CONSOLIDATED.md'>reviews/c11-expert-review-2026-11-22</a>. "
         "The fix round that followed is at the end of <a href='CORRECTIONS.md'>CORRECTIONS.md</a>.</p>",
         "<table><tr><th>Review</th>" + "".join(f"<th>{k.replace('_', ' ')}</th>" for k in keys) + "</tr>"]
    for name, vals in rows:
        h.append(f"<tr><td>{escape(name[:-3])}</td>" + "".join(f"<td>{vals.get(k, '')}</td>" for k in keys) + "</tr>")
    h.append("<tr><th>C10 findings, reviewers 01–27</th>" + "".join(f"<th>{tot.get(k, 0)}</th>" for k in keys) + "</tr></table>")
    h.append("<p class='sub'>Reviewer 28 scored the ledger: 'fixed' = verified rows, 'worse' = rows it found overstated or false (6 of 108), all corrected in the fix round. "
             "New-finding counts are raw: several reviewers found the same problem.</p>")
    h.append("<h3>What the fix round changed</h3><ul>" + "".join(f"<li>{escape(x)}</li>" for x in FIXES) + "</ul>")
    return "".join(h)


def fig(src: str, caption: str, link: str | None = None) -> str:
    img = f"<img src='{src}' alt='{escape(caption[:80], quote=True)}' loading='lazy'>"
    if link:
        img = f"<a href='{link}'>{img}</a>"
    return f"<figure>{img}<figcaption>{caption}</figcaption></figure>"


def build(opt, gm, report: dict, model: dict, here: Path, cmp_html: str, elements, swalls) -> None:
    shots.write_page(here, model)
    taken = shots.take(here)
    L = opt.levels
    ew = report["earthworks"]
    gross = {k: lv.footprint.area for k, lv in L.items()}
    covered = unary_union([lv.footprint for lv in L.values()]).area
    garden = E.ENVELOPE.intersection(E.R(L["lower"].footprint.bounds[2] + E.EXT_OUT, -1, 40, 19)).area
    pits = [r for r in ew["rows"] if r["kind"] in ("pit", "void")]
    deepest = max(r["max_cut_m"] for r in pits)
    terr_main = sum(t.geom.area for t in L["main"].terraces if t.kind == "terrace")
    fails = [c for c in report["rules"] if c["status"] == "FAIL"]
    n_pass = sum(c["status"] == "pass" for c in report["rules"])
    n_open = sum(c["status"] == "open" for c in report["rules"])
    sup = {r["id"]: r for r in report["support"]}
    court = next(t for t in L["main"].terraces if t.id == "court-w").geom.area
    porch = next(t for t in L["main"].terraces if t.id == "porch").geom.area
    nums = dict(court=court, porch=porch, deepest=deepest, cut=ew["total_cut_m3"], fill=ew["total_fill_m3"], **{"s_" + k.replace("-", "_"): v for k, v in sup.items()})

    p: list[str] = []
    a = p.append
    a("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
      f"<title>My House · C11</title><style>{CSS}</style></head><body><main>")
    a("<header><h1>My House · C11<br>C10 corrected: every floor stands on something</h1>"
      "<p class='sub'>Claude Code · 22 Nov 2026 · C10 with every correction of the 27-reviewer review and your rules of today (stmt-027, stmt-028, stmt-029) · "
      "<a href='CORRECTIONS.md'>ledger of all 108 corrections</a></p></header>")
    a("<nav><a href='#idea'>The idea</a><a href='#stands'>What stands on what</a><a href='#3d'>3D</a><a href='#field'>Field</a><a href='#road'>Road level</a>"
      "<a href='#main'>Main floor</a><a href='#lower'>Lower floor</a><a href='#outside'>Court + stairs</a><a href='#sections'>Sections</a>"
      "<a href='#compare'>C10 vs C11</a><a href='#review'>Review + fixes</a><a href='#rules'>Rule check</a><a href='#decisions'>Your decisions</a></nav>")
    a("<div class='notice'><b>Exploratory concept.</b> Nothing here is stored in the project record or validated. The site is still unconfirmed. "
      "Nothing is engineered, permit-ready or code-checked: the structure shown is a consistent concept for an engineer to design, not a design by one. "
      "<a href='#limits'>All limits</a>.</div>")

    a("<h2 id='idea'>The idea in one minute</h2><div class='split'><div>")
    if "house-se" in taken:
        a(fig("views/house-se.png", "<b>C11 on your field, from the south-east.</b> Road top left, garden bottom right.", "3d.html"))
    a("</div><div><ul class='big'>" + "".join(f"<li><b>{escape(h)}</b> {escape(t.format(**nums))}</li>" for h, t in IDEA) + "</ul></div></div>")
    a("<div class='cards'>"
      f"<div class='card'><b>0 m²</b><span>of floor, terrace or balcony standing on nothing (C10: about 55 m²)</span></div>"
      f"<div class='card'><b>{court + porch:.0f} m²</b><span>arrival court with its covered porch (C10: 34 m²)</span></div>"
      f"<div class='card'><b>15 cm</b><span>highest step from the court to the garden and the lawn; 16 cm on the road stair. Every link of the route checked</span></div>"
      f"<div class='card'><b>{sum(gross.values()):.0f} m²</b><span>floor on three floors (road {gross['road']:.0f}, main {gross['main']:.0f}, lower {gross['lower']:.0f}); {100 * covered / E.PARCEL.area:.0f}% of the field covered</span></div>"
      f"<div class='card'><b>{garden:.0f} m²</b><span>east garden inside the setbacks; {terr_main:.0f} m² of main-floor terraces</span></div>"
      f"<div class='card'><b>{deepest:.1f} m</b><span>deepest dig to formation (limit about 4.5 m); dig ≈ {ew['total_cut_m3']:.0f} m³, fill ≈ {ew['total_fill_m3']:.0f} m³</span></div>"
      f"<div class='card'><b>{n_pass} pass</b><span>{len(fails)} fail, {n_open} wait for your decision</span></div></div>")
    if fails:
        a("<div class='notice'><b>Failing checks:</b> " + escape("; ".join(c["id"] for c in fails)) + "</div>")

    a("<h2 id='stands'>What stands on what: your three questions</h2>"
      "<p>You asked: <i>“Garage stays on top of what? Also the main floor stays on top of what?”</i> Here is the answer for every floor, terrace and balcony. "
      "Each answer is measured: a script walks every 25 cm of every slab and finds what holds it.</p>")
    for h, t in STANDS:
        a(f"<div class='ans'><b>{escape(h)}</b>{escape(t.format(**nums))}</div>")
    a(fig("drawings/supports.png", "<b>What stands on what.</b> Each floor coloured by what carries it, over the walls, beams and columns of the storey below. "
          "No red: nothing stands on nothing.", "drawings/supports.svg"))
    if "structure" in taken:
        a(fig("views/structure.png", "<b>The structure in 3D</b>, upper floors lifted off: columns, retaining and foundation walls with their real heights.", "3d.html#mode=structure"))

    a("<h2 id='3d'>The 3D model</h2><p>Drag to turn, scroll to zoom. “What stands on what” shows the columns and walls. "
      "<a class='btn' href='3d.html'>Open full screen</a></p><iframe src='3d.html' title='3D model'></iframe>")

    a("<h2 id='field'>Your field and the house on it</h2><div class='two'>")
    if "field" in taken:
        a(fig("views/field.png", "<b>The bare field, coloured by height.</b> The two arrows are the two slopes."))
    a(fig("drawings/site.png", "<b>The house on the field.</b> Dashed lines: where the ground is exactly at the main and lower floor levels. A–H: the section cuts.", "drawings/site.svg"))
    a("</div>")

    intro = {"road": "You arrive here, by car or on foot. Floor 1677.50, level with the road.",
             "main": "The family's day floor, one storey below the road. Floor 1673.60.",
             "lower": "Children, grandparents, the lounge and the garden. Floor 1670.00."}
    for key in ("road", "main", "lower"):
        lv = L[key]
        a(f"<h2 id='{key}'>{escape(lv.title.title())}</h2><p>{intro[key]}</p><div class='split'><div>")
        if f"open-{key}" in taken:
            a(fig(f"views/open-{key}.png", f"<b>{escape(lv.title.title())} in 3D,</b> everything above lifted off."))
        a("</div><div><h3>How this floor works</h3><ul>" + "".join(f"<li>{escape(n)}</li>" for n in lv.notes) + "</ul></div></div>")
        a(fig(f"drawings/{key}.png", f"<b>{escape(lv.title.title())} plan</b>, furnished. Black squares: columns. Purple dashes: beams overhead. Brown: retaining and site walls; "
              "dashed brown: foundations under this floor. Blue lines: 1.1 m guards. Arrows: grid north, true north, qibla. Click for full size.", f"drawings/{key}.svg"))
        a("<details><summary>Room sizes on this floor</summary>" + schedule(lv) + "</details>")

    a("<h2 id='outside'>The arrival court and every outdoor stair</h2>"
      "<p>Your proposal (rule 4.10): dig out the ground west of the court and south of the forecourt, put the stair from the road at the far west against the road. "
      "Every outdoor stair is now easy (rule 4.11):</p><table><tr><th>Stair</th><th>Route</th><th>Flights</th><th>Landings</th><th>Width</th></tr>")
    for st in D.outdoor_stairs():
        fl = " + ".join(f"{f.risers} × {f.rise * 1000:.0f} mm / {f.going * 1000:.0f} mm" for f in st.flights)
        a(f"<tr><td>{escape(st.name.title())}</td><td>{escape(st.route)}</td><td>{fl}</td><td>≥ {st.landing_min:.1f} m between flights, top and bottom</td><td>{st.width_clear:.2f} m clear, {escape(st.handrails)}</td></tr>")
    a("</table>")
    a(f"<p>The court is {court:.1f} m² open plus a {porch:.1f} m² covered porch at the front door (C10: 34.0 m²). The reviewers estimated 51.6 m² with walls of no thickness; "
      "the real retaining walls (0.30–0.40 m) must stand inside your parcel and the 1 m south setback, and the road stair moved 0.30 m off the road for its own wall. "
      "That costs about 7 m². Water: the court falls 1:60 to a channel on its south edge with two gullies and a pipe down the garden stair band; a snow pit sits in its north-west corner.</p>")

    a("<h2 id='sections'>Sections through the hill</h2><p>Eight cuts in true scale, two ways, through every outdoor stair, the lift pit and the forecourt deck. "
      "Every column and wall is drawn from the same list as the plans and the 3D model.</p>")
    a(fig("drawings/sections.png", "<b>Sections A–H.</b> Brown line: today's ground. Hatch: dug (brown) or filled (green). Black: columns and beams. Grey: walls with their real tops and footings.", "drawings/sections.svg"))
    a("<div class='split'><div>")
    if "dig" in taken:
        a(fig("views/dig.png", "<b>Digging and filling</b>, the house lifted off."))
    a("</div><div><h3>Earthwork</h3><table><tr><th>Where</th><th>Area</th><th>Dig</th><th>Fill</th></tr>")
    for r in ew["rows"]:
        nm = r["zone"].split(" (")[0].replace(" + Garden", "").strip() or "stair landing"
        dig = f"{r['cut_m3']:.0f} m³, up to {r['max_cut_m']:.1f} m" if r["cut_m3"] >= 1 else "–"
        fil = f"{r['fill_m3']:.0f} m³, up to {r['max_fill_m']:.1f} m" if r["fill_m3"] >= 1 else "–"
        a(f"<tr><td>{escape(nm)}</td><td>{r['area_m2']:.0f} m²</td><td>{dig}</td><td>{fil}</td></tr>")
    a(f"<tr><th>Total</th><th></th><th>≈ {ew['total_cut_m3']:.0f} m³</th><th>≈ {ew['total_fill_m3']:.0f} m³</th></tr></table>"
      f"<p class='sub'>{escape(ew['method'])} Inferred from the survey TIN, not a soil survey.</p></div></div>")

    a(cmp_html)
    a(review_section(here))

    a("<h2 id='rules'>Rule check (rule 8.1)</h2><p>Each of your rules, how it was checked, and the evidence. “Measured” means a script tested the geometry in design.py.</p>")
    a(checklist(report, "rule"))
    a("<h3>The 22 new checks the reviewers asked for (CONSOLIDATED §7)</h3>" + checklist(report, "new"))
    a(f"<p class='sub'>Geometry hygiene: {escape('; '.join(c['evidence'] for c in report['rules'] if c['group'] == 'geom' and c['status'] != 'pass') or 'no overlapping rooms on any floor')}. "
      f"Overlapping labels: {escape(str({k: v for k, v in report['label_collisions'].items() if v}) or 'none')}.</p>")

    a("<h2 id='decisions'>Your decisions</h2><p>Where a question is yours, C11 uses the reviewers' default and lists it here with my recommendation.</p>")
    for k, (h, t, rec) in enumerate(DECISIONS, 1):
        a(f"<div class='q'><b>{k}. {escape(h)}</b>{escape(t.format(**nums))}<br><i>My recommendation:</i> {escape(rec)}</div>")
    a("<h2 id='limits'>Limits of this study</h2><ul>" + "".join(f"<li>{escape(x)}</li>" for x in LIMITS) + "</ul>")
    a("<p class='sub'>Rebuild: <code>.venv/bin/python projects/my-house/design/989_2026-11-22_claude-c11/build.py</code>. "
      "Geometry and structure are in design.py; plans, sections, the support sheet, the 3D model and the checks are drawn from it.</p></main></body></html>")
    (here / "index.html").write_text("".join(p))
