"""Render C10: one sheet per level, the section sheet, the 3D model, the checks and index.html."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from checks import check_option  # noqa: E402
from design import option  # noqa: E402
from engine import GroundModel, draw_level, draw_sections, earthworks  # noqa: E402


def png(svg: Path, width: int = 2200) -> None:
    subprocess.run(["rsvg-convert", "-w", str(width), "-o", str(svg.with_suffix(".png")), str(svg)], check=True)


def main() -> None:
    opt = option()
    gm = GroundModel(opt)
    out = HERE / "drawings"
    out.mkdir(exist_ok=True)
    labels = {}
    for key, lv in opt.levels.items():
        svg = out / f"{key}.svg"
        labels[key] = draw_level(lv, opt, svg)["label_collisions"]
        png(svg)
    ew = earthworks(gm)
    draw_sections(opt, gm, out / "sections.svg")
    png(out / "sections.svg")
    report = check_option(opt, ew, gm)
    report["label_collisions"] = labels
    report["earthworks"] = ew
    (HERE / "checks.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(opt.code, "fails:", [(c["id"], c["evidence"]) for c in report["rules"] if c["status"] == "FAIL"],
          "labels:", {k: v for k, v in labels.items() if v})
    for r in ew["rows"]:
        print("  ", r)
    print("   total cut", ew["total_cut_m3"], "fill", ew["total_fill_m3"])
    if "--plans-only" in sys.argv:
        return
    from model3d import build_model  # noqa: E402
    from report import build  # noqa: E402
    from sitemap import draw_site  # noqa: E402

    draw_site(opt, gm, out / "site.svg")
    png(out / "site.svg")
    model = build_model(opt, gm)
    build(opt, gm, report, model, HERE)


if __name__ == "__main__":
    main()
