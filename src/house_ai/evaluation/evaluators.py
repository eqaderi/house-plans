"""The six Milestone D evaluators.

Each reports individual metrics and violations. Every value says how it was
obtained: ``measured`` (computed exactly from the model's geometry or graph),
``inferred`` (derived through an approximation, e.g. terrain interpolated
between survey points or straight-line walking distance), or
``not_checked`` (no value). Nothing is scored as a single number.
"""

from __future__ import annotations

import math
from collections import deque

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from house_ai.constants.evaluations import (
    METRIC_ROOM_TERRACE_DOOR_COUNT,
    METRIC_ROOM_TERRACE_LEVEL_DELTA,
    METRIC_TERRACE_GROUND_DELTA,
    VIOLATION_ELONGATED_ROOM,
    VIOLATION_REQUIRED_DAYLIGHT_NO_WINDOW,
    VIOLATION_TERRACE_NO_DOOR,
    VIOLATION_TERRACE_STEP_TOO_HIGH,
)
from house_ai.domain.base import EXTERIOR
from house_ai.domain.constraints import MinAreaRule, MinDimensionRule
from house_ai.domain.epistemics import ClaimStatus, Epistemic
from house_ai.domain.evaluation import EvaluatorRun, EvaluatorRunStatus, MetricClaim, Violation
from house_ai.domain.integrity import FindingSeverity, check_model, circulation_graph
from house_ai.domain.model import HouseModel, Opening, OpeningKind, OpeningRole, Space, WallKind
from house_ai.domain.program import (
    DaylightNeed,
    Privacy,
    SpaceFunction,
    SpaceRelationshipKind,
    Strength,
    level_preference_met,
)
from house_ai.domain.relations import hops_between, is_relation_satisfied
from house_ai.domain.site import PointGeometry, PolygonGeometry, PolylineGeometry, SiteFeatureKind
from house_ai.domain.terrain import elevation_at, site_surface

from .base import EvaluationContext, EvaluatorResult

VERSION = "0.1.0"
M, INF, NC = ClaimStatus.MEASURED, ClaimStatus.INFERRED, ClaimStatus.NOT_CHECKED
S = SpaceFunction
CIRCULATION = {S.CORRIDOR, S.HALL, S.ENTRY, S.STAIR, S.LIFT}
OUTDOOR = {S.TERRACE, S.BALCONY}
#: Shared boundary at least this long counts as sharing a wall.
SHARED_WALL_M = 0.9


class EvaluatorOutput:
    """The metrics and Findings one evaluator run collects."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.metrics: list[MetricClaim] = []
        self.violations: list[Violation] = []

    def metric(
        self,
        metric: str,
        value,
        method: str,
        status: ClaimStatus = M,
        unit: str | None = None,
        subjects: list[str] | None = None,
    ) -> None:
        if isinstance(value, float):
            value = round(value, 3)
        self.metrics.append(
            MetricClaim(
                metric=metric,
                value=None if status is NC else value,
                unit=unit,
                method=method,
                status=status,
                evaluator=self.name,
                evaluator_version=VERSION,
                subject_ids=subjects or [],
            )
        )

    def violation(
        self,
        code: str,
        strength: Strength,
        message: str,
        subjects: list[str],
        status: ClaimStatus = M,
        constraint_id: str | None = None,
        method: str | None = None,
    ) -> None:
        self.violations.append(
            Violation(
                id="v-pending",
                constraint_id=constraint_id,
                code=code,
                strength=strength,
                message=message,
                subject_ids=subjects,
                status=status,
                evaluator=self.name,
                method=method,
            )
        )

    def result(self) -> EvaluatorResult:
        return EvaluatorResult(
            run=EvaluatorRun(name=self.name, version=VERSION, status=EvaluatorRunStatus.RAN),
            metrics=self.metrics,
            violations=self.violations,
        )


def _constraint_ids(ctx: EvaluationContext) -> set[str]:
    return {c.id for c in ctx.constraints.constraints} if ctx.constraints else set()


def _known(ctx: EvaluationContext, cid: str) -> str | None:
    return cid if cid in _constraint_ids(ctx) else None


def _min_side(space: Space) -> float:
    r = space.boundary.to_shapely().minimum_rotated_rectangle
    pts = list(r.exterior.coords)
    return min(math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2]))


def space_privacy(model: HouseModel) -> dict[str, Privacy]:
    """The privacy of each Space's Zone, for Spaces in a Zone."""
    by_zone = {z.id: z.privacy for z in model.zones}
    return {s.id: by_zone[s.zone_id] for s in model.spaces if s.zone_id in by_zone}


