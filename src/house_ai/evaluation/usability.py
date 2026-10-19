"""Element-grounded conceptual usability critics (ADR 0019).

Measured geometry is kept separate from inferred feasibility under planning
assumptions. Findings are soft; these checks confer no regulatory approval.
"""

from __future__ import annotations

import math
from hashlib import sha256
from itertools import combinations

from shapely import affinity
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from house_ai.domain.base import EXTERIOR
from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.model import Operation, StairKind, WallKind
from house_ai.domain.program import Privacy, SpaceFunction, Strength
from house_ai.domain.terrain import elevation_at, site_surface

from .base import EvaluationContext
from .evaluators import _Out, _privacy
from .routes import RouteNetwork, shortest_in_polygon
from .templates import PROJECT, TEMPLATES, UsabilityPolicy, dimension, template
from .usability_geometry import (
    BUDGET_EXHAUSTED,
    EPS,
    door_geometry,
    fit_templates,
    free_floor,
    net_floor,
    objects_in,
    opening_segment,
    placed_envelope,
    wall_solid,
)

S = SpaceFunction
M, INF, NC = ClaimStatus.MEASURED, ClaimStatus.INFERRED, ClaimStatus.NOT_CHECKED
HABITABLE = {
    S.BEDROOM,
    S.GUEST_SUITE,
    S.LIVING,
    S.FAMILY,
    S.RECEPTION,
    S.STUDY,
    S.DINING,
    S.KITCHEN,
    S.PLAY,
}
CIRCULATION = {S.ENTRY, S.CORRIDOR, S.HALL, S.STAIR, S.LIFT}


# Distance ahead of a counter front searched for an opposite run (numerical choice).
AISLE_SEARCH_M = 3.0


def template_front_strip(item, depth):
    """Strip of the given depth in front of a placed item (front is local negative Y)."""
    w, d = item.width_m, item.depth_m
    strip = box(-w / 2, -d / 2 - depth, w / 2, -d / 2)
    strip = affinity.rotate(strip, item.rotation_deg, origin=(0, 0))
    return affinity.translate(strip, *item.position)


class _CriticOut(_Out):
    def result(self):
        result = super().result()
        result.run.version = "1.0.0"
        for metric in result.metrics:
            metric.evaluator_version = "1.0.0"
        return result

    def claim(self, name, value, ids, method, status=M, unit=None, basis=None):
        self.metric(name, value, method, status, unit, ids)
        self.metrics[-1].assumption_basis = basis

    def flag(self, code, ids, message, *, method="polygon_intersection", basis=PROJECT, status=INF):
        self.violation(code, Strength.SOFT, message, ids, status)
        self.violations[-1].id = (
            "u-" + sha256((self.name + code + repr(ids) + message).encode()).hexdigest()[:20]
        )
        self.violations[-1].method = method
        self.violations[-1].assumption_basis = basis


class Critic:
    version = "1.0.0"

    def __init__(self, policy: UsabilityPolicy | None = None):
        self.policy = policy or UsabilityPolicy()


class NetAreaEvaluator(Critic):
    name = "NetAreaEvaluator"

    def evaluate(self, ctx):
        out, model = _CriticOut(self.name), ctx.model
        for s in model.spaces:
            net = net_floor(model, s)
            ids = [s.id]
            out.claim("gross_area_m2", s.area_m2, ids, "polygon_area_centerline", unit="m2")
            relevant = [
                w
                for w in model.walls
                if w.level_id == s.level_id
                and w.start != w.end
                and s.boundary.to_shapely().distance(LineString([w.start, w.end])) < EPS
            ]
            coverage = unary_union([LineString([w.start, w.end]) for w in relevant])
            complete = (
                s.boundary.to_shapely().boundary.difference(coverage.buffer(EPS)).length < EPS
            )
            # Without walls on every edge the net value is an upper bound, not a measurement.
            out.claim(
                "net_area_m2",
                net.area,
                ids,
                "wall_solids_minus_floor_apertures",
                M if complete else INF,
                unit="m2",
            )
            rect = net.minimum_rotated_rectangle
            if rect.geom_type == "Polygon" and not rect.is_empty:
                pts = list(rect.exterior.coords)
                dims = sorted(math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False))
                for name, value in (
                    ("net_extent_short_m", dims[0]),
                    ("net_extent_long_m", dims[-1]),
                ):
                    out.claim(name, value, ids, "net_minimum_rotated_bounds", unit="m")
            else:
                for name in ("net_extent_short_m", "net_extent_long_m"):
                    out.claim(name, None, ids, "empty_or_degenerate_net_floor", NC)
            out.claim("net_wall_basis_complete", complete, ids, "boundary_wall_coverage")
            if not complete:
                out.flag(
                    "net_wall_basis_incomplete",
                    ids,
                    "Net area subtracts modelled walls only; wall thickness is missing on edges.",
                )
        return out.result()


