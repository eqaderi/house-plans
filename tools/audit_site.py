"""Read-only source replay; writes a review export, never ProjectStore state.

Run with the project venv: python tools/audit_site.py PROJECT --out EXPORT.json.
DWG replay requires the installed ODA converter. Private values stay in the
project's review export; no private fixture or expected value lives here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

from shapely.geometry import Point, Polygon

from house_ai.cad.layers import load_layer_mapping
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.site import Site
from house_ai.domain.units import METRES_PER_UNIT
from house_ai.geospatial.terrain import elevation_at, terrain_from_survey, triangle_slope_pct
from house_ai.geospatial.validation import validate_site
from house_ai.orchestration.site_ingestion import _load, combined_frame, interpret
from house_ai.storage import ProjectStore


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(project: Path) -> dict:
    store = ProjectStore(project)
    errors = store.verify()
    if errors:
        raise ValueError(errors)
    mapping = load_layer_mapping(project / "site/layers.yaml")
    stored = store.get_latest(K.SITE, "site")
    if not isinstance(stored, Site):
        raise ValueError("no stored site")
    ids = [ref.id for ref in stored.provenance.inputs if ref.kind is K.SOURCE_DOCUMENT]
    sources = [_load(store, sid, mapping) for sid in sorted(ids)]
    frame, issues = combined_frame(sources)
    if issues:
        raise ValueError([i.title for i in issues])
    interp = interpret([(s.doc.id, s.extraction) for s in sources], mapping, frame)
    terrain, _ = terrain_from_survey(interp.extraction.spot_elevations, interp.extraction.contours)
    if stored.boundary is None or terrain.surface is None or terrain.contours:
        raise ValueError("this audit requires a parcel and a spot-only TIN")
    # Compare a fresh parse/interpretation/TIN to the immutable stored version.
    # Semantic equality ignores list ordering but includes every source reference.
    fresh_spots = {s.id: s.model_dump(mode="json") for s in terrain.spot_elevations}
    old_spots = {s.id: s.model_dump(mode="json") for s in stored.terrain.spot_elevations}
    if fresh_spots != old_spots or interp.extraction.boundary != stored.boundary:
        raise ValueError("fresh geometry differs from stored site; investigate before reporting")
    def triangle_geometry(surface):
        return sorted(tuple(sorted(surface.vertices[i] for i in tri))
                      for tri in surface.triangles)

    if triangle_geometry(terrain.surface) != triangle_geometry(stored.terrain.surface):
        raise ValueError("fresh TIN differs from stored surface")
    replay = stored.model_copy(update={"terrain": terrain})
    report = validate_site(replay)
    result = {"store_verified": True, "fresh_geometry_matches_stored": True,
              "sources": [], "triangles": [], "points": []}
    for src in sources:
        doc, ext = src.doc, src.extraction
        original = project / "surveys" / doc.original_filename
        before = sha(original)
        if before != doc.sha256 or sha(project / doc.stored_path) != before:
            raise ValueError(f"source hash mismatch: {original}")
        result["sources"].append({
            "id": doc.id, "filename": doc.original_filename, "sha256": before,
            "inspection": asdict(ext.inspection),
            "raw_entities": {"points_and_labels": [asdict(p) for p in ext.points],
                             "polylines": [asdict(p) for p in ext.polylines]},
            "label_checks": [c.model_dump(mode="json")
                             for c in interp.per_source[doc.id].label_checks],
        })
        for raw in ext.points:
            if raw.entity_type != "POINT":
                continue
            ref = f"{doc.id}#{raw.handle}"
            spot = next((s for s in terrain.spot_elevations
                         if s.source_ref == f"{ref} (layer {raw.layer})"), None)
            if spot is None:
                continue  # Excluded entities remain in the raw ledger above.
            labels = [asdict(p) for p in ext.points if p.text is not None
                      and math.dist(p.xy, raw.xy) <= 0.001]
            result["points"].append({
                "source_ref": ref, "raw_xyz": [*raw.xy, raw.z], "labels": labels,
                "local_xyz_m": [*spot.xy, spot.z_m],
                "inside_parcel": stored.boundary.to_shapely().covers(Point(spot.xy)),
            })
        if sha(original) != before:
            raise ValueError("original changed during audit")
    surface = terrain.surface
    parcel = stored.boundary.to_shapely()
    point_refs = {tuple([*s.xy, s.z_m]): s.source_ref for s in terrain.spot_elevations}
    clipped_z = []
    for indices in surface.triangles:
        pts = [surface.vertices[i] for i in indices]
        tri = Polygon([p[:2] for p in pts])
        clipped = tri.intersection(parcel)
        if clipped.area:
            for x, y in clipped.exterior.coords:
                clipped_z.append(elevation_at(surface, (x, y)))
        result["triangles"].append({
            "indices": indices, "sources": [point_refs[p] for p in pts],
            "slope_pct": triangle_slope_pct(*pts), "horizontal_area_m2": tri.area,
            "parcel_intersection_m2": clipped.area,
            "edges": [{"run_m": math.dist(pts[a][:2], pts[b][:2]),
                       "abs_dz_m": abs(pts[a][2] - pts[b][2])}
                      for a, b in ((0, 1), (1, 2), (2, 0))],
        })
    slopes = [t["slope_pct"] for t in result["triangles"]]
    result["metrics"] = {
        "report": report.model_dump(mode="json"),
        "arithmetic_triangle_mean_pct": sum(slopes) / len(slopes),
        "tin_horizontal_area_m2": sum(t["horizontal_area_m2"] for t in result["triangles"]),
        "all_spot_relief_m": report.terrain.z_max_m - report.terrain.z_min_m,
        "parcel_interpolated_z_range_m": [min(clipped_z), max(clipped_z)],
        "parcel_interpolated_relief_m": max(clipped_z) - min(clipped_z),
        "local_origin_grid_m": interp.local.origin,
        "rotation_deg": interp.local.rotation_deg,
        "horizontal_scale_m_per_source_unit": METRES_PER_UNIT[frame.source_units.unit],
        "vertical_scale_m_per_source_unit": METRES_PER_UNIT[frame.elevation_units.unit],
    }
    # The dump contains converter byte hashes for traceability. ODA embeds volatile
    # metadata, so use the entity ledger rather than DXF byte equality for replay.
    semantic = {k: result[k] for k in ("points", "triangles", "metrics")}
    result["semantic_sha256"] = hashlib.sha256(
        json.dumps(semantic, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.project)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"semantic_sha256": result["semantic_sha256"],
                      "output": str(args.out)}))
