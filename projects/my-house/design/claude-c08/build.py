"""Render every C08 option: one sheet per level, a section sheet, checks, and index.html."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from checks import check_option  # noqa: E402
from engine import draw_level, draw_sections, earthworks  # noqa: E402
from options import OPTIONS  # noqa: E402


def png(svg: Path, width: int = 2200) -> None:
    subprocess.run(["rsvg-convert", "-w", str(width), "-o", str(svg.with_suffix(".png")), str(svg)], check=True)


def main(only: str | None = None) -> None:
    results = []
    for make in OPTIONS:
        opt = make()
        if only and opt.code != only:
            continue
        out = HERE / opt.code.lower()
        out.mkdir(exist_ok=True)
        label_issues = {}
        for key, lv in opt.levels.items():
            svg = out / f"{key}.svg"
            r = draw_level(lv, opt, svg)
            label_issues[key] = r["label_collisions"]
            png(svg)
        ew = earthworks(opt)
        draw_sections(opt, out / "sections.svg", ew)
        png(out / "sections.svg")
        report = check_option(opt, ew)
        report["label_collisions"] = label_issues
        report["earthworks"] = ew
        (out / "checks.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
        results.append((opt, report))
        print(opt.code, "fails:", [c["id"] for c in report["rules"] if c["status"] == "FAIL"],
              "labels:", {k: v for k, v in label_issues.items() if v})
    if not only:
        from report import build
        build(results, HERE)
    return results


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