class DoorClearanceEvaluator(Critic):
    name = "DoorClearanceEvaluator"

    def evaluate(self, ctx):
        out, model, p = _CriticOut(self.name), ctx.model, self.policy
        swings = []
        for o in model.openings:
            if not o.is_passable:
                continue
            geometry = door_geometry(model, o, p.approach_m)
            if geometry is None:
                out.claim("door_swing_checked", None, [o.id], "missing_swing_side", NC)
                continue
            out.claim(
                "door_swing_area_m2",
                geometry.swept.area,
                [o.id],
                "quarter_circle_sweep_0_5deg_conservative",
                unit="m2",
            )
            level = model.wall(o.host_wall_id).level_id
            swings.append((o, geometry, level))
            for w in model.walls:
                if w.level_id == level and w.id != o.host_wall_id:
                    if geometry.swept.intersection(wall_solid(model, w)).area > 1e-4:
                        out.flag(
                            "door_wall_conflict", [o.id, w.id], "Door sweep intersects wall solid."
                        )
            for sid in o.connects:
                if sid == EXTERIOR:
                    continue
                for f in objects_in(model, sid):
                    shape = placed_envelope(f)
                    shape = shape if shape is not None else f.footprint_polygon().to_shapely()
                    if geometry.swept.intersection(shape).area > 1e-4:
                        out.flag(
                            "door_object_conflict",
                            [o.id, f.id, sid],
                            "Door sweep intersects an object or its access envelope.",
                        )
                    zone = geometry.approaches.get(sid)
                    if (
                        zone is not None
                        and zone.intersection(f.footprint_polygon().to_shapely()).area > 1e-4
                    ):
                        out.flag(
                            "door_approach_blocked",
                            [o.id, f.id, sid],
                            "Object blocks conceptual door approach.",
                            basis=p.basis("approach_m"),
                        )
            for z in model.clearance_zones:
                if (
                    z.space_id in o.connects
                    and geometry.swept.intersection(z.boundary.to_shapely()).area > 1e-4
                ):
                    out.flag(
                        "door_clearance_zone_conflict",
                        [o.id, z.id, z.element_id],
                        "Door sweeps into declared clearance zone.",
                        basis=z.basis,
                    )
        for (a, ga, level_a), (b, gb, level_b) in combinations(swings, 2):
            if level_a == level_b and ga.swept.intersection(gb.swept).area > 1e-4:
                out.flag("door_door_conflict", [a.id, b.id], "Door swept envelopes overlap.")
        return out.result()


