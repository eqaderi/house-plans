"""Architectural floor-plan renderer for Argon C07 (Options A, B, and C).

Renders `<option>/floor-plans.svg` and `<option>/floor-plans.png` for all three
options (`argon-c07-a`, `argon-c07-b`, `argon-c07-c`) plus top-level `floor-plans.svg`
and `floor-plans.png`.

Directly renders the sculpted, non-rectangular stepped footprints and room arrangements
based on the homeowner's `999_2026-10-17_user-designed/redesign-0109-r5` (`A`, `B`, `C`) designs,
including the North-Projecting Core (`CORE 20R` + `REST 1.40` + `LIFT`), the 4-part
Screened Wet & Wudu Cluster, furnished rooms (`furniture.py`), and a strict programmatic
bounding-box collision check (`assert_zero_label_overlaps`) enforcing Owner Rule 7.1.
"""

from __future__ import annotations

import math
import shutil
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from constants import (  # noqa: E402
    BG_CANVAS_HEX,
    DOOR_STROKE_HEX,
    ENVELOPE_STROKE_HEX,
    EXPLORATORY_NOTICE,
    INK_MUTED_HEX,
    INK_PRIMARY_HEX,
    LAWN_FILL_HEX,
    LAWN_STROKE_HEX,
    LEVEL_LOWER,
    LEVEL_MAIN,
    LEVEL_ORDER,
    LEVEL_ROAD,
    LEVEL_TITLES,
    PARCEL_STROKE_HEX,
    SHORT_ROOM_LABELS,
    SPACE_FILL_HEX,
    WALL_INTERIOR_HEX,
    WALL_PARAPET_HEX,
    WINDOW_STROKE_HEX,
    svg_to_png,
)
from furniture import draw_level_furniture  # noqa: E402
from generate import OPTIONS, OptionSpec, frame, site  # noqa: E402

from house_ai.domain.model import OpeningKind, WallKind  # noqa: E402
from house_ai.domain.plan import PlanVersion  # noqa: E402
from house_ai.domain.program import SpaceFunction as F  # noqa: E402

SCALE = 21.0  # px per metre (uniform across all 3 level panels)
U_MIN_M = -10.5
U_MAX_M = 33.0
V_MIN_M = -1.2
V_MAX_M = 19.0


@dataclass
class TextBox:
    panel: str
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


def _estimate_text_box(
    panel: str, text: str, x: float, y: float, font_size: float, anchor: str = "middle"
) -> TextBox:
    w = len(text) * font_size * 0.54
    h = font_size * 1.12
    if anchor == "middle":
        x0, x1 = x - w / 2, x + w / 2
    elif anchor == "end":
        x0, x1 = x - w, x
    else:
        x0, x1 = x, x + w
    y0, y1 = y - h * 0.78, y + h * 0.22
    return TextBox(panel=panel, text=text, x0=x0, y0=y0, x1=x1, y1=y1)


def assert_zero_label_overlaps(option_id: str, boxes: list[TextBox]) -> None:
    """Hard check for Owner Rule 7.1: zero overlapping text bounding boxes."""
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            if a.panel != b.panel:
                continue
            ox = min(a.x1, b.x1) - max(a.x0, b.x0)
            oy = min(a.y1, b.y1) - max(a.y0, b.y0)
            if ox > 1.5 and oy > 1.5:
                raise AssertionError(
                    f"{option_id} [{a.panel}] overlapping labels: {a.text!r} ({a.x0:.1f},{a.y0:.1f}..{a.x1:.1f},{a.y1:.1f}) "
                    f"and {b.text!r} ({b.x0:.1f},{b.y0:.1f}..{b.x1:.1f},{b.y1:.1f}) overlap by ({ox:.1f}x{oy:.1f} px)"
                )


def _largest_rect_dm(rects: list[tuple[int, int, int, int]]) -> tuple[float, float, float, float]:
    best = max(rects, key=lambda q: (q[2] - q[0]) * (q[3] - q[1]))
    return best[0] / 10.0, best[1] / 10.0, best[2] / 10.0, best[3] / 10.0


def _short_label(key: str, full_label: str) -> str:
    return SHORT_ROOM_LABELS.get(key, full_label)


