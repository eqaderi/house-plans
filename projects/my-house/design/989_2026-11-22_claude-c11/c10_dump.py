"""Read C10 with C10's own code, in its own process, for the C10 ↔ C11 comparison (rule 8.5).

    c10_dump.py doors                      -> JSON [[level, a, b], ...]
    c10_dump.py items                      -> JSON {level: [{id, name, kind, wkt, area}], ...}
    c10_dump.py render <level> <svg> <ids> -> C10 plan of that level, cropped, <ids> outlined in orange
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

C10 = Path(__file__).resolve().parent.parent / "990_2026-11-18_claude-c10"
sys.path[0] = str(C10)  # never import C11's modules here

from design import option  # noqa: E402
from engine import draw_level  # noqa: E402


def main() -> None:
    opt = option()
    cmd = sys.argv[1]
    if cmd == "doors":
        print(json.dumps([[k, d.a, d.b] for k, lv in opt.levels.items() for d in lv.doors]))
    elif cmd == "items":
        out = {}
        for k, lv in opt.levels.items():
            out[k] = [{"id": x.id, "name": x.name, "kind": x.kind, "wkt": x.geom.wkt, "area": round(x.geom.area, 2), "z": getattr(x, "z", lv.z)}
                      for x in lv.rooms + lv.terraces]
            out[k + "_footprint"] = lv.footprint.wkt
        print(json.dumps(out))
    elif cmd == "render":
        key, svg, ids = sys.argv[2], Path(sys.argv[3]), set(filter(None, sys.argv[4].split(",")))
        x0, y0, x1, y1 = draw_level(opt.levels[key], opt, svg, highlight=ids)["crop"]
        txt = svg.read_text()
        head, rest = txt.split(">", 1)
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" '
                f'viewBox="{x0:.0f} {y0:.0f} {x1 - x0:.0f} {y1 - y0:.0f}"')
        svg.write_text(head + ">" + rest)
        subprocess.run(["rsvg-convert", "-w", "1400", "-o", str(svg.with_suffix(".png")), str(svg)], check=True)


if __name__ == "__main__":
    main()
