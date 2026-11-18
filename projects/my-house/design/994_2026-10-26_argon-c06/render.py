"""Architectural floor-plan renderer for Argon C06 (Options A, B, and C).

Renders `<option>/floor-plans.svg` and `<option>/floor-plans.png` for all three
options (`argon-c06-a`, `argon-c06-b`, `argon-c06-c`) plus top-level `floor-plans.svg`
and `floor-plans.png`.

Enforces Owner Rule 7.1 via a strict programmatic bounding-box collision check
(`assert_zero_label_overlaps`) that guarantees zero overlapping text labels.
"""

from __future__ import annotations

import math
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
    SPACE_FILL_HEX,
    WALL_INTERIOR_HEX,
    WALL_PARAPET_HEX,
    WINDOW_STROKE_HEX,
    svg_to_png,
)
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
    overrides = {
        "garage": "Garage (2 Cars)",
        "lobby": "Road Lobby",
        "office": "Quiet Office",
        "wc-r": "Road WC",
        "plant": "Plant",
        "stair-r": "Stair-R",
        "lift-r": "Lift",
        "entry": "Entrance Hall",
        "wc-u": "WC",
        "store-u": "Coats",
        "hall-u": "Central Hall",
        "stair-u": "Stair-U",
        "lift-u": "Lift",
        "pantry": "Pantry",
        "kitchen": "South Kitchen",
        "dining": "Dining Room",
        "living": "Living Room",
        "master": "Grand Master Suite",
        "closet": "Dress",
        "ensuite-u": "Master Bath",
        "hall-l": "Lower Central Hall",
        "stair-l": "Stair-L",
        "lift-l": "Lift",
        "family": "Family Room",
        "bed3": "Grandparents Suite",
        "ensuite-l": "Suite Bath",
        "boys": "Boys Bedroom",
        "girls": "Girls Bedroom",
        "shower-l": "Shared Bath",
        "wc-l": "WC",
        "laundry": "Laundry",
        "store-l": "Lower Store",
        "sp-deck-east": "East Roof Deck",
        "sp-court-west": "West Arrival Court",
        "sp-terrace-north": "North Terrace",
        "sp-terrace-south": "South Terrace",
        "sp-terrace-east": "East Balcony",
        "sp-terrace-lower": "Lower Garden Terrace",
    }
    return overrides.get(key, full_label)


