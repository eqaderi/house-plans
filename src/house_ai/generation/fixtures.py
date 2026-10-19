"""Canonical fixtures in kitchens and wet rooms (S10-08, ISS-30).

A deterministic layout from the shared templates (`domain/usability_templates.py`),
following the rules of the critics' study (ADR 0019): each fixture stands with its
back against a wall's finish face and its front towards the room (template front is
local negative Y); its clear zone stays in the net floor and out of door swings; its
body stays out of door approaches and clear of other bodies' clear zones. A room gets
its whole set or nothing; when nothing fits, the critics' sampled study still reports.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from house_ai.domain.model import Fixture, HouseModel, Operation, Space
from house_ai.domain.program import SpaceFunction as S
from house_ai.domain.records import Issue, Severity
from house_ai.domain.usability_templates import TEMPLATES

#: Fixture sets by room function, laid out largest first.
FIXTURE_SETS = {
    S.KITCHEN: ["kitchen-run", "appliance"],
    S.BATHROOM: ["shower", "basin", "wc"],
    S.WC: ["basin", "wc"],
    S.LAUNDRY: ["laundry"],
}
#: Depth of a door's approach from the wall's finish face (ADR 0019 value).
APPROACH_M = 0.9
STEP_M = 0.1
SWINGS = {Operation.SWING_LEFT, Operation.SWING_RIGHT, Operation.DOUBLE_SWING}


def _strip(a: Point, b: Point, n: tuple[float, float], near: float, far: float) -> Polygon:
    return Polygon(
        [
            (a.x + n[0] * near, a.y + n[1] * near),
            (b.x + n[0] * near, b.y + n[1] * near),
            (b.x + n[0] * far, b.y + n[1] * far),
            (a.x + n[0] * far, a.y + n[1] * far),
        ]
    )


def _doors(model: HouseModel, space: Space, poly: Polygon):
    """(swing zones, approach zones) of the passable openings into ``space``.

    A swing is taken as the leaf's square (a superset of its quarter circle)."""
    swings, approaches = [], []
    for o in model.openings:
        if not o.is_passable or space.id not in o.connects:
            continue
        wall = model.wall(o.host_wall_id)
        line = LineString([wall.start, wall.end])
        a, b = line.interpolate(o.offset_m), line.interpolate(o.offset_m + o.width_m)
        ux, uy = (b.x - a.x) / o.width_m, (b.y - a.y) / o.width_m
        n = (-uy, ux)
        mid = Point((a.x + b.x) / 2 + n[0] * 0.2, (a.y + b.y) / 2 + n[1] * 0.2)
        if not poly.covers(mid):
            n = (uy, -ux)
        face = wall.thickness_m / 2
        approaches.append(_strip(a, b, n, face, face + APPROACH_M))
        if o.operation in SWINGS and o.opens_into in (space.id, None):
            swings.append(_strip(a, b, n, face, face + o.width_m))
    return unary_union(swings), unary_union(approaches)


def _place(floor, sides, template, envelopes, bodies, swings, approaches):
    """First wall position (longest side first) that keeps the rules above."""
    w, d = template.width.value, template.depth.value
    left, right = template.left.value, template.right.value
    front, back = template.front.value, template.back.value
    for (ax, ay), (ux, uy), (nx, ny), length, face in sides:
        s = face + left
        while s + w + right <= length - face + 1e-9:

            def at(t, k, ax=ax, ay=ay, ux=ux, uy=uy, nx=nx, ny=ny):
                return (ax + ux * t + nx * k, ay + uy * t + ny * k)

            base = face + back
            body = Polygon([at(s, base), at(s + w, base), at(s + w, base + d), at(s, base + d)])
            env = Polygon(
                [
                    at(s - left, face),
                    at(s + w + right, face),
                    at(s + w + right, base + d + front),
                    at(s - left, base + d + front),
                ]
            )
            if (
                floor.covers(env)
                and env.intersection(swings).area < 1e-6
                and body.intersection(approaches).area < 1e-6
                and env.intersection(bodies).area < 1e-6
                and body.intersection(envelopes).area < 1e-6
            ):
                return body, env, at(s + w / 2, base + d / 2), math.degrees(math.atan2(nx, -ny))
            s += STEP_M
    return None


