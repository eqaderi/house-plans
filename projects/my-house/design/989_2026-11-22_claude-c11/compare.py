"""C10 ↔ C11 comparison (rule 8.5): a table of only what changed, and each floor side by side with the
changed rooms and terraces outlined in orange. Built on ../991_2026-10-27_claude-c09/compare.py.

C10 is read with C10's own code in a separate process (c10_dump.py), so the two engines never mix.
Areas in the table are on the grid lines (gross), the only measure the two designs share: C10 drew 0.30 m
outer walls and C11 draws the real 0.40-0.45 m ones.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from html import escape
from pathlib import Path

import engine as E
from shapely import wkt as W
from shapely.ops import unary_union

LEVEL_KEYS = ("road", "main", "lower")
LEVEL_NAMES = {"road": "Road level", "main": "Main floor", "lower": "Lower floor + garden"}
HERE = Path(__file__).resolve().parent
C10_DIR = HERE.parent / "990_2026-11-18_claude-c10"

# What the 27 reviewers measured on C10 (CONSOLIDATED.md §1, §4), for the rows C10's own files cannot show
C10_FACTS = {
    "What the garage stands on": "28.9 of 57.1 m² on main-floor walls; 28.2 m² on 0.4–4.1 m of air or loose fill (review 01/02/03)",
    "What the main floor stands on": "119 m² on lower rooms, ~31 m² on dug ground, ~27 m² on nothing (master north strip, living over the loggia on 5–6 m posts)",
    "Road stair": "22 risers of 173 mm in one flight, no landing, beside a 3.8 m drop",
    "Court → garden": "drops 2.30 m in a 2.0 m run; then a stepless path",
    "Lawn stair": "14 risers of 170 mm in one flight, open sides",
    "Walls drawn": "0.30 m outside, 0.12 m inside",
    "Lift shaft (grid)": "2.0 × 2.3 m: too short for a stretcher",
    "Water tanks": "on the road level, over the kitchen",
    "Terraces over rooms": "flush with the floor: no depth for waterproofing",
}


def _c10_items() -> dict:
    out = subprocess.run([sys.executable, str(HERE / "c10_dump.py"), "items"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _c11_items(opt) -> dict:
    out = {}
    for k, lv in opt.levels.items():
        out[k] = [{"id": x.id, "name": x.name, "kind": x.kind, "wkt": x.geom.wkt, "area": round(x.geom.area, 2)} for x in lv.rooms + lv.terraces]
        out[k + "_footprint"] = lv.footprint.wkt
    return out


def _sig(it) -> str:
    g = W.loads(it["wkt"]).normalize().simplify(0.01)
    return f"{it['name']}|{g.wkt}"


def differing(c10: dict, c11: dict, key: str) -> tuple[set, set]:
    a = {i["id"]: _sig(i) for i in c10[key] if i["name"]}
    b = {i["id"]: _sig(i) for i in c11[key] if i["name"]}
    da = {k for k, v in a.items() if b.get(k) != v}
    db = {k for k, v in b.items() if a.get(k) != v}
    return da, db


def _area(items, key, rid):
    it = next((i for i in items[key] if i["id"] == rid), None)
    return f"{it['area']:.1f} m²" if it else "—"


def metrics(items: dict, ew: dict, extra: dict) -> dict:
    rows = {}
    for key, rid, label in (("main", "kitchen", "Kitchen"), ("main", "dining", "Dining"), ("main", "living", "Living"),
                            ("main", "master", "Master bedroom"), ("main", "pantry", "Pantry"), ("main", "hall", "Main family hall"),
                            ("lower", "boys", "Boys"), ("lower", "girls", "Girls"), ("lower", "guest", "Grandparents"),
                            ("lower", "lounge", "Garden lounge"), ("lower", "laundry", "Laundry"), ("lower", "hall-l", "Lower family hall"),
                            ("road", "garage", "Garage"), ("road", "office", "Quiet office")):
        rows[f"{label} (grid)"] = _area(items, key, rid)
    fps = {k: W.loads(items[k + "_footprint"]) for k in LEVEL_KEYS}
    rows["Floors (grid): road / main / lower"] = " / ".join(f"{fps[k].area:.0f}" for k in LEVEL_KEYS) + f" = {sum(f.area for f in fps.values()):.0f} m²"
    rows["Floor extents u: road / main / lower"] = " / ".join(f"{fps[k].bounds[0]:.1f}–{fps[k].bounds[2]:.1f}" for k in LEVEL_KEYS)
    cover = unary_union(list(fps.values())).area
    rows["Ground covered"] = f"{cover:.0f} m² ({100 * cover / E.PARCEL.area:.0f}%)"
    # measured from the lower floor's outer wall face (0.25 m outside the grid line), the same figure as check 4.7
    rows["East garden inside the setbacks"] = f"{E.ENVELOPE.intersection(E.R(fps['lower'].bounds[2] + E.EXT_OUT, -1, 40, 19)).area:.0f} m²"
    terr = {i["name"].title(): i["area"] for i in items["main"] if i["kind"] in ("terrace",) and i["name"]}
    rows["Main-floor terraces"] = ", ".join(f"{k} {v:.0f}" for k, v in terr.items()) + f" = {sum(terr.values()):.0f} m²"
    court = next((i for i in items["main"] if i["id"] == "court-w"), None)
    porch = next((i for i in items["main"] if i["id"] == "porch"), None)
    rows["Arrival court"] = f"{court['area']:.1f} m²" + (f" + {porch['area']:.1f} m² covered porch" if porch else "")
    rows["Earthwork (inferred)"] = f"cut {ew['total_cut_m3']:.0f} m³ · fill {ew['total_fill_m3']:.0f} m³"
    pits = [r for r in ew["rows"] if r["kind"] in ("pit", "void")]
    rows["Deepest building cut"] = f"{max(r['max_cut_m'] for r in pits):.2f} m"
    rows.update(extra)
    return rows


def _crop_svg(svg: Path, crop) -> None:
    x0, y0, x1, y1 = crop
    txt = svg.read_text()
    head, rest = txt.split(">", 1)
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" '
            f'viewBox="{x0:.0f} {y0:.0f} {x1 - x0:.0f} {y1 - y0:.0f}"')
    svg.write_text(head + ">" + rest)
    subprocess.run(["rsvg-convert", "-w", "1400", "-o", str(svg.with_suffix(".png")), str(svg)], check=True)


CSS = """
.cmp table td.diff{background:rgba(240,138,60,.13)}
.cmp .tabs input{display:none}.cmp .tabs label{display:inline-block;padding:6px 14px;border:1px solid var(--line);border-radius:16px;margin:0 6px 8px 0;cursor:pointer;color:var(--accent)}
.cmp .tabs input:checked+label{background:var(--accent);color:#fff;border-color:var(--accent)}
.cmp .pane{display:none}.cmp #t-main:checked~#p-main,.cmp #t-lower:checked~#p-lower,.cmp #t-road:checked~#p-road,.cmp #t-sec:checked~#p-sec{display:block}
.cmp .side{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.cmp .side figure{margin:0}.cmp figcaption{font-size:13px;color:var(--muted)}.cmp figcaption b{color:var(--ink)}
@media (max-width:760px){.cmp .side{grid-template-columns:1fr}}
.cmp details{margin:6px 0 18px}.cmp summary{cursor:pointer;color:var(--muted)}
"""


def section(opt, report: dict, here: Path) -> str:
    c10 = _c10_items()
    c11 = _c11_items(opt)
    cdir = here / "compare"
    cdir.mkdir(exist_ok=True)
    caps = {}
    for key in LEVEL_KEYS:
        d10, d11 = differing(c10, c11, key)
        subprocess.run([sys.executable, str(here / "c10_dump.py"), "render", key, str(cdir / f"c10-{key}.svg"), ",".join(sorted(d10))], check=True)
        svg = cdir / f"c11-{key}.svg"
        _crop_svg(svg, E.draw_level(opt.levels[key], opt, svg, highlight=d11)["crop"])
        name10 = {i["id"]: i["name"].title() for i in c10[key]}
        name11 = {i["id"]: i["name"].title() for i in c11[key]}
        caps[key] = (sorted({name10[i] for i in d10 if name10.get(i)}), sorted({name11[i] for i in d11 if name11.get(i)}))
    c10_ew = json.loads((C10_DIR / "checks.json").read_text())["earthworks"]
    sup = {r["id"]: r for r in report["support"]}
    road = sup["road-plate"]
    mainp = sup["main-plate"]
    extra11 = {
        "What the garage stands on": f"all {road['area']:.0f} m² of the road floor on walls and beams below ({road['wall'] + road['span']:.0f} m²); 0 m² on nothing",
        "What the main floor stands on": f"{mainp['area']:.0f} m²: {mainp['ground']:.0f} on dug ground, {mainp['wall'] + mainp['span']:.0f} on lower walls and beams, {mainp['unsupported']:.0f} on nothing",
        "Road stair": "24 risers of 158–164 mm, 320 mm goings, 12 + 12 with a corner landing, 1.4 m clear, against the road",
        "Court → garden": "24 risers of 150 mm / 340 mm in three flights of 8 with 1.5 m landings, to the garden walk at the lower floor",
        "Lawn stair": "16 risers of 149 mm / 320 mm, two flights of 8 and a 1.2 m landing, walls and handrails both sides",
        "Walls drawn": "0.40 m outside (0.45 against earth), 0.25 RC core, 0.20 RC lift and acoustic walls, 0.12 partitions",
        "Lift shaft (grid)": "2.0 × 2.8 m: 1.80 × 2.60 m clear, stretcher car",
        "Water tanks": "on the ground slab of the service room under the garage",
        "Terraces over rooms": "structural slab set down 0.25 m for the inverted roof",
    }
    t10 = metrics(c10, c10_ew, C10_FACTS)
    t11 = metrics(c11, report["earthworks"], extra11)
    keys = list(t11)
    differ = [k for k in keys if t10.get(k) != t11.get(k)]
    same = [k for k in keys if k not in differ]
    head = "<tr><th></th><th>C10<br><span class='sub'>18 Nov 2026</span></th><th>C11<br><span class='sub'>this design</span></th></tr>"

    def rows(ks, mark):
        return "".join(f"<tr><td>{escape(k)}</td><td class='{'diff' if mark else ''}'>{escape(str(t10.get(k, '—')))}</td>"
                       f"<td class='{'diff' if mark else ''}'>{escape(str(t11.get(k, '—')))}</td></tr>" for k in ks)

    h = [f"<style>{CSS}</style><section class='cmp' id='compare'><h2>C10 and C11 side by side</h2>",
         "<p>The table shows <b>only what changed</b> (areas on the grid lines, the one measure both designs share). Below it, the same floor of C10 and C11 "
         "side by side, with every room or terrace that changed <b>outlined in orange</b>.</p>",
         f"<table>{head}{rows(differ, True)}</table>",
         f"<details><summary>Unchanged ({len(same)} items)</summary><table>{head}{rows(same, False)}</table></details>", "<div class='tabs'>"]
    panes = [("main", "Main floor"), ("lower", "Lower floor"), ("road", "Road level"), ("sec", "Sections")]
    for i, (k, lab) in enumerate(panes):
        h.append(f"<input type='radio' name='cmpt' id='t-{k}'{' checked' if i == 0 else ''}><label for='t-{k}'>{lab}</label>")
    v = int(time.time())
    for k, lab in panes:
        h.append(f"<div class='pane' id='p-{k}'><div class='side'>")
        if k == "sec":
            h.append("<figure><a href='../990_2026-11-18_claude-c10/drawings/sections.png'><img src='../990_2026-11-18_claude-c10/drawings/sections.png' alt='C10 sections'></a>"
                     "<figcaption><b>C10</b> · posts invented by the drawing, no stair cut</figcaption></figure>")
            h.append("<figure><a href='drawings/sections.png'><img src='drawings/sections.png' alt='C11 sections'></a>"
                     "<figcaption><b>C11</b> · every column and wall from the structure model; every outdoor stair cut</figcaption></figure>")
        else:
            c10c, c11c = caps[k]
            h.append(f"<figure><a href='compare/c10-{k}.png?v={v}'><img src='compare/c10-{k}.png?v={v}' alt='C10 {lab}'></a>"
                     f"<figcaption><b>C10</b> · changed: {escape(', '.join(c10c) or 'nothing')}</figcaption></figure>")
            h.append(f"<figure><a href='compare/c11-{k}.png?v={v}'><img src='compare/c11-{k}.png?v={v}' alt='C11 {lab}'></a>"
                     f"<figcaption><b>C11</b> · changed or new: {escape(', '.join(c11c) or 'nothing')}</figcaption></figure>")
        h.append("</div></div>")
    h.append("</div></section>")
    return "".join(h)
