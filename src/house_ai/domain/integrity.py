"""Deterministic integrity checks on a canonical house model.

These are not design evaluations; they decide whether a model is a coherent
building description at all: ids unique and resolvable, geometry valid,
spaces not overlapping, openings inside their host walls and actually
between the spaces they claim to connect, every space reachable, and the
footprint inside the site's buildable envelope.

Any ERROR finding blocks the plan approval gate. The checks run on the model
itself every time; no "passed" flag is ever stored and trusted.
"""

from __future__ import annotations

from collections import deque
from enum import StrEnum
from itertools import combinations

from pydantic import Field
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from .base import EPS_M, EXTERIOR, StrictModel
from .geometry import left_normal, unit_direction
from .model import HouseModel, Opening, Wall
from .program import SpaceProgram, SpaceRelationshipKind, Strength
from .records import IssueStatus, Severity
from .site import Site

#: Overlap area below this is treated as touching along an edge.
OVERLAP_TOLERANCE_M2 = 1e-4
#: How far beyond a wall face we probe to find what an opening opens onto.
PROBE_BEYOND_FACE_M = 0.05
#: Inset from opening ends when sampling along the opening span.
OPENING_END_INSET_M = 0.05

CODE_DUPLICATE_ID = "duplicate_id"
CODE_RESERVED_ID = "reserved_id"
CODE_DANGLING_REFERENCE = "dangling_reference"
CODE_SPACE_OVERLAP = "space_overlap"
CODE_UNATTACHED_WALL = "unattached_wall"
CODE_OPENING_OUTSIDE_WALL = "opening_outside_wall"
CODE_OPENING_TALLER_THAN_WALL = "opening_taller_than_wall"
CODE_OPENING_OVERLAP = "opening_overlap"
CODE_OPENING_SIDE_AMBIGUOUS = "opening_side_ambiguous"
CODE_OPENING_SIDES_MISMATCH = "opening_sides_mismatch"
CODE_FIXTURE_OUTSIDE_SPACE = "fixture_outside_space"
CODE_FIXTURE_OVERLAP = "fixture_overlap"
CODE_STAIR_LEVEL_MISMATCH = "stair_level_mismatch"
CODE_STAIR_OUTSIDE_SPACE = "stair_outside_connected_space"
CODE_SPACE_UNREACHABLE = "space_unreachable"
CODE_COORDINATE_SYSTEM_MISMATCH = "coordinate_system_mismatch"
CODE_ENVELOPE_UNKNOWN = "envelope_unknown"
CODE_OUTSIDE_ENVELOPE = "outside_envelope"
CODE_MIN_AREA_VIOLATION = "min_area_violation"
CODE_HARD_ADJACENCY_VIOLATION = "hard_adjacency_violation"


class FindingSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class IntegrityFinding(StrictModel):
    code: str
    severity: FindingSeverity
    message: str
    subject_ids: list[str] = Field(default_factory=list)


def errors(findings: list[IntegrityFinding]) -> list[IntegrityFinding]:
    return [f for f in findings if f.severity is FindingSeverity.ERROR]


def _err(code: str, message: str, *ids: str) -> IntegrityFinding:
    return IntegrityFinding(
        code=code, severity=FindingSeverity.ERROR, message=message, subject_ids=list(ids)
    )


def _warn(code: str, message: str, *ids: str) -> IntegrityFinding:
    return IntegrityFinding(
        code=code, severity=FindingSeverity.WARNING, message=message, subject_ids=list(ids)
    )


def check_model(
    model: HouseModel,
    site: Site | None = None,
    program: SpaceProgram | None = None,
) -> list[IntegrityFinding]:
    findings = _check_ids(model)
    findings += [
        _err("blocking_plan_issue", issue.title, issue.id, *issue.subject_ids)
        for issue in model.issues
        if issue.severity is Severity.BLOCKING and issue.status is IssueStatus.OPEN
    ]
    ref_findings = _check_references(model, program)
    findings += ref_findings
    if ref_findings:
        # Geometry checks below assume references resolve.
        return findings
    findings += _check_overlaps(model)
    findings += _check_earthwork_pads(model, site)
    findings += _check_walls(model)
    findings += _check_openings(model)
    findings += _check_fixtures(model)
    findings += _check_stairs(model)
    findings += _check_reachability(model)
    if site is not None:
        findings += _check_site(model, site)
    if program is not None:
        findings += _check_program(model, program)
    return findings


