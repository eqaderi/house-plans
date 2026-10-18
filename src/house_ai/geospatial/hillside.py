"""Per-concept terrain relationships and unresolved professional risk register."""

from __future__ import annotations

import math

from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, unary_union

from house_ai.domain.hillside import HillsideSettings
from house_ai.domain.model import HouseModel, OpeningKind, WallKind
from house_ai.domain.program import SpaceFunction
from house_ai.domain.site import PointGeometry, PolygonGeometry, PolylineGeometry, Site
from house_ai.domain.terrain import elevation_at, site_surface

from .earthworks import earthworks, facets, retained_face, terrain_profile

HABITABLE = {
    SpaceFunction.BEDROOM,
    SpaceFunction.GUEST_SUITE,
    SpaceFunction.LIVING,
    SpaceFunction.FAMILY,
    SpaceFunction.RECEPTION,
    SpaceFunction.STUDY,
    SpaceFunction.DINING,
    SpaceFunction.KITCHEN,
    SpaceFunction.PLAY,
}


def triangle_quality(surface, settings: HillsideSettings) -> list[dict]:
    """Scale-invariant 4√3 area / sum(edge²), 1 for equilateral, near 0 for slivers."""
    results = []
    for i, (shape, _, vertices) in enumerate(facets(surface)):
        edges = [
            math.dist(a[:2], b[:2])
            for a, b in zip(vertices, vertices[1:] + vertices[:1], strict=True)
        ]
        quality = 4 * math.sqrt(3) * shape.area / sum(d * d for d in edges)
        a, b, c = vertices
        ux, uy, uz = (b[j] - a[j] for j in range(3))
        vx, vy, vz = (c[j] - a[j] for j in range(3))
        slope = 100 * math.hypot(uy * vz - uz * vy, uz * vx - ux * vz) / abs(ux * vy - uy * vx)
        if quality < settings.sliver_quality_trigger or slope > 100:
            results.append(
                {
                    "triangle_index": i,
                    "xy": list(shape.centroid.coords)[0],
                    "quality": quality,
                    "slope_pct": slope,
                    "triggers": [
                        *(["sliver"] if quality < settings.sliver_quality_trigger else []),
                        *(["steep_review"] if slope > 100 else []),
                    ],
                    "status": "measured",
                    "note": "Suspicious geometry for review, not evidence of bad survey; "
                    "real steep slopes are retained, never smoothed.",
                }
            )
    return results


def _feature_shape(feature):
    g = feature.geometry
    if isinstance(g, PolygonGeometry):
        return g.polygon.to_shapely()
    if isinstance(g, PolylineGeometry):
        return g.line.to_shapely()
    if isinstance(g, PointGeometry):
        return Point(g.xy)
    return None


