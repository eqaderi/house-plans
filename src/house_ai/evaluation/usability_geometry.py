"""Derived finish-face geometry. Numerical tolerances are not planning thresholds."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from shapely import affinity
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.wkb import loads

from house_ai.domain.base import EXTERIOR
from house_ai.domain.geometry import left_normal, unit_direction
from house_ai.domain.model import HouseModel, Opening, OpeningKind, Operation, SlabKind, Space

from .templates import TEMPLATES

EPS = 1e-7


def opening_segment(model: HouseModel, door: Opening) -> LineString:
    wall = model.wall(door.host_wall_id)
    u = unit_direction(wall.start, wall.end)
    return LineString(
        [
            (wall.start[0] + u[0] * t, wall.start[1] + u[1] * t)
            for t in (door.offset_m, door.offset_m + door.width_m)
        ]
    )


def wall_solid(model: HouseModel, wall):
    solid = LineString([wall.start, wall.end]).buffer(wall.thickness_m / 2, cap_style=2)
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
        if sl.level_id == space.level_id
        and sl.kind in {SlabKind.FLOOR, SlabKind.TERRACE}
        and abs(sl.top_offset_m) < EPS
    ]
    return floor.intersection(unary_union(slabs)) if slabs else floor


def objects_in(model, space_id):
    return [f for f in [*model.fixtures, *model.furniture] if f.space_id == space_id]


def free_floor(model: HouseModel, space: Space):
    return net_floor(model, space).difference(
        unary_union([f.footprint_polygon().to_shapely() for f in objects_in(model, space.id)])
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
    for sid in door.connects:
        if sid == EXTERIOR:
            continue
        poly = model.space(sid).boundary.to_shapely()
        for sign in (1, -1):
            probe = Point(mid.x + n[0] * sign * 0.1, mid.y + n[1] * sign * 0.1)
            if poly.covers(probe):
                approaches[sid] = Polygon(
                    [
                        a,
                        b,
                        (b[0] + n[0] * sign * approach_m, b[1] + n[1] * sign * approach_m),
                        (a[0] + n[0] * sign * approach_m, a[1] + n[1] * sign * approach_m),
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


def fit_templates(model, space, templates):
    """Finite 0.1 m, four-rotation search; False means no sampled arrangement.

    Clear zones may overlap each other but cannot overlap another solid body.
    Exhaustive continuous infeasibility is not claimed.
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
    excluded = unary_union(swings)
    return _fit_cached(
        floor.wkb,
        excluded.wkb,
        unary_union(approaches).wkb,
        tuple(t.model_dump_json() for t in templates),
    )


@lru_cache(maxsize=256)
def _fit_cached(floor_wkb, excluded_wkb, approach_wkb, template_jsons):
    from house_ai.domain.usability import FurnitureTemplate

    floor, excluded = loads(floor_wkb), loads(excluded_wkb)
    approaches = loads(approach_wkb)
    templates = [FurnitureTemplate.model_validate_json(s) for s in template_jsons]
    tolerant = floor.buffer(EPS)
    xmin, ymin, xmax, ymax = floor.bounds if not floor.is_empty else (0, 0, 0, 0)

    def placements(t):
        for angle in (0, 90, 180, 270):
            _, env = template_shapes(t, (0, 0), angle)
            ex0, ey0, ex1, ey1 = env.bounds
            if ex1 - ex0 > xmax - xmin + EPS or ey1 - ey0 > ymax - ymin + EPS:
                continue
            # Include both bounds exactly as well as the regular sampling grid.
            xs = sorted(
                {
                    xmin - ex0,
                    xmax - ex1,
                    *[xmin - ex0 + i / 10 for i in range(int((xmax - xmin - ex1 + ex0) * 10) + 1)],
                }
            )
            ys = sorted(
                {
                    ymin - ey0,
                    ymax - ey1,
                    *[ymin - ey0 + i / 10 for i in range(int((ymax - ymin - ey1 + ey0) * 10) + 1)],
                }
            )
            for x in xs:
                for y in ys:
                    body, env = template_shapes(t, (x, y), angle)
                    if (
                        tolerant.covers(env)
                        and env.intersection(excluded).area < EPS
                        and body.intersection(approaches).area < EPS
                    ):
                        yield body, env

    class Replay:
        def __init__(self, values):
            self.values, self.cache, self.done = iter(values), [], False

        def __iter__(self):
            yield from self.cache
            if not self.done:
                for value in self.values:
                    self.cache.append(value)
                    yield value
                self.done = True

    candidates = [Replay(placements(t)) for t in templates]

    def search(i, chosen):
        if i == len(candidates):
            return chosen
        for body, env in candidates[i]:
            if all(
                body.intersection(e).area < EPS and env.intersection(b).area < EPS
                for b, e in chosen
            ):
                found = search(i + 1, [*chosen, (body, env)])
                if found is not None:
                    return found
        return None

    return search(0, [])