def _check_earthwork_pads(model: HouseModel, site: Site | None) -> list[IntegrityFinding]:
    findings = []
    for a, b in combinations(model.earthwork_pads, 2):
        if a.boundary.to_shapely().intersection(b.boundary.to_shapely()).area > 1e-8:
            findings.append(
                _err("earthwork_pad_overlap", "Proposed earthwork pads overlap", a.id, b.id)
            )
    for pad in model.earthwork_pads:
        polygon = pad.boundary.to_shapely()
        if site and site.boundary and not site.boundary.to_shapely().buffer(EPS_M).covers(polygon):
            findings.append(
                _err("earthwork_pad_outside_site", "Proposed pad outside parcel", pad.id)
            )
        for space in model.spaces:
            if (
                polygon.intersection(space.boundary.to_shapely()).area > 1e-8
                and pad.elevation_m > model.level(space.level_id).elevation_m + EPS_M
            ):
                findings.append(
                    _err(
                        "earthwork_pad_above_floor",
                        "Proposed formation pad above a floor",
                        pad.id,
                        space.id,
                    )
                )
    return findings


def _check_ids(model: HouseModel) -> list[IntegrityFinding]:
    ids = model.all_ids()
    seen: set[str] = set()
    dupes: list[str] = []
    for i in ids:
        if i in seen and i not in dupes:
            dupes.append(i)
        seen.add(i)
    findings = [_err(CODE_DUPLICATE_ID, f"id {i!r} is used more than once", i) for i in dupes]
    if EXTERIOR in seen:
        findings.append(_err(CODE_RESERVED_ID, f"{EXTERIOR!r} is reserved", EXTERIOR))
    return findings


def _check_references(
    model: HouseModel, program: SpaceProgram | None = None
) -> list[IntegrityFinding]:
    levels = {lv.id for lv in model.levels}
    spaces = {s.id for s in model.spaces}
    walls = {w.id for w in model.walls}
    zones = {z.id for z in model.zones}
    materials = {m.id for m in model.materials}
    all_entities = set(model.all_ids())
    program_items = {i.id for i in program.space_requirements} if program is not None else None
    program_adjs = {a.id for a in program.space_relationships} if program is not None else None
    out: list[IntegrityFinding] = []

    def need(owner: str, field: str, ref: str | None, valid: set[str]) -> None:
        if ref is not None and ref not in valid:
            out.append(_err(CODE_DANGLING_REFERENCE, f"{owner}.{field} -> unknown {ref!r}", owner))

    for s in model.spaces:
        need(s.id, "level_id", s.level_id, levels)
        need(s.id, "zone_id", s.zone_id, zones)
        need(s.id, "floor_material_id", s.floor_material_id, materials)
        if program_items is not None:
            need(s.id, "program_item_id", s.program_item_id, program_items)
    for group in model.composite_spaces:
        need(group.id, "level_id", group.level_id, levels)
        for sid in group.space_ids:
            need(group.id, "space_ids", sid, spaces)
        if set(group.space_ids) <= spaces:
            children = [model.space(sid) for sid in group.space_ids]
            union = unary_union([sp.boundary.to_shapely() for sp in children])
            if (
                any(sp.level_id != group.level_id for sp in children)
                or union.geom_type != "Polygon"
                or union.symmetric_difference(group.boundary.to_shapely()).area > 1e-4
            ):
                out.append(
                    _err(
                        "invalid_composite_space",
                        "Composite boundary/levels do not match its zones",
                        group.id,
                    )
                )
    for w in model.walls:
        need(w.id, "level_id", w.level_id, levels)
        need(w.id, "material_id", w.material_id, materials)
        need(w.id, "left_material_id", w.left_material_id, materials)
        need(w.id, "right_material_id", w.right_material_id, materials)
    for o in model.openings:
        need(o.id, "host_wall_id", o.host_wall_id, walls)
        need(o.id, "material_id", o.material_id, materials)
        for end in o.connects:
            need(o.id, "connects", end, spaces | {EXTERIOR})
    for sl in model.slabs:
        need(sl.id, "level_id", sl.level_id, levels)
        need(sl.id, "material_id", sl.material_id, materials)
    for c in model.ceilings:
        need(c.id, "space_id", c.space_id, spaces)
        need(c.id, "material_id", c.material_id, materials)
    for st in model.stairs:
        need(st.id, "from_level_id", st.from_level_id, levels)
        need(st.id, "to_level_id", st.to_level_id, levels)
        need(st.id, "bottom_space_id", st.bottom_space_id, spaces)
        need(st.id, "top_space_id", st.top_space_id, spaces)
    for z in model.zones:
        for sid in z.space_ids:
            need(z.id, "space_ids", sid, spaces)
    for f in model.fixtures:
        need(f.id, "space_id", f.space_id, spaces)
        need(f.id, "material_id", f.material_id, materials)
    for f in model.furniture:
        need(f.id, "space_id", f.space_id, spaces)
    for zone in model.clearance_zones:
        need(zone.id, "space_id", zone.space_id, spaces)
        clearable = {
            e.id
            for group in (model.furniture, model.fixtures, model.openings, model.stairs)
            for e in group
        }
        need(zone.id, "element_id", zone.element_id, clearable)
    for r in model.relationships:
        need(r.id, "a", r.a, spaces)
        need(r.id, "b", r.b, spaces)
        if program_adjs is not None:
            need(r.id, "requirement_id", r.requirement_id, program_adjs)
    for iss in model.issues:
        for subj in iss.subject_ids:
            need(iss.id, "subject_ids", subj, all_entities)
    for assump in model.assumptions:
        for target in assump.affects:
            need(assump.id, "affects", target, all_entities)
    return out