def _hops(graph: dict[str, set[str]], origin: str) -> dict[str, int]:
    return hops_between(graph, origin)


def _spaces_for(model: HouseModel, item_id: str) -> list[str]:
    return [s.id for s in model.spaces if s.program_item_id == item_id]


# --------------------------------------------------------------------- geometry


class GeometryEvaluator:
    name = "GeometryEvaluator"
    version = VERSION

    CODE_TO_CONSTRAINT: dict[str, str] = {
        "space_overlap": "c-no-overlap",
        "opening_outside_wall": "c-openings-on-walls",
        "opening_taller_than_wall": "c-openings-on-walls",
        "opening_overlap": "c-openings-on-walls",
        "opening_side_ambiguous": "c-doors-connect",
        "opening_sides_mismatch": "c-doors-connect",
        "space_unreachable": "c-reach-all",
        "outside_envelope": "c-within-envelope",
    }

    def evaluate(self, ctx: EvaluationContext) -> EvaluatorResult:
        out, model = EvaluatorOutput(self.name), ctx.model
        findings = check_model(model, ctx.site, ctx.program)
        for f in findings:
            cid = self.CODE_TO_CONSTRAINT.get(f.code)
            if f.code == "min_area_violation" and f.subject_ids:
                item = model.space(f.subject_ids[0]).program_item_id
                cid = f"c-min-area-{item}"
            elif f.code == "hard_adjacency_violation" and f.subject_ids:
                cid = f"c-{f.subject_ids[0]}"
            elif cid is None:
                cid = "c-valid-geometry"
            strength = Strength.HARD if f.severity is FindingSeverity.ERROR else Strength.SOFT
            out.violation(
                f.code, strength, f.message, list(f.subject_ids), constraint_id=_known(ctx, cid)
            )
        errors_n = sum(f.severity is FindingSeverity.ERROR for f in findings)
        out.metric("integrity_errors", errors_n, "check_model")
        out.metric("integrity_warnings", len(findings) - errors_n, "check_model")
        self._dimensions(ctx, out)
        shapes = [s.boundary.to_shapely() for s in model.spaces]
        gross = sum(s.area_m2 for s in model.spaces)
        foot = unary_union(shapes) if shapes else None
        out.metric("gross_floor_area_m2", gross, "polygon_area_centerline", unit="m2")
        if foot is not None:
            out.metric("footprint_area_m2", foot.area, "polygon_union_area", unit="m2")
            out.metric("footprint_perimeter_m", foot.length, "polygon_union_perimeter", unit="m")
            out.metric(
                "footprint_compactness",
                4 * math.pi * foot.area / foot.length**2,
                "isoperimetric_ratio",
            )
        out.metric("level_count", len(model.levels), "count")
        out.metric("storey_count", model.storey_count, "level_elevations_storey_height", INF)
        out.metric("space_count", len(model.spaces), "count")
        ext = sum(
            w.length_m for w in model.walls if w.kind in (WallKind.EXTERIOR, WallKind.RETAINING)
        )
        out.metric("exterior_wall_length_m", ext, "wall_length_sum", unit="m")
        out.metric(
            "interior_wall_length_m",
            sum(w.length_m for w in model.walls if w.kind is WallKind.INTERIOR),
            "wall_length_sum",
            unit="m",
        )
        return out.result()

    def _dimensions(self, ctx: EvaluationContext, out: EvaluatorOutput) -> None:
        if ctx.constraints is None:
            return
        model = ctx.model
        for c in ctx.constraints.constraints:
            rule = c.rule
            if isinstance(rule, MinDimensionRule):
                for sid in _spaces_for(model, rule.program_item_id):
                    side = _min_side(model.space(sid))
                    if side + 1e-6 < rule.min_width_m:
                        code = (
                            "codepack_min_dimension" if c.code_rule else "min_dimension_violation"
                        )
                        out.violation(
                            code,
                            c.strength,
                            f"{sid} is {side:.2f} m wide, below {rule.min_width_m:.2f} m ({c.id})",
                            [sid],
                            constraint_id=c.id,
                        )
            elif isinstance(rule, MinAreaRule) and c.code_rule is not None:
                for sid in _spaces_for(model, rule.program_item_id):
                    area = model.space(sid).area_m2
                    if area + 1e-6 < rule.min_area_m2:
                        out.violation(
                            "codepack_min_area",
                            c.strength,
                            f"{sid} has {area:.2f} m², below {rule.min_area_m2:.2f} m² ({c.id})",
                            [sid],
                            constraint_id=c.id,
                        )


