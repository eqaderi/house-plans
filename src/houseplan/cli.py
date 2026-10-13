"""houseplan command line.

  hp check  <design.yaml>            schema, geometry and rule checks
  hp sketch <design.yaml>...         check, then one PDF + PNG per level: for showing options
  hp zoom   <design.yaml> [--room R]  1:50 close-ups of every room, for inspection
  hp build  <design.yaml> [--out D]  final stage: DXF/PDF/PNG per level, IFC, report, read-back
  hp ground <design.yaml> [--at x,y]  interpolated ground Z under each level's corners, or at points
  hp doctor                          which external tools are available
  hp dwg2dxf <file.dwg> <out_dir>    convert a survey DWG with ODA, original untouched
  hp survey <file.dxf>               units, layers, extents, outlines, measured heights

Exit status is 1 when any error is found, so hooks and CI can gate on it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from . import checks, family, geometry, model, rules, usability
from .checks import Finding

ROOT = Path(__file__).resolve().parents[2]


def _analyse(path: str):
    design = model.load(path)
    geo = geometry.build(design)
    findings = checks.run_all(design, geo) + family.run_family(design, geo) + usability.run_usability(design, geo) + rules.run_rules(design, geo)
    return design, geo, findings


def _print(findings: list[Finding]) -> None:
    order = {"error": 0, "warning": 1, "info": 2}
    for f in sorted(findings, key=lambda f: (order[f.severity], f.code, f.subject)):
        print(f"{f.severity.upper():7} {f.code:28} {f.subject:14} {f.message}")
    n = {s: sum(f.severity == s for f in findings) for s in order}
    print(f"\n{n['error']} errors, {n['warning']} warnings, {n['info']} info")


def _schedule(design, geo) -> list[dict]:
    rows = []
    for lv in sorted(design.levels, key=lambda l: l.ffl):
        for rg in geo[lv.id].rooms.values():
            rows.append({
                "level": lv.id,
                "room": rg.room.id,
                "name": rg.room.name,
                "name_fa": rg.room.name_fa,
                "use": rg.room.use.value,
                "net_area_m2": round(rg.area_mm2 / 1e6, 3),
                "clear_height_mm": lv.clear_height,
            })
    return rows


def _report_md(design, geo, findings, files) -> str:
    lines = [f"# {design.project.name}: check report", ""]
    errors = [f for f in findings if f.severity == "error"]
    lines.append(f"**Status: {'FAILED' if errors else 'PASSED'}** ({len(errors)} errors, {sum(f.severity == 'warning' for f in findings)} warnings)")
    lines += ["", "## Room schedule (net areas from wall faces)", "", "| Level | Room | Name | Use | Net area m² | Clear height mm |", "|---|---|---|---|---:|---:|"]
    for r in _schedule(design, geo):
        lines.append(f"| {r['level']} | {r['room']} | {r['name']} {r['name_fa'] or ''} | {r['use']} | {r['net_area_m2']:.2f} | {r['clear_height_mm']} |")
    for lv in sorted(design.levels, key=lambda l: l.ffl):
        lg = geo[lv.id]
        lines.append(f"\n{lv.id}: gross footprint {lg.footprint.area / 1e6:.2f} m², walls {lg.walls_union.area / 1e6:.2f} m², rooms {sum(r.area_mm2 for r in lg.rooms.values()) / 1e6:.2f} m²")
    lines += ["", "## Findings", "", "| Severity | Code | Subject | Message |", "|---|---|---|---|"]
    for f in findings:
        lines.append(f"| {f.severity} | {f.code} | {f.subject} | {f.message} |")
    lines += ["", "## Files", ""] + [f"- `{p}`" for p in files]
    lines += ["", "Generated from the design spec. Not for construction or permit until reviewed and signed by a licensed engineer (مهندس دارای پروانه اشتغال)."]
    return "\n".join(lines) + "\n"


def cmd_check(args) -> int:
    try:
        _, _, findings = _analyse(args.design)
    except ValidationError as e:
        print(f"SPEC INVALID\n{e}")
        return 1
    _print(findings)
    return 1 if any(f.severity == "error" for f in findings) else 0


def cmd_sketch(args) -> int:
    from . import render
    from .drawing import plan_dxf, site_dxf

    worst = 0
    for path in args.design:
        try:
            design, geo, findings = _analyse(path)
        except ValidationError as e:
            print(f"SPEC INVALID {path}\n{e}")
            worst = 1
            continue
        errors = [f for f in findings if f.severity == "error"]
        out = ROOT / "out" / Path(path).stem
        out.mkdir(parents=True, exist_ok=True)
        status = f"SKETCH - {len(errors)} errors" if errors else "SKETCH - checks passed"
        print(f"== {path}")
        _print([f for f in findings if f.severity != "info"])
        for lv in design.levels:
            doc, sheet = plan_dxf(design, geo[lv.id], scale=args.scale, status=status)
            png = out / f"sketch-{lv.id}.png"
            render.render(doc, sheet, str(out / f"sketch-{lv.id}.pdf"), str(png))
            print(f"   {png}")
        if design.site is not None:
            doc, sheet = site_dxf(design, geo, status=status)
            png = out / "sketch-site.png"
            render.render(doc, sheet, str(out / "sketch-site.pdf"), str(png))
            print(f"   {png}")
        worst = max(worst, 1 if errors else 0)
    return worst


def cmd_zoom(args) -> int:
    """Close-ups of every room at 1:50, for looking at junctions, doors and labels."""
    from . import render
    from .drawing import plan_dxf

    design, geo, _ = _analyse(args.design)
    out = ROOT / "out" / Path(args.design).stem / "zoom"
    out.mkdir(parents=True, exist_ok=True)
    for lv in design.levels:
        doc, _ = plan_dxf(design, geo[lv.id], scale=args.scale)
        for rid, rg in geo[lv.id].rooms.items():
            if rg.outline is None or (args.room and rid not in args.room):
                continue
            png = out / f"{lv.id}-{rid}.png"
            render.close_up(doc, rg.outline.bounds, args.scale, str(png))
            print(png)
    return 0


def cmd_build(args) -> int:
    from . import ifc, render, verify
    from .drawing import plan_dxf, site_dxf

    try:
        design, geo, findings = _analyse(args.design)
    except ValidationError as e:
        print(f"SPEC INVALID\n{e}")
        return 1
    out = Path(args.out or ROOT / "out" / Path(args.design).stem)
    out.mkdir(parents=True, exist_ok=True)
    status = "FAILED" if any(f.severity == "error" for f in findings) else "passed"
    files: list[str] = []
    for lv in design.levels:
        doc, sheet = plan_dxf(design, geo[lv.id], scale=args.scale, status=status)
        stem = out / f"plan-{lv.id}"
        doc.saveas(f"{stem}.dxf")
        render.render(doc, sheet, f"{stem}.pdf", f"{stem}.png")
        files += [f"{stem}.dxf", f"{stem}.pdf", f"{stem}.png"]
        findings += verify.verify_dxf(f"{stem}.dxf", geo[lv.id])
        findings += verify.verify_text(f"{stem}.dxf", geo[lv.id], args.scale)
    if design.site is not None:
        doc, sheet = site_dxf(design, geo, status=status)
        stem = out / "site"
        doc.saveas(f"{stem}.dxf")
        render.render(doc, sheet, f"{stem}.pdf", f"{stem}.png")
        files += [f"{stem}.dxf", f"{stem}.pdf", f"{stem}.png"]
        lowest = min(design.levels, key=lambda l: l.ffl).id
        findings += [f for f in verify.verify_text(f"{stem}.dxf", geo[lowest], sheet.scale) if f.code.startswith("DXF_TEXT")]
    ifc_path = out / "model.ifc"
    ifc.build_ifc(design, geo).write(str(ifc_path))
    files.append(str(ifc_path))
    findings += verify.verify_ifc(str(ifc_path), design, geo)
    (out / "report.json").write_text(json.dumps({"findings": [f.as_dict() for f in findings], "rooms": _schedule(design, geo)}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "report.md").write_text(_report_md(design, geo, findings, files), encoding="utf-8")
    _print(findings)
    print(f"\nwrote {out}")
    return 1 if any(f.severity == "error" for f in findings) else 0


def cmd_ground(args) -> int:
    """Ground Z from the site's spot heights: at --at points, else at every
    corner of each level's outline and of the plot."""
    from .terrain import Terrain

    design = model.load(args.design)
    if design.site is None:
        print("no site block: no spot heights to interpolate")
        return 1
    t = Terrain(design.site)
    datum = design.project.datum.survey_z_mm
    print(t.describe())
    print(f"datum ±0.00 = survey Z {datum / 1000:.3f} m" if datum is not None else "datum ±0.00 not tied to the survey yet: heights are survey Z only")
    if args.at:
        targets = [("point", tuple(int(v) for v in a.split(",")), None) for a in args.at]
    else:
        geo = geometry.build(design)
        targets = [(f"{lv.id} corner", (round(x), round(y)), lv) for lv in sorted(design.levels, key=lambda l: l.ffl)
                   for p in getattr(geo[lv.id].footprint, "geoms", [geo[lv.id].footprint]) if not p.is_empty
                   for x, y in p.exterior.coords[:-1]]
        targets += [("plot corner", tuple(p), None) for p in design.site.boundary]
    for what, (x, y), lv in targets:
        g = t.z_at(x, y)
        if g is None:
            print(f"  {what:14} ({x}, {y})  outside the surveyed points: unknown")
            continue
        rel = f"  {(g.z_mm - datum) / 1000:+.3f} m to ±0.00" if datum is not None else ""
        if datum is not None and lv is not None:
            d = g.z_mm - datum - lv.ffl
            rel += f", {d / 1000:+.3f} m to {lv.id} floor ({'buried' if d > 0 else 'floor above ground'})"
        print(f"  {what:14} ({x}, {y})  Z {g.z_mm / 1000:.3f}{rel}  from {'/'.join(g.corners)} (longest edge {g.longest_edge_mm / 1000:.2f} m)")
    return 0