class StairUsabilityEvaluator(Critic):
    name = "StairUsabilityEvaluator"

    def evaluate(self, ctx):
        out, model, p = _CriticOut(self.name), ctx.model, self.policy
        for st in model.stairs:
            ids = [st.id]
            bottom, top = model.level(st.from_level_id), model.level(st.to_level_id)
            rise = top.elevation_m - bottom.elevation_m
            out.claim("stair_level_rise_m", rise, ids, "level_elevation_difference", unit="m")
            if rise <= 0:
                out.flag(
                    "stair_nonascending_levels",
                    ids + [bottom.id, top.id],
                    "Bottom/top levels are reversed or have equal elevations.",
                    status=M,
                )
                continue
            if st.riser_count and st.riser_height_m:
                error = abs(rise - st.riser_count * st.riser_height_m)
                out.claim("stair_rise_error_m", error, ids, "risers_vs_levels", unit="m")
                # Riser heights are stored to 4 dp: allow half a unit per riser.
                if error > st.riser_count * 5e-5 + 1e-6:
                    out.flag(
                        "stair_height_mismatch",
                        ids + [bottom.id, top.id],
                        "Riser total disagrees with connected floor elevations.",
                        status=M,
                    )
            above = [lv for lv in model.levels if lv.elevation_m > bottom.elevation_m + EPS]
            adjacent = min(above, key=lambda lv: lv.elevation_m).id == top.id if above else False
            # Only a stair to the next level up that arrives over the bottom level's own spaces
            # (stacked storeys) can test the bottom level's floor-to-floor (ADR 0023). Beside
            # a lower storey, a higher floor says nothing about that storey's height.
            if (
                adjacent
                and _arrives_over(model, st, bottom.id, p.landing_m)
                and bottom.floor_to_floor_m is not None
                and abs(bottom.floor_to_floor_m - rise) > 1e-4
            ):
                out.flag(
                    "floor_connection_height_mismatch",
                    ids + [bottom.id, top.id],
                    "Declared floor-to-floor height disagrees with stair connection.",
                    status=M,
                )
            for field, value, minimum, maximum in [
                ("rise", st.riser_height_m, p.min_rise_m, p.max_rise_m),
                ("going", st.tread_depth_m, p.min_going_m, math.inf),
                ("width", st.width_m, p.min_stair_width_m, math.inf),
            ]:
                out.claim(
                    f"stair_{field}_m",
                    value,
                    ids,
                    "canonical_stair_dimension",
                    NC if value is None else M,
                    unit="m",
                )
                if value is not None and not minimum <= value <= maximum:
                    basis = (
                        p.basis("min_rise_m") + "; " + p.basis("max_rise_m")
                        if field == "rise"
                        else p.basis("min_going_m" if field == "going" else "min_stair_width_m")
                    )
                    out.flag(
                        "stair_" + field + "_assumption",
                        ids,
                        f"Stair {field} is outside conceptual range.",
                        basis=basis,
                    )
            if (
                st.walking_line is None
                or st.kind != StairKind.STRAIGHT
                or len(st.walking_line) != 2
            ):
                for name in ("stair_run_fit", "stair_min_headroom_m", "stair_landing_clear"):
                    out.claim(name, None, ids, "missing_line_or_unsupported_complex_flight", NC)
                continue
            line = LineString(st.walking_line)
            if not line.is_simple or line.length < EPS:
                out.flag(
                    "stair_walking_line_invalid",
                    ids,
                    "Walking line is degenerate or crosses itself.",
                )
                continue
            footprint = st.footprint.to_shapely()
            fits_width = footprint.buffer(EPS).covers(line.buffer(st.width_m / 2, cap_style=2))
            if st.riser_count and st.tread_depth_m:
                needed = (st.riser_count - 1) * st.tread_depth_m
                out.claim("stair_required_run_m", needed, ids, "tread_count_times_going", unit="m")
                fits = fits_width and line.length + EPS >= needed
                out.claim("stair_run_fit", fits, ids, "walking_line_and_footprint_width")
                if not fits:
                    out.flag(
                        "stair_run_does_not_fit",
                        ids,
                        f"Needs {needed:.3f} m run and {st.width_m:.3f} m width.",
                    )
            else:
                out.claim("stair_run_fit", None, ids, "missing_riser_count_or_going", NC)
            self._headroom(out, model, st, line, rise)
            self._wall_clashes(out, model, st, line, rise)
            for sid, endpoint, neighbour, lv in (
                (st.bottom_space_id, st.walking_line[0], st.walking_line[1], bottom),
                (st.top_space_id, st.walking_line[-1], st.walking_line[-2], top),
            ):
                dx, dy = endpoint[0] - neighbour[0], endpoint[1] - neighbour[1]
                d = math.hypot(dx, dy)
                if d < EPS:
                    out.claim(
                        "stair_landing_clear", None, [st.id, sid], "zero_endpoint_segment", NC
                    )
                    continue
                far = (endpoint[0] + dx / d * p.landing_m, endpoint[1] + dy / d * p.landing_m)
                landing = LineString([endpoint, far]).buffer(st.width_m / 2, cap_style=2)
                floor = free_floor(model, model.space(sid))
                clear = floor.buffer(EPS).covers(landing)
                out.claim(
                    "stair_landing_clear",
                    clear,
                    [st.id, sid],
                    "landing_polygon_containment",
                    basis=p.basis("landing_m"),
                )
                if not clear:
                    out.flag(
                        "stair_landing_blocked",
                        [st.id, sid],
                        "Arrival/departure zone is outside free floor.",
                        basis=p.basis("landing_m"),
                    )
                for door in model.openings:
                    if door.is_passable and model.wall(door.host_wall_id).level_id == lv.id:
                        g = door_geometry(model, door)
                        if g and g.swept.intersection(landing).area > 1e-4:
                            out.flag(
                                "door_stair_conflict",
                                [door.id, st.id, sid],
                                "Door swings into stair arrival/departure zone.",
                            )
        return out.result()

    def _wall_clashes(self, out, model, st, line, rise):
        """Walls the flight would walk through (ADR 0023).

        Where a wall's plan line crosses the walking line, the wall must stay clear of the
        band from the pitch line to the minimum headroom above it, unless an opening in
        that wall spans the flight's width and the band.
        """
        bottom_z = model.level(st.from_level_id).elevation_m
        clear = self.policy.min_headroom_m
        clashes = 0
        for wall in model.walls:
            seg = LineString([wall.start, wall.end])
            hit = line.intersection(seg)
            if hit.is_empty:
                continue
            pts = [Point(c) for g in getattr(hit, "geoms", [hit]) for c in g.coords]
            for pt in pts:
                d = line.project(pt)
                if d <= EPS or d >= line.length - EPS:
                    continue
                pitch = bottom_z + rise * d / line.length
                wall_z = model.level(wall.level_id).elevation_m + wall.base_offset_m
                lo, hi = max(pitch, wall_z), min(pitch + clear, wall_z + wall.height_m)
                if hi - lo <= EPS:
                    continue
                along = seg.project(pt)
                level_z = model.level(wall.level_id).elevation_m
                if any(
                    o.host_wall_id == wall.id
                    and o.offset_m <= along - st.width_m / 2 + EPS
                    and along + st.width_m / 2 <= o.offset_m + o.width_m + EPS
                    and level_z + o.sill_m <= lo + EPS
                    and hi <= level_z + o.sill_m + o.height_m + EPS
                    for o in model.openings
                ):
                    continue
                clashes += 1
                out.flag(
                    "stair_wall_clash",
                    [st.id, wall.id],
                    f"Flight passes through {wall.id} between {lo - bottom_z:.3f} and "
                    f"{hi - bottom_z:.3f} m above its foot, inside the clear band.",
                    method="walking_line_wall_crossing_with_clear_band",
                    basis=self.policy.basis("min_headroom_m"),
                )
                break
        out.claim("stair_wall_clashes", clashes, [st.id], "walking_line_wall_crossing")

    def _headroom(self, out, model, st, line, rise):
        bottom_z = model.level(st.from_level_id).elevation_m
        heads = []
        slabs = [
            sl
            for sl in model.slabs
            if model.level(sl.level_id).elevation_m + sl.top_offset_m > bottom_z
        ]
        for slab in slabs:
            hit = line.intersection(slab.boundary.to_shapely())
            if hit.is_empty:
                continue
            pieces = list(hit.geoms) if hasattr(hit, "geoms") else [hit]
            # A top-arrival point on the edge of a slab opening is not an overhang.
            pieces = [
                piece for piece in pieces if piece.geom_type == "LineString" and piece.length > EPS
            ]
            if not pieces:
                continue
            distances = [line.project(Point(xy)) for piece in pieces for xy in piece.coords]
            underside = (
                model.level(slab.level_id).elevation_m + slab.top_offset_m - slab.thickness_m
            )
            head = min(underside - bottom_z - rise * d / line.length for d in distances)
            heads.append(head)
            if head + EPS < self.policy.min_headroom_m:
                out.flag(
                    "stair_low_headroom",
                    [st.id, slab.id],
                    f"Pitch-line headroom {head:.3f} m under slab.",
                    method="slab_intersection_piecewise_linear_pitchline",
                    basis=self.policy.basis("min_headroom_m"),
                )
        out.claim(
            "stair_min_headroom_m",
            min(heads) if heads else None,
            [st.id],
            "slab_intersection_pitchline" if heads else "no_overlying_slab_intersection",
            M if heads else NC,
            unit="m",
        )


def _arrives_over(model, st, level_id: str, landing_m: float) -> bool:
    """True when the stair arrives over a space on ``level_id`` (stacked storeys, ADR 0023).

    With a walking line, the test area is the arrival landing beyond the top end; without
    one (such as a U-shaped flight), the whole top space.
    """
    if st.walking_line and len(st.walking_line) >= 2:
        (x0, y0), (x1, y1) = st.walking_line[-2], st.walking_line[-1]
        d = math.hypot(x1 - x0, y1 - y0)
        if d < EPS:
            return False
        far = (x1 + (x1 - x0) / d * landing_m, y1 + (y1 - y0) / d * landing_m)
        area = LineString([(x1, y1), far]).buffer(st.width_m / 2, cap_style=2)
    else:
        area = model.space(st.top_space_id).boundary.to_shapely()
    return any(
        area.intersection(sp.boundary.to_shapely()).area > 1e-4
        for sp in model.spaces
        if sp.level_id == level_id
    )