def codepack_rules_checked(ctx: EvaluationContext) -> list[str]:
    if ctx.constraints is None:
        return []
    return sorted({c.code_rule.rule_id for c in ctx.constraints.constraints if c.code_rule})


# ---------------------------------------------------------------------- program


class ProgramEvaluator:
    name = "ProgramEvaluator"
    version = VERSION

    def evaluate(self, ctx: EvaluationContext) -> EvaluatorResult:
        out, model, program = EvaluatorOutput(self.name), ctx.model, ctx.program
        if program is None:
            return EvaluatorResult(
                run=EvaluatorRun(
                    name=self.name,
                    version=VERSION,
                    status=EvaluatorRunStatus.NOT_RUN,
                    reason="no program",
                )
            )
        entry = next((lv for lv in model.levels if lv.id == "lv-entry"), None)
        net_target = placed_net = 0.0
        prefs_met = prefs_total = 0
        for item in program.space_requirements:
            spaces = [model.space(s) for s in _spaces_for(model, item.id)]
            if (
                item.function in OUTDOOR
                or item.level_preference in ("outdoor", "roof")
                or (item.function is S.OTHER and item.target_area_m2 is None)
            ):
                if spaces:
                    out.metric(
                        "outdoor_item_placed", True, "space_for_item", subjects=[item.id]
                    )
                elif item.function in (S.TERRACE, S.BALCONY):
                    # The generators place terraces and balconies (S10-11): a missing one is
                    # a missing program item, not an unknown.
                    out.metric(
                        "outdoor_item_placed", False, "space_for_item", subjects=[item.id]
                    )
                    out.violation(
                        "program_item_missing",
                        Strength.SOFT,
                        f"{item.name} ({item.id}): not placed",
                        [item.id],
                    )
                else:
                    out.metric(
                        "outdoor_item_placed", None, "not_placed_by_generator", NC,
                        subjects=[item.id],
                    )  # fmt: skip
                continue
            want = 1 if item.function in (S.STAIR, S.LIFT) else item.quantity
            if item.function in (S.HALL, S.CORRIDOR) and not spaces:
                want = 1
            if len(spaces) < want:
                strength = Strength.HARD if item.priority.value == "must" else Strength.SOFT
                note = ""
                if item.function in (S.STAIR, S.LIFT) and len(model.levels) == 1:
                    # Vertical circulation serves levels; a one-level concept has none to serve.
                    strength, note = Strength.SOFT, "; not needed in a one-level plan option"
                out.violation(
                    "program_item_missing",
                    strength,
                    f"{item.name} ({item.id}): {len(spaces)} of {want} placed{note}",
                    [item.id],
                )
            if item.target_area_m2 is not None:
                net_target += item.target_area_m2 * want
            for sp in spaces:
                placed_net += sp.area_m2
                out.metric(
                    "room_area_m2",
                    sp.area_m2,
                    "polygon_area_centerline",
                    unit="m2",
                    subjects=[sp.id, item.id],
                )
                # Opening opportunity is measurable now; illumination, borrowed light,
                # orientation and obstruction still need a daylight study.
                windows = [
                    o
                    for o in model.openings
                    if o.kind is OpeningKind.WINDOW
                    and sp.id in o.connects
                    and EXTERIOR in o.connects
                    and model.wall(o.host_wall_id).kind is WallKind.EXTERIOR
                ]
                if item.daylight is DaylightNeed.REQUIRED:
                    out.metric(
                        "required_daylight_exterior_windows",
                        len(windows),
                        "exterior_window_count_only",
                        subjects=[sp.id, item.id],
                    )
                    if not windows:
                        out.violation(
                            VIOLATION_REQUIRED_DAYLIGHT_NO_WINDOW,
                            Strength.SOFT,
                            f"{sp.id} requests daylight but has no exterior window; borrowed "
                            "light and actual illumination are not checked",
                            [sp.id, item.id],
                        )
                if item.function not in CIRCULATION | {S.STORAGE, S.GARAGE, S.MECHANICAL}:
                    poly = sp.boundary.to_shapely().minimum_rotated_rectangle
                    pts = list(poly.exterior.coords)
                    sides = [math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])]
                    ratio = max(sides) / min(sides)
                    out.metric(
                        "room_aspect_ratio",
                        ratio,
                        "rotated_rectangle_sides",
                        subjects=[sp.id, item.id],
                    )
                    if ratio > 3 + 1e-6:
                        out.violation(
                            VIOLATION_ELONGATED_ROOM,
                            Strength.SOFT,
                            f"{sp.id} has a {ratio:.1f}:1 aspect ratio; check furniture and "
                            "clear usable dimensions (3:1 is a conceptual review trigger, "
                            "not a code limit)",
                            [sp.id, item.id],
                        )
                if item.target_area_m2:
                    out.metric(
                        "room_area_vs_target_pct",
                        100.0 * (sp.area_m2 / item.target_area_m2 - 1.0),
                        "polygon_area_centerline",
                        unit="%",
                        subjects=[sp.id, item.id],
                    )
                if item.function in (S.STAIR, S.LIFT):
                    continue
                ok = level_preference_met(
                    item.level_preference,
                    model.level(sp.level_id).elevation_m,
                    entry.elevation_m if entry else None,
                    len(model.levels),
                )
                if ok is None:
                    continue
                prefs_total += 1
                prefs_met += ok
                if not ok:
                    out.violation(
                        "level_preference_unmet",
                        Strength.SOFT,
                        f"{sp.id} is on {sp.level_id}; the program prefers {item.level_preference}",
                        [sp.id, item.id],
                    )
            if item.accessible:
                for sp in spaces:
                    if not _step_free(model, sp.id):
                        out.violation(
                            "accessible_not_step_free",
                            Strength.HARD,
                            f"{sp.id} must be reachable step-free from the entrance",
                            [sp.id, item.id],
                        )
        gross = sum(s.area_m2 for s in model.spaces)
        unprogrammed = sum(
            s.area_m2
            for s in model.spaces
            if s.program_item_id is None and s.function not in CIRCULATION
        )
        out.metric("net_program_area_m2", placed_net, "polygon_area_centerline", unit="m2")
        out.metric("net_target_area_m2", net_target, "program_sum", unit="m2")
        out.metric("unprogrammed_area_m2", unprogrammed, "polygon_area_centerline", unit="m2")
        if program.target_gross_area_m2:
            out.metric(
                "gross_vs_target_pct",
                100.0 * (gross / program.target_gross_area_m2 - 1),
                "polygon_area_centerline",
                unit="%",
            )
        out.metric("level_preferences_met", prefs_met, "level_lookup")
        out.metric("level_preferences_total", prefs_total, "level_lookup")
        if program.storeys is not None and program.storeys != model.storey_count:
            out.violation(
                "storey_count_differs",
                Strength.SOFT,
                f"the program asks for {program.storeys} storey(s); this plan option has "
                f"{model.storey_count} storey(s) on {len(model.levels)} level(s)",
                [],
            )
        return out.result()


