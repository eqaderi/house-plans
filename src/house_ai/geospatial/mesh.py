"""Trimesh/Manifold adapter adopted after S3 experiments (ADR 0022).

No mesh type crosses into the canonical domain. TINs are closed to an explicit
base below all vertices; the closing solid is a computational device only.
"""

from __future__ import annotations

import numpy as np
import trimesh
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon

from house_ai.domain.site import TinSurface

from .earthworks import parts


def closed_tin(surface: TinSurface, base_m: float):
    if base_m >= min(p[2] for p in surface.vertices):
        raise ValueError("TIN closing base must be strictly below every terrain vertex")
    points = list(surface.vertices)
    n = len(points)
    points += [(x, y, base_m) for x, y, _ in surface.vertices]
    faces = []
    edges: dict[tuple, list] = {}
    for ids in surface.triangles:
        a, b, c = ids
        pa, pb, pc = (points[i] for i in ids)
        cross = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
        if abs(cross) < 1e-12:
            raise ValueError("degenerate terrain triangle")
        if cross < 0:
            b, c = c, b
        faces.extend([(a, b, c), (c + n, b + n, a + n)])
        for x, y in ((a, b), (b, c), (c, a)):
            edges.setdefault(tuple(sorted((x, y))), []).append((x, y))
    for occurrences in edges.values():
        if len(occurrences) > 2:
            raise ValueError("nonmanifold terrain edge")
        if len(occurrences) == 1:
            a, b = occurrences[0]
            faces.extend([(b, a, a + n), (b, a + n, b + n)])
    mesh = trimesh.Trimesh(vertices=points, faces=faces, process=True)
    if not mesh.is_volume:
        raise ValueError("terrain cannot form a closed positive solid")
    return mesh


def prism(footprint, bottom_m: float, top_m: float):
    if top_m <= bottom_m:
        raise ValueError("prism top must be above bottom")
    meshes = []
    for poly in parts(footprint):
        vertices, faces, index = [], [], {}

        def vertex(x, y, z, index=index, vertices=vertices):
            key = (x, y, z)
            if key not in index:
                index[key] = len(vertices)
                vertices.append(key)
            return index[key]

        for tri in constrained_delaunay_triangles(poly).geoms:
            pts = list(tri.exterior.coords)[:3]
            if not tri.exterior.is_ccw:
                pts.reverse()
            top = [vertex(x, y, top_m) for x, y in pts]
            low = [vertex(x, y, bottom_m) for x, y in pts]
            faces.extend([top, low[::-1]])
        from shapely.geometry.polygon import orient

        poly = orient(poly, sign=1)
        for ring in [poly.exterior, *poly.interiors]:
            for a, b in zip(ring.coords, list(ring.coords)[1:], strict=False):
                ia, ib = vertex(*a, top_m), vertex(*b, top_m)
                ja, jb = vertex(*a, bottom_m), vertex(*b, bottom_m)
                faces.extend([(ib, ia, ja), (ib, ja, jb)])
        meshes.append(trimesh.Trimesh(vertices=vertices, faces=faces, process=True))
    if not meshes:
        return trimesh.Trimesh()
    result = trimesh.util.concatenate(meshes)
    if not result.is_volume:
        raise ValueError("footprint cannot form a closed positive prism")
    return result


def intersection_volume(a, b) -> float:
    """Mesh64 avoids the single precision bridge used by some Trimesh engines."""
    import manifold3d

    def convert(mesh):
        if not mesh.is_volume:
            raise ValueError("boolean input must be a closed positive solid")
        result = manifold3d.Manifold(
            manifold3d.Mesh64(
                np.asarray(mesh.vertices),
                np.asarray(mesh.faces, dtype=np.uint64),
            )
        )
        if result.status() != manifold3d.Error.NoError:
            raise ValueError(f"Manifold rejected mesh: {result.status()}")
        return result

    return max(0.0, float((convert(a) ^ convert(b)).volume()))


def terrain_intersection(surface: TinSurface, footprint: Polygon, floor_m: float) -> dict:
    """Independent boolean cross-check of 2.5D cut and underfloor quantities."""
    low = min(min(p[2] for p in surface.vertices), floor_m) - 1
    high = max(max(p[2] for p in surface.vertices), floor_m) + 1
    terrain = closed_tin(surface, low)
    above = prism(footprint, floor_m, high)
    below = prism(footprint, low, floor_m)
    # Limit below-plane volume to actual surveyed support.
    from .earthworks import support

    known = support(surface).intersection(footprint)
    return {
        "cut_m3": intersection_volume(terrain, above),
        "below_plane_m3": known.area * (floor_m - low) - intersection_volume(terrain, below),
        "known_area_m2": known.area,
        "watertight": bool(terrain.is_volume),
        "method": "trimesh_closed_tin_manifold_mesh64_boolean",
        "status": "inferred",
    }
