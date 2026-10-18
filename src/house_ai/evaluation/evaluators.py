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
from collections.abc import Callable

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from house_ai.constants.evaluations import (
    METRIC_EXCAVATION_VOLUME,
    METRIC_EXTERIOR_DOOR_GROUND_DELTA,
    METRIC_FILL_VOLUME,
    METRIC_MAX_CUT,
    METRIC_MAX_FILL,
    VIOLATION_ELEVATED_FLOOR_SUPPORT,
    VIOLATION_ELONGATED_ROOM,
    VIOLATION_EXTERIOR_ACCESS_LEVEL,
    VIOLATION_REQUIRED_DAYLIGHT_NO_WINDOW,
    VIOLATION_TERRAIN_COVERAGE_INCOMPLETE,
)
from house_ai.domain.base import EXTERIOR
from house_ai.domain.constraints import MinAreaRule, MinDimensionRule
from house_ai.domain.epistemics import ClaimStatus, Epistemic
from house_ai.domain.evaluation import EvaluatorRun, EvaluatorRunStatus, MetricClaim, Violation
from house_ai.domain.integrity import FindingSeverity, check_model, circulation_graph
from house_ai.domain.model import HouseModel, OpeningKind, Space, WallKind
from house_ai.domain.program import (
    AdjacencyKind,
    DaylightNeed,
    Privacy,
    SpaceFunction,
    Strength,
)
from house_ai.domain.site import PointGeometry, PolygonGeometry, PolylineGeometry, SiteFeatureKind
from house_ai.domain.terrain import elevation_at, site_surface

from .base import EvaluationContext, EvaluatorResult

VERSION = "0.1.0"
M, INF, NC = ClaimStatus.MEASURED, ClaimStatus.INFERRED, ClaimStatus.NOT_CHECKED
S = SpaceFunction
CIRCULATION = {S.CORRIDOR, S.HALL, S.ENTRY, S.STAIR, S.LIFT}
OUTDOOR = {S.TERRACE, S.BALCONY}
#: Grid spacing for terrain sampling under footprints, metres.
TERRAIN_GRID_M = 0.5
#: Shared boundary at least this long counts as sharing a wall.
SHARED_WALL_M = 0.9


class _Out:
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


def _privacy(model: HouseModel) -> dict[str, Privacy]:
    by_zone = {z.id: z.privacy for z in model.zones}
    return {s.id: by_zone[s.zone_id] for s in model.spaces if s.zone_id in by_zone}


def _hops(graph: dict[str, set[str]], origin: str) -> dict[str, int]:
    dist, queue = {origin: 0}, deque([origin])
    while queue:
        n = queue.popleft()
        for m in sorted(graph.get(n, ())):
            if m not in dist:
                dist[m] = dist[n] + 1
                queue.append(m)
    return dist