def _step_free(model: HouseModel, target: str) -> bool:
    """Reachable from outside through doors only (no stairs)."""
    graph: dict[str, set[str]] = {}
    for o in model.openings:
        if o.is_passable:
            a, b = o.connects
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set()).add(a)
    return target in _hops(graph, EXTERIOR)


# -------------------------------------------------------------------- adjacency


class AdjacencyEvaluator:
    name = "AdjacencyEvaluator"
    version = VERSION

    def evaluate(self, ctx: EvaluationContext) -> EvaluatorResult:
        out, model, program = EvaluatorOutput(self.name), ctx.model, ctx.program
        if program is None:
            return EvaluatorResult(
                run=EvaluatorRun(
                    name=self.name,
                    version=VERSION,
                    status=EvaluatorRunStatus.NOT_RUN,
                    reason="no program",
                )
            )
        graph = circulation_graph(model)
        hard_ok = hard_n = 0
        soft_w = soft_ok = 0.0
        outdoor = {
            i.id
            for i in program.space_requirements
            if i.function in OUTDOOR or i.level_preference in ("outdoor", "roof")
        }
        for adj in program.space_relationships:

            def ends(item_id: str) -> list[str]:
                if item_id == EXTERIOR:
                    return [EXTERIOR]
                return _spaces_for(model, item_id)

            a_s, b_s = ends(adj.a), ends(adj.b)
            if outdoor & {adj.a, adj.b} and (not a_s or not b_s):
                out.metric(
                    "adjacency_satisfied", None, "outdoor_item_not_placed", NC, subjects=[adj.id]
                )
                continue

            ok, method = is_relation_satisfied(adj.kind, model, graph, a_s, b_s)
            subjects = [adj.id, *a_s, *b_s]
            if ok is None:
                out.metric("adjacency_satisfied", None, "not_evaluated", NC, subjects=subjects)
                continue
            out.metric("adjacency_satisfied", ok, method, subjects=subjects)
            if adj.strength is Strength.HARD:
                hard_n += 1
                hard_ok += ok
                # Hard connections are already reported by the GeometryEvaluator (check_model).
                if not ok and adj.kind is not SpaceRelationshipKind.CONNECTED:
                    out.violation(
                        "hard_adjacency_unmet",
                        Strength.HARD,
                        f"{adj.id}: {adj.a} {adj.kind.value} {adj.b} is not met",
                        subjects,
                        constraint_id=_known(ctx, f"c-{adj.id}"),
                    )
            else:
                soft_w += adj.weight or 0.0
                soft_ok += (adj.weight or 0.0) * ok
                if not ok:
                    out.violation(
                        "soft_adjacency_unmet",
                        Strength.SOFT,
                        f"{adj.id}: {adj.a} {adj.kind.value} {adj.b} is not met",
                        subjects,
                        constraint_id=_known(ctx, f"c-{adj.id}"),
                    )
        out.metric("hard_adjacencies_met", hard_ok, "graph_and_boundary_analysis")
        out.metric("hard_adjacencies_total", hard_n, "count")
        if soft_w:
            out.metric("soft_adjacency_score", soft_ok / soft_w, "weighted_fraction_met")
        else:
            out.metric("soft_adjacency_score", None, "no_soft_requirements", NC)
        return out.result()