def _check_overlaps(model: HouseModel) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    for level in model.levels:
        on_level = [s for s in model.spaces if s.level_id == level.id]
        shapes = {s.id: s.boundary.to_shapely() for s in on_level}
        for a, b in combinations(on_level, 2):
            area = shapes[a.id].intersection(shapes[b.id]).area
            if area > OVERLAP_TOLERANCE_M2:
                out.append(
                    _err(
                        CODE_SPACE_OVERLAP,
                        f"{a.id} and {b.id} overlap by {area:.3f} m²",
                        a.id,
                        b.id,
                    )
                )
    return out


def _check_walls(model: HouseModel) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    for level in model.levels:
        spaces_on_level = [s.boundary.to_shapely() for s in model.spaces if s.level_id == level.id]
        if not spaces_on_level:
            continue
        footprint = unary_union(spaces_on_level)
        for w in model.walls:
            if w.level_id != level.id:
                continue
            seg = LineString([w.start, w.end])
            if footprint.buffer(w.thickness_m + EPS_M).distance(seg) > EPS_M:
                out.append(
                    _err(
                        CODE_UNATTACHED_WALL,
                        f"{w.id} is not attached to any space on level {level.id}",
                        w.id,
                    )
                )
    return out


def _probe_sides_at(model: HouseModel, wall: Wall, along: float) -> tuple[str | None, str | None]:
    direction = unit_direction(wall.start, wall.end)
    normal = left_normal(direction)
    pt = (wall.start[0] + direction[0] * along, wall.start[1] + direction[1] * along)
    reach = wall.thickness_m / 2 + PROBE_BEYOND_FACE_M
    return tuple(  # type: ignore[return-value]
        _what_is_at(
            model,
            wall,
            (pt[0] + sign * normal[0] * reach, pt[1] + sign * normal[1] * reach),
        )
        for sign in (1, -1)
    )


def opening_sides(model: HouseModel, opening: Opening) -> tuple[str | None, str | None]:
    """What lies on each side of an opening: a space id, EXTERIOR, or None if ambiguous.

    Samples near both ends and at the midpoint of the opening so an opening
    that straddles a perpendicular partition wall cannot pass as connecting a
    single pair of spaces.
    """
    wall = model.wall(opening.host_wall_id)
    inset = min(OPENING_END_INSET_M, opening.width_m * 0.1)
    sample_offsets = (
        opening.offset_m + inset,
        opening.offset_m + opening.width_m / 2,
        opening.offset_m + opening.width_m - inset,
    )
    samples = [_probe_sides_at(model, wall, along) for along in sample_offsets]
    first = samples[0]
    if None in first or any(s != first for s in samples[1:]):
        return (None, None)
    return first


def _what_is_at(model: HouseModel, wall: Wall, xy: tuple[float, float]) -> str | None:
    point = Point(xy)
    hits = [
        s.id
        for s in model.spaces
        if s.level_id == wall.level_id and s.boundary.to_shapely().contains(point)
    ]
    if not hits:
        return EXTERIOR
    return hits[0] if len(hits) == 1 else None