def _shared_length(model: HouseModel, a: str, b: str) -> float:
    sa, sb = model.space(a), model.space(b)
    if sa.level_id != sb.level_id:
        return 0.0
    inter = sa.boundary.to_shapely().boundary.intersection(sb.boundary.to_shapely().boundary)
    return float(inter.length)


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
        out, model = _Out(self.name), ctx.model
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

    def _dimensions(self, ctx: EvaluationContext, out: _Out) -> None:
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
        out, model, program = _Out(self.name), ctx.model, ctx.program
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
        for item in program.items:
            spaces = [model.space(s) for s in _spaces_for(model, item.id)]
            if (
                item.function in OUTDOOR
                or item.level_preference in ("outdoor", "roof")
                or (item.function is S.OTHER and item.target_area_m2 is None)
            ):
                out.metric(
                    "outdoor_item_placed", None, "not_placed_by_generator", NC, subjects=[item.id]
                )
                continue
            want = 1 if item.function in (S.STAIR, S.LIFT) else item.quantity
            if item.function in (S.HALL, S.CORRIDOR) and not spaces:
                want = 1
            if len(spaces) < want:
                strength = Strength.HARD if item.priority.value == "must" else Strength.SOFT
                note = ""
                if item.function in (S.STAIR, S.LIFT) and len(model.levels) == 1:
                    # Vertical circulation serves levels; a one-level concept has none to serve.
                    strength, note = Strength.SOFT, "; not needed in a one-level concept"
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
                ok = _level_ok(
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
        if program.levels is not None and program.levels != len(model.levels):
            out.violation(
                "level_count_differs",
                Strength.SOFT,
                f"the program asks for {program.levels} storey(s); this concept has "
                f"{len(model.levels)} floor level(s)",
                [],
            )
        return out.result()


def _level_ok(pref: str | None, z: float, entry: float | None, n_levels: int) -> bool | None:
    if entry is None or pref in (None, "any"):
        return None
    if pref in ("entry", "ground"):
        return abs(z - entry) < 1e-6
    if pref == "not_entry":
        return n_levels == 1 or abs(z - entry) > 1e-6
    if pref == "upper":
        return z > entry + 1e-6
    if pref == "lower":
        return z < entry - 1e-6
    return None


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
        out, model, program = _Out(self.name), ctx.model, ctx.program
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
            for i in program.items
            if i.function in OUTDOOR or i.level_preference in ("outdoor", "roof")
        }
        for adj in program.adjacencies:
            if outdoor & {adj.a, adj.b}:
                out.metric(
                    "adjacency_satisfied", None, "outdoor_item_not_placed", NC, subjects=[adj.id]
                )
                continue

            def ends(item_id: str) -> list[str]:
                if item_id == EXTERIOR:
                    return [EXTERIOR]
                return _spaces_for(model, item_id)

            a_s, b_s = ends(adj.a), ends(adj.b)
            ok = self._satisfied(adj.kind, model, graph, a_s, b_s)
            subjects = [adj.id, *a_s, *b_s]
            if ok is None:
                out.metric("adjacency_satisfied", None, "not_evaluated", NC, subjects=subjects)
                continue
            method = (
                "graph_analysis"
                if adj.kind in (AdjacencyKind.CONNECTED, AdjacencyKind.NEAR)
                else "shared_boundary"
            )
            out.metric("adjacency_satisfied", ok, method, subjects=subjects)
            if adj.strength is Strength.HARD:
                hard_n += 1
                hard_ok += ok
                # Hard connections are already reported by the GeometryEvaluator (check_model).
                if not ok and adj.kind is not AdjacencyKind.CONNECTED:
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

    @staticmethod
    def _satisfied(kind, model, graph, a_s, b_s) -> bool | None:
        if not a_s or not b_s:
            return False
        K = AdjacencyKind
        if kind is K.CONNECTED:
            return any(b in graph.get(a, set()) for a in a_s for b in b_s)
        if kind is K.VISUAL:
            return None
        pairs = [(a, b) for a in a_s for b in b_s if EXTERIOR not in (a, b)]
        if kind is K.ADJACENT:
            return any(_shared_length(model, a, b) >= SHARED_WALL_M for a, b in pairs)
        if kind is K.NEAR:
            return any(_hops(graph, a).get(b, 99) <= 2 for a in a_s for b in b_s)
        if kind is K.SEPARATED:
            return not any(
                b in graph.get(a, set()) or _shared_length(model, a, b) > 0.1 for a, b in pairs
            )
        if kind is K.ACOUSTIC_SEPARATION:
            return not any(_shared_length(model, a, b) > 0.1 for a, b in pairs)
        return None


# ------------------------------------------------------------------ circulation