# ------------------------------------------------------------------ circulation

#: Id prefixes that marked entrances before openings carried a role (ADR 0031).
_ROLE_PREFIX = {OpeningRole.MAIN_ENTRANCE: "d-front", OpeningRole.VEHICLE_ENTRANCE: "d-garage"}


def _is_entrance(o: Opening, role: OpeningRole) -> bool:
    """Whether ``o`` is the ``role`` entrance: by its role, else by its legacy id prefix."""
    if o.role is not None:
        return o.role is role
    return o.id.startswith(_ROLE_PREFIX[role])


def _pedestrian_entrances(model: HouseModel) -> tuple[set[str], str]:
    """Identify route origins without treating vehicle access as a front door."""
    candidates = [
        o
        for o in model.openings
        if o.is_passable
        and EXTERIOR in o.connects
        and model.space(next(s for s in o.connects if s != EXTERIOR)).function is not S.GARAGE
    ]
    front = [o for o in candidates if _is_entrance(o, OpeningRole.MAIN_ENTRANCE)]
    if front:
        return {o.id for o in front}, "front_door_identifier"
    entry = [
        o
        for o in candidates
        if any(s.function is S.ENTRY and s.id in o.connects for s in model.spaces)
    ]
    if entry:
        return {o.id for o in entry}, "inferred_from_entry_space"
    # Hand-authored models may not identify an entrance. Use one deterministic
    # pedestrian door, and expose the assumption instead of rooting every exit.
    if candidates:
        return {min(candidates, key=lambda o: o.id).id}, "assumed_first_pedestrian_door"
    return set(), "no_pedestrian_entrance"


