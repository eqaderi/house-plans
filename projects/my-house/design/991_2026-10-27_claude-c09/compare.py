"""Side-by-side comparison of options: a table of what differs, and plans with the differences outlined."""

from __future__ import annotations

import subprocess
import time
from html import escape
from pathlib import Path

from engine import ENVELOPE, PARCEL, R, draw_level, room_dims
from shapely.geometry import Point
from shapely.ops import unary_union

LEVEL_KEYS = ("road", "main", "lower")
LEVEL_NAMES = {"road": "Road level", "main": "Main floor", "lower": "Lower floor + garden"}


def _sig(item) -> str:
    return f"{item.name}|{item.geom.normalize().wkt}"


def differing_ids(options, key: str) -> list[set[str]]:
    """Per option: ids of rooms/terraces on this level that are not identical in every other option."""
    sigs = [{x.id: _sig(x) for x in o.levels[key].rooms + o.levels[key].terraces} for o in options]
    out = []
    for i, s in enumerate(sigs):
        others = [t for j, t in enumerate(sigs) if j != i]
        out.append({k for k, v in s.items() if any(t.get(k) != v for t in others)})
    return out


def _where(lv, room) -> str:
    """Plain-language position of a room on its plate (N/NE/E/SE/S/SW/W/NW/centre)."""
    u0, v0, u1, v1 = lv.footprint.bounds
    c = room.geom.centroid
    fu = (c.x - u0) / (u1 - u0)
    fv = (c.y - v0) / (v1 - v0)
    ns = "N" if fv < 0.36 else ("S" if fv > 0.64 else "")
    ew = "W" if fu < 0.3 else ("E" if fu > 0.78 else "")
    return (ns + ew) or "centre"


def _corner(lv, u, v) -> str:
    p = Point(u, v)
    for r in lv.rooms:
        if r.name and r.geom.contains(p):
            return r.name.title()
    for t in lv.terraces:
        if t.name and t.geom.contains(p):
            return t.name.title() + " (outdoor)"
    return "—"


def metrics(o, rep) -> dict[str, str]:
    m, lo = o.levels["main"], o.levels["lower"]
    rows: dict[str, str] = {}
    fb = m.footprint.bounds
    south = sorted([r for r in m.rooms if r.main and r.kind != "sleep" and abs(r.geom.bounds[3] - fb[3]) < 0.05],
                   key=lambda r: r.geom.bounds[0])
    rows["Main floor: south side, west → east"] = " → ".join(r.name.title() for r in south)
    master = m.room("master")
    rows["Master bedroom"] = f"{_where(m, master)} · {room_dims(master)[2]:.0f} m²"
    extras = [f"{r.name.title()} {room_dims(r)[2]:.0f} m²" for r in m.rooms
              if r.id in ("ens", "dress", "prayer", "linen")]
    extras += [f"{t.name.title()} {t.geom.area:.0f} m²" for t in m.terraces if t.id == "t-ne"]
    rows["Master suite extras"] = ", ".join(extras)
    for rid, label in (("living", "Living"), ("kitchen", "Kitchen"), ("dining", "Dining")):
        r = m.room(rid)
        rows[label] = f"{room_dims(r)[2]:.0f} m² · {_where(m, r)}"
    joined = any({d.a, d.b} == {"dining", "living"} and d.kind == "open" for d in m.doors)
    rows["Dining ↔ living"] = "open, one L-shaped room" if joined else "separate rooms"
    lb = lo.footprint.bounds
    rows["Lower floor NE corner"] = _corner(lo, lb[2] - 1.2, lb[1] + 2.9)
    rows["Lower floor east middle"] = _corner(lo, lb[2] - 1.2, (lb[1] + lb[3]) / 2)
    rows["Lower floor SE corner"] = _corner(lo, lb[2] - 1.2, lb[3] - 1.2)
    for rid, label in (("guest", "Grandparents' room"), ("gens", "Grandparents' seated ensuite"),
                       ("lounge", "Garden lounge"), ("hall-l", "Lower family hall"), ("study", "Study / play")):
        r = next((x for x in lo.rooms if x.id == rid), None)
        rows[label] = f"{room_dims(r)[2]:.0f} m² · {_where(lo, r)}" if r else "none"
    for key in LEVEL_KEYS:
        ts = [t for t in o.levels[key].terraces if t.kind in ("terrace", "deck") and t.name]
        rows[f"{LEVEL_NAMES[key]}: terraces"] = ", ".join(f"{t.name.title()} {t.geom.area:.0f}" for t in ts) + " m²" if ts else "none"
    gross = sum(lv.footprint.area for lv in o.levels.values())
    cover = unary_union([lv.footprint for lv in o.levels.values()]).area
    garden = ENVELOPE.intersection(R(lb[2], -1, 40, 18)).area
    rows["Total floor area"] = f"{gross:.0f} m²"
    rows["Ground covered"] = f"{cover:.0f} m² ({100 * cover / PARCEL.area:.0f}% of field)"
    rows["Main / lower floor ends at"] = f"u {fb[2]:.1f} / u {lb[2]:.1f} m"
    rows["East garden (inside setbacks)"] = f"{garden:.0f} m²"
    ew = rep["earthworks"]
    rows["Earthwork (inferred)"] = f"cut {ew['total_cut_m3']:.0f} m³ · fill {ew['total_fill_m3']:.0f} m³"
    rows["Your open decisions"] = str(sum(c["status"] == "open" for c in rep["rules"]))
    return rows


