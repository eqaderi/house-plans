"""Derived finish-face geometry. Numerical tolerances are not planning thresholds."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from shapely import affinity
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.wkb import loads

from house_ai.domain.base import EXTERIOR
from house_ai.domain.geometry import left_normal, unit_direction
from house_ai.domain.model import HouseModel, Opening, OpeningKind, Operation, SlabKind, Space

from .templates import TEMPLATES

# Generated plans are solved in a rotated frame; their coordinates carry ~1e-7 m noise.
EPS = 1e-5
# Upper bound on candidate placements tried by one furniture study (ADR 0019).
FIT_BUDGET = 200_000
BUDGET_EXHAUSTED = "budget_exhausted"


def opening_segment(model: HouseModel, door: Opening) -> LineString:
    wall = model.wall(door.host_wall_id)
    u = unit_direction(wall.start, wall.end)
    return LineString(
        [
            (wall.start[0] + u[0] * t, wall.start[1] + u[1] * t)
            for t in (door.offset_m, door.offset_m + door.width_m)
        ]
    )


def _joined(model: HouseModel, wall, point) -> bool:
    return any(
        w.id != wall.id
        and w.level_id == wall.level_id
        and min(math.dist(point, w.start), math.dist(point, w.end)) < EPS
        for w in model.walls
    )


def wall_solid(model: HouseModel, wall):
    """Wall solid, extended by half its thickness where it meets another wall's end.

    The extension closes the square notch a butt-capped corner leaves on its reflex side.
    """
    u = unit_direction(wall.start, wall.end)
    half = wall.thickness_m / 2
    start, end = wall.start, wall.end
    if _joined(model, wall, wall.start):
        start = (start[0] - u[0] * half, start[1] - u[1] * half)
    if _joined(model, wall, wall.end):
        end = (end[0] + u[0] * half, end[1] + u[1] * half)
    solid = LineString([start, end]).buffer(half, cap_style=2)
    apertures = [
        opening_segment(model, o).buffer(wall.thickness_m / 2 + EPS, cap_style=2)
        for o in model.openings
        if o.host_wall_id == wall.id and o.is_passable and o.sill_m == 0
    ]
    return solid.difference(unary_union(apertures))


def net_floor(model: HouseModel, space: Space):
    solids = [wall_solid(model, w) for w in model.walls if w.level_id == space.level_id]
    floor = space.boundary.to_shapely().difference(unary_union(solids))
    slabs = [
        sl.boundary.to_shapely()
        for sl in model.slabs
        if sl.level_id == space.level_id and sl.kind in {SlabKind.FLOOR, SlabKind.TERRACE}
    ]
    return floor.intersection(unary_union(slabs)) if slabs else floor


def objects_in(model, space_id):
    return [f for f in [*model.fixtures, *model.furniture] if f.space_id == space_id]


def stair_obstacles(model: HouseModel, space_id: str):
    """Flights with a declared walking line occupy their footprint on both connected levels,
    in every space of those levels they pass through: the bottom and top spaces, and a
    stairwell, stair hall or room a split-level flight crosses into (ADR 0023).

    Without a walking line the flight geometry is unknown and is not subtracted.
    """
    level = model.space(space_id).level_id
    return [
        st.footprint.to_shapely()
        for st in model.stairs
        if st.walking_line is not None
        and (
            space_id in {st.bottom_space_id, st.top_space_id}
            or level in {st.from_level_id, st.to_level_id}
        )
    ]


def free_floor(model: HouseModel, space: Space):
    return net_floor(model, space).difference(
        unary_union(
            [f.footprint_polygon().to_shapely() for f in objects_in(model, space.id)]
            + stair_obstacles(model, space.id)
        )
    )


@dataclass
class DoorGeometry:
    swept: object
    leaves: list[LineString]
    approaches: dict[str, Polygon]


def door_geometry(model: HouseModel, door: Opening, approach_m=0.9) -> DoorGeometry | None:
    """Swing handedness viewed along wall start→end; swing goes toward opens_into.

    Arc is a conservative polygonal approximation (0.5° step, outward buffered).
    Sliding/cased openings have no swing. Unknown swing side returns None.
    """
    seg = opening_segment(model, door)
    wall = model.wall(door.host_wall_id)
    u = unit_direction(wall.start, wall.end)
    n = left_normal(u)
    a, b = list(seg.coords)
    mid = seg.interpolate(0.5, normalized=True)
    approaches = {}
    face = wall.thickness_m / 2
    for sid in door.connects:
        if sid == EXTERIOR:
            continue
        poly = model.space(sid).boundary.to_shapely()
        for sign in (1, -1):
            probe = Point(mid.x + n[0] * sign * 0.1, mid.y + n[1] * sign * 0.1)
            if poly.covers(probe):
                # Measured from the finish face, not the wall centreline.
                near, far = face * sign, (face + approach_m) * sign
                approaches[sid] = Polygon(
                    [
                        (a[0] + n[0] * near, a[1] + n[1] * near),
                        (b[0] + n[0] * near, b[1] + n[1] * near),
                        (b[0] + n[0] * far, b[1] + n[1] * far),
                        (a[0] + n[0] * far, a[1] + n[1] * far),
                    ]
                )
                break
    if door.kind == OpeningKind.DOOR and door.operation in {Operation.NONE, Operation.FIXED}:
        return None
    if door.operation in {Operation.SLIDING, Operation.NONE, Operation.FIXED}:
        return DoorGeometry(GeometryCollection(), [], approaches)
    if door.operation not in {Operation.SWING_LEFT, Operation.SWING_RIGHT, Operation.DOUBLE_SWING}:
        return None
    if door.opens_into is None:
        return None
    side = approaches.get(door.opens_into)
    if side is None and door.opens_into != EXTERIOR:
        return None
    if side is not None:
        c = side.centroid
        sign = 1 if (c.x - mid.x) * n[0] + (c.y - mid.y) * n[1] > 0 else -1
    else:
        # Exterior is the opposite of the known interior side.
        if not approaches:
            return None
        c = next(iter(approaches.values())).centroid
        sign = -1 if (c.x - mid.x) * n[0] + (c.y - mid.y) * n[1] > 0 else 1
    sectors, leaves = [], []
    hinges = [(a, u, door.width_m)]
    if door.operation == Operation.SWING_RIGHT:
        hinges = [(b, (-u[0], -u[1]), door.width_m)]
    elif door.operation == Operation.DOUBLE_SWING:
        hinges = [(a, u, door.width_m / 2), (b, (-u[0], -u[1]), door.width_m / 2)]
    for h, along, radius in hinges:
        arc = [
            (
                h[0] + radius * (along[0] * math.cos(t) + sign * n[0] * math.sin(t)),
                h[1] + radius * (along[1] * math.cos(t) + sign * n[1] * math.sin(t)),
            )
            for t in [i * math.pi / 360 for i in range(181)]
        ]
        sectors.append(Polygon([h, *arc]).buffer(radius * (1 - math.cos(math.pi / 720))))
        leaves.append(LineString([h, arc[-1]]))
    return DoorGeometry(unary_union(sectors), leaves, approaches)


def template_shapes(template, position, rotation=0, width=None, depth=None):
    w, d = width or template.width.value, depth or template.depth.value
    body = box(-w / 2, -d / 2, w / 2, d / 2)
    envelope = box(
        -w / 2 - template.left.value,
        -d / 2 - template.front.value,
        w / 2 + template.right.value,
        d / 2 + template.back.value,
    )

    def transform(poly):
        return affinity.translate(affinity.rotate(poly, rotation, origin=(0, 0)), *position)

    return transform(body), transform(envelope)


def placed_envelope(item):
    ident = getattr(item, "template_id", None) or item.fixture_type.replace("_", "-")
    aliases = {"bed-double": "bed-double", "kitchen-sink": "kitchen-run"}
    template = TEMPLATES.get(aliases.get(ident, ident))
    if template is None:
        return None
    return template_shapes(template, item.position, item.rotation_deg, item.width_m, item.depth_m)[
        1
    ]


def principal_angle(space: Space) -> float:
    """Direction (degrees, 0–90) of the space's longest boundary edge."""
    pts = list(space.boundary.outer)
    edges = list(zip(pts, pts[1:] + pts[:1], strict=True))
    a, b = max(edges, key=lambda e: math.dist(*e))
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 90