def _intervals_overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return min(a1, b1) - max(a0, b0) > EPS_M


def _check_openings(model: HouseModel) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    by_wall: dict[str, list[Opening]] = {}
    for o in model.openings:
        by_wall.setdefault(o.host_wall_id, []).append(o)
        wall = model.wall(o.host_wall_id)
        if o.offset_m + o.width_m > wall.length_m + EPS_M:
            out.append(
                _err(
                    CODE_OPENING_OUTSIDE_WALL,
                    f"{o.id} runs to {o.offset_m + o.width_m:.3f} m along {wall.id}, "
                    f"which is {wall.length_m:.3f} m long",
                    o.id,
                    wall.id,
                )
            )
            continue
        if o.sill_m + o.height_m > wall.height_m + EPS_M:
            out.append(
                _err(
                    CODE_OPENING_TALLER_THAN_WALL,
                    f"{o.id} top is above {wall.id}",
                    o.id,
                    wall.id,
                )
            )
        mid_sides = _probe_sides_at(model, wall, o.offset_m + o.width_m / 2)
        sides = opening_sides(model, o)
        if None in mid_sides:
            msg = f"{o.id} opens into overlapping spaces"
            out.append(_err(CODE_OPENING_SIDE_AMBIGUOUS, msg, o.id))
        elif None in sides or set(sides) != set(o.connects):
            actual = (
                sorted(sides)  # type: ignore[type-var]
                if None not in sides
                else "multiple spaces across opening span"
            )
            out.append(
                _err(
                    CODE_OPENING_SIDES_MISMATCH,
                    f"{o.id} claims to connect {sorted(o.connects)} but lies between {actual}",
                    o.id,
                )
            )
    for wall_id, wall_openings in by_wall.items():
        for a, b in combinations(wall_openings, 2):
            horiz = _intervals_overlap(
                a.offset_m, a.offset_m + a.width_m, b.offset_m, b.offset_m + b.width_m
            )
            vert = _intervals_overlap(
                a.sill_m, a.sill_m + a.height_m, b.sill_m, b.sill_m + b.height_m
            )
            if horiz and vert:
                out.append(
                    _err(
                        CODE_OPENING_OVERLAP,
                        f"{a.id} and {b.id} overlap on wall {wall_id}",
                        a.id,
                        b.id,
                        wall_id,
                    )
                )
    return out


def _check_fixtures(model: HouseModel) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    by_space: dict[str, list[tuple[str, object]]] = {}
    for f in [*model.fixtures, *model.furniture]:
        space_poly = model.space(f.space_id).boundary.to_shapely().buffer(EPS_M)
        fx_poly = f.footprint_polygon().to_shapely()
        if not space_poly.covers(fx_poly):
            out.append(
                _err(
                    CODE_FIXTURE_OUTSIDE_SPACE,
                    f"{f.id} footprint is not inside {f.space_id}",
                    f.id,
                )
            )
        by_space.setdefault(f.space_id, []).append((f.id, fx_poly))
    for _space_id, items in by_space.items():
        for (id_a, poly_a), (id_b, poly_b) in combinations(items, 2):
            if poly_a.intersection(poly_b).area > OVERLAP_TOLERANCE_M2:  # type: ignore[attr-defined]
                out.append(
                    _err(
                        CODE_FIXTURE_OVERLAP,
                        f"fixtures {id_a} and {id_b} overlap",
                        id_a,
                        id_b,
                    )
                )
    return out


def _check_stairs(model: HouseModel) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    for st in model.stairs:
        bottom = model.space(st.bottom_space_id)
        top = model.space(st.top_space_id)
        if bottom.level_id != st.from_level_id:
            out.append(
                _err(
                    CODE_STAIR_LEVEL_MISMATCH,
                    f"{st.id} bottom space {bottom.id} is on {bottom.level_id}, "
                    f"not from_level_id {st.from_level_id}",
                    st.id,
                    bottom.id,
                )
            )
        if top.level_id != st.to_level_id:
            out.append(
                _err(
                    CODE_STAIR_LEVEL_MISMATCH,
                    f"{st.id} top space {top.id} is on {top.level_id}, "
                    f"not to_level_id {st.to_level_id}",
                    st.id,
                    top.id,
                )
            )
        fp = st.footprint.to_shapely()
        if fp.intersection(bottom.boundary.to_shapely()).area <= OVERLAP_TOLERANCE_M2:
            out.append(
                _err(
                    CODE_STAIR_OUTSIDE_SPACE,
                    f"{st.id} footprint does not intersect bottom space {bottom.id}",
                    st.id,
                    bottom.id,
                )
            )
        if fp.intersection(top.boundary.to_shapely()).area <= OVERLAP_TOLERANCE_M2:
            out.append(
                _err(
                    CODE_STAIR_OUTSIDE_SPACE,
                    f"{st.id} footprint does not intersect top space {top.id}",
                    st.id,
                    top.id,
                )
            )
    return out