class CirculationEvaluator:
    name = "CirculationEvaluator"
    version = VERSION

    def evaluate(self, ctx: EvaluationContext) -> EvaluatorResult:
        out, model = EvaluatorOutput(self.name), ctx.model
        graph = circulation_graph(model)
        entrances, entrance_basis = _pedestrian_entrances(model)
        for neighbours in graph.values():
            neighbours.discard(EXTERIOR)
        graph[EXTERIOR] = set()
        for opening in model.openings:
            if opening.id in entrances:
                room = next(s for s in opening.connects if s != EXTERIOR)
                graph[EXTERIOR].add(room)
                graph.setdefault(room, set()).add(EXTERIOR)
        out.metric("entrance_route_basis", entrance_basis, "opening_metadata", INF)
        hops = _hops(graph, EXTERIOR)
        unreachable = [s.id for s in model.spaces if s.id not in hops]
        out.metric("unreachable_spaces", len(unreachable), "graph_analysis", subjects=unreachable)
        gross = sum(s.area_m2 for s in model.spaces)
        circ = sum(s.area_m2 for s in model.spaces if s.function in CIRCULATION)
        out.metric("circulation_area_m2", circ, "polygon_area_centerline", unit="m2")
        out.metric("circulation_ratio", circ / gross if gross else 0.0, "area_ratio")
        depths = [hops[s.id] for s in model.spaces if s.id in hops]
        if depths:
            out.metric("max_depth_from_entrance", max(depths) - 1, "graph_analysis", unit="doors")
            out.metric(
                "mean_depth_from_entrance",
                sum(depths) / len(depths) - 1,
                "graph_analysis",
                unit="doors",
            )
        out.metric("stair_count", len(model.stairs), "count")
        levels_reached = {model.space(s).level_id for s in hops if s != EXTERIOR}
        out.metric(
            "all_levels_reachable",
            levels_reached == {lv.id for lv in model.levels},
            "graph_analysis",
        )
        from .routes import RouteNetwork

        network = RouteNetwork.for_model(model)
        routes = network.entrance_routes()
        complete = bool(routes) and all(sid in routes for sid in network.destinations)
        estimated = any(r.estimated for r in routes.values())
        out.metric(
            "max_walk_from_entrance_m",
            max(r.length_m for r in routes.values()) if complete else None,
            "net_floor_visibility_graph_point_path"
            + ("_with_estimated_stair_runs" if estimated else ""),
            (INF if estimated else M) if complete else NC,
            unit="m",
        )
        if not complete:
            out.metric("entrance_route_coverage", len(routes), "measurable_space_routes")
        privacy = space_privacy(model)
        crossings = 0
        crossed: list[str] = []
        parents = self._parents(graph)
        for s in model.spaces:
            if (
                privacy.get(s.id) not in (Privacy.PUBLIC, Privacy.SEMI_PRIVATE)
                or s.id not in parents
            ):
                continue
            node = parents[s.id]
            while node is not None and node != EXTERIOR:
                if privacy.get(node) is Privacy.PRIVATE:
                    crossings += 1
                    crossed.append(s.id)
                node = parents.get(node)
        out.metric("guest_private_crossings", crossings, "graph_analysis", subjects=crossed)
        if crossings:
            out.violation(
                "private_space_crossed",
                Strength.SOFT,
                f"{crossings} route(s) to shared rooms pass through private rooms",
                crossed,
                constraint_id=_known(ctx, "c-obj-circulation-efficiency"),
            )
        return out.result()

    @staticmethod
    def _parents(graph: dict[str, set[str]]) -> dict[str, str | None]:
        parents: dict[str, str | None] = {EXTERIOR: None}
        queue = deque([EXTERIOR])
        while queue:
            n = queue.popleft()
            for m in sorted(graph.get(n, ())):
                if m not in parents:
                    parents[m] = n
                    queue.append(m)
        return parents

    @staticmethod
    def _walk(model: HouseModel) -> dict[str, float]:
        """Compatibility entry point for the S6 net-floor route engine."""
        from .routes import RouteNetwork

        return RouteNetwork(model).entrance_distances()


# ---------------------------------------------------------------------- privacy