def _items(o, key, ids) -> list[str]:
    lv = o.levels[key]
    out = []
    for x in lv.rooms + lv.terraces:
        if x.id in ids and x.name:
            area = room_dims(x)[2] if hasattr(x, "main") else round(x.geom.area)
            out.append(f"{x.name.title()} ({area:.0f} m²)")
    return out


def render(results, out: Path) -> dict:
    """Write compare/<code>-<level>.png with differing rooms outlined; return per-level item lists."""
    cdir = out / "compare"
    cdir.mkdir(exist_ok=True)
    options = [o for o, _ in results]
    diffs = {}
    for key in LEVEL_KEYS:
        ids = differing_ids(options, key)
        diffs[key] = [_items(o, key, i) for o, i in zip(options, ids)]
        if not any(ids):
            continue
        for o, i in zip(options, ids):
            svg = cdir / f"{o.code.lower()}-{key}.svg"
            x0, y0, x1, y1 = draw_level(o.levels[key], o, svg, highlight=i)["crop"]
            txt = svg.read_text()
            head, rest = txt.split(">", 1)
            head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" '
                    f'viewBox="{x0:.0f} {y0:.0f} {x1 - x0:.0f} {y1 - y0:.0f}"')
            svg.write_text(head + ">" + rest)
            subprocess.run(["rsvg-convert", "-w", "1400", "-o", str(svg.with_suffix(".png")), str(svg)], check=True)
    return diffs


CSS = """
.cmp table td.diff{background:rgba(240,138,60,.13)}
.cmp .tabs input{display:none}.cmp .tabs label{display:inline-block;padding:6px 14px;border:1px solid var(--line);border-radius:16px;margin:0 6px 8px 0;cursor:pointer;color:var(--accent)}
.cmp .tabs input:checked+label{background:var(--accent);color:#fff;border-color:var(--accent)}
.cmp .pane{display:none}.cmp #t-main:checked~#p-main,.cmp #t-lower:checked~#p-lower,.cmp #t-road:checked~#p-road,.cmp #t-sec:checked~#p-sec{display:block}
.cmp .side{display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));gap:12px}
.cmp .side figure{margin:0}.cmp figcaption{font-size:13px;color:var(--muted)}.cmp figcaption b{color:var(--ink)}
@media (max-width:760px){.cmp .side{grid-template-columns:1fr}}
.cmp details{margin:6px 0 18px}.cmp summary{cursor:pointer;color:var(--muted)}
"""


def section(results, out: Path) -> str:
    diffs = render(results, out)
    options = [o for o, _ in results]
    table = [metrics(o, r) for o, r in results]
    keys = list(table[0])
    differ = [k for k in keys if len({t[k] for t in table}) > 1]
    same = [k for k in keys if k not in differ]
    head = "<tr><th></th>" + "".join(f"<th>{escape(o.code)}<br><span class='sub'>{escape(o.title)}</span></th>" for o in options) + "</tr>"

    def rows(ks, mark):
        return "".join(
            f"<tr><td>{escape(k)}</td>" + "".join(f"<td class='{'diff' if mark else ''}'>{escape(t[k])}</td>" for t in table) + "</tr>"
            for k in ks)

    h = [f"<style>{CSS}</style><section class='cmp' id='compare'><h2>Compare the options</h2>",
         "<p>The table shows <b>only what differs</b>. Below it, the same floor of each option sits side by side; "
         "rooms that differ are outlined in orange dashes.</p>",
         f"<table>{head}{rows(differ, True)}</table>",
         f"<details><summary>Identical in every option ({len(same)} items)</summary><table>{head}{rows(same, False)}</table></details>",
         "<div class='tabs'>"]
    panes = [("main", "Main floor"), ("lower", "Lower floor"), ("road", "Road level"), ("sec", "Sections")]
    for i, (k, lab) in enumerate(panes):
        h.append(f"<input type='radio' name='cmpt' id='t-{k}'{' checked' if i == 0 else ''}><label for='t-{k}'>{lab}</label>")
    for k, lab in panes:
        h.append(f"<div class='pane' id='p-{k}'><div class='side' style='--n:{len(options)}'>")
        for idx, o in enumerate(options):
            d = o.code.lower()
            if k == "sec":
                h.append(f"<figure><img src='{d}/sections.png' alt='{o.code} sections'><figcaption><b>{o.code}</b></figcaption></figure>")
                continue
            items = diffs[k][idx]
            if not any(diffs[k]):
                src = f"{d}/{k}.png"
                cap = "Identical in every option."
            else:
                src = f"compare/{d}-{k}.png?v={int(time.time())}"
                cap = ("Different here: " + ", ".join(items)) if items else "Same as the others on this floor."
            h.append(f"<figure><a href='{src}'><img src='{src}' alt='{o.code} {lab}'></a>"
                     f"<figcaption><b>{o.code}</b> · {escape(cap)}</figcaption></figure>")
        h.append("</div></div>")
    h.append("</div></section>")
    return "".join(h)
