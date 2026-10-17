"""Analytical mesh evaluation; run only in the documented disposable environment."""

from __future__ import annotations

import importlib.metadata
import json
import platform

import manifold3d
import numpy as np
import trimesh

TOLERANCE = 1e-7


def tin_solid(top: list[list[float]], triangles: list[list[int]]) -> trimesh.Trimesh:
    """Close a supplied synthetic TIN to z=0, retaining its triangulation."""
    count = len(top)
    points = top + [[x, y, 0] for x, y, _ in top]
    faces = triangles + [[c + count, b + count, a + count] for a, b, c in triangles]
    edge_counts: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for triangle in triangles:
        for a, b in zip(triangle, triangle[1:] + triangle[:1], strict=True):
            edge = tuple(sorted((a, b)))
            edge_counts.setdefault(edge, []).append((a, b))
    for occurrences in edge_counts.values():
        if len(occurrences) == 1:
            a, b = occurrences[0]
            faces.extend([[b, a, a + count], [b, a + count, b + count]])
    mesh = trimesh.Trimesh(points, faces, process=True)
    return mesh


def step_solid() -> trimesh.Trimesh:
    """Extrude the explicit 2/4 m stepped roof profile through 6 m."""
    profile = [(0, 0), (10, 0), (10, 4), (5, 4), (5, 2), (0, 2)]
    points = [[x, y, z] for y in (0, 6) for x, z in profile]
    cap = [[0, 1, 4], [1, 2, 3], [1, 3, 4], [0, 4, 5]]
    faces = cap + [[c + 6, b + 6, a + 6] for a, b, c in cap]
    for a in range(6):
        b = (a + 1) % 6
        faces.extend([[b, a, a + 6], [b, a + 6, b + 6]])
    mesh = trimesh.Trimesh(points, faces, process=True)
    return mesh


def manifold(mesh: trimesh.Trimesh) -> manifold3d.Manifold:
    return manifold3d.Manifold(
        manifold3d.Mesh64(np.asarray(mesh.vertices), np.asarray(mesh.faces, dtype=np.uint64))
    )


def section_area(mesh: trimesh.Trimesh, height: float) -> float:
    section = mesh.section(plane_origin=[0, 0, height], plane_normal=[0, 0, 1])
    assert section is not None
    # Shoelace directly on closed discrete paths avoids optional Shapely/scipy packages.
    result = 0.0
    for path in section.discrete:
        xy = path[:, :2]
        result += abs(float(np.sum(xy[:-1, 0] * xy[1:, 1] - xy[1:, 0] * xy[:-1, 1]))) / 2
    return result


def main() -> None:
    triangles = [[0, 1, 2], [0, 2, 3]]
    planar = tin_solid([[0, 0, 2], [10, 0, 4], [10, 6, 4], [0, 6, 2]], triangles)
    wedge = tin_solid([[0, 0, 1], [10, 0, 5], [10, 6, 5], [0, 6, 1]], triangles)
    pyramid = tin_solid(
        [[0, 0, 1], [10, 0, 1], [10, 6, 1], [0, 6, 1], [5, 3, 5]],
        [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]],
    )
    upper = trimesh.creation.box(extents=[10, 6, 8])
    upper.apply_translation([5, 3, 7])  # bottom at pad z=3
    pad = trimesh.creation.box(extents=[10, 6, 3])
    pad.apply_translation([5, 3, 1.5])
    rows = []
    for name, mesh, expected in [
        ("planar_slope", planar, (180, 15, 15, 30)),
        ("wedge", wedge, (180, 30, 30, 30)),
        ("pyramid", pyramid, (140, 10, 50, 15)),
        ("stepped_pad", step_solid(), (180, 30, 30, 30)),
    ]:
        direct = manifold(mesh)
        assert mesh.is_watertight and mesh.is_winding_consistent
        assert str(direct.status()) == "Error.NoError"
        cut = trimesh.boolean.intersection([mesh, upper], engine="manifold")
        void = trimesh.boolean.difference([pad, mesh], engine="manifold")
        actual = {
            "trimesh_volume_m3": float(mesh.volume),
            "trimesh_cut_m3": float(cut.volume),
            "trimesh_void_m3": float(void.volume),
            "trimesh_section_m2": section_area(mesh, 3),
            "manifold_volume_m3": direct.volume(),
            "manifold_cut_m3": (direct ^ manifold(upper)).volume(),
            "manifold_void_m3": (manifold(pad) - direct).volume(),
            "manifold_section_m2": direct.slice(3).area(),
        }
        expected_values = dict(zip(actual, expected * 2, strict=True))
        for metric, value in actual.items():
            assert abs(value - expected_values[metric]) <= TOLERANCE, (name, metric, value)
        rows.append({"fixture": name, "watertight": True, "expected": expected_values, **actual})
    # Coplanar contact: touching cubes have zero intersection and disjoint input is empty.
    cube = manifold3d.Manifold.cube([1, 1, 1])
    touching = cube.translate([1, 0, 0])
    separated = cube.translate([2, 0, 0])
    assert abs((cube ^ touching).volume()) <= TOLERANCE
    assert (cube ^ separated).is_empty()
    invalid = planar.copy()
    invalid.update_faces(np.arange(len(invalid.faces) - 1))
    invalid_status = str(manifold(invalid).status())
    assert invalid_status == "Error.NotManifold"
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "system": platform.system(),
                "architecture": platform.machine(),
                "method": "simulation_result",
                "packages": {
                    name: importlib.metadata.version(name)
                    for name in ("numpy", "trimesh", "manifold3d")
                },
                "absolute_tolerance": TOLERANCE,
                "results": rows,
                "touching_intersection_m3": (cube ^ touching).volume(),
                "disjoint_intersection_empty": True,
                "open_tin_status": invalid_status,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