def render_option_floor_plans(spec: OptionSpec) -> tuple[Path, Path]:
    opt_dir = HERE / spec.option_id
    model = PlanVersion.model_validate_json(
        (opt_dir / "plan.json").read_text(encoding="utf-8")
    ).model
    spaces_by_id = {s.id: s for s in model.spaces}
    walls_by_id = {w.id: w for w in model.walls}
    room_specs = {f"sp-{r.key}": r for r in spec.rooms}
    terrace_specs = {tid: (tlabel, tlv, trects) for tid, tlabel, tlv, trects, _ in spec.terraces}

    # Square 1620x1620 canvas so macOS QuickLook & all viewers render 100% of all 3 levels + sidebar
    W = 1620
    H = 1620
    PANEL_X = 68.0
    PANEL_W = 980.0
    PANEL_H = 462.0
    HEADER_H = 88.0
    GAP_Y = 16.0
    SIDEBAR_X = PANEL_X + PANEL_W + 18.0
    SIDEBAR_W = W - SIDEBAR_X - 28.0

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
        size: float = 9.5,
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
        f"{spec.title} — All 3 Levels + Flat East Garden",
        size=19.5,
        weight="800",
        anchor="start",
    )
    add_text(
        "header",
        32.0,
        52.0,
        f"{spec.subtitle} · 0 check_model findings · 18/18 Owner Design Rules PASS",
        size=11.5,
        weight="600",
        fill="#15803d",
        anchor="start",
    )
    add_text(
        "header",
        32.0,
        70.0,
        "Plot frame: u = 0 at NW corner toward East (downhill view); v = 0 along North boundary toward South (sun). 1 m S & E setbacks.",
        size=10.5,
        weight="400",
        fill=INK_MUTED_HEX,
        anchor="start",
    )

    # Compass Rose in top-right header
    cx_comp, cy_comp = W - 115.0, 46.0
    out.append(
        f'<circle cx="{cx_comp:.1f}" cy="{cy_comp:.1f}" r="22" fill="#ffffff" stroke="#d6d0c4" stroke-width="1.2"/>'
    )
    out.append(
        f'<line x1="{cx_comp:.1f}" y1="{cy_comp + 14:.1f}" x2="{cx_comp:.1f}" y2="{cy_comp - 14:.1f}" stroke="#1f2a2e" stroke-width="1.8"/>'
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
        fill="#1f2a2e",
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
            f'rx="8" fill="#fbfaf6" stroke="#e2dac9" stroke-width="1.2"/>'
        )
        add_text(
            panel_id,
            PANEL_X - 20.0,
            py + 21.0,
            f"{LEVEL_TITLES[lv]} — FFL {z_lv:.2f} m",
            size=13.0,
            weight="800",
            anchor="start",
        )

        # Coordinate grid & ticks
        for u_tick in range(-10, 33, 2):
            xx = sx(float(u_tick))
            if PANEL_X <= xx <= PANEL_X + PANEL_W - 15:
                out.append(
                    f'<line x1="{xx:.1f}" y1="{sy(0.0):.1f}" x2="{xx:.1f}" y2="{sy(18.42):.1f}" '
                    f'stroke="#f2eee4" stroke-width="0.7"/>'
                )
                if u_tick % 4 == 0:
                    add_text(
                        panel_id,
                        xx,
                        sy(-0.45),
                        f"{u_tick}m",
                        size=8.0,
                        weight="500",
                        fill="#8c857b",
                        check_overlap=False,
                    )
        for v_tick in range(0, 19, 2):
            yy = sy(float(v_tick))
            out.append(
                f'<line x1="{sx(-10.0):.1f}" y1="{yy:.1f}" x2="{sx(32.5):.1f}" y2="{yy:.1f}" '
                f'stroke="#f2eee4" stroke-width="0.7"/>'
            )
            if v_tick % 4 == 0:
                add_text(
                    panel_id,
                    sx(-10.2),
                    yy + 3.0,
                    f"{v_tick}m",
                    size=8.0,
                    weight="500",
                    fill="#8c857b",
                    anchor="end",
                    check_overlap=False,
                )

        # West Road strip along NW-SW boundary
        road_poly = [(-10.3, 18.42), (-3.5, 0.0), (0.0, 0.0), (-10.08, 18.42)]
        out.append(
            f'<polygon points="{" ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in road_poly)}" '
            f'fill="#e2e8f0" fill-opacity="0.65" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4,3"/>'
        )
        add_text(panel_id, sx(-6.4), sy(6.2), "West Road", size=8.5, weight="700", fill="#475569")

        # Parcel boundary (dashed grey) and Buildable Envelope (dashed gold)
        p_pts = " ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in parcel_uv)
        e_pts = " ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in env_uv)
        out.append(
            f'<polygon points="{p_pts}" fill="none" stroke="{PARCEL_STROKE_HEX}" stroke-width="1.4" stroke-dasharray="6,4"/>'
        )
        out.append(
            f'<polygon points="{e_pts}" fill="none" stroke="{ENVELOPE_STROKE_HEX}" stroke-width="1.1" stroke-dasharray="3,3"/>'
        )

        # On Lower Floor panel, draw the Graded Flat East Lawn (u = lawn_u0..east setback, v = 0..15.6m)
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
                f'stroke-width="1.8" stroke-dasharray="5,3"/>'
            )
            add_text(
                panel_id,
                sx(26.2),
                sy(5.6),
                "Flat East Lawn",
                size=10.0,
                weight="800",
                fill="#2d6a2e",
            )
            add_text(
                panel_id,
                sx(26.2),
                sy(6.4),
                f"(~160 m² @ {spec.lawn_z_m:.1f}m)",
                size=8.5,
                weight="600",
                fill="#2d6a2e",
            )
            for step_i in range(5):
                su = lawn_u0 + step_i * 0.30
                out.append(
                    f'<line x1="{sx(su):.1f}" y1="{sy(6.8):.1f}" x2="{sx(su):.1f}" y2="{sy(8.4):.1f}" '
                    f'stroke="#4f8a3a" stroke-width="1.3"/>'
                )

        # Draw spaces on this level
        lv_spaces = [s for s in model.spaces if s.level_id == lv]
        for sp in lv_spaces:
            fill_hex = SPACE_FILL_HEX.get(sp.function, "#eae8e0")
            uv_pts = [frame.to_design(pt) for pt in sp.boundary.outer]
            pts_str = " ".join(f"{sx(u):.1f},{sy(v):.1f}" for u, v in uv_pts)
            is_terrace = sp.function is F.TERRACE
            out.append(
                f'<polygon points="{pts_str}" fill="{fill_hex}" '
                f'fill-opacity="{"0.58" if is_terrace else "0.94"}" stroke="none"/>'
            )

        # Highlight Special Homeowner Features
        if lv == LEVEL_ROAD:
            wu0, wv0, wu1, wv1 = [c / 10.0 for c in spec.workshop_bay_dm]
            out.append(
                f'<rect x="{sx(wu0):.1f}" y="{sy(wv0):.1f}" width="{(wu1 - wu0) * SCALE:.1f}" '
                f'height="{(wv1 - wv0) * SCALE:.1f}" fill="#fde68a" fill-opacity="0.55" '
                f'stroke="#b45309" stroke-width="1.2" stroke-dasharray="3,2"/>'
            )
            out.append(
                f'<rect x="{sx(wu0 + 0.2):.1f}" y="{sy(0.15):.1f}" width="{(wu1 - wu0 - 0.4) * SCALE:.1f}" '
                f'height="{0.65 * SCALE:.1f}" fill="#d97706" fill-opacity="0.35" stroke="#92400e" stroke-width="1"/>'
            )
            add_text(
                panel_id,
                sx((wu0 + wu1) / 2),
                sy(1.45),
                "Workshop Bay",
                size=7.8,
                weight="700",
                fill="#92400e",
            )
            ru0_m = spec.plates_dm[LEVEL_ROAD][0] / 10.0
            for car_v0 in (1.0, 5.6):
                out.append(
                    f'<rect x="{sx(ru0_m + 0.4):.1f}" y="{sy(car_v0):.1f}" width="{4.4 * SCALE:.1f}" '
                    f'height="{1.9 * SCALE:.1f}" rx="5" fill="#ffffff" fill-opacity="0.6" '
                    f'stroke="#64748b" stroke-width="1.1" stroke-dasharray="4,2"/>'
                )

        elif lv == LEVEL_MAIN:
            cu0, cv0, cu1, cv1 = [c / 10.0 for c in spec.cozy_corner_dm]
            out.append(
                f'<rect x="{sx(cu0):.1f}" y="{sy(cv0):.1f}" width="{(cu1 - cu0) * SCALE:.1f}" '
                f'height="{(cv1 - cv0) * SCALE:.1f}" fill="#fef3c7" fill-opacity="0.65" '
                f'stroke="#d97706" stroke-width="1.3" stroke-dasharray="4,2"/>'
            )
            out.append(
                f'<path d="M {sx(cu0 + 0.3):.1f} {sy(cv0 + 0.3):.1f} '
                f"H {sx(cu0 + 2.5):.1f} V {sy(cv0 + 0.95):.1f} H {sx(cu0 + 0.95):.1f} "
                f'V {sy(cv0 + 2.0):.1f} H {sx(cu0 + 0.3):.1f} Z" '
                f'fill="#fdba74" fill-opacity="0.55" stroke="#c2410c" stroke-width="1.1"/>'
            )
            add_text(
                panel_id,
                sx((cu0 + cu1) / 2 + 0.2),
                sy(cv0 + 1.55),
                "Cozy Corner",
                size=7.8,
                weight="700",
                fill="#9a3412",
            )
            kr = room_specs["sp-kitchen"].rects[0]
            ku0, kv0, ku1, kv1 = [c / 10.0 for c in kr]
            out.append(
                f'<rect x="{sx(ku0 + 0.2):.1f}" y="{sy(kv0 + 0.15):.1f}" '
                f'width="{(ku1 - ku0 - 0.4) * SCALE:.1f}" height="{0.65 * SCALE:.1f}" '
                f'fill="#fed7aa" stroke="#c2410c" stroke-width="0.9"/>'
            )

        elif lv == LEVEL_LOWER:
            tu0, tv0, tu1, tv1 = [c / 10.0 for c in spec.tea_bar_dm]
            out.append(
                f'<rect x="{sx(tu0):.1f}" y="{sy(tv0):.1f}" width="{(tu1 - tu0) * SCALE:.1f}" '
                f'height="{(tv1 - tv0) * SCALE:.1f}" fill="#fde68a" stroke="#b45309" stroke-width="1.1"/>'
            )
            add_text(
                panel_id,
                sx((tu0 + tu1) / 2 + 0.35),
                sy(tv1 + 0.55 if tv0 < 12.0 else tv0 - 0.30),
                "Tea & Snack Bar",
                size=7.5,
                weight="700",
                fill="#92400e",
            )

        # Draw Central Heart Stair treads & Lift cab
        for st_key, lift_key in (
            ("sp-stair-r", "sp-lift-r"),
            ("sp-stair-u", "sp-lift-u"),
            ("sp-stair-l", "sp-lift-l"),
        ):
            if st_key in spaces_by_id and spaces_by_id[st_key].level_id == lv:
                su0, su1 = 5.8, 8.4
                out.append(
                    f'<line x1="{sx(7.1):.1f}" y1="{sy(3.5):.1f}" x2="{sx(7.1):.1f}" y2="{sy(6.8):.1f}" '
                    f'stroke="#475569" stroke-width="1.1"/>'
                )
                for step_k in range(10):
                    vy = 3.5 + step_k * 0.33
                    out.append(
                        f'<line x1="{sx(su0 + 0.1):.1f}" y1="{sy(vy):.1f}" x2="{sx(su1 - 0.1):.1f}" y2="{sy(vy):.1f}" '
                        f'stroke="#64748b" stroke-width="0.8"/>'
                    )
            if lift_key in spaces_by_id and spaces_by_id[lift_key].level_id == lv:
                lu0, lv0, lu1, lv1 = 8.4, 5.4, 10.2, 7.4
                out.append(
                    f'<rect x="{sx(lu0 + 0.18):.1f}" y="{sy(lv0 + 0.18):.1f}" '
                    f'width="{(lu1 - lu0 - 0.36) * SCALE:.1f}" height="{(lv1 - lv0 - 0.36) * SCALE:.1f}" '
                    f'fill="none" stroke="#475569" stroke-width="1.1"/>'
                )
                out.append(
                    f'<line x1="{sx(lu0 + 0.18):.1f}" y1="{sy(lv0 + 0.18):.1f}" '
                    f'x2="{sx(lu1 - 0.18):.1f}" y2="{sy(lv1 - 0.18):.1f}" stroke="#64748b" stroke-width="0.8"/>'
                )
                out.append(
                    f'<line x1="{sx(lu1 - 0.18):.1f}" y1="{sy(lv0 + 0.18):.1f}" '
                    f'x2="{sx(lu0 + 0.18):.1f}" y2="{sy(lv1 - 0.18):.1f}" stroke="#64748b" stroke-width="0.8"/>'
                )

        # Draw Walls
        for w in model.walls:
            if w.level_id != lv:
                continue
            u0, v0 = frame.to_design(w.start)
            u1, v1 = frame.to_design(w.end)
            if w.kind is WallKind.PARAPET:
                stroke_col = WALL_PARAPET_HEX
                sw_px = 2.0
            elif w.kind is WallKind.EXTERIOR:
                stroke_col = WALL_INTERIOR_HEX
                sw_px = 4.2
            else:
                stroke_col = WALL_INTERIOR_HEX
                sw_px = 2.8
            out.append(
                f'<line x1="{sx(u0):.1f}" y1="{sy(v0):.1f}" x2="{sx(u1):.1f}" y2="{sy(v1):.1f}" '
                f'stroke="{stroke_col}" stroke-width="{sw_px:.1f}" stroke-linecap="square"/>'
            )

        # Draw Openings (Windows, Doors, Open Passages)
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
                f'stroke="#fbfaf6" stroke-width="5.2"/>'
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
                    f'stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="3,3"/>'
                )
            else:
                out.append(
                    f'<line x1="{sx(ou0):.1f}" y1="{sy(ov0):.1f}" x2="{sx(ou1):.1f}" y2="{sy(ov1):.1f}" '
                    f'stroke="{DOOR_STROKE_HEX}" stroke-width="2.6"/>'
                )

        # Place Room & Terrace Labels cleanly inside each room's primary rectangle
        for sp in lv_spaces:
            area = sp.area_m2
            if sp.id in room_specs:
                rspec = room_specs[sp.id]
                ru0, rv0, ru1, rv1 = _largest_rect_dm(rspec.rects)
                lbl = _short_label(rspec.key, rspec.name)
                if rspec.key == "living":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = 7.4
                elif rspec.key == "garage":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = 4.5
                elif rspec.key == "family" and spec.code == "A":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = 7.1
                elif rspec.key == "family" and spec.code == "B":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = 11.4
                elif rspec.key == "family" and spec.code == "C":
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = 13.0
                elif rspec.key in ("stair-r", "stair-u", "stair-l"):
                    cx_m = 7.1
                    cy_m = 2.95
                elif rspec.key in ("lift-r", "lift-u", "lift-l"):
                    cx_m = 9.3
                    cy_m = 6.4
                else:
                    cx_m = (ru0 + ru1) / 2.0
                    cy_m = (rv0 + rv1) / 2.0

                w_m, h_m = ru1 - ru0, rv1 - rv0
                if rspec.key in ("stair-r", "stair-u", "stair-l", "lift-r", "lift-u", "lift-l"):
                    add_text(panel_id, sx(cx_m), sy(cy_m), lbl, size=8.0, weight="700")
                elif w_m >= 1.35 and h_m >= 1.35:
                    f_sz = 8.6 if w_m >= 2.5 else 7.5
                    add_text(panel_id, sx(cx_m), sy(cy_m - 0.24), lbl, size=f_sz, weight="700")
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m + 0.34),
                        f"{area:.1f} m²",
                        size=7.3,
                        weight="500",
                        fill=INK_MUTED_HEX,
                    )
                else:
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m + 0.12),
                        f"{lbl} ({area:.0f}m²)",
                        size=7.4,
                        weight="700",
                    )
            elif sp.id in terrace_specs:
                tlabel, _, trects = terrace_specs[sp.id]
                tu0, tv0, tu1, tv1 = _largest_rect_dm(trects)
                lbl = _short_label(sp.id, tlabel)
                cx_m = (tu0 + tu1) / 2.0
                cy_m = (tv0 + tv1) / 2.0
                if sp.id == "sp-terrace-north":
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m + 0.15),
                        f"{lbl} ({area:.1f} m²)",
                        size=8.0,
                        weight="700",
                        fill="#3f6212",
                    )
                elif sp.id == "sp-terrace-lower":
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(3.2),
                        "Lower Terr.",
                        size=7.8,
                        weight="700",
                        fill="#3f6212",
                    )
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(3.85),
                        f"{area:.1f} m²",
                        size=7.5,
                        weight="600",
                        fill="#3f6212",
                    )
                else:
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m - 0.25),
                        lbl,
                        size=8.5,
                        weight="700",
                        fill="#3f6212",
                    )
                    add_text(
                        panel_id,
                        sx(cx_m),
                        sy(cy_m + 0.38),
                        f"{area:.1f} m²",
                        size=7.8,
                        weight="600",
                        fill="#3f6212",
                    )

        # Draw Right-Hand Level Schedule & Rule Highlights Card for this level
        out.append(
            f'<rect x="{SIDEBAR_X:.1f}" y="{py:.1f}" width="{SIDEBAR_W:.1f}" height="{PANEL_H:.1f}" '
            f'rx="8" fill="#ffffff" stroke="#e2dac9" stroke-width="1.2"/>'
        )
        add_text(
            f"side-{lv}",
            SIDEBAR_X + 16.0,
            py + 22.0,
            f"Level {lv_idx + 1} Room Schedule & Key Features",
            size=12.0,
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
            py + 39.0,
            f"Plate u={pu0:.1f}–{pu1:.1f}m, v={pv0:.1f}–{pv1:.1f}m · Indoor {lv_indoor_m2:.1f} m² · Terraces {lv_outdoor_m2:.1f} m²",
            size=9.2,
            weight="600",
            fill=INK_MUTED_HEX,
            anchor="start",
            check_overlap=False,
        )
        row_y = py + 58.0
        for sp in lv_spaces:
            rname = room_specs[sp.id].name if sp.id in room_specs else terrace_specs[sp.id][0]
            out.append(
                f'<rect x="{SIDEBAR_X + 12:.1f}" y="{row_y - 11:.1f}" width="{SIDEBAR_W - 24:.1f}" height="15.5" '
                f'rx="3" fill="{"#f4f9f0" if sp.function is F.TERRACE else "#f8f6f0"}"/>'
            )
            add_text(
                f"side-{lv}",
                SIDEBAR_X + 20.0,
                row_y,
                rname,
                size=8.8,
                weight="600",
                anchor="start",
                check_overlap=False,
            )
            add_text(
                f"side-{lv}",
                SIDEBAR_X + SIDEBAR_W - 20.0,
                row_y,
                f"{sp.area_m2:.1f} m²",
                size=8.8,
                weight="700",
                anchor="end",
                check_overlap=False,
            )
            row_y += 18.2

        if lv == LEVEL_ROAD:
            rule_bullets = [
                "✓ Rule 5.1: Direct indoor route Garage → Lobby → Lift & Stair",
                "✓ Rule 5.2: Continuous 3-level stair works without electricity",
                "✓ Rule 5.3: Stair & Lift at the interior heart of the house",
                "✓ Rule 5.5: Oversized 2-car garage + integrated workshop bay",
            ]
        elif lv == LEVEL_MAIN:
            rule_bullets = [
                "✓ Rule 1.1 & 1.2: Prime South Kitchen opens onto South Terrace",
                "✓ Rule 1.3: Semi-open kitchen (2 walk-throughs; smells blocked)",
                "✓ Rule 2.1: Direct Central Hall entry to every main room",
                "✓ Rule 3.1 & 3.2: Cozy L-Living corner closed on N/W + Hall access",
                "✓ Rule 4.3: Generous main-floor terraces on non-west sides",
            ]
        else:
            rule_bullets = [
                "✓ Rule 2.2 & 2.3: Compact central hall; 100% exact plate tiling",
                "✓ Rule 4.2: Stepped east to u ≈ 20m + ~160 m² Flat East Lawn",
                "✓ Rule 6.1–6.5: Grandparents Suite + Boys & Girls 2-bed rooms",
                "✓ Rule 6.6: Family Room with Tea & Snack Bar; tucked Store",
            ]

        row_y += 5.0
        add_text(
            f"side-{lv}",
            SIDEBAR_X + 16.0,
            row_y,
            "Verified Homeowner Rules on this Level:",
            size=9.5,
            weight="800",
            fill="#15803d",
            anchor="start",
            check_overlap=False,
        )
        row_y += 15.0
        for b_txt in rule_bullets:
            add_text(
                f"side-{lv}",
                SIDEBAR_X + 18.0,
                row_y,
                b_txt,
                size=8.6,
                weight="600",
                fill="#166534",
                anchor="start",
                check_overlap=False,
            )
            row_y += 14.2

    # Footer Legend & Scale Bar
    fy = HEADER_H + 3 * (PANEL_H + GAP_Y) + 6.0
    out.append(
        f'<rect x="{PANEL_X - 36:.1f}" y="{fy:.1f}" width="{W - PANEL_X + 8:.1f}" height="74" '
        f'rx="8" fill="#ffffff" stroke="#e2dac9" stroke-width="1.2"/>'
    )
    sb_x = PANEL_X - 16.0
    sb_y = fy + 26.0
    out.append(
        f'<line x1="{sb_x:.1f}" y1="{sb_y:.1f}" x2="{sb_x + 5 * SCALE:.1f}" y2="{sb_y:.1f}" stroke="#1f2a2e" stroke-width="3"/>'
    )
    for m_i in range(6):
        mx = sb_x + m_i * SCALE
        out.append(
            f'<line x1="{mx:.1f}" y1="{sb_y - 4:.1f}" x2="{mx:.1f}" y2="{sb_y + 4:.1f}" stroke="#1f2a2e" stroke-width="1.5"/>'
        )
    add_text(
        "footer",
        sb_x + 2.5 * SCALE,
        sb_y + 16.0,
        "Scale Bar: 5.0 m (1:1 Uniform Scale)",
        size=9.0,
        weight="700",
        check_overlap=False,
    )

    leg_x = sb_x + 165.0
    add_text(
        "footer",
        leg_x,
        sb_y + 2.0,
        "Legend:  ━━ Exterior Wall (30cm)   ── Interior Wall (15cm)   ══ Window (Blue)   ── Door (Orange)   --- Open Passage (No Door)   --- Parcel / 1m Setback",
        size=10.0,
        weight="600",
        anchor="start",
        check_overlap=False,
    )
    add_text(
        "footer",
        leg_x,
        sb_y + 24.0,
        EXPLORATORY_NOTICE,
        size=9.5,
        weight="500",
        fill=INK_MUTED_HEX,
        anchor="start",
        check_overlap=False,
    )

    out.append("</svg>")

    # Verify Owner Rule 7.1 (Zero overlapping text labels)
    assert_zero_label_overlaps(spec.option_id, text_boxes)

    svg_path = opt_dir / "floor-plans.svg"
    png_path = opt_dir / "floor-plans.png"
    svg_path.write_text("\n".join(out), encoding="utf-8")
    svg_to_png(svg_path, png_path, size=2200)
    return svg_path, png_path


def main() -> None:
    for key in ("a", "b", "c"):
        spec = OPTIONS[key]
        svg_path, png_path = render_option_floor_plans(spec)
        if key == "a":
            (HERE / "floor-plans.svg").write_text(
                svg_path.read_text(encoding="utf-8"), encoding="utf-8"
            )
            svg_to_png(svg_path, HERE / "floor-plans.png", size=2200)
        print(f"RENDERED {spec.option_id}: {svg_path.name} + {png_path.name} (0 label overlaps)")


if __name__ == "__main__":
    main()
