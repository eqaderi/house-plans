"""True vertical cuts derived from canonical geometry, with no projected bands.

Section coordinates are (distance along requested line, LOCAL elevation).
Every cut retains its canonical subject ID. Missing stair orientation and
survey coverage stay unknown. Elevations are separately labelled projections.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring, unary_union

from house_ai.domain.hillside import SectionLine
from house_ai.domain.model import HouseModel, OpeningKind, WallKind
from house_ai.domain.program import SpaceFunction
from house_ai.domain.site import Site
from house_ai.domain.terrain import site_surface

from .earthworks import parts, terrain_profile


def _compatible_site(model, site):
    return bool(
        site and site.coordinates.local and site.coordinates.local.id == model.coordinate_system_id
    )


def _intervals(line, shape):
    for segment in parts(line.intersection(shape), "LineString"):
        distances = [line.project(Point(p)) for p in segment.coords]
        yield min(distances), max(distances)


def _rectangle(a, b, lo, hi):
    return Polygon([(a, lo), (b, lo), (b, hi), (a, hi)])


def cut_section(model: HouseModel, site: Site | None, request: SectionLine) -> dict:
    line = LineString([request.start, request.end])
    cuts, unknowns = [], []

    def add(subject, kind, shape):
        for poly in parts(shape):
            if poly.area > 1e-10:
                cuts.append(
                    {
                        "subject_id": subject,
                        "kind": kind,
                        "polygon": list(poly.exterior.coords),
                        "holes": [list(r.coords) for r in poly.interiors],
                        "status": "measured",
                    }
                )

    for wall in model.walls:
        footprint = LineString([wall.start, wall.end]).buffer(wall.thickness_m / 2, cap_style=2)
        floor = model.level(wall.level_id).elevation_m + wall.base_offset_m
        opening_floor = model.level(wall.level_id).elevation_m
        opening_cuts = []
        for opening in model.openings:
            if opening.host_wall_id != wall.id:
                continue
            axis = LineString([wall.start, wall.end])
            a = axis.interpolate(opening.offset_m)
            b = axis.interpolate(opening.offset_m + opening.width_m)
            aperture = LineString([a, b]).buffer(wall.thickness_m / 2 + 1e-7, cap_style=2)
            for lo, hi in _intervals(line, aperture):
                shape = _rectangle(
                    lo,
                    hi,
                    opening_floor + opening.sill_m,
                    opening_floor + opening.sill_m + opening.height_m,
                )
                opening_cuts.append(shape)
                add(opening.id, opening.kind.value, shape)
        for lo, hi in _intervals(line, footprint):
            wall_cut = _rectangle(lo, hi, floor, floor + wall.height_m)
            add(wall.id, "wall", wall_cut.difference(unary_union(opening_cuts)))
    for slab in model.slabs:
        top = model.level(slab.level_id).elevation_m + slab.top_offset_m
        for lo, hi in _intervals(line, slab.boundary.to_shapely()):
            add(slab.id, "slab", _rectangle(lo, hi, top - slab.thickness_m, top))
    for stair in model.stairs:
        hit = line.intersection(stair.footprint.to_shapely())
        if hit.is_empty:
            continue
        if not stair.walking_line or not stair.riser_count:
            unknowns.append({"subject_id": stair.id, "reason": "stair walking line/risers unknown"})
            continue
        path = LineString(stair.walking_line)
        low = model.level(stair.from_level_id).elevation_m
        high = model.level(stair.to_level_id).elevation_m
        if low > high:
            low, high = high, low
        for i in range(stair.riser_count):
            tread = substring(
                path, path.length * i / stair.riser_count, path.length * (i + 1) / stair.riser_count
            )
            tread_shape = tread.buffer(stair.width_m / 2, cap_style=2).intersection(
                stair.footprint.to_shapely()
            )
            z = low + (high - low) * (i + 1) / stair.riser_count
            for lo, hi in _intervals(line, tread_shape):
                add(stair.id, "stair", _rectangle(lo, hi, low, z))
    surface = site_surface(site) if _compatible_site(model, site) else None
    return {
        "id": request.id,
        "line": request.model_dump(mode="json"),
        "length_m": line.length,
        "cuts": cuts,
        "unknowns": unknowns,
        "ground": terrain_profile(surface, line),
        "method": "vertical_plane_intersection_of_canonical_elements",
        "note": "True cut, LOCAL metres; terrain interpolated (inferred); "
        "stairs use canonical walking line and risers, no structural thickness specified.",
    }


def standard_sections(model: HouseModel, site: Site | None) -> list[SectionLine]:
    shapes = [s.boundary.to_shapely() for s in model.spaces]
    if not shapes:
        return []
    footprint = unary_union(shapes)
    outline = (
        site.boundary.to_shapely()
        if _compatible_site(model, site) and site.boundary
        else footprint.buffer(3)
    )
    center = footprint.centroid
    rect = list(footprint.minimum_rotated_rectangle.exterior.coords)
    a, b = max(zip(rect, rect[1:], strict=False), key=lambda ab: math.dist(*ab))
    d = math.dist(a, b)
    direction = ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
    requests = []

    def through(identifier, point, vector):
        coords = list(outline.exterior.coords)
        distances = [(x - point[0]) * vector[0] + (y - point[1]) * vector[1] for x, y in coords]
        lo, hi = min(distances) - 1, max(distances) + 1
        requests.append(
            SectionLine(
                id=identifier,
                start=(point[0] + lo * vector[0], point[1] + lo * vector[1]),
                end=(point[0] + hi * vector[0], point[1] + hi * vector[1]),
            )
        )

    through("longitudinal", (center.x, center.y), direction)
    through("transverse", (center.x, center.y), (-direction[1], direction[0]))
    for stair in model.stairs:
        c = stair.footprint.to_shapely().centroid
        v = direction
        if stair.walking_line:
            a, b = stair.walking_line[:2]
            d = math.dist(a, b)
            if d > 1e-8:
                v = ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
                p = LineString([a, b]).interpolate(0.5, normalized=True)
                c = p
        through(f"stair-{stair.id}"[:64], (c.x, c.y), v)
    for space in model.spaces:
        if space.function is SpaceFunction.GARAGE:
            c = space.boundary.to_shapely().centroid
            through(f"garage-{space.id}"[:64], (c.x, c.y), direction)
    for door in model.openings:
        if door.kind is OpeningKind.DOOR and "exterior" in door.connects:
            wall = model.wall(door.host_wall_id)
            p = LineString([wall.start, wall.end]).interpolate(door.offset_m + door.width_m / 2)
            vector = (
                (wall.start[1] - wall.end[1]) / wall.length_m,
                (wall.end[0] - wall.start[0]) / wall.length_m,
            )
            through(f"entrance-{door.id}"[:64], (p.x, p.y), vector)
    return requests


def facade_elevations(model: HouseModel, site: Site | None) -> list[dict]:
    """Four orthographic facade projections; hidden-line removal not claimed."""
    output = []
    for name, direction in (
        ("east", (0, 1)),
        ("west", (0, -1)),
        ("north", (-1, 0)),
        ("south", (1, 0)),
    ):
        cuts = []

        def project(p, direction=direction):
            return p[0] * direction[0] + p[1] * direction[1]

        for wall in model.walls:
            if wall.kind is WallKind.INTERIOR:
                continue
            a, b = sorted([project(wall.start), project(wall.end)])
            if b - a < 1e-6:
                continue
            floor = model.level(wall.level_id).elevation_m + wall.base_offset_m
            opening_floor = model.level(wall.level_id).elevation_m
            cuts.append(
                {
                    "subject_id": wall.id,
                    "kind": "wall",
                    "polygon": list(_rectangle(a, b, floor, floor + wall.height_m).exterior.coords),
                }
            )
            for opening in model.openings:
                if opening.host_wall_id != wall.id:
                    continue
                axis = LineString([wall.start, wall.end])
                p, q = [
                    project(axis.interpolate(t).coords[0])
                    for t in (opening.offset_m, opening.offset_m + opening.width_m)
                ]
                cuts.append(
                    {
                        "subject_id": opening.id,
                        "kind": opening.kind.value,
                        "polygon": list(
                            _rectangle(
                                min(p, q),
                                max(p, q),
                                opening_floor + opening.sill_m,
                                opening_floor + opening.sill_m + opening.height_m,
                            ).exterior.coords
                        ),
                    }
                )
        if not cuts:
            continue
        # Ground cut on the facing boundary of the building's bounding rectangle.
        bounds = unary_union([s.boundary.to_shapely() for s in model.spaces]).bounds
        x0, y0, x1, y1 = bounds
        if name == "north":
            start, end = (x1, y1), (x0, y1)
        elif name == "south":
            start, end = (x0, y0), (x1, y0)
        elif name == "east":
            start, end = (x1, y0), (x1, y1)
        else:
            start, end = (x0, y1), (x0, y0)
        ground = terrain_profile(
            site_surface(site) if _compatible_site(model, site) else None, LineString([start, end])
        )
        shift = project(start)
        ground = [
            {**p, "start_m": p["start_m"] + shift, "end_m": p["end_m"] + shift} for p in ground
        ]
        for pad in model.earthwork_pads:
            positions = [project(p) for p in pad.boundary.outer]
            cuts.append(
                {
                    "subject_id": pad.id,
                    "kind": "platform",
                    "polygon": list(
                        _rectangle(
                            min(positions), max(positions), pad.elevation_m - 0.05, pad.elevation_m
                        ).exterior.coords
                    ),
                }
            )
        output.append(
            {
                "id": f"elevation-{name}",
                "cuts": cuts,
                "ground": ground,
                "unknowns": [],
                "method": "orthographic_projection",
                "note": "LOCAL axes, projected facades and platforms; "
                "occlusion not resolved. Ground is a cut at the facing building bound.",
            }
        )
    return output