class PrivacyEvaluator:
    name = "PrivacyEvaluator"
    version = VERSION

    def evaluate(self, ctx: EvaluationContext) -> EvaluatorResult:
        out, model = EvaluatorOutput(self.name), ctx.model
        privacy = space_privacy(model)
        entry_spaces = {s.id for s in model.spaces if s.function is S.ENTRY}
        bedrooms = [s.id for s in model.spaces if s.function in (S.BEDROOM, S.GUEST_SUITE)]
        on_entry = sorted(
            {
                sid
                for o in model.openings
                if o.is_passable
                for sid in o.connects
                if sid in bedrooms and set(o.connects) & entry_spaces
            }
        )
        out.metric("bedroom_doors_on_entrance", len(on_entry), "graph_analysis", subjects=on_entry)
        shared = 0
        pairs: list[str] = []
        for w in model.walls:
            if w.kind is not WallKind.INTERIOR:
                continue
            sides = self._sides(model, w)
            kinds = {privacy.get(s) for s in sides}
            if Privacy.PRIVATE in kinds and Privacy.PUBLIC in kinds:
                shared += 1
                pairs.extend(sorted(sides))
        out.metric(
            "private_public_shared_walls", shared, "shared_boundary", subjects=sorted(set(pairs))
        )
        living_levels = {s.level_id for s in model.spaces if privacy.get(s.id) is Privacy.PUBLIC}
        bed_levels = {model.space(b).level_id for b in bedrooms}
        if bedrooms and len(model.levels) > 1:
            out.metric(
                "bedrooms_on_separate_level", not (bed_levels & living_levels), "level_lookup"
            )
        sightline = self._sightline(model, privacy)
        if sightline is None:
            out.metric("entrance_sightline_private_spaces", None, "no_main_entrance", NC)
        else:
            out.metric(
                "entrance_sightline_private_spaces",
                sightline,
                "ray_from_front_door_8m_ignoring_door_leaves",
                INF,
            )
        if on_entry:
            out.violation(
                "bedroom_opens_on_entrance",
                Strength.SOFT,
                "bedroom doors open directly onto the entrance",
                on_entry,
                constraint_id=_known(ctx, "c-obj-privacy"),
            )
        return out.result()

    @staticmethod
    def _sides(model: HouseModel, w) -> set[str]:
        d = w.length_m
        mx, my = (w.start[0] + w.end[0]) / 2, (w.start[1] + w.end[1]) / 2
        nx, ny = -(w.end[1] - w.start[1]) / d, (w.end[0] - w.start[0]) / d
        reach = w.thickness_m / 2 + 0.05
        found = set()
        for sgn in (1, -1):
            p = Point(mx + sgn * nx * reach, my + sgn * ny * reach)
            for s in model.spaces:
                if s.level_id == w.level_id and s.boundary.to_shapely().contains(p):
                    found.add(s.id)
        return found

    @staticmethod
    def _sightline(model: HouseModel, privacy: dict[str, Privacy]) -> int | None:
        """Private Spaces an 8 m ray from the front door crosses; None without a front door."""
        fronts = [
            o
            for o in model.openings
            if o.kind is OpeningKind.DOOR
            and EXTERIOR in o.connects
            and _is_entrance(o, OpeningRole.MAIN_ENTRANCE)
        ]
        if not fronts:
            return None
        o = fronts[0]
        w = model.wall(o.host_wall_id)
        inside = o.connects[0] if o.connects[1] == EXTERIOR else o.connects[1]
        d = w.length_m
        t = o.offset_m + o.width_m / 2
        p = (
            w.start[0] + (w.end[0] - w.start[0]) * t / d,
            w.start[1] + (w.end[1] - w.start[1]) * t / d,
        )
        n = (-(w.end[1] - w.start[1]) / d, (w.end[0] - w.start[0]) / d)
        sp = model.space(inside).boundary.to_shapely()
        if not sp.contains(Point(p[0] + n[0] * 0.3, p[1] + n[1] * 0.3)):
            n = (-n[0], -n[1])
        ray = LineString([p, (p[0] + n[0] * 8.0, p[1] + n[1] * 8.0)])
        return sum(
            1
            for s in model.spaces
            if s.level_id == w.level_id
            and privacy.get(s.id) is Privacy.PRIVATE
            and s.boundary.to_shapely().intersects(ray)
        )


# ------------------------------------------------------------------------- site