class FurnitureUsabilityEvaluator(Critic):
    name = "FurnitureUsabilityEvaluator"

    def evaluate(self, ctx):
        out, model = _CriticOut(self.name), ctx.model
        # Explicit placements always checked; missing placements get labelled sampled studies.
        for s in model.spaces:
            objects = objects_in(model, s.id)
            floor = net_floor(model, s)
            if s.function == S.KITCHEN:
                counters = [
                    f
                    for f in objects
                    if getattr(f, "template_id", None) == "kitchen-run"
                    or getattr(f, "fixture_type", None) in {"kitchen_run", "counter"}
                ]
                run = sum(f.width_m for f in counters)
                out.claim(
                    "kitchen_counter_run_m",
                    run if counters else None,
                    [s.id, *[f.id for f in counters]],
                    "placed_counter_width_sum",
                    M if counters else NC,
                    unit="m",
                )
                if counters and run < TEMPLATES["kitchen-run"].width.value:
                    out.flag(
                        "kitchen_counter_run_short",
                        [s.id, *[f.id for f in counters]],
                        "Placed counter run is shorter than the conceptual 3 m template.",
                    )
                self._kitchen_aisles(out, s, counters)
            item = (
                next((i for i in ctx.program.items if i.id == s.program_item_id), None)
                if ctx.program
                else None
            )
            if item and item.accessible:
                possible = (
                    not free_floor(model, s)
                    .buffer(-self.policy.turning_diameter_m / 2 - 0.0001)
                    .is_empty
                )
                out.claim(
                    "accessible_turning_space",
                    possible,
                    [s.id],
                    "eroded_free_floor_turning_circle",
                    INF,
                    basis=self.policy.basis("turning_diameter_m"),
                )
                if not possible:
                    out.flag(
                        "accessible_turning_space_missing",
                        [s.id],
                        "No assumed turning circle in free floor.",
                    )
            for obj in objects:
                env = placed_envelope(obj)
                if env is None:
                    out.claim(
                        "object_clearance_checked",
                        None,
                        [obj.id, s.id],
                        "unknown_object_template",
                        NC,
                    )
                    continue
                blockers = [f for f in objects if f.id != obj.id]
                blocked = [
                    f.id
                    for f in blockers
                    if env.intersection(f.footprint_polygon().to_shapely()).area > 1e-4
                ]
                if not floor.buffer(EPS).covers(env) or blocked:
                    out.flag(
                        "object_clearance_blocked",
                        [obj.id, s.id, *blocked],
                        "Object access envelope leaves net floor or hits another object.",
                    )
            studies = self._studies(ctx, s, out)
            # Furniture already placed represents a design, not an invitation to fit a second set.
            if objects:
                continue
            for label, templates, required in studies:
                result = fit_templates(model, s, templates)
                basis = "assumption: " + "; ".join(t.id + ": " + t.width.source for t in templates)
                if result == BUDGET_EXHAUSTED:
                    out.claim(
                        label + "_sampled_fit",
                        None,
                        [s.id],
                        "search_budget_exhausted_before_decision",
                        NC,
                        basis=basis,
                    )
                    continue
                out.claim(
                    label + "_sampled_fit",
                    result is not None,
                    [s.id],
                    "0_1m_four_rotation_room_frame_packing",
                    INF,
                    basis=basis,
                )
                if result is None and required:
                    out.flag(
                        label + "_no_sampled_fit",
                        [s.id],
                        "No arrangement in the declared discrete template search; "
                        "continuous infeasibility has not been proved.",
                        method="0_1m_four_rotation_room_frame_packing",
                    )
                elif s.function == S.GARAGE:
                    self._garage_route(out, model, s, result)
        return out.result()

    def _kitchen_aisles(self, out, s, counters):
        """Clear width between placed runs whose fronts face each other."""
        aisle = TEMPLATES["kitchen-run"].front.value
        widths = []
        for a, b in combinations(counters, 2):
            bodies = [c.footprint_polygon().to_shapely() for c in (a, b)]
            # Each front is local negative Y: a facing pair sees the other body ahead.
            ahead = [
                template_front_strip(c, AISLE_SEARCH_M).intersects(other)
                for c, other in ((a, bodies[1]), (b, bodies[0]))
            ]
            if not all(ahead):
                continue
            width = bodies[0].distance(bodies[1])
            widths.append(width)
            out.claim(
                "kitchen_aisle_width_m",
                width,
                [s.id, a.id, b.id],
                "facing_counter_body_distance",
                unit="m",
                basis=TEMPLATES["kitchen-run"].front.source,
            )
            if width + EPS < aisle:
                out.flag(
                    "kitchen_aisle_narrow",
                    [s.id, a.id, b.id],
                    f"Aisle between facing runs is {width:.3f} m, below the {aisle} m assumption.",
                    method="facing_counter_body_distance",
                    basis=TEMPLATES["kitchen-run"].front.source,
                )
        if not widths:
            out.claim(
                "kitchen_aisle_width_m",
                None,
                [s.id, *[c.id for c in counters]],
                "no_facing_counter_pair",
                NC,
            )

    def _garage_route(self, out, model, s, result):
        remaining = net_floor(model, s).difference(unary_union([b for b, _ in result]))
        doors = [
            o
            for o in model.openings
            if o.is_passable and s.id in o.connects and EXTERIOR not in o.connects
        ]
        reachable = all(
            any(
                shortest_in_polygon(
                    remaining,
                    opening_segment(model, door).centroid.coords[0],
                    env.difference(body).representative_point().coords[0],
                )
                is not None
                for door in doors
            )
            for body, env in result
        )
        out.claim(
            "garage_pedestrian_route",
            reachable if doors else None,
            [s.id],
            "sampled_vehicle_clear_zone_to_house_portal_point_paths",
            INF if doors else NC,
            basis=PROJECT,
        )
        if doors and not reachable:
            out.flag(
                "garage_pedestrian_route_blocked",
                [s.id, *[o.id for o in doors]],
                "Sampled vehicles cannot reach the pedestrian house door.",
            )

    def _studies(self, ctx, s, out):
        req = ctx.program.usability if ctx.program else None
        if s.function in {S.BEDROOM, S.GUEST_SUITE}:
            # Undesignated rooms must hold a single bed; the double study is information only.
            variants = [("bed-double", False), ("bed-single", True)]
            if req and s.program_item_id in req.double_bed_program_item_ids:
                variants = [("bed-double", True)]
            elif req and s.program_item_id in req.single_bed_program_item_ids:
                variants = [("bed-single", True)]
            return [
                (v.replace("-", "_"), [TEMPLATES[v], TEMPLATES["wardrobe"]], required)
                for v, required in variants
            ]
        if s.function == S.STUDY:
            return [("desk_chair", [TEMPLATES["desk"]], True)]
        if s.function == S.DINING:
            if req is None or req.household_seats is None:
                out.claim("dining_sampled_fit", None, [s.id], "household_seats_unknown", NC)
                return []
            # 0.6 m per place, with two end seats; width and chair space are assumptions.
            t = TEMPLATES["dining"].model_copy(deep=True)
            t.width = dimension(
                "dining-household-width",
                max(1.2, math.ceil(max(1, req.household_seats - 2) / 2) * 0.6),
            )
            return [("dining", [t], True)]
        lookup = {
            S.LIVING: ("living", ["sofa-group"]),
            S.FAMILY: ("living", ["sofa-group"]),
            S.KITCHEN: ("kitchen", ["kitchen-run", "appliance"]),
            S.BATHROOM: ("bathroom", ["wc", "basin", "shower"]),
            S.WC: ("wc", ["wc", "basin"]),
            S.STORAGE: ("storage", ["shelf"]),
            S.PANTRY: ("storage", ["shelf"]),
            S.MECHANICAL: ("service", ["appliance"]),
            S.LAUNDRY: ("laundry_folding", ["laundry"]),
        }
        if s.function in lookup:
            label, ids = lookup[s.function]
            return [(label, [TEMPLATES[i] for i in ids], True)]
        if s.function == S.GARAGE:
            if req is None or req.vehicles is None:
                out.claim("garage_sampled_fit", None, [s.id], "vehicle_count_or_size_unknown", NC)
                return []
            vehicles = [
                template(
                    "vehicle-" + sha256(v.id.encode()).hexdigest()[:16],
                    v.width_m,
                    v.length_m,
                    left=v.door_side_clearance_m,
                    right=v.door_side_clearance_m,
                    front=0.9,
                    back=0.3,
                    source=v.source + "; " + PROJECT,
                )
                for v in req.vehicles
            ]
            return [("garage", vehicles, True)] if vehicles else []
        return []


