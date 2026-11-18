"""True 1:1 terrain & excavation sections + canonical TIN earthwork for Argon C06 (A, B, C).

Computes canonical TIN earthwork (`house_ai.geospatial.earthworks.integrate`) and renders
1:1 scale (no vertical exaggeration, Rule 4.5) East–West and North–South cross-sections
for all three Argon C06 options (`argon-c06-a`, `argon-c06-b`, `argon-c06-c`).
"""

from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

from shapely.geometry import Polygon as ShapelyPolygon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from constants import (  # noqa: E402
    EXPLORATORY_NOTICE,
    FORMATION_OFFSET_M,
    LEVEL_LOWER,
    LEVEL_MAIN,
    LEVEL_ROAD,
    ROAD_ASPHALT_Z_M,
    svg_to_png,
)
from generate import OPTIONS, OptionSpec, frame, ground, site  # noqa: E402

from house_ai.geospatial.earthworks import integrate  # noqa: E402

PARCEL_POLY = ShapelyPolygon(site.boundary.outer)
ENVELOPE_POLY = ShapelyPolygon(site.buildable_envelope.polygon.outer)


def z_ground(u_m: float, v_m: float) -> float | None:
    return ground.at(u_m, v_m)


def rect_poly(u0: float, v0: float, u1: float, v1: float) -> ShapelyPolygon:
    return ShapelyPolygon(
        frame.rect(round(u0 * 10), round(v0 * 10), round(u1 * 10), round(v1 * 10)).outer
    )


def compute_option_earthwork(spec: OptionSpec) -> dict[str, object]:
    """Integrate canonical TIN earthwork across the stepped zones + flat east lawn."""
    z_road = spec.elevations_m[LEVEL_ROAD]
    z_main = spec.elevations_m[LEVEL_MAIN]
    z_lower = spec.elevations_m[LEVEL_LOWER]

    ru0, rv0, ru1, rv1 = [c / 10 for c in spec.plates_dm[LEVEL_ROAD]]
    mu0, mv0, mu1, mv1 = [c / 10 for c in spec.plates_dm[LEVEL_MAIN]]
    lu0, lv0, lu1, lv1 = [c / 10 for c in spec.plates_dm[LEVEL_LOWER]]
    lawn_u0 = spec.lawn_u0_m

    zone_defs = [
        (
            "west-arrival-court",
            rect_poly(-2.0, 4.0, mu0, 9.6)
            .union(rect_poly(-4.8, 9.6, mu0, 12.4))
            .intersection(PARCEL_POLY),
            z_main - FORMATION_OFFSET_M,
            f"West sunken court & steps (z={z_main:.1f} m)",
            True,
        ),
        (
            "road-garage-west",
            rect_poly(ru0, 0.0, mu0, 12.4).intersection(PARCEL_POLY),
            z_road - FORMATION_OFFSET_M,
            f"Road garage west apron (FFL {z_road:.1f} m)",
            True,
        ),
        (
            "main-west-band",
            rect_poly(mu0, mv0, lu0, 12.4).intersection(PARCEL_POLY),
            z_main - FORMATION_OFFSET_M,
            f"Main floor west band (FFL {z_main:.1f} m, Road stacked above)",
            True,
        ),
        (
            "lower-footprint",
            rect_poly(lu0, 0.0, lu1, 15.6).intersection(PARCEL_POLY),
            z_lower - FORMATION_OFFSET_M,
            f"Lower floor footprint u={lu0:.1f}..{lu1:.1f} m (FFL {z_lower:.1f} m)",
            True,
        ),
        (
            "south-terrace-west",
            rect_poly(mu0, 12.4, lu0, 15.6).intersection(ENVELOPE_POLY),
            z_main,
            f"South terrace west band (z={z_main:.1f} m)",
            True,
        ),
        (
            "lower-east-terrace",
            rect_poly(lu1, 0.0, lawn_u0, 15.6).intersection(ENVELOPE_POLY),
            z_lower,
            f"Lower east garden terrace u={lu1:.1f}..{lawn_u0:.1f} m (z={z_lower:.1f} m)",
            False,
        ),
        (
            "flat-east-lawn",
            rect_poly(lawn_u0, -1.0, 35.0, 20.0).intersection(ENVELOPE_POLY),
            spec.lawn_z_m,
            f"Graded flat east garden lawn u={lawn_u0:.1f}..31.4 m (z={spec.lawn_z_m:.1f} m)",
            False,
        ),
    ]
    zones_out = []
    b_cut = 0.0
    b_fill = 0.0
    b_max_cut = 0.0
    tot_cut = 0.0
    tot_fill = 0.0
    for zid, zpoly, z_plane, zlabel, is_bldg in zone_defs:
        r = integrate(site.terrain.surface, zpoly, z_plane)
        c_m3 = round(r.cut_m3 or 0.0, 1)
        f_m3 = round(r.below_plane_m3 or 0.0, 1)
        mc_m = round(r.max_cut_m or 0.0, 2)
        mf_m = round(r.max_below_m or 0.0, 2)
        zones_out.append(
            {
                "id": zid,
                "label": zlabel,
                "area_m2": round(zpoly.area, 1),
                "formation_z_m": round(z_plane, 2),
                "cut_m3": c_m3,
                "fill_m3": f_m3,
                "max_cut_m": mc_m,
                "max_fill_m": mf_m,
            }
        )
        tot_cut += c_m3
        tot_fill += f_m3
        if is_bldg:
            b_cut += c_m3
            b_fill += f_m3
            b_max_cut = max(b_max_cut, mc_m)

    tot_cut = round(tot_cut, 1)
    tot_fill = round(tot_fill, 1)
    net_export = round(tot_cut - tot_fill, 1)
    out = {
        "option_id": spec.option_id,
        "zones": zones_out,
        "total_cut_m3": tot_cut,
        "total_fill_m3": tot_fill,
        "net_export_m3": net_export,
        "summary": {
            "building_cut_m3": round(b_cut, 1),
            "building_fill_m3": round(b_fill, 1),
            "building_net_export_m3": round(b_cut - b_fill, 1),
            "building_max_cut_m": round(b_max_cut, 2),
            "total_cut_with_terrace_and_lawn_m3": tot_cut,
            "total_fill_with_terrace_and_lawn_m3": tot_fill,
            "net_export_with_lawn_m3": net_export,
            "reuse_ratio_pct": round(100.0 * min(tot_cut, tot_fill) / max(tot_cut, 1.0), 1),
        },
        "method": (
            "house_ai.geospatial.earthworks.integrate on stored survey TIN (INFERRED); "
            "0.35 m formation below finished floors; excludes footings, batters, bulking, drainage."
        ),
    }
    return out