def layout_fixtures(model: HouseModel) -> tuple[list[Fixture], list[str]]:
    """Fixtures for rectangular kitchens and wet rooms, and the rooms that got none."""
    fixtures: list[Fixture] = []
    missed: list[str] = []
    for space in model.spaces:
        ids = FIXTURE_SETS.get(space.function)
        if ids is None or space.boundary.holes:
            continue
        poly = space.boundary.to_shapely()
        # Rectangles may carry shared-edge T-junction vertices after the 2D grid
        # is rotated to LOCAL. Simplify only those sub-micrometre collinear nodes
        # for wall-side candidates; the actual net floor below stays unchanged.
        corners = poly.simplify(1e-6)
        if len(corners.exterior.coords) != 5:
            continue
        walls = [w for w in model.walls if w.level_id == space.level_id]
        solids = unary_union(
            [LineString([w.start, w.end]).buffer(w.thickness_m / 2, cap_style=2) for w in walls]
        )
        floor = poly.difference(solids).buffer(1e-6)
        c = poly.centroid
        pts = list(corners.exterior.coords)[:-1]
        sides = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1], strict=True):
            length = math.dist((ax, ay), (bx, by))
            ux, uy = (bx - ax) / length, (by - ay) / length
            nx, ny = -uy, ux
            if (c.x - ax) * nx + (c.y - ay) * ny < 0:
                nx, ny = uy, -ux
            edge = LineString([(ax, ay), (bx, by)])
            # The finish face of the thickest wall on this side.
            face = max(
                (w.thickness_m / 2 for w in walls
                 if LineString([w.start, w.end]).distance(edge) < 0.02
                 and LineString([w.start, w.end]).buffer(0.02).intersection(edge).length > 0.05),
                default=0.15,
            )  # fmt: skip
            sides.append(((ax, ay), (ux, uy), (nx, ny), length, face))
        sides.sort(key=lambda side: -side[3])
        swings, approaches = _doors(model, space, poly)
        placed: list[Fixture] = []
        bodies = envelopes = Polygon()
        for n, ident in enumerate(ids, start=1):
            t = TEMPLATES[ident]
            spot = _place(floor, sides, t, envelopes, bodies, swings, approaches)
            if spot is None:
                break
            body, env, centre, rotation = spot
            bodies, envelopes = bodies.union(body), envelopes.union(env)
            placed.append(
                Fixture(
                    id=f"fx-{space.id.removeprefix('sp-')}-{n}"[:64],
                    space_id=space.id,
                    fixture_type=ident.replace("-", "_"),
                    position=(round(centre[0], 6), round(centre[1], 6)),
                    rotation_deg=round(rotation, 6),
                    width_m=t.width.value,
                    depth_m=t.depth.value,
                )
            )
        if len(placed) == len(ids):
            fixtures.extend(placed)
        else:
            missed.append(space.id)
    return fixtures, missed


def with_fixtures(model: HouseModel, actor) -> HouseModel:
    """``model`` with its fixture layout, and a warning issue for each room left without."""
    fixtures, missed = layout_fixtures(model)
    issues = [
        Issue(
            id=f"iss-no-fixtures-{sid.removeprefix('sp-')}"[:64],
            title=f"No fixture layout found for {sid}; the sampled study reports on it",
            severity=Severity.WARNING,
            subject_ids=[sid],
            raised_by=actor,
        )
        for sid in missed
    ]
    return model.model_copy(
        update={"fixtures": [*model.fixtures, *fixtures], "issues": [*model.issues, *issues]}
    )
