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
from shapely.geometry import Point

from .base import EPS_M, EXTERIOR, StrictModel
from .geometry import left_normal, unit_direction
from .model import HouseModel, Opening, Wall
from .site import Site

#: Overlap area below this is treated as touching along an edge.
OVERLAP_TOLERANCE_M2 = 1e-4
#: How far beyond a wall face we probe to find what an opening opens onto.
PROBE_BEYOND_FACE_M = 0.05


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


def check_model(model: HouseModel, site: Site | None = None) -> list[IntegrityFinding]:
    findings = _check_ids(model)
    ref_findings = _check_references(model)
    findings += ref_findings
    if ref_findings:
        # Geometry checks below assume references resolve.
        return findings
    findings += _check_overlaps(model)
    findings += _check_openings(model)
    findings += _check_fixtures(model)
    findings += _check_reachability(model)
    if site is not None:
        findings += _check_site(model, site)
    return findings


def _check_ids(model: HouseModel) -> list[IntegrityFinding]:
    ids = model.all_ids()
    seen: set[str] = set()
    dupes: list[str] = []
    for i in ids:
        if i in seen and i not in dupes:
            dupes.append(i)
        seen.add(i)
    findings = [_err("duplicate_id", f"id {i!r} is used more than once", i) for i in dupes]
    if EXTERIOR in seen:
        findings.append(_err("reserved_id", f"{EXTERIOR!r} is reserved", EXTERIOR))
    return findings


def _check_references(model: HouseModel) -> list[IntegrityFinding]:
    levels = {lv.id for lv in model.levels}
    spaces = {s.id for s in model.spaces}
    walls = {w.id for w in model.walls}
    zones = {z.id for z in model.zones}
    materials = {m.id for m in model.materials}
    out: list[IntegrityFinding] = []

    def need(owner: str, field: str, ref: str | None, valid: set[str]) -> None:
        if ref is not None and ref not in valid:
            out.append(_err("dangling_reference", f"{owner}.{field} -> unknown {ref!r}", owner))

    for s in model.spaces:
        need(s.id, "level_id", s.level_id, levels)
        need(s.id, "zone_id", s.zone_id, zones)
        need(s.id, "floor_material_id", s.floor_material_id, materials)
    for w in model.walls:
        need(w.id, "level_id", w.level_id, levels)
        need(w.id, "material_id", w.material_id, materials)
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
    for r in model.relationships:
        need(r.id, "a", r.a, spaces)
        need(r.id, "b", r.b, spaces)
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
                    _err("space_overlap", f"{a.id} and {b.id} overlap by {area:.3f} m²", a.id, b.id)
                )
    return out


def opening_sides(model: HouseModel, opening: Opening) -> tuple[str | None, str | None]:
    """What lies on each side of an opening: a space id, EXTERIOR, or None if ambiguous."""
    wall = model.wall(opening.host_wall_id)
    direction = unit_direction(wall.start, wall.end)
    normal = left_normal(direction)
    along = opening.offset_m + opening.width_m / 2
    centre = (wall.start[0] + direction[0] * along, wall.start[1] + direction[1] * along)
    reach = wall.thickness_m / 2 + PROBE_BEYOND_FACE_M
    return tuple(  # type: ignore[return-value]
        _what_is_at(
            model,
            wall,
            (centre[0] + sign * normal[0] * reach, centre[1] + sign * normal[1] * reach),
        )
        for sign in (1, -1)
    )


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


def _check_openings(model: HouseModel) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    for o in model.openings:
        wall = model.wall(o.host_wall_id)
        if o.offset_m + o.width_m > wall.length_m + EPS_M:
            out.append(
                _err(
                    "opening_outside_wall",
                    f"{o.id} runs to {o.offset_m + o.width_m:.3f} m along {wall.id}, "
                    f"which is {wall.length_m:.3f} m long",
                    o.id,
                    wall.id,
                )
            )
            continue
        if o.sill_m + o.height_m > wall.height_m + EPS_M:
            out.append(
                _err("opening_taller_than_wall", f"{o.id} top is above {wall.id}", o.id, wall.id)
            )
        sides = opening_sides(model, o)
        if None in sides:
            msg = f"{o.id} opens into overlapping spaces"
            out.append(_err("opening_side_ambiguous", msg, o.id))
        elif set(sides) != set(o.connects):
            out.append(
                _err(
                    "opening_sides_mismatch",
                    f"{o.id} claims to connect {sorted(o.connects)} but lies between "
                    f"{sorted(sides)}",  # type: ignore[type-var]
                    o.id,
                )
            )
    return out


def _check_fixtures(model: HouseModel) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    for f in model.fixtures:
        if not model.space(f.space_id).boundary.to_shapely().covers(Point(f.position)):
            out.append(_err("fixture_outside_space", f"{f.id} is not inside {f.space_id}", f.id))
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
        _err("space_unreachable", f"{s.id} cannot be reached from outside through doors", s.id)
        for s in model.spaces
        if s.id not in reached
    ]


def _check_site(model: HouseModel, site: Site) -> list[IntegrityFinding]:
    out: list[IntegrityFinding] = []
    local = site.coordinates.local
    if local is None or local.id != model.coordinate_system_id:
        out.append(
            _err(
                "coordinate_system_mismatch",
                f"model is drawn in {model.coordinate_system_id!r}, site frame is "
                f"{local.id if local else None!r}",
            )
        )
        return out
    if site.buildable_envelope is not None:
        limit, label = site.buildable_envelope.polygon.to_shapely(), "buildable envelope"
    elif site.boundary is not None:
        limit, label = site.boundary.to_shapely(), "parcel boundary"
        out.append(_warn("envelope_unknown", "no buildable envelope; checked the boundary only"))
    else:
        return [*out, _warn("envelope_unknown", "site has neither envelope nor boundary")]
    tolerant = limit.buffer(EPS_M)
    for s in model.spaces:
        if not tolerant.covers(s.boundary.to_shapely()):
            out.append(_err("outside_envelope", f"{s.id} extends outside the {label}", s.id))
    return out