def fit_templates(model, space, templates):
    """Finite 0.1 m, four-rotation search in the room's own frame.

    Returns placed (body, envelope) polygons, None when no sampled arrangement exists,
    or BUDGET_EXHAUSTED when the search stopped before deciding. Clear zones may
    overlap each other but cannot overlap another solid body. Exhaustive continuous
    infeasibility is not claimed.
    """
    floor = free_floor(model, space)
    swings = []
    approaches = []
    for o in model.openings:
        if o.is_passable and space.id in o.connects:
            g = door_geometry(model, o)
            if g is not None:
                swings.append(g.swept)
                if space.id in g.approaches:
                    approaches.append(g.approaches[space.id])
    angle = principal_angle(space)

    def local(geom):
        return affinity.rotate(geom, -angle, origin=(0, 0))

    found = _fit_cached(
        local(floor).wkb,
        local(unary_union(swings)).wkb,
        local(unary_union(approaches)).wkb,
        # Templates with equal dimensions sit next to each other (see `_dimensions`).
        tuple(t.model_dump_json() for t in sorted(templates, key=_dimensions)),
    )
    if found is None or found == BUDGET_EXHAUSTED:
        return found
    return [
        (
            affinity.rotate(box(*body), angle, origin=(0, 0)),
            affinity.rotate(box(*env), angle, origin=(0, 0)),
        )
        for body, env in found
    ]