def _route_status(route):
    if route is None:
        return NC
    return INF if route.estimated else M


def _route_method(route, missing):
    if route is None:
        return missing
    return "net_floor_visibility_graph_point_path" + (
        "_with_estimated_stair_run" if route.estimated else ""
    )


class RouteUsabilityEvaluator(Critic):
    name = "RouteUsabilityEvaluator"

    def evaluate(self, ctx):
        out, model, p = _CriticOut(self.name), ctx.model, self.policy
        net = RouteNetwork.for_model(model)
        privacy = _privacy(model)
        crossing_routes = 0
        guest_routes_complete = True
        guest_routes_estimated = False
        for s in model.spaces:
            route = net.from_entrance(s.id)
            out.claim(
                "entrance_route_length_m",
                route.length_m if route else None,
                [s.id],
                _route_method(route, "no_measurable_portal_path"),
                _route_status(route),
                unit="m",
            )
            guest_destination = s.function in {S.RECEPTION, S.LIVING, S.DINING, S.GUEST_SUITE, S.WC}
            if guest_destination and route is None:
                guest_routes_complete = False
            if route and guest_destination:
                guest_routes_estimated |= route.estimated
                private = [
                    sid for sid in route.space_ids[:-1] if privacy.get(sid) == Privacy.PRIVATE
                ]
                if private:
                    crossing_routes += 1
                    out.flag(
                        "guest_route_crosses_private",
                        [s.id, *private],
                        "Shortest guest-destination route crosses named private rooms.",
                        method="destination_visibility_graph",
                        status=_route_status(route),
                    )
            if s.function in {S.LIVING, S.FAMILY, S.KITCHEN}:
                self._through_traffic(out, model, s, net)
        out.claim(
            "guest_routes_crossing_private_count",
            crossing_routes,
            [],
            "destination_visibility_graph",
            (INF if guest_routes_estimated else M) if guest_routes_complete else NC,
        )
        for a, b, pairs in net.daily_routes():
            name = f"{a.value}_to_{b.value}"
            if not pairs:
                out.claim(name + "_length_m", None, [], "missing_route_endpoint", NC)
            for source, target, route in pairs:
                ids = [source.id, target.id]
                out.claim(
                    name + "_length_m",
                    route.length_m if route else None,
                    ids,
                    _route_method(route, "no_measurable_path"),
                    _route_status(route),
                    unit="m",
                )
                if route:
                    out.claim(name + "_level_changes", route.level_changes, ids, "stair_edges")
                    out.claim(name + "_rooms_crossed", ",".join(route.space_ids), ids, "path_trace")
                    if route.length_m > p.max_daily_route_m:
                        out.flag(
                            "daily_route_long",
                            [*ids, *route.element_ids],
                            f"{name}: {route.length_m:.3f} m point route.",
                            method="visibility_graph",
                            basis=p.basis("max_daily_route_m"),
                            status=_route_status(route),
                        )
        for lv in model.levels:
            spaces = [s for s in model.spaces if s.level_id == lv.id]
            total = sum(net_floor(model, s).area for s in spaces)
            circ = [s for s in spaces if s.function in CIRCULATION]
            area = sum(net_floor(model, s).area for s in circ)
            out.claim(
                "level_circulation_ratio", area / total if total else 0, [lv.id], "net_area_ratio"
            )
            if total and area / total > p.max_corridor_ratio:
                out.flag(
                    "excess_circulation",
                    [lv.id, *[s.id for s in circ]],
                    "Circulation share exceeds the conceptual assumption.",
                    basis=p.basis("max_corridor_ratio"),
                )
            for s in spaces:
                floor = free_floor(model, s)
                # Opening/closing reveals narrow unusable appendages; use labelled morphology.
                core = floor.buffer(-p.residual_width_m / 2).buffer(p.residual_width_m / 2)
                residual = floor.difference(core).area
                out.claim(
                    "residual_area_m2",
                    residual,
                    [s.id],
                    "morphological_opening",
                    unit="m2",
                    basis=p.basis("residual_width_m"),
                )
                if s.function not in CIRCULATION and residual > floor.area * p.max_residual_share:
                    out.flag(
                        "residual_space",
                        [s.id],
                        "Most floor is narrower than assumed usable width.",
                        basis=p.basis("residual_width_m"),
                    )
                if s.function in {S.CORRIDOR, S.HALL}:
                    portals = [o for o in model.openings if o.is_passable and s.id in o.connects]
                    length = 0.0
                    if len(portals) == 1 and not floor.is_empty:
                        start = opening_segment(model, portals[0]).centroid.coords[0]
                        for xy in s.boundary.outer:
                            # Finish-face endpoints nearest the original corners.
                            from shapely.ops import nearest_points

                            end = nearest_points(Point(xy), floor)[1].coords[0]
                            d = shortest_in_polygon(floor, start, end)
                            if d is not None:
                                length = max(length, d)
                    out.claim(
                        "dead_end_length_m",
                        length if len(portals) == 1 and not floor.is_empty else None,
                        [s.id],
                        "one_portal_farthest_corner_path",
                        M if len(portals) == 1 and not floor.is_empty else NC,
                        unit="m",
                    )
                    if length > p.max_dead_end_m:
                        out.flag(
                            "long_dead_end",
                            [s.id],
                            "Single-ended corridor has a long return path.",
                            basis=p.basis("max_dead_end_m"),
                        )
        return out.result()

    def _through_traffic(self, out, model, s, net):
        portals = [
            (k, xy)
            for k, (sid, xy, _) in net.nodes.items()
            if sid == s.id
            and k.startswith("door:")
            and EXTERIOR not in next(o for o in model.openings if o.id == net.nodes[k][2]).connects
        ]
        if len(portals) < 2:
            return
        floor = net_floor(model, s)
        # A conservative central work/seating zone; actual declared clear zones take priority.
        zones = [z.boundary.to_shapely() for z in model.clearance_zones if z.space_id == s.id]
        zone = unary_union(zones) if zones else floor.buffer(-self.policy.work_zone_inset_m)
        for (a, pa), (b, pb) in combinations(portals, 2):
            direct = LineString([pa, pb])
            if (
                floor.buffer(EPS).covers(direct)
                and direct.intersection(zone).length > self.policy.min_traffic_intersection_m
            ):
                code = (
                    "kitchen_through_traffic"
                    if s.function == S.KITCHEN
                    else "living_through_traffic"
                )
                out.flag(
                    code,
                    [s.id, net.nodes[a][2], net.nodes[b][2]],
                    "Portal desire line crosses a work/seating zone; alternate routes may exist.",
                    method="direct_desire_line_zone_intersection",
                )


