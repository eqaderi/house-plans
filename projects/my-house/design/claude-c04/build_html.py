"""Build a self-contained HTML review page for a C04 option (zoomable plans + all data).

Run: .venv/bin/python projects/my-house/design/claude-c04/build_html.py claude-c04-a
Writes <option>/review.html (open it in any browser; no network needed).
"""

import html
import json
import re
import sys
from pathlib import Path

from shapely.geometry import Polygon

import render
from house_ai.domain.plan import PlanVersion

HERE = Path(__file__).resolve().parent
LEVELS = [("lv-upper", "Road level", 1677.7), ("lv-entry", "Upper floor", 1674.3),
          ("lv-lower", "Lower floor", 1670.7)]


def level_svg(model, level_id):
    render.OY = 34
    w, h = render.PANEL_W + 2 * render.PAD, render.PANEL_H + 50
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'font-family="Helvetica, Arial, sans-serif">'
            '<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">'
            '<path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker></defs>'
            f'<rect width="100%" height="100%" fill="#fbfaf6"/>{render.panel(model, level_id, render.PAD)}</svg>')


def section_svg(folder):
    svg = (folder / "terrain-sections.svg").read_text()
    return re.sub(r'<svg([^>]*?) width="[^"]*" height="[^"]*"', r"<svg\1", svg, count=1)


def esc(s):
    return html.escape(str(s))


def main():
    option = sys.argv[1] if len(sys.argv) > 1 else "claude-c04-a"
    folder = HERE / option
    plan = PlanVersion.model_validate_json((folder / "plan.json").read_text())
    m = plan.model
    earth = json.loads((folder / "section-earthwork.json").read_text())
    names = {s.id: s.name for s in m.spaces}
    walls = {w.id: w for w in m.walls}
    rows, totals = {}, {}
    for s in m.spaces:
        g = Polygon([render.design(p) for p in s.boundary.outer])
        minx, miny, maxx, maxy = g.bounds
        rect = abs(g.area - (maxx - minx) * (maxy - miny)) < 0.05
        win = sum(1 for o in m.openings if o.kind.value == "window" and s.id in o.connects)
        outdoor = s.function.value == "terrace"
        rows.setdefault(s.level_id, []).append(
            (s.name, s.function.value, g.area, f"{maxx - minx:.1f} × {maxy - miny:.1f}" if rect else "L-shaped",
             win, outdoor))
        t = totals.setdefault(s.level_id, [0.0, 0.0])
        t[1 if outdoor else 0] += g.area
    doors = [(names.get(o.connects[0], o.connects[0]), names.get(o.connects[1], "outside"), o.width_m,
              walls[o.host_wall_id].level_id)
             for o in m.openings if o.kind.value == "door"]
    passages = [(names.get(o.connects[0]), names.get(o.connects[1], "outside"), o.width_m,
                 walls[o.host_wall_id].level_id)
                for o in m.openings if o.kind.value == "opening"]
    level_name = {lv: n for lv, n, _ in LEVELS}
    indoor = sum(t[0] for t in totals.values())
    outdoor = sum(t[1] for t in totals.values())

    def table(level_id):
        body = "".join(
            f"<tr class='{'out' if o else ''}'><td>{esc(n)}</td><td>{a:.1f}</td><td>{esc(d)}</td>"
            f"<td>{w or ''}</td></tr>"
            for n, f, a, d, w, o in sorted(rows[level_id], key=lambda r: (r[5], -r[2])))
        return ("<table><thead><tr><th>Room</th><th>m²</th><th>Size (m)</th><th>Windows</th></tr></thead>"
                f"<tbody>{body}</tbody></table>")

    plans = ""
    for lv, label, z in LEVELS:
        plans += f"""
<section id="{lv}">
  <h2>{label} <span class="z">+{z}</span></h2>
  <p class="meta">Indoor {totals[lv][0]:.1f} m² · outdoor {totals[lv][1]:.1f} m²</p>
  <div class="viewer" data-viewer>
    <div class="tools"><button data-zin>+</button><button data-zout>−</button><button data-reset>Reset</button>
      <button data-full>Full screen</button></div>
    {level_svg(m, lv)}
  </div>
  {table(lv)}
</section>"""

    b = earth["building"]
    door_rows = "".join(f"<tr><td>{esc(level_name[lv])}</td><td>{esc(a)}</td><td>{esc(c)}</td><td>{w:.1f}</td></tr>"
                        for a, c, w, lv in doors)
    pass_rows = "".join(f"<tr><td>{esc(level_name[lv])}</td><td>{esc(a)}</td><td>{esc(c)}</td><td>{w:.1f}</td></tr>"
                        for a, c, w, lv in passages)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude C04-A review</title>