def render_option_sections(spec: OptionSpec, ew: dict[str, object]) -> tuple[Path, Path]:
    """Render 1:1 true-scale East–West and North–South terrain & excavation sections."""
    SCALE = 21.0  # 1 m = 21 px in BOTH horizontal and vertical axes (1:1 true scale, Rule 4.5)
    W = 1360
    H = 1360

    z_road = spec.elevations_m[LEVEL_ROAD]
    z_main = spec.elevations_m[LEVEL_MAIN]
    z_lower = spec.elevations_m[LEVEL_LOWER]
    h_road = spec.storey_heights_m[LEVEL_ROAD]
    h_main = spec.storey_heights_m[LEVEL_MAIN]
    h_lower = spec.storey_heights_m[LEVEL_LOWER]

    ru0, rv0, ru1, rv1 = [c / 10 for c in spec.plates_dm[LEVEL_ROAD]]
    mu0, mv0, mu1, mv1 = [c / 10 for c in spec.plates_dm[LEVEL_MAIN]]
    lu0, lv0, lu1, lv1 = [c / 10 for c in spec.plates_dm[LEVEL_LOWER]]
    lawn_u0 = spec.lawn_u0_m
    lawn_z = spec.lawn_z_m

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        'font-family="Helvetica, Arial, sans-serif">',
        "<defs>",
        '<pattern id="earth" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">'
        '<line x1="0" y1="0" x2="0" y2="12" stroke="#b99b78" stroke-width="1.2"/></pattern>',
        '<pattern id="cut" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
        '<rect width="8" height="8" fill="#fde68a" fill-opacity="0.32"/>'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#d97706" stroke-width="1.3"/></pattern>',
        '<pattern id="fill" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="8" height="8" fill="#bbf7d0" fill-opacity="0.35"/>'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#15803d" stroke-width="1.3"/></pattern>',
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="#fbfaf6"/>',
        f'<text x="36" y="34" font-size="18.5" font-weight="800" fill="#181614">'
        f"{escape(spec.title)} — True 1:1 Site &amp; Excavation Sections</text>",
        f'<text x="36" y="54" font-size="11.5" fill="#57534e">'
        f"True 1:1 vertical-to-horizontal scale (no vertical exaggeration, Rule 4.5) · "
        f"Building cut {ew['summary']['building_cut_m3']:.0f} m³ (max cut {ew['summary']['building_max_cut_m']:.2f} m) · "
        f"Total cut {ew['total_cut_m3']:.0f} m³ reused into {ew['total_fill_m3']:.0f} m³ terrace &amp; East Lawn fill "
        f"({ew['summary']['reuse_ratio_pct']:.0f}% on-site reuse)</text>",
    ]

    def draw_ew_panel(
        panel_y: float,
        v_cut: float,
        title: str,
        subtitle: str,
        rooms_road: list[tuple[float, float, str, str]],
        rooms_main: list[tuple[float, float, str, str]],
        rooms_lower: list[tuple[float, float, str, str]],
    ) -> None:
        panel_x = 86.0
        panel_w = 1236.0
        panel_h = 398.0
        u_min = -6.0
        z_top = 1682.0
        z_bot = 1666.0

        def sx(u: float) -> float:
            return panel_x + (u - u_min) * SCALE

        def sy(z: float) -> float:
            return panel_y + 52.0 + (z_top - z) * SCALE

        out.append(
            f'<rect x="{panel_x - 58:.1f}" y="{panel_y:.1f}" width="{panel_w + 58:.1f}" height="{panel_h:.1f}" '
            f'rx="8" fill="#ffffff" stroke="#e5dec9" stroke-width="1.2"/>'
        )
        out.append(
            f'<text x="{panel_x - 42:.1f}" y="{panel_y + 21:.1f}" font-size="13" font-weight="800" fill="#181614">'
            f"{escape(title)}</text>"
        )
        out.append(
            f'<text x="{panel_x - 42:.1f}" y="{panel_y + 38:.1f}" font-size="10.5" fill="#57534e">'
            f"{escape(subtitle)}</text>"
        )

        # Elevation grid lines (1666m to 1682m)
        for z_tick in range(1666, 1683, 2):
            yy = sy(float(z_tick))
            out.append(
                f'<line x1="{panel_x:.1f}" y1="{yy:.1f}" x2="{panel_x + panel_w - 18:.1f}" y2="{yy:.1f}" '
                f'stroke="#f1ece1" stroke-width="1"/>'
            )
            out.append(
                f'<text x="{panel_x - 8:.1f}" y="{yy + 3.5:.1f}" text-anchor="end" font-size="9.5" fill="#78716c">'
                f"{z_tick}m</text>"
            )

        # Distance ticks along bottom (below 1666m line)
        for u_tick in range(-5, 33, 5):
            xx = sx(float(u_tick))
            if panel_x <= xx <= panel_x + panel_w - 140:
                out.append(
                    f'<line x1="{xx:.1f}" y1="{sy(z_top):.1f}" x2="{xx:.1f}" y2="{sy(z_bot):.1f}" '
                    f'stroke="#f5f2eb" stroke-width="0.8"/>'
                )
                out.append(
                    f'<text x="{xx:.1f}" y="{sy(z_bot) + 14:.1f}" text-anchor="middle" font-size="9.5" fill="#78716c">'
                    f"u={u_tick}m</text>"
                )

        # Sample natural ground along v_cut
        u_samples = [u_min + 0.25 * i for i in range(int((31.5 - u_min) / 0.25) + 1)]
        nat_pts: list[tuple[float, float]] = []
        for u in u_samples:
            zg = z_ground(u, v_cut)
            if zg is None:
                zg = ROAD_ASPHALT_Z_M if u <= 0 else 1667.0
            nat_pts.append((u, max(zg, z_bot + 0.2)))

        # Ground mass below natural terrain
        poly_ground = (
            [(sx(nat_pts[0][0]), sy(z_bot))]
            + [(sx(u), sy(z)) for u, z in nat_pts]
            + [(sx(nat_pts[-1][0]), sy(z_bot))]
        )
        pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in poly_ground)
        out.append(f'<polygon points="{pts_str}" fill="url(#earth)" opacity="0.45"/>')

        # Cut & Fill hatch polygons between natural ground and formation profile
        def formation_z(u: float) -> float | None:
            if -2.0 <= u < mu0 and v_cut >= 4.0:
                return z_main - 0.15
            if ru0 <= u < mu0 and v_cut < 4.0:
                return z_road - FORMATION_OFFSET_M
            if mu0 <= u < lu0:
                return z_main - FORMATION_OFFSET_M
            if lu0 <= u <= lu1:
                return z_lower - FORMATION_OFFSET_M
            if lu1 < u <= lawn_u0:
                return z_lower - 0.25
            if lawn_u0 < u <= 29.5:
                return lawn_z
            return None

        cut_poly: list[tuple[float, float, float]] = []
        for u, zg in nat_pts:
            zf = formation_z(u)
            if zf is not None:
                cut_poly.append((u, zg, zf))
        if cut_poly:
            c_top = [(sx(u), sy(max(zg, zf))) for u, zg, zf in cut_poly]
            c_bot = [(sx(u), sy(zf)) for u, zg, zf in reversed(cut_poly)]
            c_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in (c_top + c_bot))
            out.append(f'<polygon points="{c_str}" fill="url(#cut)"/>')
            f_top = [(sx(u), sy(zf)) for u, zg, zf in cut_poly]
            f_bot = [(sx(u), sy(min(zg, zf))) for u, zg, zf in reversed(cut_poly)]
            f_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in (f_top + f_bot))
            out.append(f'<polygon points="{f_str}" fill="url(#fill)"/>')

        # Retaining walls (dark concrete verticals at step faces)
        for u_ret, z0_ret, z1_ret in [
            (mu0, z_main - FORMATION_OFFSET_M, z_road),
            (lu0, z_lower - FORMATION_OFFSET_M, z_main),
        ]:
            out.append(
                f'<rect x="{sx(u_ret) - 4:.1f}" y="{sy(z1_ret):.1f}" width="6" '
                f'height="{(z1_ret - z0_ret) * SCALE:.1f}" fill="#44403c"/>'
            )

        # Draw rooms on Lower, Main, Road
        for z_lv, h_lv, r_list, slab_col in [
            (z_lower, h_lower, rooms_lower, "#57534e"),
            (z_main, h_main, rooms_main, "#44403c"),
            (z_road, h_road, rooms_road, "#292524"),
        ]:
            for u0, u1, label, fill_hex in r_list:
                rx = sx(u0)
                rw = (u1 - u0) * SCALE
                ry = sy(z_lv + h_lv)
                rh = h_lv * SCALE
                out.append(
                    f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
                    f'fill="{fill_hex}" fill-opacity="0.88" stroke="#1c1917" stroke-width="1.6"/>'
                )
                out.append(
                    f'<rect x="{rx:.1f}" y="{sy(z_lv):.1f}" width="{rw:.1f}" height="{0.30 * SCALE:.1f}" '
                    f'fill="{slab_col}"/>'
                )
                if rw >= 36:
                    font_sz = 9.0 if rw >= 56 else 8.0
                    out.append(
                        f'<text x="{rx + rw / 2:.1f}" y="{ry + rh / 2 + 3.0:.1f}" text-anchor="middle" '
                        f'font-size="{font_sz}" font-weight="700" fill="#1c1917">{escape(label)}</text>'
                    )

        # Draw East Terraces & Flat East Lawn
        out.append(
            f'<line x1="{sx(ru1):.1f}" y1="{sy(z_road):.1f}" x2="{sx(mu1):.1f}" y2="{sy(z_road):.1f}" '
            f'stroke="#b45309" stroke-width="3"/>'
        )
        out.append(
            f'<text x="{sx((ru1 + mu1) / 2):.1f}" y="{sy(z_road) - 6:.1f}" text-anchor="middle" '
            f'font-size="8.5" font-weight="700" fill="#b45309">Roof Deck</text>'
        )
        out.append(
            f'<line x1="{sx(mu1):.1f}" y1="{sy(z_main):.1f}" x2="{sx(lu1):.1f}" y2="{sy(z_main):.1f}" '
            f'stroke="#b45309" stroke-width="3"/>'
        )
        out.append(
            f'<text x="{sx((mu1 + lu1) / 2):.1f}" y="{sy(z_main) - 6:.1f}" text-anchor="middle" '
            f'font-size="8.5" font-weight="700" fill="#b45309">East Balcony</text>'
        )
        out.append(
            f'<line x1="{sx(lu1):.1f}" y1="{sy(z_lower):.1f}" x2="{sx(lawn_u0):.1f}" y2="{sy(z_lower):.1f}" '
            f'stroke="#92400e" stroke-width="3"/>'
        )
        out.append(
            f'<text x="{sx((lu1 + lawn_u0) / 2):.1f}" y="{sy(z_lower) - 6:.1f}" text-anchor="middle" '
            f'font-size="8.0" font-weight="700" fill="#92400e">Terr.</text>'
        )
        # Flat East Lawn (graded lawn u=22.6..29.5m)
        out.append(
            f'<line x1="{sx(lawn_u0):.1f}" y1="{sy(lawn_z):.1f}" x2="{sx(29.5):.1f}" y2="{sy(lawn_z):.1f}" '
            f'stroke="#15803d" stroke-width="4"/>'
        )
        out.append(
            f'<text x="{sx((lawn_u0 + 29.5) / 2):.1f}" y="{sy(lawn_z) - 7:.1f}" text-anchor="middle" '
            f'font-size="9.5" font-weight="800" fill="#15803d">Flat East Lawn ({lawn_z:.1f}m)</text>'
        )

        # West Road Asphalt indicator
        out.append(
            f'<line x1="{sx(-5.5):.1f}" y1="{sy(ROAD_ASPHALT_Z_M):.1f}" x2="{sx(0.0):.1f}" y2="{sy(ROAD_ASPHALT_Z_M):.1f}" '
            f'stroke="#334155" stroke-width="4"/>'
        )
        out.append(
            f'<text x="{sx(-2.75):.1f}" y="{sy(ROAD_ASPHALT_Z_M) - 10:.1f}" text-anchor="middle" '
            f'font-size="9" font-weight="700" fill="#334155">West Road (~1677.6m)</text>'
        )

        # Natural ground dashed line on top
        nat_line = " ".join(f"{sx(u):.1f},{sy(z):.1f}" for u, z in nat_pts)
        out.append(
            f'<polyline points="{nat_line}" fill="none" stroke="#854d0e" stroke-width="2.2" stroke-dasharray="7,4"/>'
        )
        # Place natural ground label in clear east air space above the lawn
        out.append(
            f'<text x="{sx(23.2):.1f}" y="{sy(1672.5):.1f}" '
            f'font-size="9.5" font-weight="700" fill="#854d0e">── Natural ground profile (dashed)</text>'
        )

        # Max cut dimension callout at u=lu0, placed to the LEFT (in the earth below Main floor) so it never touches Stair-L
        zg_cut = z_ground(lu0, v_cut) or 1674.0
        zf_cut = z_lower - FORMATION_OFFSET_M
        cut_depth = zg_cut - zf_cut
        cx = sx(lu0) - 8.0
        out.append(
            f'<line x1="{cx:.1f}" y1="{sy(zg_cut):.1f}" x2="{cx:.1f}" y2="{sy(zf_cut):.1f}" '
            f'stroke="#b91c1c" stroke-width="1.8" stroke-dasharray="3,2"/>'
        )
        out.append(
            f'<rect x="{cx - 78:.1f}" y="{sy((zg_cut + zf_cut) / 2) - 9:.1f}" width="72" height="16" '
            f'rx="3" fill="#fef2f2" stroke="#fca5a5" stroke-width="0.9"/>'
        )
        out.append(
            f'<text x="{cx - 42:.1f}" y="{sy((zg_cut + zf_cut) / 2) + 2.5:.1f}" text-anchor="middle" '
            f'font-size="9" font-weight="800" fill="#b91c1c">Cut {cut_depth:.1f} m</text>'
        )

        # Level FFL callouts on right margin
        for lbl, z_val in [
            (f"Road FFL {z_road:.1f}m", z_road),
            (f"Main FFL {z_main:.1f}m", z_main),
            (f"Lower FFL {z_lower:.1f}m", z_lower),
        ]:
            out.append(
                f'<text x="{panel_x + panel_w - 22:.1f}" y="{sy(z_val) - 3:.1f}" text-anchor="end" '
                f'font-size="9.5" font-weight="700" fill="#292524">{lbl}</text>'
            )

    # Panel 1: Section A–A
    draw_ew_panel(
        panel_y=72.0,
        v_cut=4.2,
        title="Section A–A (East–West @ v = 4.2 m — Garage, Central Heart Stair, Cozy Living & Boys Room)",
        subtitle=f"3-level Central Stair (u=5.8–8.4m), Main Floor Cozy Living Corner (u=11.6–{mu1:.1f}m), Lower Floor (to u={lu1:.1f}m) & Flat East Lawn",
        rooms_road=[
            (ru0, 5.8, "Garage (2 Cars)", "#e7e5e4"),
            (5.8, 8.4, "Stair-R", "#fde68a"),
            (8.4, ru1, "Quiet Office", "#dbeafe"),
        ],
        rooms_main=[
            (mu0, 5.8, "WC / Store", "#e0f2fe"),
            (5.8, 8.4, "Stair-U", "#fde68a"),
            (8.4, 10.2, "Dress", "#f3e8ff"),
            (10.2, 11.6, "", "#fef3c7"),
            (11.6, mu1, "Cozy Living", "#ffedd5"),
        ],
        rooms_lower=[
            (5.8, 8.4, "Stair-L", "#fde68a"),
            (8.4, 10.2, "WC", "#e0f2fe"),
            (10.2, 12.6, "Hall-L", "#fef3c7"),
            (12.6, lu1, "Boys Bedroom (East View)", "#dcfce7"),
        ],
    )

    # Panel 2: Section B–B
    if spec.code == "C":
        main_south_rooms = [
            (mu0, 7.2, "Dining Room (SW)", "#ffedd5"),
            (7.2, 13.0, "South Kitchen", "#fed7aa"),
            (13.0, 14.4, "Pantry", "#f3e8ff"),
            (14.4, mu1, "Living SE", "#ffedd5"),
        ]
        lower_south_rooms = [
            (5.8, 8.8, "Laundry", "#e0f2fe"),
            (8.8, 12.6, "Family + Tea", "#fef3c7"),
            (12.6, lu1, "Grandparents Suite", "#dcfce7"),
        ]
    elif spec.code == "B":
        main_south_rooms = [
            (mu0, 3.8, "Pantry", "#f3e8ff"),
            (3.8, 9.8, "South Kitchen", "#fed7aa"),
            (9.8, 13.4, "Dining", "#ffedd5"),
            (13.4, mu1, "Living SE", "#ffedd5"),
        ]
        lower_south_rooms = [
            (5.8, 8.8, "Laundry", "#e0f2fe"),
            (8.8, 12.6, "Girls Bed", "#dcfce7"),
            (12.6, lu1, "Family Room + Tea Bar", "#fef3c7"),
        ]
    else:
        main_south_rooms = [
            (mu0, 3.8, "Pantry", "#f3e8ff"),
            (3.8, 10.0, "South Kitchen", "#fed7aa"),
            (10.0, 14.0, "Dining Room", "#ffedd5"),
            (14.0, mu1, "Living SE", "#ffedd5"),
        ]
        lower_south_rooms = [
            (5.8, 8.8, "Laundry", "#e0f2fe"),
            (8.8, 12.6, "Girls Bed", "#dcfce7"),
            (12.6, lu1, "Grandparents Suite", "#dcfce7"),
        ]

    draw_ew_panel(
        panel_y=484.0,
        v_cut=10.8,
        title="Section B–B (East–West @ v = 10.8 m — Road Lobby, South Kitchen & Dining, Lower Suite & East Lawn)",
        subtitle=f"Road Entrance Lobby, Prime South Kitchen & Dining (opening to South Terrace), and Lower Garden walk-out at u={lu1:.1f}m",
        rooms_road=[
            (ru0, 5.8, "Road Entrance Lobby", "#fef3c7"),
            (5.8, 8.4, "Plant", "#e5e7eb"),
            (8.4, ru1, "Road WC", "#e0f2fe"),
        ],
        rooms_main=main_south_rooms,
        rooms_lower=lower_south_rooms,
    )

    # Panel 3: Section C–C (North–South Cross-Slope Section @ u = 13.5 m + Earthwork Summary Card)
    panel_x = 86.0
    panel_y = 896.0
    panel_w = 600.0
    panel_h = 408.0
    v_min = -1.0
    z_top = 1682.0
    z_bot = 1666.0

    def sx_ns(v: float) -> float:
        return panel_x + (v - v_min) * SCALE

    def sy_ns(z: float) -> float:
        return panel_y + 52.0 + (z_top - z) * SCALE

    out.append(
        f'<rect x="{panel_x - 58:.1f}" y="{panel_y:.1f}" width="{panel_w + 58:.1f}" height="{panel_h:.1f}" '
        f'rx="8" fill="#ffffff" stroke="#e5dec9" stroke-width="1.2"/>'
    )
    out.append(
        f'<text x="{panel_x - 42:.1f}" y="{panel_y + 22:.1f}" font-size="13" font-weight="800" fill="#181614">'
        f"Section C–C (North–South @ u = 13.5 m — Cross-Slope &amp; South Terrace)</text>"
    )
    out.append(
        f'<text x="{panel_x - 42:.1f}" y="{panel_y + 39:.1f}" font-size="10.5" fill="#57534e">'
        f"Looking West across North Master Suite, Cozy Living Corner, Dining/Kitchen &amp; South Terrace</text>"
    )
    for z_tick in range(1666, 1683, 2):
        yy = sy_ns(float(z_tick))
        out.append(
            f'<line x1="{panel_x:.1f}" y1="{yy:.1f}" x2="{panel_x + panel_w - 16:.1f}" y2="{yy:.1f}" '
            f'stroke="#f1ece1" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{panel_x - 8:.1f}" y="{yy + 3.5:.1f}" text-anchor="end" font-size="9.5" fill="#78716c">'
            f"{z_tick}m</text>"
        )
    for v_tick in range(0, 19, 3):
        xx = sx_ns(float(v_tick))
        out.append(
            f'<text x="{xx:.1f}" y="{sy_ns(z_bot) + 14:.1f}" text-anchor="middle" font-size="9.5" fill="#78716c">'
            f"v={v_tick}m</text>"
        )

    v_samples = [0.0 + 0.25 * i for i in range(int(17.25 / 0.25) + 1)]
    ns_nat = [(v, max(z_ground(13.5, v) or 1672.0, z_bot + 0.2)) for v in v_samples]
    ns_poly = (
        [(sx_ns(ns_nat[0][0]), sy_ns(z_bot))]
        + [(sx_ns(v), sy_ns(z)) for v, z in ns_nat]
        + [(sx_ns(ns_nat[-1][0]), sy_ns(z_bot))]
    )
    out.append(
        f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in ns_poly)}" fill="url(#earth)" opacity="0.45"/>'
    )

    ns_lower = [
        (0.0, 4.8, "Boys Bed", "#dcfce7"),
        (4.8, 8.6, "Family / Girls", "#fef3c7"),
        (8.6, 13.2, "Grandparents", "#dcfce7"),
        (13.2, 15.6, "Bath", "#e0f2fe"),
    ]
    for v0, v1, lbl, col in ns_lower:
        rx, rw = sx_ns(v0), (v1 - v0) * SCALE
        ry, rh = sy_ns(z_lower + h_lower), h_lower * SCALE
        out.append(
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
            f'fill="{col}" fill-opacity="0.88" stroke="#1c1917" stroke-width="1.5"/>'
        )
        out.append(
            f'<rect x="{rx:.1f}" y="{sy_ns(z_lower):.1f}" width="{rw:.1f}" height="{0.30 * SCALE:.1f}" fill="#57534e"/>'
        )
        out.append(
            f'<text x="{rx + rw / 2:.1f}" y="{ry + rh / 2 + 3.0:.1f}" text-anchor="middle" '
            f'font-size="8.5" font-weight="700" fill="#1c1917">{escape(lbl)}</text>'
        )

    ns_main = [
        (mv0, 3.6 if spec.code != "B" else 3.8, "Master Suite", "#dcfce7"),
        (3.6 if spec.code != "B" else 3.8, 6.2, "Cozy Corner", "#ffedd5"),
        (6.2, 9.0, "Living Room", "#ffedd5"),
        (9.0, 12.4, "Dining / Pantry", "#fed7aa"),
    ]
    for v0, v1, lbl, col in ns_main:
        rx, rw = sx_ns(v0), (v1 - v0) * SCALE
        ry, rh = sy_ns(z_main + h_main), h_main * SCALE
        out.append(
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
            f'fill="{col}" fill-opacity="0.88" stroke="#1c1917" stroke-width="1.5"/>'
        )
        out.append(
            f'<rect x="{rx:.1f}" y="{sy_ns(z_main):.1f}" width="{rw:.1f}" height="{0.30 * SCALE:.1f}" fill="#44403c"/>'
        )
        out.append(
            f'<text x="{rx + rw / 2:.1f}" y="{ry + rh / 2 + 3.0:.1f}" text-anchor="middle" '
            f'font-size="8.5" font-weight="700" fill="#1c1917">{escape(lbl)}</text>'
        )

    out.append(
        f'<line x1="{sx_ns(12.4):.1f}" y1="{sy_ns(z_main):.1f}" x2="{sx_ns(15.6):.1f}" y2="{sy_ns(z_main):.1f}" '
        f'stroke="#b45309" stroke-width="3.5"/>'
    )
    out.append(
        f'<text x="{sx_ns(14.0):.1f}" y="{sy_ns(z_main) - 7:.1f}" text-anchor="middle" '
        f'font-size="9" font-weight="800" fill="#b45309">South Terrace</text>'
    )
    if spec.code == "B":
        out.append(
            f'<line x1="{sx_ns(0.0):.1f}" y1="{sy_ns(z_main):.1f}" x2="{sx_ns(1.4):.1f}" y2="{sy_ns(z_main):.1f}" '
            f'stroke="#b45309" stroke-width="3.5"/>'
        )
        out.append(
            f'<text x="{sx_ns(0.7):.1f}" y="{sy_ns(z_main) - 7:.1f}" text-anchor="middle" '
            f'font-size="8.0" font-weight="800" fill="#b45309">N.Terr</text>'
        )

    ns_line = " ".join(f"{sx_ns(v):.1f},{sy_ns(z):.1f}" for v, z in ns_nat)
    out.append(
        f'<polyline points="{ns_line}" fill="none" stroke="#854d0e" stroke-width="2.2" stroke-dasharray="7,4"/>'
    )

    # Earthwork & Rule 4.2 / 4.5 / 6.7 Summary Card on bottom right
    card_x = 704.0
    card_y = 896.0
    card_w = 618.0
    card_h = 408.0
    out.append(
        f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="{card_w:.1f}" height="{card_h:.1f}" '
        f'rx="8" fill="#ffffff" stroke="#e5dec9" stroke-width="1.2"/>'
    )
    out.append(
        f'<text x="{card_x + 20:.1f}" y="{card_y + 26:.1f}" font-size="13.5" font-weight="800" fill="#181614">'
        f"Earthwork &amp; Stepped Hillside Metrics ({escape(spec.option_id)})</text>"
    )
    rows = [
        (
            "Road Level Plate & FFL",
            f"u = {ru0:.1f}–{ru1:.1f} m · FFL {z_road:.1f} m (matches ~1677.6 m road)",
        ),
        (
            "Main Floor Plate & FFL",
            f"u = {mu0:.1f}–{mu1:.1f} m · FFL {z_main:.1f} m (stepped 1.4–2.2 m E)",
        ),
        (
            "Lower Floor Plate & FFL",
            f"u = {lu0:.1f}–{lu1:.1f} m · FFL {z_lower:.1f} m (walk-out at u={lu1:.1f} m)",
        ),
        (
            "Lower East Terrace",
            f"u = {lu1:.1f}–{lawn_u0:.1f} m · z = {z_lower:.1f} m (2.4–2.8 m deep)",
        ),
        (
            "Flat East Garden Lawn",
            f"u = {lawn_u0:.1f}–31.4 m (~8.8 m deep flat lawn @ {lawn_z:.1f} m)",
        ),
        (
            "Building Footprint Cut",
            f"{ew['summary']['building_cut_m3']:.0f} m³ cut · {ew['summary']['building_fill_m3']:.0f} m³ fill",
        ),
        (
            "Maximum Cut Depth",
            f"{ew['summary']['building_max_cut_m']:.2f} m (moderate hillside step, Rule 4.2)",
        ),
        (
            "Total Cut (incl. Lawn)",
            f"{ew['total_cut_m3']:.0f} m³ cut · {ew['total_fill_m3']:.0f} m³ fill ({ew['summary']['reuse_ratio_pct']:.0f}% reuse)",
        ),
        (
            "Net Soil Balance",
            f"{ew['net_export_m3']:.0f} m³ (100% of excavated soil reused on site)",
        ),
    ]
    for idx, (k_txt, v_txt) in enumerate(rows):
        ry = card_y + 62.0 + idx * 36.0
        if idx % 2 == 0:
            out.append(
                f'<rect x="{card_x + 14:.1f}" y="{ry - 17:.1f}" width="{card_w - 28:.1f}" height="28" '
                f'rx="4" fill="#f8f6f0"/>'
            )
        out.append(
            f'<text x="{card_x + 24:.1f}" y="{ry:.1f}" font-size="11" font-weight="700" fill="#44403c">'
            f"{escape(k_txt)}</text>"
        )
        out.append(
            f'<text x="{card_x + 220:.1f}" y="{ry:.1f}" font-size="11" fill="#1c1917">'
            f"{escape(v_txt)}</text>"
        )

    out.append(
        f'<text x="36" y="{H - 18}" font-size="10.5" fill="#78716c">{escape(EXPLORATORY_NOTICE)}</text>'
    )
    out.append("</svg>")

    opt_dir = HERE / spec.option_id
    opt_dir.mkdir(parents=True, exist_ok=True)
    svg_path = opt_dir / "terrain-sections.svg"
    png_path = opt_dir / "terrain-sections.png"
    svg_path.write_text("\n".join(out), encoding="utf-8")
    svg_to_png(svg_path, png_path, size=2200)
    return svg_path, png_path


def main() -> None:
    all_ew: dict[str, object] = {}
    for key in ("a", "b", "c"):
        spec = OPTIONS[key]
        ew = compute_option_earthwork(spec)
        all_ew[spec.option_id] = ew
        opt_dir = HERE / spec.option_id
        opt_dir.mkdir(parents=True, exist_ok=True)
        (opt_dir / "section-earthwork.json").write_text(json.dumps(ew, indent=2), encoding="utf-8")
        svg_path, png_path = render_option_sections(spec, ew)
        if key == "a":
            (HERE / "terrain-sections.svg").write_text(
                svg_path.read_text(encoding="utf-8"), encoding="utf-8"
            )
            svg_to_png(svg_path, HERE / "terrain-sections.png", size=2200)
        print(
            f"SECTIONS {spec.option_id}: building_cut={ew['summary']['building_cut_m3']} m3, "
            f"max_cut={ew['summary']['building_max_cut_m']} m, "
            f"total_cut={ew['total_cut_m3']} m3, total_fill={ew['total_fill_m3']} m3 "
            f"({ew['summary']['reuse_ratio_pct']}% reuse)"
        )
    (HERE / "earthwork.json").write_text(json.dumps(all_ew, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