class PrivacyUsabilityEvaluator(Critic):
    name = "PrivacyUsabilityEvaluator"

    def evaluate(self, ctx):
        out, model = _CriticOut(self.name), ctx.model
        levels = sorted(model.levels, key=lambda lv: (lv.elevation_m, lv.id))
        ranks = {lv.id: i for i, lv in enumerate(levels)}
        noisy = {S.KITCHEN, S.GARAGE, S.LAUNDRY, S.MECHANICAL, S.LIVING, S.FAMILY, S.GYM, S.PLAY}
        for bedroom in [s for s in model.spaces if s.function in {S.BEDROOM, S.GUEST_SUITE}]:
            for room in [s for s in model.spaces if s.function in noisy]:
                a, b = bedroom.boundary.to_shapely(), room.boundary.to_shapely()
                same = bedroom.level_id == room.level_id
                contact = (
                    a.boundary.intersection(b.boundary).length if same else a.intersection(b).area
                )
                if contact > EPS and (
                    same or abs(ranks[bedroom.level_id] - ranks[room.level_id]) == 1
                ):
                    out.flag(
                        "bedroom_noise_adjacency" if same else "bedroom_noise_stacking",
                        [bedroom.id, room.id],
                        "Noisy activity beside/above/below sleeping space; "
                        "acoustic assembly performance is unknown.",
                        method="plan_contact_or_stack",
                    )
        for door in model.openings:
            bathrooms = [
                sid
                for sid in door.connects
                if sid != EXTERIOR and model.space(sid).function in {S.BATHROOM, S.WC}
            ]
            if not door.is_passable or not bathrooms:
                continue
            lv = model.wall(door.host_wall_id).level_id
            solids = unary_union([wall_solid(model, w) for w in model.walls if w.level_id == lv])
            for source in model.spaces:
                if source.level_id != lv or source.function not in {S.ENTRY, S.LIVING, S.FAMILY}:
                    continue
                start = source.boundary.to_shapely().representative_point()
                end = opening_segment(model, door).centroid
                line = LineString([start, end])
                if line.intersection(solids).length < EPS:
                    out.flag(
                        "bathroom_entrance_visible",
                        [door.id, source.id, *bathrooms],
                        "Open-door sightline from a shared/entrance point to bathroom door.",
                        method="wall_occluded_open_door_ray",
                    )
        return out.result()