def circulation_graph(model: HouseModel) -> dict[str, set[str]]:
    """Undirected graph of spaces (and EXTERIOR) joined by passable openings and stairs."""
    graph: dict[str, set[str]] = {s.id: set() for s in model.spaces}
    graph[EXTERIOR] = set()
    for o in model.openings:
        if o.is_passable:
            a, b = o.connects
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set()).add(a)
    for st in model.stairs:
        graph[st.bottom_space_id].add(st.top_space_id)
        graph[st.top_space_id].add(st.bottom_space_id)
    return graph


def reachable_from(graph: dict[str, set[str]], origin: str) -> set[str]:
    seen = {origin}
    queue = deque([origin])
    while queue:
        for nxt in graph.get(queue.popleft(), ()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _check_reachability(model: HouseModel) -> list[IntegrityFinding]:
    graph = circulation_graph(model)
    reached = reachable_from(graph, EXTERIOR)
    return [
        _err(
            CODE_SPACE_UNREACHABLE,
            f"{s.id} cannot be reached from outside through doors",
            s.id,
        )
        for s in model.spaces
        if s.id not in reached
    ]


def _check_site(model: HouseModel, site: Site) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    local = site.coordinates.local
    if local is None or local.id != model.coordinate_system_id:
        out.append(
            _err(
                CODE_COORDINATE_SYSTEM_MISMATCH,
                f"model is drawn in {model.coordinate_system_id!r}, site frame is "
                f"{local.id if local else None!r}",
            )
        )
        return out
    if site.buildable_envelope is not None:
        limit, label = site.buildable_envelope.polygon.to_shapely(), "buildable envelope"
    elif site.boundary is not None:
        limit, label = site.boundary.to_shapely(), "parcel boundary"
        out.append(_warn(CODE_ENVELOPE_UNKNOWN, "no buildable envelope; checked the boundary only"))
    else:
        return [*out, _warn(CODE_ENVELOPE_UNKNOWN, "site has neither envelope nor boundary")]
    tolerant = limit.buffer(EPS_M)
    for s in model.spaces:
        if not tolerant.covers(s.boundary.to_shapely()):
            out.append(_err(CODE_OUTSIDE_ENVELOPE, f"{s.id} extends outside the {label}", s.id))
    return out


def _check_program(model: HouseModel, program: SpaceProgram) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    items_by_id = {i.id: i for i in program.space_requirements}
    spaces_by_item: dict[str, list[str]] = {i.id: [] for i in program.space_requirements}
    for s in model.spaces:
        if s.program_item_id and s.program_item_id in items_by_id:
            spaces_by_item[s.program_item_id].append(s.id)
            item = items_by_id[s.program_item_id]
            if item.min_area_m2 is not None and s.area_m2 + EPS_M < item.min_area_m2:
                out.append(
                    _err(
                        CODE_MIN_AREA_VIOLATION,
                        f"{s.id} area {s.area_m2:.2f} m² is below program minimum "
                        f"{item.min_area_m2:.2f} m² for {item.id}",
                        s.id,
                    )
                )
    graph = circulation_graph(model)
    for adj in program.space_relationships:
        if adj.strength is Strength.HARD and adj.kind is SpaceRelationshipKind.CONNECTED:
            a_spaces = [EXTERIOR] if adj.a == EXTERIOR else spaces_by_item.get(adj.a, [])
            b_spaces = [EXTERIOR] if adj.b == EXTERIOR else spaces_by_item.get(adj.b, [])
            connected = any(b in graph.get(a, set()) for a in a_spaces for b in b_spaces)
            if not connected:
                out.append(
                    _err(
                        CODE_HARD_ADJACENCY_VIOLATION,
                        f"hard connected adjacency {adj.id} ({adj.a} <-> {adj.b}) is not satisfied",
                        adj.id,
                    )
                )
    return out