def _dimensions(t):
    """Placement-relevant identity: body and access margins, not IDs or sources."""
    return tuple(getattr(t, k).value for k in ("width", "depth", "left", "right", "front", "back"))


def _overlap(p, q):
    """Overlap area of two axis-aligned boxes given as bounds."""
    return max(0.0, min(p[2], q[2]) - max(p[0], q[0])) * max(0.0, min(p[3], q[3]) - max(p[1], q[1]))


@lru_cache(maxsize=256)
def _fit_cached(floor_wkb, excluded_wkb, approach_wkb, template_jsons):
    from house_ai.domain.usability import FurnitureTemplate

    floor, excluded = loads(floor_wkb), loads(excluded_wkb)
    approaches = loads(approach_wkb)
    templates = [FurnitureTemplate.model_validate_json(s) for s in template_jsons]
    if sum(t.width.value * t.depth.value for t in templates) > floor.area + EPS:
        return None
    tolerant = prep(floor.buffer(EPS))
    excluded_p, approaches_p = prep(excluded), prep(approaches)
    xmin, ymin, xmax, ymax = floor.bounds if not floor.is_empty else (0, 0, 0, 0)
    # Finish faces (not only the overall bounds, which include door recesses) anchor offsets.
    parts = getattr(floor, "geoms", [floor])
    rings = [r for g in parts if g.geom_type == "Polygon" for r in (g.exterior, *g.interiors)]
    vx = {round(x, 6) for r in rings for x, _ in r.coords}
    vy = {round(y, 6) for r in rings for _, y in r.coords}

    def offsets(lo, hi, e0, e1, faces):
        aligned = {f - e for f in faces for e in (e0, e1)}
        grid = {lo - e0 + i / 10 for i in range(int((hi - lo - e1 + e0) * 10) + 1)}
        return sorted(
            v for v in aligned | grid | {lo - e0, hi - e1} if lo - e0 - EPS <= v <= hi - e1 + EPS
        )

    def placements(t):
        """In the room frame, every rotated body and envelope is an axis-aligned box."""
        out = []
        for angle in (0, 90, 180, 270):
            _, env = template_shapes(t, (0, 0), angle)
            ex0, ey0, ex1, ey1 = env.bounds
            if ex1 - ex0 > xmax - xmin + EPS or ey1 - ey0 > ymax - ymin + EPS:
                continue
            # Bounds, face-aligned offsets and the regular 0.1 m sampling grid.
            for x in offsets(xmin, xmax, ex0, ex1, vx):
                for y in offsets(ymin, ymax, ey0, ey1, vy):
                    body, env = template_shapes(t, (x, y), angle)
                    if (
                        tolerant.contains(env)
                        and (
                            not excluded_p.intersects(env) or env.intersection(excluded).area < EPS
                        )
                        and (
                            not approaches_p.intersects(body)
                            or body.intersection(approaches).area < EPS
                        )
                    ):
                        out.append((body.bounds, env.bounds))
        return out

    keys = [_dimensions(t) for t in templates]
    by_template = {}
    candidates = [
        by_template[k] if k in by_template else by_template.setdefault(k, placements(t))
        for k, t in zip(keys, templates, strict=True)
    ]
    budget = [FIT_BUDGET]

    def search(i, chosen, first):
        if i == len(candidates):
            return chosen
        # Identical templates are interchangeable: place them in increasing candidate order.
        same = i > 0 and keys[i] == keys[i - 1]
        for k in range(first if same else 0, len(candidates[i])):
            budget[0] -= 1
            if budget[0] < 0:
                return BUDGET_EXHAUSTED
            body, env = candidates[i][k]
            if all(_overlap(body, e) < EPS and _overlap(env, b) < EPS for b, e in chosen):
                found = search(i + 1, [*chosen, (body, env)], k + 1)
                if found is not None:
                    return found
        return None

    return search(0, [], 0)