def cmd_doctor(args) -> int:
    from .tools import doctor

    return doctor()


def cmd_survey(args) -> int:
    from .survey import survey

    return survey(args.dxf)


def cmd_dwg2dxf(args) -> int:
    from .tools import dwg_to_dxf

    return dwg_to_dxf(Path(args.dwg), Path(args.out_dir))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("design")
    c.set_defaults(fn=cmd_check)
    k = sub.add_parser("sketch")
    k.add_argument("design", nargs="+")
    k.add_argument("--scale", type=int, default=100)
    k.set_defaults(fn=cmd_sketch)
    z = sub.add_parser("zoom")
    z.add_argument("design")
    z.add_argument("--room", nargs="*")
    z.add_argument("--scale", type=int, default=50)
    z.set_defaults(fn=cmd_zoom)
    b = sub.add_parser("build")
    b.add_argument("design")
    b.add_argument("--out")
    b.add_argument("--scale", type=int, default=100)
    b.set_defaults(fn=cmd_build)
    g = sub.add_parser("ground")
    g.add_argument("design")
    g.add_argument("--at", nargs="*", help="spec points x,y in mm")
    g.set_defaults(fn=cmd_ground)
    d = sub.add_parser("doctor")
    d.set_defaults(fn=cmd_doctor)
    v = sub.add_parser("survey")
    v.add_argument("dxf")
    v.set_defaults(fn=cmd_survey)
    w = sub.add_parser("dwg2dxf")
    w.add_argument("dwg")
    w.add_argument("out_dir")
    w.set_defaults(fn=cmd_dwg2dxf)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
