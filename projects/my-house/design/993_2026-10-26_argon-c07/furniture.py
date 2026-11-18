"""Reusable architectural furniture and analytical overlay renderer for Argon C07.

Draws the crafted room furnishings and analytical verification overlays directly inspired by
`projects/my-house/design/999_2026-10-17_user-designed/redesign-0109-r5` (`A`, `B`, `C`) while illustrating
the fixes for `projects/my-house/design/999_2026-10-17_user-designed/independent-review-0110-r2`:
- Two Independent Car Bays (LC300 5.10×2.10m + 2nd car 4.80×1.95m) with 0.65m door zones (I09 fix)
- North Workshop Bay + 6 family lockers (L1–L6) in Six-Person Unloading + 1.20m Replaceable Plant
- 4-Part Screened Wet & Wudu Cluster (Shared WC + Shared Shower + Wudu + Screened Lobby with opaque sightline baffle, P3)
- Walk-in Bulk Pantry shelving, South Kitchen counters/island, 6–8 seat Dining table (I26 & I14 fix)
- Sheltered NE Reading / Prayer & Cozy Sitting Bay with L-sofa and Qibla 204.65° prayer mats (I11 fix)
- Parents Suite king bed, walk-in dress wardrobes, and 1.525m accessible bathroom turning circle (P1, I15/I30 fix)
- Twin-furnished Boys & Girls rooms: 2 beds (B1/B2), 2 study desks (D1/D2), 2 wardrobes (W1/W2) (P2)
- Lower Parents/Guest Suite bed + private accessible Seated WC & shower en-suite (I10 fix)
- Garden Lounge sofa + Night Tea & Snack Bar + Laundry washer/dryer/drying rack (I12) + Household Store racks (I22)
"""

from __future__ import annotations

from collections.abc import Callable

from constants import (
    CAR_DOOR_ZONE_M,
    FURNITURE_FILL_HEX,
    FURNITURE_STROKE_HEX,
    LC300_LENGTH_M,
    LC300_WIDTH_M,
    LEVEL_LOWER,
    LEVEL_MAIN,
    LEVEL_ROAD,
    SECOND_CAR_LENGTH_M,
    SECOND_CAR_WIDTH_M,
    SIGHTLINE_BAFFLE_HEX,
)
from generate import OptionSpec


