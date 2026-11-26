"""Render C11: plans, sections, the support sheet, the site plan, the 3D model, the checks and index.html.

Rebuild from the repository root:
    .venv/bin/python projects/my-house/design/989_2026-11-22_claude-c11/build.py [--plans-only]
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import checks as C  # noqa: E402
import design as D  # noqa: E402
import engine as E  # noqa: E402
import structure as S  # noqa: E402


def png(svg: Path, width: int = 2200) -> None:
    subprocess.run(["rsvg-convert", "-w", str(width), "-o", str(svg.with_suffix(".png")), str(svg)], check=True)


def claims(opt, gm, ew) -> list[tuple]:
    """Numbers written in the notes, recomputed from the geometry: (what, written, measured, tolerance)."""
    L = opt.levels
    main, lower, road = L["main"], L["lower"], L["road"]
    lw, ld, _ = E.room_dims(main.room("living"))
    gd = next(d for d in road.doors if d.kind == "fire")
    ld_ = next(d for d in road.doors if d.b == "lift-r")
    walk = abs(ld_.u - gd.u) + abs(gd.v - (ld_.v + 0.75))
    boys = lower.room("boys").geom.bounds
    plant = road.room("plant").geom.bounds
    beds = [f.geom.bounds for f in lower.furniture if f.geom.geom_type == "Polygon" and abs(f.geom.area - 1.8) < 0.01]
    gap = min(abs(b[0] - a[2]) for a in beds for b in beds if a != b and abs(a[1] - b[1]) < 0.01 and b[0] > a[2]) if len(beds) > 1 else 0
    return [
        ("living clear width (note: 5.2)", 5.2, lw, 0.05), ("living clear depth (note: 6.5)", 6.5, ld, 0.06),
        ("garage door → lift door walk (note: 4.4 m)", 4.4, round(walk, 2), 0.15),
        ("court stair risers (note: 24 × 15.1 cm)", 24, sum(f.risers for f in D.outdoor_stairs()[1].flights), 0),
        ("lawn stair risers (note: 16)", 16, sum(f.risers for f in D.outdoor_stairs()[2].flights), 0),
        ("laundry clear m² (note: about 5)", 5.0, E.room_dims(lower.room("laundry"))[2], 0.5),
        ("open ground in front of the children's windows (note: 2.4 m)", 2.4, round(18.42 - (boys[3] + E.EXT_OUT), 2), 0.05),
        ("grandparents' transfer space (note: 1.75 m)", 1.75, round(gap, 2), 0.01),
        ("plant room on the grid (note: 5.0 × 1.7 m)", 5.0 * 1.7, round((plant[2] - plant[0]) * (plant[3] - plant[1]), 2), 0.01),
        ("master balcony starts south of the north wall (note: 1.5 m)", 1.5, round(main.terraces[3].geom.bounds[1] - 1.1, 2), 0.01),
        ("stools at the island (note: 3)", 3, sum(1 for f in main.furniture if f.geom.geom_type == "Polygon" and abs(f.geom.area - math.pi * 0.19 ** 2) < 0.02
                                                 and main.room("kitchen").geom.contains(f.geom.centroid)), 0),
    ]


def main() -> None:
    opt = D.build()
    gm = E.GroundModel(opt)
    els = D.structure()
    swalls = S.site_walls(gm, els)
    gd = C.guards(opt, gm, els, swalls)
    out = HERE / "drawings"
    out.mkdir(exist_ok=True)
    labels, drawn_plans = {}, {}

    def overlay(lv):
        def f(sheet):
            ids = S.draw_on_plan(sheet, lv, els, swalls)
            for ln in gd["lines"].get(lv.key, []):
                sheet.path(ln, "guard")
            for t in lv.terraces:  # outlets (dots), overflow (ring) and fall (arrow), from the same table the water check reads
                if t.id in D.WATER:
                    fall, outs, ovf, _ = D.WATER[t.id]
                    for o in outs:
                        sheet.path(E.Point(o).buffer(0.12), "drain")
                    sheet.path(E.Point(ovf).buffer(0.12).exterior, "fall")
                    c = t.geom.representative_point()
                    sheet.path(E.LineString([(c.x - fall[0] * 0.6, c.y - fall[1] * 0.6), (c.x + fall[0] * 0.6, c.y + fall[1] * 0.6)]), "fall")
            return ids
        return f

    for key, lv in opt.levels.items():
        svg = out / f"{key}.svg"
        r = E.draw_level(lv, opt, svg, overlay=overlay(lv))
        labels[key] = r["label_collisions"]
        drawn_plans[key] = r["drawn"]
        png(svg)
    ew = E.earthworks(gm)
    drawn_sec = E.draw_sections(opt, gm, out / "sections.svg", els, swalls)
    png(out / "sections.svg", 2250)
    rep = S.support_report(opt, gm, els)
    S.draw_support_sheet(opt, gm, els, rep, out / "supports.svg", (D.GRID_U, D.GRID_V))
    png(out / "supports.svg", 2400)
    from model3d import build_model  # noqa: E402

    model, drawn_3d = build_model(opt, gm, els, swalls)
    c10_doors = set()
    dump = subprocess.run([sys.executable, str(HERE / "c10_dump.py"), "doors"], capture_output=True, text=True, check=True)
    for lvk, a, b in json.loads(dump.stdout):
        c10_doors.add((lvk, frozenset((a, b))))
    court = next(t for t in opt.levels["main"].terraces if t.id == "court-w").geom.area
    porch = next(t for t in opt.levels["main"].terraces if t.id == "porch").geom.area
    extras = {"support": rep, "wall_over_wall": S.wall_over_wall(opt, els), "columns_beams": S.columns_and_beams(opt, gm, els),
              "lower_foundations": S.lower_foundations(opt, els), "routes": C.routes(opt, gm),
              "guards": gd, "water": D.WATER, "pans": D.WC_PANS, "claims": claims(opt, gm, ew), "facades": C.facades(opt, gm),
              "c10_doors": c10_doors, "labels": labels, "court_area": court, "porch_area": porch}
    report = C.check_option(opt, ew, gm, els, swalls, {"plans": drawn_plans, "sections": drawn_sec, "3d": drawn_3d},
                            D.outdoor_stairs(), extras)
    report["label_collisions"] = labels
    report["earthworks"] = ew
    report["support"] = rep.slabs
    report["wall_over_wall"] = extras["wall_over_wall"]
    report["site_walls"] = [{"id": w.id, "from": [round(c, 2) for c in w.geom.coords[0]], "to": [round(c, 2) for c in w.geom.coords[-1]],
                             "top": w.z_top, "bottom": w.z_bot, "height": round(w.height, 2)} for w in swalls]
    report["elements"] = [{"id": e.id, "kind": e.kind, "z_bot": e.z_bot, "z_top": e.z_top, "t": e.t, "note": e.note} for e in els]
    report["claims"] = [list(c) for c in extras["claims"]]
    report["facades"] = extras["facades"]
    report["guards_m"] = round(gd["total_m"], 1)
    (HERE / "checks.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    fails = [(c["id"], c["evidence"][:400]) for c in report["rules"] if c["status"] == "FAIL"]
    print(opt.code, "FAIL:", len(fails))
    for f in fails:
        print("  ", f)
    print("labels:", {k: v for k, v in labels.items() if v})
    for r in ew["rows"]:
        print("  ", r["zone"], r["cut_m3"], r["fill_m3"], r["max_cut_m"], r["max_fill_m"])
    print("   total cut", ew["total_cut_m3"], "fill", ew["total_fill_m3"])
    if "--plans-only" in sys.argv:
        return
    from compare import section as compare_section  # noqa: E402
    from report import build  # noqa: E402
    from sitemap import draw_site  # noqa: E402

    draw_site(opt, gm, out / "site.svg")
    png(out / "site.svg")
    cmp_html = compare_section(opt, report, HERE)
    build(opt, gm, report, model, HERE, cmp_html, els, swalls)


if __name__ == "__main__":
    main()