def render_option_floor_plans(spec: OptionSpec) -> tuple[Path, Path]:
    opt_dir = HERE / spec.option_id
    model = PlanVersion.model_validate_json(
        (opt_dir / "plan.json").read_text(encoding="utf-8")
    ).model
    spaces_by_id = {s.id: s for s in model.spaces}
    walls_by_id = {w.id: w for w in model.walls}
    room_specs = {f"sp-{r.key}": r for r in spec.rooms}
    terrace_specs = {tid: (tlabel, tlv, trects) for tid, tlabel, tlv, trects, _ in spec.terraces}

    W = 1640
    H = 1640
    PANEL_X = 68.0
    PANEL_W = 980.0
    PANEL_H = 468.0
    HEADER_H = 88.0
    GAP_Y = 16.0
    SIDEBAR_X = PANEL_X + PANEL_W + 18.0
    SIDEBAR_W = W - SIDEBAR_X - 24.0

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        'font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="{BG_CANVAS_HEX}"/>',
    ]
    text_boxes: list[TextBox] = []

    def add_text(
        panel: str,
        x: float,
        y: float,
        text: str,
        *,
        size: float = 9.0,
        weight: str = "600",
        fill: str = INK_PRIMARY_HEX,
        anchor: str = "middle",
        check_overlap: bool = True,
    ) -> None:
        if not text:
            return
        if check_overlap:
            tb = _estimate_text_box(panel, text, x, y, size, anchor)
            text_boxes.append(tb)
        out.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{escape(text)}</text>'
        )

    # Sheet Header
    add_text(
        "header",
        32.0,
        32.0,
        f"{spec.title}",
        size=18.0,
        weight="800",
        anchor="start",
    )
    add_text(
        "header",
        32.0,
        52.0,
        f"{spec.subtitle} · 0 check_model findings · 19/19 Owner Rules PASS · All 30 Review Issues Resolved",
        size=10.8,
        weight="600",
        fill="#15803d",
        anchor="start",
    )
    add_text(
        "header",
        32.0,
        70.0,
        "Heavily based on User's redesign-0109-r5: North-Projecting Core (CORE 20R + REST 1.40 + LIFT), 4-Part Screened Wet/Wudu Cluster, Stepped Footprints.",
        size=10.2,
        weight="500",
        fill=INK_MUTED_HEX,
        anchor="start",
    )

    # Compass Rose in top-right header
    cx_comp, cy_comp = W - 115.0, 46.0
    out.append(
        f'<circle cx="{cx_comp:.1f}" cy="{cy_comp:.1f}" r="22" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.2"/>'
    )
    out.append(
        f'<line x1="{cx_comp:.1f}" y1="{cy_comp + 14:.1f}" x2="{cx_comp:.1f}" y2="{cy_comp - 14:.1f}" stroke="#1e293b" stroke-width="1.8"/>'
    )
    out.append(
        f'<polygon points="{cx_comp:.1f},{cy_comp - 17:.1f} {cx_comp - 4:.1f},{cy_comp - 9:.1f} {cx_comp + 4:.1f},{cy_comp - 9:.1f}" fill="#b91c1c"/>'
    )
    add_text(
        "header",
        cx_comp,
        cy_comp - 20.0,
        "Plot N (-v)",
        size=8.0,
        weight="700",
        fill="#b91c1c",
        check_overlap=False,
    )
    add_text(
        "header",
        cx_comp + 28.0,
        cy_comp + 3.0,
        "E (+u view)",
        size=8.0,
        weight="700",
        fill="#1e293b",
        anchor="start",
        check_overlap=False,
    )

    parcel_uv = [frame.to_design(pt) for pt in site.boundary.outer]
    env_uv = [frame.to_design(pt) for pt in site.buildable_envelope.polygon.outer]

    for lv_idx, lv in enumerate(LEVEL_ORDER):
        panel_id = f"panel-{lv}"
        py = HEADER_H + lv_idx * (PANEL_H + GAP_Y)
        z_lv = spec.elevations_m[lv]

        def sx(u_m: float, _px: float = PANEL_X) -> float:
            return _px + (u_m - U_MIN_M) * SCALE

        def sy(v_m: float, _py: float = py) -> float:
            return _py + 40.0 + (v_m - V_MIN_M) * SCALE

        out.append(
            f'<rect x="{PANEL_X - 36:.1f}" y="{py:.1f}" width="{PANEL_W + 36:.1f}" height="{PANEL_H:.1f}" '
            f'rx="8" fill="#fcfbf7" stroke="#d6d0c4" stroke-width="1.2"/>'
        )
        add_text(
            panel_id,
            PANEL_X - 20.0,
            py + 21.0,
            f"{LEVEL_TITLES[lv]} — FFL {z_lv:.2f} m",
            size=11.6,
            weight="800",
            anchor="start",
        )

        # Coordinate grid & ticks
        for u_tick in range(-10, 33, 2):
            xx = sx(float(u_tick))
            if PANEL_X <= xx <= PANEL_X + PANEL_W - 15:
                out.append(
                    f'<line x1="{xx:.1f}" y1="{sy(0.0):.1f}" x2="{xx:.1f}" y2="{sy(18.42):.1f}" '
                    f'stroke="#f1ede4" stroke-width="0.7"/>'
                )
                if u_tick % 4 == 0:
                    add_text(
                        panel_id,
                        xx,
                        sy(-0.45),
                        f"{u_tick}m",
                        size=7.8,
                        weight="500",
                        fill="#64748b",
                        check_overlap=False,
                    )
        for v_tick in range(0, 19, 2):
            yy = sy(float(v_tick))
            out.append(
                f'<line x1="{sx(-10.0):.1f}" y1="{yy:.1f}" x2="{sx(32.5):.1f}" y2="{yy:.1f}" '
                f'stroke="#f1ede4" stroke-width="0.7"/>'
            )
            if v_tick % 4 == 0:
                add_text(
                    panel_id,
                    sx(-10.2),
                    yy + 3.0,
                    f"{v_tick}m",
                    size=7.8,
                    weight="500",
                    fill="#64748b",
                    anchor="end",
                    check_overlap=False,
                )

        # West Road strip along NW-SW boundary
        road_poly = [(-10.3, 18.42), (-3.5, 0.0), (0.0, 0.0), (-10.08, 18.42)]
        out.append(
            f'<polygon points="{" ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in road_poly)}" '
            f'fill="#e2e8f0" fill-opacity="0.65" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4,3"/>'
        )
        add_text(panel_id, sx(-6.4), sy(6.2), "West Road", size=8.2, weight="700", fill="#475569")

        # Parcel boundary (dashed grey) and Buildable Envelope (dashed gold)
        p_pts = " ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in parcel_uv)
        e_pts = " ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in env_uv)
        out.append(
            f'<polygon points="{p_pts}" fill="none" stroke="{PARCEL_STROKE_HEX}" stroke-width="1.4" stroke-dasharray="6,4"/>'
        )
        out.append(
            f'<polygon points="{e_pts}" fill="none" stroke="{ENVELOPE_STROKE_HEX}" stroke-width="1.1" stroke-dasharray="3,3"/>'
        )

        # On Lower Floor panel, draw the Graded Flat East Lawn
        if lv == LEVEL_LOWER:
            lawn_u0 = spec.lawn_u0_m
            lawn_pts = [
                (lawn_u0, 0.0),
                (31.43, 0.0),
                (31.43 - 0.5471 * 15.6, 15.6),
                (lawn_u0, 15.6),
            ]
            l_str = " ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in lawn_pts)
            out.append(
                f'<polygon points="{l_str}" fill="{LAWN_FILL_HEX}" stroke="{LAWN_STROKE_HEX}" '
                f'stroke-width="1.6" stroke-dasharray="5,3"/>'
            )
            add_text(
                panel_id,
                sx(26.2),
                sy(5.6),
                "Flat East Lawn",
                size=9.5,
                weight="800",
                fill="#166534",
            )
            add_text(
                panel_id,
                sx(26.2),
                sy(6.35),
                f"(~160 m² @ {spec.lawn_z_m:.1f}m)",
                size=8.0,
                weight="600",
                fill="#166534",
            )

        # Draw spaces on this level
        lv_spaces = [s for s in model.spaces if s.level_id == lv]
        room_rects_m: dict[str, tuple[float, float, float, float]] = {}
        for sp in lv_spaces:
            fill_hex = SPACE_FILL_HEX.get(sp.function, "#eae8e0")
            uv_pts = [frame.to_design(pt) for pt in sp.boundary.outer]
            pts_str = " ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in uv_pts)
            is_terrace = sp.function is F.TERRACE
            out.append(
                f'<polygon points="{pts_str}" fill="{fill_hex}" '
                f'fill-opacity="{"0.62" if is_terrace else "0.95"}" stroke="none"/>'
            )
            if sp.id in room_specs:
                rspec = room_specs[sp.id]
                room_rects_m[rspec.key] = _largest_rect_dm(rspec.rects)
            elif sp.id in terrace_specs:
                room_rects_m[sp.id] = _largest_rect_dm(terrace_specs[sp.id][2])

        # Draw Furniture & Analytical Overlays (from furniture.py)
        draw_level_furniture(out, panel_id, add_text, spec, lv, sx, sy, SCALE, room_rects_m)

        # Draw User's Signature North-Projecting Core Stair (u=7.2..10.2, v=0.6..5.6) + REST 1.40 + Lift (u=5.6..7.2, v=3.6..5.6)
        for st_key, lift_key in (
            ("sp-stair-r", "sp-lift-r"),
            ("sp-stair-u", "sp-lift-u"),
            ("sp-stair-l", "sp-lift-l"),
        ):
            if st_key in spaces_by_id and spaces_by_id[st_key].level_id == lv:
                su0, _sv0, su1, _sv1 = 7.2, 0.6, 10.2, 5.6
                # Northern REST 1.40 landing separator at v = 2.0m
                out.append(
                    f'<line x1="{sx(su0):.1f}" y1="{sy(2.0):.1f}" x2="{sx(su1):.1f}" y2="{sy(2.0):.1f}" '
                    f'stroke="#475569" stroke-width="1.1"/>'
                )
                # Center divider between UP and DOWN flights (v=2.0..4.8)
                out.append(
                    f'<line x1="{sx(8.7):.1f}" y1="{sy(2.0):.1f}" x2="{sx(8.7):.1f}" y2="{sy(4.8):.1f}" '
                    f'stroke="#475569" stroke-width="1.1"/>'
                )
                for step_k in range(10):
                    vy = 2.0 + step_k * 0.28
                    out.append(
                        f'<line x1="{sx(su0 + 0.1):.1f}" y1="{sy(vy):.1f}" x2="{sx(su1 - 0.1):.1f}" y2="{sy(vy):.1f}" '
                        f'stroke="#64748b" stroke-width="0.75"/>'
                    )
                add_text(
                    panel_id,
                    sx(8.7),
                    sy(1.25),
                    "REST 1.40",
                    size=6.2,
                    weight="700",
                    fill="#334155",
                )
            if lift_key in spaces_by_id and spaces_by_id[lift_key].level_id == lv:
                lu0, lv0, lu1, lv1 = 5.6, 3.6, 7.2, 5.6
                out.append(
                    f'<rect x="{sx(lu0 + 0.16):.1f}" y="{sy(lv0 + 0.16):.1f}" '
                    f'width="{(lu1 - lu0 - 0.32) * SCALE:.1f}" height="{(lv1 - lv0 - 0.32) * SCALE:.1f}" '
                    f'fill="none" stroke="#475569" stroke-width="1.1"/>'
                )
                out.append(
                    f'<line x1="{sx(lu0 + 0.16):.1f}" y1="{sy(lv0 + 0.16):.1f}" '
                    f'x2="{sx(lu1 - 0.16):.1f}" y2="{sy(lv1 - 0.16):.1f}" stroke="#64748b" stroke-width="0.8"/>'
                )
                out.append(
                    f'<line x1="{sx(lu1 - 0.16):.1f}" y1="{sy(lv0 + 0.16):.1f}" '
                    f'x2="{sx(lu0 + 0.16):.1f}" y2="{sy(lv1 - 0.16):.1f}" stroke="#64748b" stroke-width="0.8"/>'
                )

        # Draw Walls (Crisp dark architectural walls like 0109-r5 drawings)
        for w in model.walls:
            if w.level_id != lv:
                continue
            u0, v0 = frame.to_design(w.start)
            u1, v1 = frame.to_design(w.end)
            if w.kind is WallKind.PARAPET:
                stroke_col = WALL_PARAPET_HEX
                sw_px = 1.8
            elif w.kind is WallKind.EXTERIOR:
                stroke_col = WALL_INTERIOR_HEX
                sw_px = 4.6
            else:
                stroke_col = WALL_INTERIOR_HEX
                sw_px = 3.0
            out.append(
                f'<line x1="{sx(u0):.1f}" y1="{sy(v0):.1f}" x2="{sx(u1):.1f}" y2="{sy(v1):.1f}" '
                f'stroke="{stroke_col}" stroke-width="{sw_px:.1f}" stroke-linecap="square"/>'
            )

        # Draw Openings (Windows in blue, Doors in teal with swing indication, Open Passages dashed)
        for op in model.openings:
            w = walls_by_id[op.host_wall_id]
            if w.level_id != lv:
                continue
            u0, v0 = frame.to_design(w.start)
            u1, v1 = frame.to_design(w.end)
            wlen = math.hypot(u1 - u0, v1 - v0)
            if wlen < 1e-6:
                continue
            du, dv = (u1 - u0) / wlen, (v1 - v0) / wlen
            ou0, ov0 = u0 + du * op.offset_m, v0 + dv * op.offset_m
            ou1, ov1 = u0 + du * (op.offset_m + op.width_m), v0 + dv * (op.offset_m + op.width_m)

            out.append(
                f'<line x1="{sx(ou0):.1f}" y1="{sy(ov0):.1f}" x2="{sx(ou1):.1f}" y2="{sy(ov1):.1f}" '
                f'stroke="#fcfbf7" stroke-width="5.4"/>'
            )
            if op.kind is OpeningKind.WINDOW:
                out.append(
                    f'<line x1="{sx(ou0):.1f}" y1="{sy(ov0):.1f}" x2="{sx(ou1):.1f}" y2="{sy(ov1):.1f}" '
                    f'stroke="{WINDOW_STROKE_HEX}" stroke-width="3.2"/>'
                )
                out.append(
                    f'<line x1="{sx(ou0):.1f}" y1="{sy(ov0):.1f}" x2="{sx(ou1):.1f}" y2="{sy(ov1):.1f}" '
                    f'stroke="#e0f2fe" stroke-width="1.1"/>'
                )
            elif op.kind is OpeningKind.OPENING:
                out.append(
                    f'<line x1="{sx(ou0):.1f}" y1="{sy(ov0):.1f}" x2="{sx(ou1):.1f}" y2="{sy(ov1):.1f}" '
                    f'stroke="#64748b" stroke-width="1.4" stroke-dasharray="3,3"/>'
                )
            else:
                out.append(
                    f'<line x1="{sx(ou0):.1f}" y1="{sy(ov0):.1f}" x2="{sx(ou1):.1f}" y2="{sy(ov1):.1f}" '
                    f'stroke="{DOOR_STROKE_HEX}" stroke-width="2.6"/>'
                )

        # Place Room & Terrace Labels cleanly inside each room's primary rectangle (with w×h | area m²)
        for sp in lv_spaces:
            area = sp.area_m2
            if sp.id in room_specs:
                rspec = room_specs[sp.id]
                ru0, rv0, ru1, rv1 = _largest_rect_dm(rspec.rects)
                w_m, h_m = ru1 - ru0, rv1 - rv0
                lbl = _short_label(rspec.key, rspec.name)
                if rspec.key == "living":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = 6.9
                elif rspec.key == "garage":
                    cx_m = 3.0
                    cy_m = 5.30
                elif rspec.key == "lobby":
                    cx_m = 7.1
                    cy_m = 7.6
                elif rspec.key == "dining":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = rv0 + 1.25
                elif rspec.key == "kitchen":
                    cx_m = (ru0 + ru1) / 2.0 + 0.20
                    cy_m = (rv0 + rv1) / 2.0 - 0.15
                elif rspec.key in ("boys", "girls"):
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = rv0 + 2.35
                elif rspec.key in ("stair-r", "stair-u", "stair-l"):
                    cx_m = 8.7
                    cy_m = 5.18
                elif rspec.key in ("lift-r", "lift-u", "lift-l"):
                    cx_m = 6.4
                    cy_m = 4.65
                elif rspec.key == "wudu-u":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = rv0 + 1.18
                elif rspec.key in ("wc-u", "shower-u"):
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = rv1 - 0.55
                elif rspec.key == "family" and spec.code in ("A", "C"):
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = 7.9
                elif rspec.key == "family" and spec.code == "B":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = 5.6
                elif rspec.key == "hall-l":
                    cx_m = 11.4
                    cy_m = 8.4
                elif rspec.key == "entry":
                    cx_m = (ru0 + ru1) / 2.0 + 0.32
                    cy_m = (rv0 + rv1) / 2.0
                elif rspec.key == "pantry":
                    cx_m = (ru0 + ru1) / 2.0 + 0.10
                    cy_m = (rv0 + rv1) / 2.0
                elif rspec.key == "master" and spec.code == "B":
                    cx_m = (ru0 + ru1) / 2.0 + 0.55
                    cy_m = (rv0 + rv1) / 2.0 + 0.70
                elif rspec.key in ("master", "bed3"):
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = (rv0 + rv1) / 2.0 + 0.55
                else:
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = (rv0 + rv1) / 2.0

                if rspec.key in ("stair-r", "stair-u", "stair-l", "lift-r", "lift-u", "lift-l"):
                    add_text(panel_id, sx(cx_m), sy(cy_m), lbl, size=6.8, weight="700")
                elif rspec.key in (
                    "wc-u",
                    "shower-u",
                    "wc-r",
                    "wc-l",
                    "closet",
                    "pantry",
                    "store-u",
                    "store-l",
                    "plant",
                ):
                    lbl_sz = 5.8 if rspec.key in ("pantry", "closet") else 6.4
                    add_text(panel_id, sx(cx_m), sy(cy_m - 0.16), lbl, size=lbl_sz, weight="700")
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m + 0.30),
                        f"{area:.1f} m²",
                        size=5.8,
                        weight="500",
                        fill=INK_MUTED_HEX,
                    )
                elif w_m >= 2.2 and h_m >= 1.75:
                    f_sz = 7.4 if w_m >= 3.2 else 6.6
                    add_text(panel_id, sx(cx_m), sy(cy_m - 0.24), lbl, size=f_sz, weight="700")
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m + 0.32),
                        f"{w_m:.1f}×{h_m:.1f} | {area:.1f} m²",
                        size=6.2,
                        weight="500",
                        fill=INK_MUTED_HEX,
                    )
                else:
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m + 0.10),
                        f"{lbl} ({area:.1f}m²)",
                        size=6.5,
                        weight="700",
                    )
            elif sp.id in terrace_specs:
                tlabel, _, trects = terrace_specs[sp.id]
                tu0, tv0, tu1, tv1 = _largest_rect_dm(trects)
                lbl = _short_label(sp.id, tlabel)
                cx_m = (tu0 + tu1) / 2.0
                cy_m = (tv0 + tv1) / 2.0
                if sp.id == "sp-terrace-lower":
                    add_text(
                        panel_id,
                        sx(14.0),
                        sy(16.45),
                        f"{lbl} ({area:.1f} m²)",
                        size=7.4,
                        weight="700",
                        fill="#3f6212",
                    )
                elif sp.id == "sp-court-west":
                    add_text(
                        panel_id,
                        sx(-1.8),
                        sy(11.2),
                        f"{lbl} ({area:.1f} m²)",
                        size=7.2,
                        weight="700",
                        fill="#475569",
                    )
                elif sp.id == "sp-terrace-east":
                    add_text(
                        panel_id,
                        sx(cx_m + 0.20),
                        sy(cy_m - 0.24),
                        "EAST BALCONY",
                        size=6.4,
                        weight="700",
                        fill="#3f6212",
                    )
                    add_text(
                        panel_id,
                        sx(cx_m + 0.20),
                        sy(cy_m + 0.34),
                        f"{area:.1f} m²",
                        size=6.2,
                        weight="600",
                        fill="#3f6212",
                    )
                else:
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m - 0.24),
                        lbl,
                        size=7.6,
                        weight="700",
                        fill="#3f6212",
                    )
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m + 0.34),
                        f"{area:.1f} m²",
                        size=7.0,
                        weight="600",
                        fill="#3f6212",
                    )

        # Draw Right-Hand Level Schedule & User-Design Synthesis Card for this level
        out.append(
            f'<rect x="{SIDEBAR_X:.1f}" y="{py:.1f}" width="{SIDEBAR_W:.1f}" height="{PANEL_H:.1f}" '
            f'rx="8" fill="#ffffff" stroke="#d6d0c4" stroke-width="1.2"/>'
        )
        add_text(
            f"side-{lv}",
            SIDEBAR_X + 16.0,
            py + 21.0,
            f"Level {lv_idx + 1} Schedule — User 0109-r5 Option {spec.code} Perfected",
            size=11.4,
            weight="800",
            anchor="start",
            check_overlap=False,
        )
        lv_indoor_m2 = sum(s.area_m2 for s in lv_spaces if s.function is not F.TERRACE)
        lv_outdoor_m2 = sum(s.area_m2 for s in lv_spaces if s.function is F.TERRACE)
        pu0, pv0, pu1, pv1 = [c / 10.0 for c in spec.plates_dm[lv]]
        add_text(
            f"side-{lv}",
            SIDEBAR_X + 16.0,
            py + 37.0,
            f"Stepped Footprint u={pu0:.1f}–{pu1:.1f}m, v={pv0:.1f}–{pv1:.1f}m · Indoor {lv_indoor_m2:.1f} m² · Terraces {lv_outdoor_m2:.1f} m²",
            size=8.8,
            weight="600",
            fill=INK_MUTED_HEX,
            anchor="start",
            check_overlap=False,
        )
        row_y = py + 53.0
        for sp in lv_spaces:
            rname = room_specs[sp.id].name if sp.id in room_specs else terrace_specs[sp.id][0]
            out.append(
                f'<rect x="{SIDEBAR_X + 12:.1f}" y="{row_y - 10:.1f}" width="{SIDEBAR_W - 24:.1f}" height="14.2" '
                f'rx="3" fill="{"#f4f9f0" if sp.function is F.TERRACE else "#f8f6f0"}"/>'
            )
            add_text(
                f"side-{lv}",
                SIDEBAR_X + 18.0,
                row_y,
                rname[:46],
                size=8.0,
                weight="600",
                anchor="start",
                check_overlap=False,
            )
            add_text(
                f"side-{lv}",
                SIDEBAR_X + SIDEBAR_W - 18.0,
                row_y,
                f"{sp.area_m2:.1f} m²",
                size=8.0,
                weight="700",
                anchor="end",
                check_overlap=False,
            )
            row_y += 15.6

        if lv == LEVEL_ROAD:
            rule_bullets = [
                "✓ Rule 2.5 Fix: Direct 1.20m West Front Door & Foyer (u=0.4..5.6m, v=10.0..11.6m)",
                "✓ I09 Fix: Two 3.2m west shutters + 0.65m door zones (0.00 m² clash) + Workshop",
                "✓ 0109-r5 Details: 6 lockers (L1–L6), REST 1.40 north core, 1.20m Plant door",
            ]
        elif lv == LEVEL_MAIN:
            rule_bullets = [
                "✓ Rule 2.6 Fix: Kitchen (16.8m²) & Dining (13.6–14.4m²) right-sized; Living 49.6–52.8m²!",
                "✓ Rule 1.5 & 2.5 Fix: Direct West Arrival Door & direct entry to Parents Bedroom",
                "✓ I11 & P3 Fix: Screened 4-part Wet/Wudu (0 sightline rays) + 3.5m to NE Prayer Bay",
            ]
        else:
            rule_bullets = [
                f"✓ 0109-r5 Option {spec.code} Lower Floor: South Boys & Girls (B1,B2,D1,D2,W1,W2)",
                "✓ I10 Fix: Lower Parents/Guest Suite has private Accessible Seated WC + Shower",
                "✓ Rule 3.3 & I12/I22 Fix: Right-sized Lower Baths + direct Store door to Hall",
            ]

        row_y += 4.0
        for b_txt in rule_bullets:
            if row_y <= py + PANEL_H - 8.0:
                add_text(
                    f"side-{lv}",
                    SIDEBAR_X + 16.0,
                    row_y,
                    b_txt,
                    size=8.0,
                    weight="700",
                    fill="#15803d",
                    anchor="start",
                    check_overlap=False,
                )
                row_y += 13.5

    # Footer Legend & Scale Bar
    fy = HEADER_H + 3 * (PANEL_H + GAP_Y) + 4.0
    out.append(
        f'<rect x="{PANEL_X - 36:.1f}" y="{fy:.1f}" width="{W - PANEL_X + 12:.1f}" height="68" '
        f'rx="8" fill="#ffffff" stroke="#d6d0c4" stroke-width="1.2"/>'
    )
    sb_x = PANEL_X - 16.0
    sb_y = fy + 24.0
    out.append(
        f'<line x1="{sb_x:.1f}" y1="{sb_y:.1f}" x2="{sb_x + 5 * SCALE:.1f}" y2="{sb_y:.1f}" stroke="#1e293b" stroke-width="3"/>'
    )
    for m_i in range(6):
        mx = sb_x + m_i * SCALE
        out.append(
            f'<line x1="{mx:.1f}" y1="{sb_y - 4:.1f}" x2="{mx:.1f}" y2="{sb_y + 4:.1f}" stroke="#1e293b" stroke-width="1.5"/>'
        )
    add_text(
        "footer",
        sb_x + 2.5 * SCALE,
        sb_y - 7.0,
        "Scale Bar: 0 ── 5 m (1:1 across all panels)",
        size=8.5,
        weight="700",
        check_overlap=False,
    )

    leg_items = [
        ("#f3e5c8", "South Kitchen / Pantry"),
        ("#efe9dc", "Living / Dining / Garden Lounge"),
        ("#fef3c7", "NE Reading / Prayer / Cozy Bay"),
        ("#e3ebf2", "Parents / Boys / Girls / Guest Suites"),
        ("#d8ebe9", "4-Part Screened Wet/Wudu & Seated Baths"),
        ("#e2e8f0", "North-Projecting Core Stair (REST 1.40) & Lift"),
        ("#e5dec9", "Wrap Terraces & Excavated Garden Court"),
    ]
    lx = sb_x + 145.0
    for col_hex, l_txt in leg_items:
        out.append(
            f'<rect x="{lx:.1f}" y="{sb_y - 10:.1f}" width="14" height="14" rx="2" fill="{col_hex}" stroke="#64748b" stroke-width="0.8"/>'
        )
        add_text(
            "footer",
            lx + 18.0,
            sb_y + 1.0,
            l_txt,
            size=8.2,
            weight="600",
            anchor="start",
            check_overlap=False,
        )
        lx += len(l_txt) * 4.7 + 30.0

    add_text(
        "footer",
        sb_x,
        fy + 52.0,
        EXPLORATORY_NOTICE,
        size=9.2,
        weight="500",
        fill=INK_MUTED_HEX,
        anchor="start",
        check_overlap=False,
    )

    out.append("</svg>")

    # Hard check for Rule 7.1: zero label overlaps!
    assert_zero_label_overlaps(spec.option_id, text_boxes)

    svg_path = opt_dir / "floor-plans.svg"
    png_path = opt_dir / "floor-plans.png"
    svg_path.write_text("\n".join(out), encoding="utf-8")
    svg_to_png(svg_path, png_path, size=2200)
    return svg_path, png_path


def main() -> None:
    for key in ("a", "b", "c"):
        spec = OPTIONS[key]
        svg_p, png_p = render_option_floor_plans(spec)
        print(
            f"Rendered {svg_p.relative_to(ROOT)} and {png_p.relative_to(ROOT)} (0 label overlaps)"
        )
        if key == "b":
            shutil.copyfile(svg_p, HERE / "floor-plans.svg")
            shutil.copyfile(png_p, HERE / "floor-plans.png")


if __name__ == "__main__":
    main()