class DaylightOpportunityEvaluator(Critic):
    name = "DaylightOpportunityEvaluator"

    def evaluate(self, ctx: EvaluationContext):
        out, model, p = _CriticOut(self.name), ctx.model, self.policy
        site = ctx.site
        frame_matches = bool(
            site
            and site.coordinates.local
            and site.coordinates.local.id == model.coordinate_system_id
        )
        surface = site_surface(site) if site and frame_matches else None
        for s in model.spaces:
            if s.function not in HABITABLE:
                continue
            capable, glazing, facades = 0.0, 0.0, []
            unknown_ground = False
            for wall in model.walls:
                if wall.level_id != s.level_id or wall.kind not in {
                    WallKind.EXTERIOR,
                    WallKind.RETAINING,
                }:
                    continue
                seg = LineString([wall.start, wall.end])
                contact = seg.intersection(s.boundary.to_shapely().boundary)
                if contact.length < EPS:
                    continue
                windows = [
                    o
                    for o in model.openings
                    if o.host_wall_id == wall.id
                    and o.kind.value == "window"
                    and s.id in o.connects
                    and EXTERIOR in o.connects
                ]
                floor_z = model.level(s.level_id).elevation_m
                # Sampling is deliberately labelled inferred, including partially buried faces.
                count = max(2, math.ceil(contact.length / 0.25))
                points = [
                    contact.interpolate((i + 0.5) / count, normalized=True) for i in range(count)
                ]
                zs = [elevation_at(surface, (pt.x, pt.y)) if surface else None for pt in points]
                known = all(z is not None for z in zs)
                unknown_ground |= not known
                if wall.kind != WallKind.RETAINING and known:
                    capable += (
                        contact.length * sum(z <= floor_z + p.potential_sill_m for z in zs) / count
                    )
                for window in windows:
                    wseg = opening_segment(model, window)
                    samples = [wseg.interpolate(t, normalized=True) for t in (0, 0.5, 1)]
                    ground = [
                        elevation_at(surface, (pt.x, pt.y)) if surface else None for pt in samples
                    ]
                    if any(z is None for z in ground):
                        unknown_ground = True
                        continue
                    available = (
                        0
                        if wall.kind == WallKind.RETAINING
                        else sum(
                            min(
                                window.height_m,
                                max(0, floor_z + window.sill_m + window.height_m - z),
                            )
                            for z in ground
                        )
                        / 3
                    )
                    glazing += window.width_m * available
                    if available < window.height_m - EPS:
                        out.flag(
                            "window_buried",
                            [window.id, wall.id, s.id],
                            "Terrain/retaining face obscures part or all of this window.",
                            method="three_point_tin_sill_sampling",
                        )
                    if available > EPS and window.operation not in {
                        Operation.FIXED,
                        Operation.NONE,
                    }:
                        angle = (
                            math.degrees(
                                math.atan2(wall.end[1] - wall.start[1], wall.end[0] - wall.start[0])
                            )
                            % 360
                        )
                        # Opposite walls have opposite outward normals, using room side.
                        c, m = s.boundary.to_shapely().representative_point(), seg.centroid
                        ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                        inward_left = (c.x - m.x) * -uy + (c.y - m.y) * ux > 0
                        facades.append((angle + (-90 if inward_left else 90)) % 360)
            area = net_floor(model, s).area
            status = NC if unknown_ground or surface is None else INF
            out.claim(
                "window_capable_external_length_m",
                capable,
                [s.id],
                "0_25m_tin_unburied_face_sampling_sill_0_9m",
                status,
                unit="m",
                basis=p.basis("potential_sill_m"),
            )
            ratio = glazing / area if area else 0
            out.claim(
                "unburied_glazing_to_net_area",
                ratio,
                [s.id],
                "three_point_tin_window_area_ratio",
                status,
                basis=p.basis("min_glazing_ratio"),
            )
            if status != NC and ratio < p.min_glazing_ratio:
                out.flag(
                    "low_daylight_opportunity",
                    [s.id],
                    "Unburied glazing ratio is below assumption; no daylight simulation.",
                    method="glazing_area_ratio",
                    basis=p.basis("min_glazing_ratio"),
                )
            cross = any(
                min(abs(a - b), 360 - abs(a - b)) >= p.min_facade_angle_deg
                for a, b in combinations(facades, 2)
            )
            out.claim(
                "cross_ventilation_opportunity",
                cross,
                [s.id],
                "operable_unburied_different_facades_no_airflow_simulation",
                status,
                basis=p.basis("min_facade_angle_deg"),
            )
        self._outdoor_doors(out, model, surface)
        out.claim(
            "daylight_orientation",
            None,
            [],
            "orientation_simulation_not_implemented_opportunity_metrics_only",
            NC,
        )
        return out.result()

    def _outdoor_doors(self, out, model, surface):
        for door in model.openings:
            if not door.is_passable or EXTERIOR not in door.connects:
                continue
            wall = model.wall(door.host_wall_id)
            # Probe just outside the wall; never extrapolate TIN.
            mid = opening_segment(model, door).centroid
            u = (
                (wall.end[0] - wall.start[0]) / wall.length_m,
                (wall.end[1] - wall.start[1]) / wall.length_m,
            )
            sid = next(sid for sid in door.connects if sid != EXTERIOR)
            poly = model.space(sid).boundary.to_shapely()
            sign = -1 if poly.covers(Point(mid.x - u[1] * 0.1, mid.y + u[0] * 0.1)) else 1
            xy = (
                mid.x - u[1] * sign * (wall.thickness_m / 2 + 0.05),
                mid.y + u[0] * sign * (wall.thickness_m / 2 + 0.05),
            )
            z = elevation_at(surface, xy) if surface else None
            delta = (
                model.level(wall.level_id).elevation_m + door.sill_m - z if z is not None else None
            )
            out.claim(
                "outdoor_door_grade_delta_m",
                delta,
                [door.id, wall.id],
                "outside_face_tin_interpolation",
                INF if z is not None else NC,
                unit="m",
            )
            if delta is not None and abs(delta) > self.policy.max_grade_step_m:
                out.flag(
                    "outdoor_door_grade_mismatch",
                    [door.id, wall.id, sid],
                    f"Door threshold is {delta:.3f} m relative to grade; check landing/ramp.",
                    method="outside_face_tin_interpolation",
                    basis=self.policy.basis("max_grade_step_m"),
                )