def draw_level_furniture(
    out: list[str],
    panel_id: str,
    add_text_fn: Callable[..., None],
    spec: OptionSpec,
    lv: str,
    sx: Callable[[float], float],
    sy: Callable[[float], float],
    scale: float,
    room_rects_m: dict[str, tuple[float, float, float, float]],
) -> None:
    """Append SVG furniture & analytical overlay elements for level `lv` to `out`."""

    def rbox(
        u0: float,
        v0: float,
        w_m: float,
        h_m: float,
        *,
        fill: str = FURNITURE_FILL_HEX,
        stroke: str = FURNITURE_STROKE_HEX,
        opacity: float = 0.68,
        sw: float = 0.9,
        rx: float = 1.8,
        dash: str = "",
    ) -> None:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(
            f'<rect x="{sx(u0):.1f}" y="{sy(v0):.1f}" width="{w_m * scale:.1f}" '
            f'height="{h_m * scale:.1f}" rx="{rx:.1f}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{sw}"{dash_attr}/>'
        )

    def tag(u: float, v: float, txt: str, color: str = "#334155", sz: float = 5.8) -> None:
        add_text_fn(panel_id, sx(u), sy(v), txt, size=sz, weight="700", fill=color)

    if lv == LEVEL_ROAD:
        # 1. North Workshop Bay (u=5.6..7.2, v=0.6..3.6)
        wu0, wv0, wu1, wv1 = [c / 10.0 for c in spec.workshop_bay_dm]
        rbox(
            wu0,
            wv0,
            wu1 - wu0,
            wv1 - wv0,
            fill="#fde68a",
            stroke="#b45309",
            opacity=0.48,
            sw=1.0,
            dash="3,2",
        )
        rbox(
            wu0 + 0.15,
            wv0 + 0.15,
            wu1 - wu0 - 0.30,
            0.55,
            fill="#fcd34d",
            stroke="#92400e",
            opacity=0.80,
        )

        # 2. Two Independent Car Bays (LC300 + 2nd Car) with 0.65m clear door-swing envelopes (I09 fix)
        car_u0 = 0.60
        c1_v0 = 2.00
        rbox(
            car_u0,
            c1_v0 - CAR_DOOR_ZONE_M,
            LC300_LENGTH_M - 0.3,
            LC300_WIDTH_M + 2 * CAR_DOOR_ZONE_M,
            fill="#dcfce7",
            stroke="#16a34a",
            opacity=0.30,
            sw=0.8,
            dash="2,2",
        )
        rbox(car_u0, c1_v0, LC300_LENGTH_M - 0.3, LC300_WIDTH_M, rx=3.5, opacity=0.78, sw=1.1)
        tag(car_u0 + 1.05, c1_v0 + 1.15, "LC300", "#1e293b", 6.2)

        c2_v0 = 6.45
        rbox(
            car_u0,
            c2_v0 - CAR_DOOR_ZONE_M,
            SECOND_CAR_LENGTH_M - 0.2,
            SECOND_CAR_WIDTH_M + 2 * CAR_DOOR_ZONE_M,
            fill="#dcfce7",
            stroke="#16a34a",
            opacity=0.30,
            sw=0.8,
            dash="2,2",
        )
        rbox(
            car_u0,
            c2_v0,
            SECOND_CAR_LENGTH_M - 0.2,
            SECOND_CAR_WIDTH_M,
            rx=3.5,
            opacity=0.78,
            sw=1.1,
        )
        tag(car_u0 + 1.05, c2_v0 + 1.08, "CAR 2", "#1e293b", 6.2)

        # 2b. Dedicated West Front Pedestrian Entrance Foyer (u=0.4..5.6, v=10.0..11.6) & 1.2m Front Door
        rbox(0.50, 10.20, 0.75, 1.20, fill="#ccfbf1", stroke="#0f766e", opacity=0.85, sw=1.0)
        tag(3.45, 10.92, "FRONT DOOR FOYER (1.2m)", "#0f766e", 5.8)

        # 3. 6-Person Family Lockers (L1..L6) in Six-Person Unloading
        lu0, lv0, lu1, lv1 = [c / 10.0 for c in spec.lockers_dm]
        locker_w = (lu1 - lu0) / 6.0
        for i in range(6):
            rbox(
                lu0 + i * locker_w,
                lv0,
                locker_w - 0.04,
                lv1 - lv0,
                fill="#fed7aa",
                stroke="#c2410c",
                opacity=0.78,
                sw=0.8,
                rx=1.0,
            )

        # 4. Replaceable Plant equipment (BLR / HP / CYL)
        if "plant" in room_rects_m:
            pu0, pv0, pu1, pv1 = room_rects_m["plant"]
            rbox(pu0 + 0.25, pv0 + 0.20, 0.70, 0.45, fill="#e2e8f0", stroke="#475569")
            rbox(pu1 - 0.95, pv0 + 0.20, 0.70, 0.45, fill="#e2e8f0", stroke="#475569")

        # 5. Quiet Office desk & chair at SE corner
        if "office" in room_rects_m:
            ou0, ov0, ou1, ov1 = room_rects_m["office"]
            rbox(ou0 + 0.30, ov1 - 0.85, 1.50, 0.60, fill="#e0f2fe", stroke="#0369a1")
            rbox(ou1 - 0.85, ov0 + 0.25, 0.65, 1.40, fill="#f1f5f9", stroke="#475569")

    elif lv == LEVEL_MAIN:
        # 0. West Family Arrival entrance mat at 1.20m West Arrival Door (Rule 2.5)
        if "entry" in room_rects_m:
            eu0, ev0, _eu1, _ev1 = room_rects_m["entry"]
            rbox(eu0 + 0.10, ev0 + 0.30, 0.55, 1.20, fill="#ccfbf1", stroke="#0f766e", opacity=0.82)

        # 1. 4-Part Screened Wet & Wudu Cluster fixtures + Opaque Sightline Baffle (P3)
        if "wc-u" in room_rects_m:
            wu0, wv0, wu1, wv1 = room_rects_m["wc-u"]
            rbox(wu0 + 0.45, wv0 + 0.20, 0.55, 0.70, fill="#ffffff", stroke="#0f766e")
        if "shower-u" in room_rects_m:
            su0, sv0, su1, sv1 = room_rects_m["shower-u"]
            rbox(su0 + 0.25, sv0 + 0.20, 1.10, 0.80, fill="#e0f2fe", stroke="#0284c7")
        if "wudu-u" in room_rects_m:
            wdu0, wdv0, wdu1, wdv1 = room_rects_m["wudu-u"]
            rbox(wdu0 + 0.20, wdv0 + 0.15, 1.20, 0.42, fill="#ccfbf1", stroke="#0f766e")
            out.append(
                f'<line x1="{sx(wdu0 + 0.25):.1f}" y1="{sy(wdv1 - 0.08):.1f}" '
                f'x2="{sx(wdu1 - 0.25):.1f}" y2="{sy(wdv1 - 0.08):.1f}" '
                f'stroke="{SIGHTLINE_BAFFLE_HEX}" stroke-width="3.2"/>'
            )

        # 2. NE Reading / Prayer & Cozy Sitting Bay (Qibla 204.65°, matching 0109-r5 upper-floor.png)
        cu0, cv0, cu1, cv1 = [c / 10.0 for c in spec.cozy_corner_dm]
        rbox(
            cu0,
            cv0,
            cu1 - cu0,
            cv1 - cv0,
            fill="#fef3c7",
            stroke="#d97706",
            opacity=0.52,
            sw=1.1,
            dash="4,2",
        )
        # L-shaped sofa in living room
        out.append(
            f'<path d="M {sx(cu0 + 0.30):.1f} {sy(cv1 - 1.75):.1f} '
            f"H {sx(cu1 - 0.35):.1f} V {sy(cv1 - 0.25):.1f} H {sx(cu1 - 1.00):.1f} "
            f'V {sy(cv1 - 1.10):.1f} H {sx(cu0 + 0.30):.1f} Z" '
            f'fill="#fdba74" fill-opacity="0.58" stroke="#c2410c" stroke-width="1.0"/>'
        )
        # Angled Qibla prayer mats (204.65°) in NE Reading/Prayer bay
        pnu0, pnv0, pnu1, pnv1 = [c / 10.0 for c in spec.prayer_nook_dm]
        for pm_i, pm_u in enumerate((pnu0 + 0.15, pnu0 + 1.15)):
            pm_cx, pm_cy = sx(pm_u + 0.40), sy(pnv0 + 0.72)
            out.append(
                f'<g transform="rotate(24.65 {pm_cx:.1f} {pm_cy:.1f})">'
                f'<rect x="{pm_cx - 0.38 * scale:.1f}" y="{pm_cy - 0.60 * scale:.1f}" '
                f'width="{0.76 * scale:.1f}" height="{1.20 * scale:.1f}" rx="2" '
                f'fill="#dcfce7" fill-opacity="0.78" stroke="#15803d" stroke-width="1.0"/>'
                f"</g>"
            )
            if pm_i == 0:
                tag(pnu0 + 1.10, pnv0 + 1.62, "QIBLA 204.65°", "#166534", 5.4)

        # 3. Walk-in Pantry shelving
        if "pantry" in room_rects_m:
            pu0, pv0, pu1, pv1 = room_rects_m["pantry"]
            rbox(pu0 + 0.08, pv0 + 0.20, 0.20, pv1 - pv0 - 0.40, fill="#fed7aa", stroke="#b45309")

        # 4. South Kitchen L-counter (HOB / SINK / F) + island (matching 0109-r5)
        if "kitchen" in room_rects_m:
            ku0, kv0, ku1, kv1 = room_rects_m["kitchen"]
            rbox(
                ku0 + 0.15,
                kv0 + 0.20,
                0.60,
                kv1 - kv0 - 0.40,
                fill="#fed7aa",
                stroke="#c2410c",
                opacity=0.78,
            )
            rbox(
                ku0 + 0.15,
                kv1 - 0.75,
                ku1 - ku0 - 1.10,
                0.55,
                fill="#fed7aa",
                stroke="#c2410c",
                opacity=0.78,
            )
            tag(ku0 + 0.45, kv1 - 1.35, "HOB", "#9a3412", 5.4)
            rbox(ku1 - 0.85, kv0 + 0.20, 0.65, 0.65, fill="#e2e8f0", stroke="#475569")
            tag(ku1 - 0.52, kv0 + 0.60, "F", "#334155", 5.5)

        # 5. Dining Table for 6–8 with chairs (matching 0109-r5)
        if "dining" in room_rects_m:
            du0, dv0, du1, dv1 = room_rects_m["dining"]
            tw, th = min(2.1, (du1 - du0) - 1.1), 0.90
            tu0 = (du0 + du1 - tw) / 2.0
            tv0 = dv1 - 1.55
            rbox(tu0, tv0, tw, th, fill="#fef3c7", stroke="#92400e", opacity=0.62)
            for ci in range(3):
                cx = tu0 + 0.22 + ci * ((tw - 0.72) / 2.0)
                rbox(cx, tv0 - 0.22, 0.28, 0.16, fill="#ffffff", stroke="#78716c")
                rbox(cx, tv0 + th + 0.06, 0.28, 0.16, fill="#ffffff", stroke="#78716c")

        # 6. Parents / Main Suite bed, dress wardrobes, and 1.525m accessible bath circle (P1)
        if "master" in room_rects_m:
            mu0, mv0, mu1, mv1 = room_rects_m["master"]
            rbox(mu0 + 0.20, mv0 + 0.30, 1.85, 1.65, fill="#ffffff", stroke="#475569", opacity=0.75)
        if "closet" in room_rects_m:
            clu0, clv0, clu1, clv1 = room_rects_m["closet"]
            rbox(
                clu1 - 0.42, clv0 + 0.15, 0.30, clv1 - clv0 - 0.30, fill="#e9d5ff", stroke="#7e22ce"
            )
        if "ensuite-u" in room_rects_m:
            bu0, bv0, bu1, bv1 = room_rects_m["ensuite-u"]
            out.append(
                f'<circle cx="{sx((bu0 + bu1) / 2):.1f}" cy="{sy((bv0 + bv1) / 2):.1f}" r="{0.68 * scale:.1f}" '
                f'fill="none" stroke="#0284c7" stroke-width="0.9" stroke-dasharray="3,2"/>'
            )

        # 7. Exterior Garden Stair (GS) on South-East Terrace
        if "sp-terrace-south" in room_rects_m:
            tsu0, tsv0, tsu1, tsv1 = room_rects_m["sp-terrace-south"]
            gsu0 = tsu1 - 2.6
            rbox(gsu0, tsv0 + 0.35, 2.2, 1.05, fill="#e2e8f0", stroke="#475569", opacity=0.82)
            for s_i in range(6):
                sx_line = sx(gsu0 + 0.2 + s_i * 0.35)
                out.append(
                    f'<line x1="{sx_line:.1f}" y1="{sy(tsv0 + 0.35):.1f}" '
                    f'x2="{sx_line:.1f}" y2="{sy(tsv0 + 1.40):.1f}" stroke="#475569" stroke-width="0.8"/>'
                )
            tag(gsu0 + 1.1, tsv0 + 1.85, "Garden Stair (GS)", "#334155", 5.8)

    elif lv == LEVEL_LOWER:
        # 1. Night Tea & Snack Bar in Garden Lounge (Rule 6.6)
        tu0, tv0, tu1, tv1 = [c / 10.0 for c in spec.tea_bar_dm]
        rbox(tu0, tv0, tu1 - tu0, tv1 - tv0, fill="#fde68a", stroke="#b45309", opacity=0.85, sw=1.1)

        # 2. Boys & Girls Shared Rooms along South Row: 2 Beds (B1, B2), 2 Desks (D1, D2), 2 Wardrobes (W1, W2) (matching 0109-r5 lower-floor.png!)
        for kid_key in ("boys", "girls"):
            if kid_key in room_rects_m:
                ku0, kv0, ku1, kv1 = room_rects_m[kid_key]
                # D1 (NW) and D2 (NE) desks along north wall
                rbox(
                    ku0 + 0.25,
                    kv0 + 0.20,
                    1.25,
                    0.55,
                    fill="#e0f2fe",
                    stroke="#0284c7",
                    opacity=0.78,
                )
                tag(ku0 + 0.88, kv0 + 0.56, "D1", "#0369a1", 5.4)
                rbox(
                    ku1 - 1.50,
                    kv0 + 0.20,
                    1.25,
                    0.55,
                    fill="#e0f2fe",
                    stroke="#0284c7",
                    opacity=0.78,
                )
                tag(ku1 - 0.88, kv0 + 0.56, "D2", "#0369a1", 5.4)
                # W1 (west wall) and W2 (east wall) wardrobes
                rbox(
                    ku0 + 0.15,
                    kv0 + 1.05,
                    0.52,
                    1.35,
                    fill="#fed7aa",
                    stroke="#b45309",
                    opacity=0.78,
                )
                tag(ku0 + 0.41, kv0 + 1.80, "W1", "#92400e", 5.2)
                rbox(
                    ku1 - 0.67,
                    kv0 + 1.05,
                    0.52,
                    1.35,
                    fill="#fed7aa",
                    stroke="#b45309",
                    opacity=0.78,
                )
                tag(ku1 - 0.41, kv0 + 1.80, "W2", "#92400e", 5.2)
                # B1 (SW) and B2 (SE) twin beds along south half (matching 0109-r5 lower-floor.png!)
                rbox(
                    ku0 + 0.20,
                    kv1 - 2.15,
                    0.98,
                    1.95,
                    fill="#ffffff",
                    stroke="#475569",
                    opacity=0.80,
                )
                tag(ku0 + 0.69, kv1 - 1.10, "B1", "#1e293b", 5.6)
                rbox(
                    ku1 - 1.18,
                    kv1 - 2.15,
                    0.98,
                    1.95,
                    fill="#ffffff",
                    stroke="#475569",
                    opacity=0.80,
                )
                tag(ku1 - 0.69, kv1 - 1.10, "B2", "#1e293b", 5.6)

        # 3. Lower Parents / Guest Suite bed + Accessible Seated En-Suite 1.525m turning circle (I10 fix)
        if "bed3" in room_rects_m:
            pu0, pv0, pu1, pv1 = room_rects_m["bed3"]
            rbox(pu0 + 0.25, pv0 + 0.25, 1.85, 1.55, fill="#ffffff", stroke="#475569", opacity=0.75)
        if "ensuite-l" in room_rects_m:
            eu0, ev0, eu1, ev1 = room_rects_m["ensuite-l"]
            out.append(
                f'<circle cx="{sx((eu0 + eu1) / 2):.1f}" cy="{sy((ev0 + ev1) / 2):.1f}" r="{0.58 * scale:.1f}" '
                f'fill="none" stroke="#0284c7" stroke-width="0.9" stroke-dasharray="3,2"/>'
            )

        # 4. Laundry washer (W), dryer (D), and indoor drying rack (I12 fix)
        if "laundry" in room_rects_m:
            lu0, lv0, lu1, lv1 = room_rects_m["laundry"]
            rbox(lu0 + 0.20, lv1 - 0.78, 0.62, 0.60, fill="#e0f2fe", stroke="#0369a1")
            tag(lu0 + 0.51, lv1 - 0.40, "W", "#0369a1", 5.5)
            rbox(lu0 + 0.90, lv1 - 0.78, 0.62, 0.60, fill="#e0f2fe", stroke="#0369a1")
            tag(lu0 + 1.21, lv1 - 0.40, "D", "#0369a1", 5.5)
            rbox(
                lu1 - 0.65,
                lv0 + 0.30,
                0.45,
                1.40,
                fill="#f0fdf4",
                stroke="#15803d",
                opacity=0.75,
                dash="2,2",
            )

        # 5. Lower Household Store shelving (I22 fix)
        if "store-l" in room_rects_m:
            su0, sv0, su1, sv1 = room_rects_m["store-l"]
            rbox(su0 + 0.20, sv0 + 0.15, su1 - su0 - 0.40, 0.40, fill="#fed7aa", stroke="#b45309")