def _pedestrian_entrances(model: HouseModel) -> tuple[set[str], str]:
    """Identify route origins without treating vehicle access as a front door."""
    candidates = [
        o
        for o in model.openings
        if o.is_passable
        and EXTERIOR in o.connects
        and model.space(next(s for s in o.connects if s != EXTERIOR)).function is not S.GARAGE
    ]
    front = [o for o in candidates if o.id.startswith("d-front")]
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
        out, model = _Out(self.name), ctx.model
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

        network = RouteNetwork(model)
        walk = network.entrance_distances()
        out.metric(
            "max_walk_from_entrance_m",
            max(walk.values()) if walk else None,
            "net_floor_visibility_graph_point_path",
            M if walk and len(walk) == len(model.spaces) else NC,
            unit="m",
        )
        if len(walk) < len(model.spaces):
            out.metric("entrance_route_coverage", len(walk), "measurable_space_routes")
        privacy = _privacy(model)
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
        out, model = _Out(self.name), ctx.model
        privacy = _privacy(model)
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
        out.metric(
            "entrance_sightline_private_spaces",
            self._sightline(model, privacy),
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
    def _sightline(model: HouseModel, privacy: dict[str, Privacy]) -> int:
        fronts = [
            o
            for o in model.openings
            if o.kind is OpeningKind.DOOR and EXTERIOR in o.connects and o.id.startswith("d-front")
        ]
        if not fronts:
            return 0
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
        out, model, site = _Out(self.name), ctx.model, ctx.site
        if site is None:
            return EvaluatorResult(
                run=EvaluatorRun(
                    name=self.name,
                    version=VERSION,
                    status=EvaluatorRunStatus.NOT_RUN,
                    reason="no site",
                )
            )
        if ctx.site_verified is not None:
            out.metric("site_verified", ctx.site_verified, "workflow_site_gate")
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
    def _road(out: _Out, model: HouseModel, site) -> None:
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
        for prefix, metric in (
            ("d-front", "entrance_to_road_m"),
            ("d-garage", "garage_door_to_road_m"),
        ):
            door = next(
                (o for o in model.openings if o.id.startswith(prefix) and EXTERIOR in o.connects),
                None,
            )
            if door is None:
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
    def _terrain(ctx: EvaluationContext, out: _Out, foot) -> None:
        model, site = ctx.model, ctx.site
        assert site is not None
        surface = site_surface(site)
        tin = "tin_interpolation_0.5m_grid"
        if surface is None:
            for name in (
                "excavation_volume_m3",
                "fill_volume_m3",
                "max_cut_m",
                "max_fill_m",
                "retaining_wall_face_area_m2",
            ):
                out.metric(name, None, "terrain_unknown", NC)
            return
        z_of: Callable = lambda xy: elevation_at(surface, xy)  # noqa: E731
        cut_v = fill_v = 0.0
        max_cut = max_fill = 0.0
        known = total = 0
        ground_seen: list[float] = []
        cell = TERRAIN_GRID_M**2
        levels = sorted(model.levels, key=lambda lv: lv.elevation_m)
        # The lowest floor at each grid point decides how deep the house reaches into the ground.
        shapes = {
            lv.id: unary_union(
                [s.boundary.to_shapely() for s in model.spaces if s.level_id == lv.id]
            )
            for lv in levels
        }
        minx, miny, maxx, maxy = foot.bounds
        y = miny + TERRAIN_GRID_M / 2
        while y < maxy:
            x = minx + TERRAIN_GRID_M / 2
            while x < maxx:
                pt = Point(x, y)
                floor = next((lv.elevation_m for lv in levels if shapes[lv.id].contains(pt)), None)
                if floor is not None:
                    total += 1
                    g = z_of((x, y))
                    if g is not None:
                        known += 1
                        ground_seen.append(g)
                        cut, fill = max(0.0, g - floor), max(0.0, floor - g)
                        cut_v += cut * cell
                        fill_v += fill * cell
                        max_cut, max_fill = max(max_cut, cut), max(max_fill, fill)
                x += TERRAIN_GRID_M
            y += TERRAIN_GRID_M
        cov = 100.0 * known / total if total else 0.0
        out.metric("terrain_coverage_pct", cov, "tin_hull_sampling", unit="%")
        status = INF if known else NC
        out.metric(METRIC_EXCAVATION_VOLUME, cut_v, tin, status, unit="m3")
        out.metric(METRIC_FILL_VOLUME, fill_v, tin, status, unit="m3")
        out.metric(METRIC_MAX_CUT, max_cut, tin, status, unit="m")
        out.metric(METRIC_MAX_FILL, max_fill, tin, status, unit="m")
        if known < total:
            out.violation(
                VIOLATION_TERRAIN_COVERAGE_INCOMPLETE,
                Strength.SOFT,
                f"Survey TIN covers {cov:.1f}% of floor samples; cut/void quantities cover "
                "only known samples and cannot represent the whole building",
                [],
                INF,
            )
        if known and max_fill > 0.6:
            out.violation(
                VIOLATION_ELEVATED_FLOOR_SUPPORT,
                Strength.SOFT,
                f"About {fill_v:.1f} m³ lies between terrain and the lowest floors, up to "
                f"{max_fill:.2f} m high. This is underfloor void, not specified engineered "
                "fill; supports, lateral stability, foundations and drainage are unresolved. "
                "Compare embedded, walk-out and stepped alternatives without assuming "
                "that less excavation is preferable",
                [],
                INF,
            )
        # Door distance to a road alone does not establish usable outdoor access.
        for door in model.openings:
            if door.kind is not OpeningKind.DOOR or EXTERIOR not in door.connects:
                continue
            wall = model.wall(door.host_wall_id)
            t = (door.offset_m + door.width_m / 2) / wall.length_m
            xy = (
                wall.start[0] + t * (wall.end[0] - wall.start[0]),
                wall.start[1] + t * (wall.end[1] - wall.start[1]),
            )
            ground = z_of(xy)
            delta = model.level(wall.level_id).elevation_m - ground if ground is not None else None
            out.metric(
                METRIC_EXTERIOR_DOOR_GROUND_DELTA,
                delta,
                "tin_at_door_midpoint",
                INF if ground is not None else NC,
                unit="m",
                subjects=[door.id],
            )
            if delta is not None and abs(delta) > 0.3:
                out.violation(
                    VIOLATION_EXTERIOR_ACCESS_LEVEL,
                    Strength.SOFT,
                    f"{door.id} floor differs from existing ground by {delta:+.2f} m; "
                    "an approach, ramp, steps or excavated terrace has not been designed "
                    "(0.3 m is a conceptual review trigger, not an accessibility rule)",
                    [door.id],
                    INF,
                )
        if ground_seen:
            span = max(math.dist(a, b) for a in _vertices(foot) for b in _vertices(foot))
            out.metric(
                "ground_relief_under_footprint_m",
                max(ground_seen) - min(ground_seen),
                tin,
                INF,
                unit="m",
            )
            out.metric(
                "footprint_slope_pct",
                100 * (max(ground_seen) - min(ground_seen)) / span,
                tin,
                INF,
                unit="%",
            )
            top = max(lv.elevation_m + (lv.floor_to_floor_m or 3.0) for lv in model.levels)
            height = top - min(ground_seen)
            out.metric("height_above_lowest_ground_m", height, tin, INF, unit="m")
            env = site.buildable_envelope
            if env is not None and env.max_height_m is not None and height > env.max_height_m:
                hard = env.status is Epistemic.VERIFIED_FACT
                out.violation(
                    "height_limit_exceeded",
                    Strength.HARD if hard else Strength.SOFT,
                    f"about {height:.1f} m above the lowest ground under the house; the "
                    f"envelope allows {env.max_height_m:g} m ({env.status.value})",
                    [],
                    INF,
                )
        retained_area = 0.0
        retaining = [w for w in model.walls if w.kind is WallKind.RETAINING]
        for w in retaining:
            z = model.level(w.level_id).elevation_m
            n = max(2, int(w.length_m / 0.5))
            d = w.length_m
            nx, ny = -(w.end[1] - w.start[1]) / d, (w.end[0] - w.start[0]) / d
            hs = []
            for i in range(n):
                t = (i + 0.5) / n
                px = w.start[0] + (w.end[0] - w.start[0]) * t
                py = w.start[1] + (w.end[1] - w.start[1]) * t
                for sgn in (1, -1):
                    g = z_of((px + sgn * nx * 0.6, py + sgn * ny * 0.6))
                    if g is not None and g > z:
                        hs.append(g - z)
                        break
            if hs:
                retained_area += w.length_m * sum(hs) / len(hs)
        out.metric(
            "retaining_wall_length_m",
            sum(w.length_m for w in retaining),
            "wall_kind_sum",
            unit="m",
            subjects=[w.id for w in retaining],
        )
        out.metric("retaining_wall_face_area_m2", retained_area, tin, INF, unit="m2")
        steps = sorted({lv.elevation_m for lv in model.levels})
        out.metric("level_elevations_m", ", ".join(f"{z:.2f}" for z in steps), "level_lookup")


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