class VehicleArrivalEvaluator(Critic):
    name = "VehicleArrivalEvaluator"

    def evaluate(self, ctx):
        out = _CriticOut(self.name)
        req = ctx.program.usability if ctx.program else None
        surfaces = (
            [
                f
                for f in ctx.site.features
                if f.kind.value in {"road", "driveway"} and f.geometry.type == "polygon"
            ]
            if ctx.site
            else []
        )
        frame_matches = bool(
            ctx.site
            and ctx.site.coordinates.local
            and ctx.site.coordinates.local.id == ctx.model.coordinate_system_id
        )
        if not req or not req.arrival_path or not req.vehicles or not surfaces or not frame_matches:
            out.claim(
                "vehicle_swept_path",
                None,
                [],
                "road_drive_polygon_arrival_path_or_vehicle_unknown",
                NC,
            )
            return out.result()
        road = unary_union([f.geometry.polygon.to_shapely() for f in surfaces])
        for v in req.vehicles:
            if v.turning_radius_m is None:
                out.claim("vehicle_swept_path", None, [v.id], "turning_radius_unknown", NC)
                continue
            centreline = filleted_path(req.arrival_path, v.turning_radius_m)
            turns = centreline is not None
            # Vehicle is bounded by a circle: deliberately conservative at bends and endpoints.
            radius = math.hypot(v.width_m, v.length_m) / 2
            fits = turns and road.buffer(EPS).covers(
                LineString(centreline).buffer(radius + 0.001, quad_segs=64)
            )
            out.claim(
                "vehicle_swept_path",
                fits,
                [v.id, *[f.id for f in surfaces]],
                "bounding_circle_sweep_of_turning_radius_filleted_centreline",
                INF,
                basis="assumption: circular vehicle bound; turning radius as centreline radius; "
                + v.source,
            )
            if not fits:
                out.flag(
                    "vehicle_arrival_conflict",
                    [v.id, *[f.id for f in surfaces]],
                    "Corner cannot take the turning radius, or the swept envelope leaves the "
                    "road/drive.",
                    method="bounding_circle_sweep_of_turning_radius_filleted_centreline",
                )
        return out.result()


def filleted_path(path, radius):
    """Arrival polyline with each corner replaced by a circular arc of `radius`.

    Returns None when a fillet's tangent length does not fit its legs (interior legs
    are shared equally by their two corners). Arcs are sampled every 1 degree.
    """
    pts = [tuple(path[0])]
    lengths = [math.dist(a, b) for a, b in zip(path, path[1:], strict=False)]
    last = len(path) - 2
    for i in range(1, len(path) - 1):
        a, b, c = path[i - 1], path[i], path[i + 1]
        u1 = ((b[0] - a[0]) / lengths[i - 1], (b[1] - a[1]) / lengths[i - 1])
        u2 = ((c[0] - b[0]) / lengths[i], (c[1] - b[1]) / lengths[i])
        cross = u1[0] * u2[1] - u1[1] * u2[0]
        theta = math.atan2(abs(cross), u1[0] * u2[0] + u1[1] * u2[1])
        if theta < 1e-9:
            pts.append(tuple(b))
            continue
        if theta > math.pi - 1e-9:
            return None
        tangent = radius * math.tan(theta / 2)
        room_prev = lengths[i - 1] if i == 1 else lengths[i - 1] / 2
        room_next = lengths[i] if i == last else lengths[i] / 2
        if tangent > min(room_prev, room_next) + EPS:
            return None
        sign = 1 if cross > 0 else -1
        p1 = (b[0] - u1[0] * tangent, b[1] - u1[1] * tangent)
        centre = (p1[0] - u1[1] * sign * radius, p1[1] + u1[0] * sign * radius)
        start = math.atan2(p1[1] - centre[1], p1[0] - centre[0])
        steps = max(1, math.ceil(math.degrees(theta)))
        pts.extend(
            (
                centre[0] + radius * math.cos(start + sign * theta * k / steps),
                centre[1] + radius * math.sin(start + sign * theta * k / steps),
            )
            for k in range(steps + 1)
        )
    pts.append(tuple(path[-1]))
    return pts


USABILITY_EVALUATORS = [
    NetAreaEvaluator(),
    DoorClearanceEvaluator(),
    StairUsabilityEvaluator(),
    FurnitureUsabilityEvaluator(),
    RouteUsabilityEvaluator(),
    PrivacyUsabilityEvaluator(),
    DaylightOpportunityEvaluator(),
    VehicleArrivalEvaluator(),
]
