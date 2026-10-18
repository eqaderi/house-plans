"""SVG views of derived section/elevation geometry, at equal axis scales."""

from __future__ import annotations

import math
from html import escape


def section_fragment(section: dict, x0=0, y0=0, width=1100, height=300) -> str:
    points = [p for c in section["cuts"] for p in c["polygon"]]
    points += [
        (p[k], p[z])
        for p in section["ground"]
        if p["status"] != "unknown"
        for k, z in (("start_m", "start_z_m"), ("end_m", "end_z_m"))
    ]
    if not points:
        points = [(0, 0), (section.get("length_m", 10), 3)]
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    zmin, zmax = min(p[1] for p in points) - 1, max(p[1] for p in points) + 1
    scale = min((width - 80) / max(1, xmax - xmin), (height - 90) / max(1, zmax - zmin))

    def xy(p):
        return (x0 + 40 + (p[0] - xmin) * scale, y0 + height - 38 - (p[1] - zmin) * scale)

    view_label = (
        "True section" if section["method"].startswith("vertical_plane") else "Facade projection"
    )
    out = [
        f'<text x="{x0 + 14}" y="{y0 + 20}" font-size="13" font-weight="bold">'
        f"{escape(section['id'])} — {view_label}</text>",
        f'<text x="{x0 + 14}" y="{y0 + 37}" font-size="10">'
        "LOCAL metres · equal horizontal/vertical scale · conceptual, not engineered</text>",
    ]
    colors = {
        "wall": "#9c8b75",
        "slab": "#555",
        "stair": "#d0b485",
        "window": "#d4eefb",
        "door": "#fff",
        "platform": "#ba9159",
    }
    for cut in section["cuts"]:
        path = []
        for ring in [cut["polygon"], *cut.get("holes", [])]:
            coords = [xy(p) for p in ring]
            path.append("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in coords) + " Z")
        out.append(
            f'<path data-subject-id="{escape(cut["subject_id"])}" '
            f'd="{" ".join(path)}" fill="{colors.get(cut["kind"], "#ddd")}" '
            'fill-rule="evenodd" stroke="#333" stroke-width="0.7"/>'
        )
    for ground in section["ground"]:
        if ground["status"] == "unknown":
            a, _ = xy((ground["start_m"], zmin))
            b, _ = xy((ground["end_m"], zmin))
            y = y0 + height - 23
            out.append(
                f'<path d="M{a:.3f},{y} H{b:.3f}" stroke="#b00020" '
                'stroke-dasharray="4 3"/><title>Terrain unknown on this interval</title>'
            )
        else:
            a, b = xy((ground["start_m"], ground["start_z_m"]))
            c, d = xy((ground["end_m"], ground["end_z_m"]))
            out.append(
                f'<path d="M{a:.3f},{b:.3f} L{c:.3f},{d:.3f}" '
                'stroke="#8b4f1c" stroke-width="2" fill="none"/>'
            )
    target_step = (zmax - zmin) * 30 / max(1, height - 90)
    magnitude = 10 ** math.floor(math.log10(max(target_step, 0.01)))
    step = next(f * magnitude for f in (1, 2, 5, 10) if f * magnitude >= target_step)
    tick_values = [step * i for i in range(math.ceil(zmin / step), math.floor(zmax / step) + 1)]
    for z in tick_values:
        _, y = xy((xmin, z))
        out.append(f'<text x="{x0 + 3}" y="{y:.3f}" font-size="8">{z:+.2f}</text>')
    if any(g["status"] == "unknown" for g in section["ground"]) or section["unknowns"]:
        out.append(
            f'<text x="{x0 + 40}" y="{y0 + height - 5}" font-size="10" fill="#b00020">'
            "Unknown: unsupported terrain intervals and/or stair geometry</text>"
        )
    return "".join(out)


def render_sections_svg(sections: list[dict]) -> str:
    height = max(1, len(sections)) * 330
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" '
        f'viewBox="0 0 1100 {height}" font-family="Arial, sans-serif">',
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    for i, section in enumerate(sections):
        out.append(section_fragment(section, y0=i * 330, height=320))
    return "".join(out) + "</svg>\n"