def hillside_report(
    model: HouseModel, site: Site | None, settings: HillsideSettings | None = None
) -> dict:
    settings = settings or HillsideSettings()
    frame_matches = bool(
        site and site.coordinates.local and site.coordinates.local.id == model.coordinate_system_id
    )
    surface = site_surface(site) if frame_matches else None
    terrain_error = None
    try:
        works = earthworks(model, surface)
    except ValueError as exc:
        terrain_error = str(exc)
        surface = None
        works = earthworks(model.model_copy(update={"earthwork_pads": []}), None)
        works["error"] = terrain_error
    retaining, doors, terraces, garages, buried = [], [], [], [], []
    risks = []

    def risk(discipline, trigger, subjects=()):
        risks.append(
            {
                "discipline": discipline,
                "status": "needs_professional",
                "trigger": trigger,
                "subject_ids": list(subjects),
            }
        )

    if terrain_error:
        risk("survey", f"Invalid terrain/earthwork geometry: {terrain_error}")

    risk("structure", "Concept load paths, lateral stability and support systems unresolved")
    risk("foundations", "Bearing capacity, settlement and footing depths unverified")
    risk("slope_stability", "Survey TIN does not establish geotechnical or slope stability")
    for wall in model.walls:
        if wall.kind not in {WallKind.EXTERIOR, WallKind.RETAINING}:
            continue
        floor = model.level(wall.level_id).elevation_m + wall.base_offset_m
        face = retained_face(surface, wall.start, wall.end, floor)
        if wall.kind is WallKind.RETAINING or (face["max_retained_height_m"] or 0) > 0.6:
            retaining.append(
                {
                    "wall_id": wall.id,
                    **face,
                    "status": "inferred" if face["known_length_m"] else "not_checked",
                }
            )
            risk("retaining", "Earth-contact wall needs engineered retaining design", [wall.id])
            risk(
                "drainage",
                "Uphill earth-contact face: intercept and discharge routes unresolved",
                [wall.id],
            )
            adj = [
                s.id
                for s in model.spaces
                if s.level_id == wall.level_id
                and s.function in HABITABLE
                and s.boundary.to_shapely()
                .boundary.intersection(LineString([wall.start, wall.end]))
                .length
                > 0.01
            ]
            if adj:
                buried.append({"wall_id": wall.id, "space_ids": adj, **face})
                risk(
                    "waterproofing",
                    "Buried habitable wall: waterproofing and moisture control",
                    [wall.id, *adj],
                )
    if not retaining:
        risk("retaining", "Retaining requirements have not been professionally assessed")
        risk("drainage", "Surface/subsoil drainage and safe discharge unverified")
        risk("waterproofing", "Building-ground moisture details unverified")
    if (works["max_underfloor_void_height_m"] or 0) > settings.large_void_height_m:
        risk(
            "structure",
            f"Underfloor clear space exceeds configured "
            f"{settings.large_void_height_m:g} m concept trigger; large void needs review",
        )
    if works["unknown_area_m2"] > 1e-8:
        risk("survey", "Footprint outside surveyed terrain; quantities only cover known support")
    footprints = {
        lv.id: unary_union([s.boundary.to_shapely() for s in model.spaces if s.level_id == lv.id])
        for lv in model.levels
    }
    for door in model.openings:
        if door.kind is not OpeningKind.DOOR or "exterior" not in door.connects:
            continue
        wall = model.wall(door.host_wall_id)
        p = LineString([wall.start, wall.end]).interpolate(door.offset_m + door.width_m / 2)
        nx, ny = (
            -(wall.end[1] - wall.start[1]) / wall.length_m,
            (wall.end[0] - wall.start[0]) / wall.length_m,
        )
        outside = Point(p.x + nx * 0.5, p.y + ny * 0.5)
        if footprints[wall.level_id].covers(outside):
            outside = Point(p.x - nx * 0.5, p.y - ny * 0.5)
        ground = elevation_at(surface, (outside.x, outside.y)) if surface else None
        threshold = model.level(wall.level_id).elevation_m + door.sill_m
        delta = threshold - ground if ground is not None else None
        doors.append(
            {
                "door_id": door.id,
                "outside_xy": list(outside.coords)[0],
                "threshold_z_m": threshold,
                "ground_z_m": ground,
                "delta_m": delta,
                "outside_level_change_needed": abs(delta) > settings.access_step_trigger_m
                if delta is not None
                else None,
                "status": "inferred" if ground is not None else "not_checked",
            }
        )
        if delta is not None:
            risk(
                "drainage",
                "Terrain-contact door: threshold drainage and approach unresolved",
                [door.id],
            )
    roads = []
    if site:
        roads = [_feature_shape(f) for f in site.features if f.kind.value == "frontage"]
        if not roads:
            roads = [_feature_shape(f) for f in site.features if f.kind.value == "road"]
    road = unary_union([r for r in roads if r is not None])
    for garage in (s for s in model.spaces if s.function is SpaceFunction.GARAGE):
        vehicle_doors = [
            d
            for d in model.openings
            if d.kind is OpeningKind.DOOR
            and "exterior" in d.connects
            and garage.id in d.connects
            and d.width_m >= 2
        ]
        for door in vehicle_doors or [None]:
            p = garage.boundary.to_shapely().centroid
            if door:
                wall = model.wall(door.host_wall_id)
                p = LineString([wall.start, wall.end]).interpolate(door.offset_m + door.width_m / 2)
            q = nearest_points(road, p)[0] if not road.is_empty else None
            z = elevation_at(surface, (q.x, q.y)) if surface and q else None
            floor = model.level(garage.level_id).elevation_m
            run = p.distance(q) if q else None
            delta = floor - z if z is not None else None
            grade = 100 * delta / run if delta is not None and run and run > 1e-6 else None
            route = LineString([q, p]) if q and run and run > 1e-6 else None
            inside = bool(
                site
                and site.boundary
                and route
                and site.boundary.to_shapely().buffer(1e-6).covers(route)
            )
            garages.append(
                {
                    "garage_id": garage.id,
                    "door_id": door.id if door else None,
                    "floor_z_m": floor,
                    "frontage_z_m": z,
                    "delta_m": delta,
                    "candidate_run_m": run,
                    "candidate_grade_pct": grade,
                    "candidate_route_xy": list(route.coords) if route else None,
                    "inside_parcel": inside,
                    "status": "inferred" if grade is not None else "not_checked",
                    "method": "straight_candidate_approach_to_nearest_frontage",
                    "note": "Candidate only; usable ramp, vertical curves, clearance, "
                    "turning, drainage and easements need design; no feasibility claim.",
                }
            )
            risk(
                "vehicle_access",
                "Garage ramp approach needs design and professional review",
                [garage.id, *([door.id] if door else [])],
            )
    for space in model.spaces:
        if space.function not in {SpaceFunction.TERRACE, SpaceFunction.BALCONY}:
            continue
        z = model.level(space.level_id).elevation_m
        ring = list(space.boundary.to_shapely().exterior.coords)
        edges = []
        for a, b in zip(ring, ring[1:], strict=False):
            profile = terrain_profile(surface, LineString([a, b]))
            deltas = [
                z - p[key]
                for p in profile
                if p["status"] != "unknown"
                for key in ("start_z_m", "end_z_m")
            ]
            edges.append(
                {
                    **retained_face(surface, a, b, z),
                    "ground_profile": profile,
                    "floor_z_m": z,
                    "min_floor_ground_delta_m": min(deltas) if deltas else None,
                    "max_floor_ground_delta_m": max(deltas) if deltas else None,
                }
            )
        connected = [d.id for d in model.openings if d.is_passable and space.id in d.connects]
        terraces.append(
            {
                "space_id": space.id,
                "edge_ground_relationships": edges,
                "connected_openings": connected,
                "garden_access": {
                    "status": "inferred"
                    if any(e["known_length_m"] for e in edges)
                    else "not_checked",
                    "candidate_at_grade_edges": [
                        i
                        for i, e in enumerate(edges)
                        if e["min_floor_ground_delta_m"] is not None
                        and e["min_floor_ground_delta_m"] <= settings.access_step_trigger_m
                        and e["max_floor_ground_delta_m"] >= -settings.access_step_trigger_m
                    ],
                    "note": "Terrain contact candidates only; a traversable garden approach, "
                    "stairs/ramp, edge protection and support need design.",
                },
            }
        )
        risk(
            "foundations",
            "Terrace supports, edge protection and garden approach unresolved",
            [space.id],
        )
    return {
        "earthworks": works,
        "retaining_candidates": retaining,
        "doors": doors,
        "garages": garages,
        "terraces": terraces,
        "buried_habitable_faces": buried,
        "outdoor_level_changes_count": sum(d["outside_level_change_needed"] is True for d in doors),
        "indoor_stairs_count": len(model.stairs),
        "terrain_quality": triangle_quality(surface, settings) if surface else [],
        "risks": risks,
        "settings": settings.model_dump(),
        "site_frame_matches": frame_matches,
        "geometry_error": terrain_error,
        "note": "Inferred conceptual relationships against surveyed TIN. All engineering "
        "disciplines listed as needs professional; no excavation-depth penalty.",
    }