class SiteEvaluator:
    name = "SiteEvaluator"
    version = VERSION

    def evaluate(self, ctx: EvaluationContext) -> EvaluatorResult:
        out, model, site = EvaluatorOutput(self.name), ctx.model, ctx.site
        if site is None:
            return EvaluatorResult(
                run=EvaluatorRun(
                    name=self.name,
                    version=VERSION,
                    status=EvaluatorRunStatus.NOT_RUN,
                    reason="no site",
                )
            )
        if ctx.site_approved is not None:
            out.metric("site_approved", ctx.site_approved, "workflow_site_gate")
        env = site.buildable_envelope
        limit = (
            env.polygon.to_shapely()
            if env
            else (site.boundary.to_shapely() if site.boundary else None)
        )
        out.metric(
            "envelope_basis",
            "buildable_envelope" if env else ("parcel_boundary_only" if site.boundary else "none"),
            "site_record",
        )
        out.metric(
            "envelope_status", env.status.value if env else Epistemic.UNKNOWN.value, "site_record"
        )
        foot = unary_union([s.boundary.to_shapely() for s in model.spaces])
        if limit is not None:
            out.metric("within_envelope", bool(limit.buffer(1e-6).covers(foot)), "polygon_covers")
            out.metric(
                "min_clearance_to_envelope_m",
                min(limit.exterior.distance(Point(p)) for p in _vertices(foot)),
                "polygon_distance",
                unit="m",
            )
        if site.boundary is not None:
            out.metric(
                "parcel_coverage_pct",
                100 * foot.area / site.boundary.area_m2,
                "polygon_area_ratio",
                unit="%",
            )
        self._road(out, model, site)
        self._terrain(ctx, out, foot)
        return out.result()

    @staticmethod
    def _road(out: EvaluatorOutput, model: HouseModel, site) -> None:
        shapes = []
        for f in site.features:
            if f.kind not in (SiteFeatureKind.ROAD, SiteFeatureKind.FRONTAGE):
                continue
            g = f.geometry
            if isinstance(g, PolygonGeometry):
                shapes.append(g.polygon.to_shapely())
            elif isinstance(g, PolylineGeometry):
                shapes.append(g.line.to_shapely())
            elif isinstance(g, PointGeometry):
                shapes.append(Point(g.xy))
        if not shapes:
            out.metric("entrance_to_road_m", None, "no_road_on_record", NC)
            return
        road = unary_union(shapes)
        has_garage = any(s.function is S.GARAGE for s in model.spaces)
        for role, metric in (
            (OpeningRole.MAIN_ENTRANCE, "entrance_to_road_m"),
            (OpeningRole.VEHICLE_ENTRANCE, "garage_door_to_road_m"),
        ):
            door = next(
                (o for o in model.openings if _is_entrance(o, role) and EXTERIOR in o.connects),
                None,
            )
            if door is None:
                if role is OpeningRole.MAIN_ENTRANCE or has_garage:
                    out.metric(metric, None, f"no_{role.value}", NC)
                continue
            w = model.wall(door.host_wall_id)
            t = door.offset_m + door.width_m / 2
            d = w.length_m
            p = Point(
                w.start[0] + (w.end[0] - w.start[0]) * t / d,
                w.start[1] + (w.end[1] - w.start[1]) * t / d,
            )
            out.metric(
                metric, road.distance(p), "point_to_feature_distance", unit="m", subjects=[door.id]
            )

    @staticmethod
    def _terrain(ctx: EvaluationContext, out: EvaluatorOutput, foot) -> None:
        model, site = ctx.model, ctx.site
        assert site is not None
        from house_ai.evaluation.hillside import terrain_metrics

        terrain_metrics(ctx, out)
        surface = site_surface(site)
        z_of = lambda xy: elevation_at(surface, xy) if surface else None  # noqa: E731
        # Indoor/outdoor relationships and room-to-terrace connections (S7-20)
        terrace_spaces = [s for s in model.spaces if s.function in OUTDOOR]
        for t_space in terrace_spaces:
            t_level = model.level(t_space.level_id)
            t_doors = [d for d in model.openings if d.is_passable and t_space.id in d.connects]
            out.metric(
                METRIC_ROOM_TERRACE_DOOR_COUNT,
                len(t_doors),
                "doors_connecting_to_terrace",
                INF,
                unit="count",
                subjects=[t_space.id],
            )
            if not t_doors:
                out.violation(
                    VIOLATION_TERRACE_NO_DOOR,
                    Strength.SOFT,
                    f"Terrace {t_space.id} has no direct door connection to an interior room",
                    [t_space.id],
                    INF,
                )
            for d in t_doors:
                other_id = next(
                    (sid for sid in d.connects if sid != t_space.id and sid != EXTERIOR),
                    None,
                )
                if other_id:
                    other_sp = model.space(other_id)
                    other_level = model.level(other_sp.level_id)
                    level_delta = round(other_level.elevation_m - t_level.elevation_m, 3)
                    out.metric(
                        METRIC_ROOM_TERRACE_LEVEL_DELTA,
                        level_delta,
                        "room_terrace_elevation_difference",
                        INF,
                        unit="m",
                        subjects=[t_space.id, other_id, d.id],
                    )
                    if abs(level_delta) > 0.3:
                        out.violation(
                            VIOLATION_TERRACE_STEP_TOO_HIGH,
                            Strength.SOFT,
                            f"Step between {other_id} and terrace {t_space.id} through {d.id} "
                            f"is {level_delta:+.2f} m (> 0.30 m)",
                            [t_space.id, other_id, d.id],
                            INF,
                        )

            # Terrace ground delta
            pts = t_space.boundary.outer
            if pts:
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
                t_ground = z_of((cx, cy))
                t_delta = round(t_level.elevation_m - t_ground, 3) if t_ground is not None else None
                out.metric(
                    METRIC_TERRACE_GROUND_DELTA,
                    t_delta,
                    "tin_at_terrace_centroid",
                    INF if t_ground is not None else NC,
                    unit="m",
                    subjects=[t_space.id],
                )



def _vertices(geom) -> list[tuple[float, float]]:
    polys = getattr(geom, "geoms", [geom])
    return [c for p in polys for c in p.exterior.coords]


REQUIRED = [
    GeometryEvaluator(),
    ProgramEvaluator(),
    AdjacencyEvaluator(),
    CirculationEvaluator(),
    PrivacyEvaluator(),
    SiteEvaluator(),
]