<style>
:root {{ --bg:#f4f1ea; --card:#fff; --ink:#1f2a2e; --muted:#5f6b6e; --line:#d9d4c7; --accent:#2f6f6a; --warn:#a4462c; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#16191a; --card:#202425; --ink:#e8e6e1;
  --muted:#a3abad; --line:#3a3f40; --accent:#6fb5ae; --warn:#e08b6e; }} }}
:root[data-theme="dark"] {{ --bg:#16191a; --card:#202425; --ink:#e8e6e1; --muted:#a3abad; --line:#3a3f40;
  --accent:#6fb5ae; --warn:#e08b6e; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system, Helvetica, Arial, sans-serif; }}
nav {{ position:sticky; top:0; z-index:5; background:var(--card); border-bottom:1px solid var(--line);
  display:flex; gap:4px; flex-wrap:wrap; padding:8px 16px; }}
nav a {{ color:var(--ink); text-decoration:none; padding:6px 10px; border-radius:6px; }}
nav a:hover {{ background:var(--bg); }}
main {{ max-width:1200px; margin:0 auto; padding:16px; }}
h1 {{ margin:8px 0 4px; font-size:26px; }} h2 {{ margin:32px 0 4px; }} .z {{ color:var(--muted); font-weight:400; }}
.meta {{ color:var(--muted); margin:0 0 10px; }}
.banner {{ background:var(--card); border-left:4px solid var(--warn); padding:10px 14px; margin:12px 0; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px; margin:14px 0; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px; }}
.card b {{ display:block; font-size:22px; }}
.viewer {{ position:relative; background:#fbfaf6; border:1px solid var(--line); border-radius:10px; height:72vh;
  overflow:hidden; touch-action:none; cursor:grab; }}
.viewer:active {{ cursor:grabbing; }}
.viewer svg {{ width:100%; height:100%; display:block; }}
.viewer:fullscreen {{ height:100vh; border-radius:0; }}
.tools {{ position:absolute; top:8px; right:8px; display:flex; gap:4px; z-index:2; }}
.tools button {{ border:1px solid #bbb; background:#fff; color:#222; border-radius:6px; padding:4px 10px; font-size:15px;
  cursor:pointer; }}
.hint {{ color:var(--muted); font-size:13px; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; background:var(--card); }}
th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-weight:600; }} tr.out td {{ color:var(--muted); }}
ul {{ padding-left:20px; }} li {{ margin:4px 0; }}
.q {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px; margin:10px 0; }}
</style></head>
<body>
<nav><a href="#top">Overview</a><a href="#lv-upper">Road</a><a href="#lv-entry">Upper</a><a href="#lv-lower">Lower</a>
<a href="#sections">Side view &amp; digging</a><a href="#doors">Doors</a><a href="#notes">Weak points</a>
<a href="#questions">Questions</a></nav>
<main id="top">
<h1>Claude C04-A: house on the slope</h1>
<p class="meta">22 October 2026 · agent:claude-code · private project data</p>
<div class="banner"><b>Exploratory.</b> The site and program approvals are still open. Not reviewed by an architect or engineer.
Structure, retaining walls, drainage, waterproofing and building rules are unresolved.</div>
<p class="hint">Plans: scroll or pinch to zoom, drag to move, “Reset” to fit. On each plan, field east (downhill, the view) is to the right
and the north boundary is at the top. Blue = windows, brown = doors, white gaps = open passages, dashed = parcel boundary.</p>
<div class="cards">
 <div class="card">Indoor total<b>{indoor:.0f} m²</b>road {totals['lv-upper'][0]:.0f} · upper {totals['lv-entry'][0]:.0f} · lower {totals['lv-lower'][0]:.0f}</div>
 <div class="card">Terraces, decks, court<b>{outdoor:.0f} m²</b>plus a flat lawn of about {earth['lawn']['area_m2']:.0f} m²</div>
 <div class="card">Digging (estimate)<b>~{earth['building_cut_m3']:.0f} m³</b>deepest cut about {b[0]['max_cut_m']:.1f} m (lower floor, north-west)</div>
 <div class="card">Lawn<b>+{earth['lawn']['level']}</b>{earth['lawn']['fill_m3']:.0f} m³ fill · east wall about {earth['lawn']['max_fill_m']:.1f} m · 14 steps down</div>
 <div class="card">Levels<b>3 floors</b>road 1677.7 · upper 1674.3 · lower 1670.7</div>
 <div class="card">Integrity check<b>0 findings</b>{len(doors)} doors · {len(passages)} open passages</div>
</div>
{plans}
<section id="sections">
  <h2>Side view &amp; digging</h2>
  <p class="meta">Three cuts through the surveyed ground at equal horizontal and vertical scale. Red = cut depth, brown = retaining walls.</p>
  <div class="viewer" data-viewer><div class="tools"><button data-zin>+</button><button data-zout>−</button>
    <button data-reset>Reset</button><button data-full>Full screen</button></div>{section_svg(folder)}</div>
  <table><thead><tr><th>Part</th><th>Cut m³</th><th>Deepest cut m</th></tr></thead><tbody>
  {''.join(f"<tr><td>{esc(x['region'])}</td><td>{x['cut_m3']}</td><td>{x['max_cut_m']}</td></tr>" for x in b)}
  </tbody></table>
  <ul>
   <li>Lawn at {earth['lawn']['level']}: {earth['lawn']['fill_m3']} m³ fill, {earth['lawn']['cut_m3']} m³ cut. Most of the dug soil can be reused here.</li>
   <li>Raised parts needing supports or fill: the west half of the upper south terrace (up to about 2.4 m above the ground)
   and the south-east corner of the lower floor (about 1.8 m).</li>
   <li>Road forecourt: a slab at road level over the north part of the sunken west court. It gives the garage and lobby level doorsteps
   and the upper entrance a covered porch. South of it the court is open to the sky, with a stair down along the road border.</li>
   <li>All quantities are estimates from the survey, not contractor quantities. They exclude footings, working space, slopes and drainage.</li>
  </ul>
</section>
<section id="doors">
  <h2>Doors and open passages</h2>
  <p class="meta">As you asked: doors only where needed. Everything else is an open passage.</p>
  <h3>Open passages ({len(passages)})</h3>
  <table><thead><tr><th>Level</th><th>From</th><th>To</th><th>Width m</th></tr></thead><tbody>{pass_rows}</tbody></table>
  <h3>Doors ({len(doors)})</h3>
  <table><thead><tr><th>Level</th><th>From</th><th>To</th><th>Width m</th></tr></thead><tbody>{door_rows}</tbody></table>
</section>
<section id="notes">
  <h2>Weak points I know about</h2>
  <ul>
   <li>The parents/grandparents room (lower, south-west) has one 1.4 m window, and the ground outside is just below the sill.</li>
   <li>The garage apron needs about 1.4 m of build-up, carried by the forecourt slab. The road edge itself is level with the garage floor.</li>
   <li>Upstairs, the lift opens into the small stair hall, which is open to the living room.</li>
   <li>Total size is about {indoor:.0f} m² indoors, partly because you chose the bigger upper floor.</li>
   <li>Room sizes are my proposal. They are not yet an approved program.</li>
  </ul>
</section>
<section id="questions">
  <h2>Questions for you</h2>
  <div class="q"><b>1. Weak room.</b> Parents/grandparents room: swap with the girls' room (south-east corner), swap with the family room, or keep it as is?</div>
  <div class="q"><b>2. Size.</b> About {indoor:.0f} m² indoors. Keep it, or trim it (for example the garage-store strip or a smaller family room)?</div>
  <div class="q"><b>3. Lift door upstairs.</b> Is it okay that it opens into the stair hall (open to the living room), not straight into the living room?</div>
  <div class="q"><b>4. Arriving on foot.</b> Road → stair down along the road border → sunken court → covered porch → entrance hall. Is that okay?</div>
</section>
</main>
<script>
document.querySelectorAll('[data-viewer]').forEach(function (box) {{
  var svg = box.querySelector('svg');
  var vb0 = svg.getAttribute('viewBox').split(/[ ,]+/).map(Number);
  var vb = vb0.slice();
  function apply() {{ svg.setAttribute('viewBox', vb.join(' ')); }}
  function zoom(f, cx, cy) {{
    var r = svg.getBoundingClientRect();
    var px = cx === undefined ? 0.5 : (cx - r.left) / r.width, py = cy === undefined ? 0.5 : (cy - r.top) / r.height;
    var nw = Math.min(vb0[2] * 2, Math.max(vb0[2] / 25, vb[2] * f)), nh = nw * vb[3] / vb[2];
    vb[0] += (vb[2] - nw) * px; vb[1] += (vb[3] - nh) * py; vb[2] = nw; vb[3] = nh; apply();
  }}
  box.addEventListener('wheel', function (e) {{ e.preventDefault(); zoom(e.deltaY > 0 ? 1.15 : 1 / 1.15, e.clientX, e.clientY); }},
    {{ passive: false }});
  var pts = new Map(), last = null, pinch = null;
  box.addEventListener('pointerdown', function (e) {{ if (e.target.closest('button')) return;
    box.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); last = [e.clientX, e.clientY]; }});
  box.addEventListener('pointermove', function (e) {{
    if (!pts.has(e.pointerId)) return; pts.set(e.pointerId, [e.clientX, e.clientY]);
    var r = svg.getBoundingClientRect();
    if (pts.size === 2) {{
      var p = Array.from(pts.values()), d = Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]);
      if (pinch) zoom(pinch / d, (p[0][0] + p[1][0]) / 2, (p[0][1] + p[1][1]) / 2); pinch = d; return;
    }}
    if (last) {{ vb[0] -= (e.clientX - last[0]) * vb[2] / r.width; vb[1] -= (e.clientY - last[1]) * vb[3] / r.height; apply(); }}
    last = [e.clientX, e.clientY];
  }});
  function up(e) {{ pts.delete(e.pointerId); pinch = null; last = null; }}
  box.addEventListener('pointerup', up); box.addEventListener('pointercancel', up);
  box.querySelector('[data-zin]').onclick = function () {{ zoom(1 / 1.4); }};
  box.querySelector('[data-zout]').onclick = function () {{ zoom(1.4); }};
  box.querySelector('[data-reset]').onclick = function () {{ vb = vb0.slice(); apply(); }};
  box.querySelector('[data-full]').onclick = function () {{
    if (document.fullscreenElement) document.exitFullscreen(); else box.requestFullscreen();
  }};
}});
</script>
</body></html>"""
    out = folder / "review.html"
    out.write_text(page)
    print("wrote", out)


if __name__ == "__main__":
    main()
