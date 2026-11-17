"""DXF adapter built on ezdxf.

Reads model space only and keeps every coordinate exactly as drawn (SOURCE
frame, drawing units). Nothing here interprets layers, units or the CRS;
that happens in :mod:`house_ai.cad.site_extract` and the geospatial layer.
The file is opened read-only and never written.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import recover
from ezdxf.entities import DXFGraphic

from .base import CadExtraction, CadInspection, RawPoint, RawPolyline

#: Header variables reported by inspection when present. $LATITUDE,
#: $LONGITUDE and $NORTHDIRECTION are left out on purpose: drawing templates
#: carry default values (ezdxf's: San Francisco) that look like a declared
#: location but are not. A real georeference is a GEODATA object.
HEADER_VARS = (
    "$ACADVER",
    "$INSUNITS",
    "$MEASUREMENT",
    "$LUNITS",
    "$AUNITS",
    "$ANGBASE",
    "$ANGDIR",
)

GEODATA_COORDINATE_TYPES = {0: "unknown", 1: "local grid", 2: "projected grid", 3: "geographic"}

POINT_TYPES = ("POINT", "TEXT", "MTEXT", "INSERT", "CIRCLE")
LINE_TYPES = ("LINE", "LWPOLYLINE", "POLYLINE")


class DxfReadError(ValueError):
    pass


def _plain(value: Any) -> Any:
    """Header values as JSON-friendly Python values."""
    if hasattr(value, "x") and hasattr(value, "y"):
        return [float(c) for c in value]
    if isinstance(value, float | int | str):
        return value
    return str(value)


class EzdxfAdapter:
    name = "ezdxf"

    @property
    def version(self) -> str:
        return ezdxf.__version__

    def _read(self, path: Path) -> tuple[Any, list[str]]:
        try:
            doc, auditor = recover.readfile(str(path))
        except (OSError, ezdxf.DXFStructureError) as exc:
            raise DxfReadError(f"cannot read {path.name} as DXF: {exc}") from exc
        warnings = [f"DXF audit error: {e.message}" for e in auditor.errors]
        warnings += [f"DXF audit fixed: {f.message}" for f in auditor.fixes]
        return doc, warnings

    # ------------------------------------------------------------------ inspect

    def inspect_cad(self, path: Path) -> CadInspection:
        doc, warnings = self._read(path)
        return self._inspection(doc, warnings, self._extract(doc))

    def _inspection(self, doc: Any, warnings: list[str], ext: CadExtraction) -> CadInspection:
        msp = doc.modelspace()
        per_layer: dict[str, Counter[str]] = {layer.dxf.name: Counter() for layer in doc.layers}
        types: Counter[str] = Counter()
        for e in msp:
            per_layer.setdefault(e.dxf.layer, Counter())[e.dxftype()] += 1
            types[e.dxftype()] += 1
        header = {v: _plain(doc.header.get(v)) for v in HEADER_VARS if v in doc.header}
        geodata, declared_epsg = _geodata_summary(msp, warnings)
        if not types:
            warnings = [*warnings, "model space has no entities (empty or truncated drawing?)"]
        paper = sum(len(layout) for layout in doc.layouts if not layout.is_modelspace)
        if paper:
            warnings = [*warnings, f"{paper} paper-space entities ignored (model space only)"]
        insunits = doc.header.get("$INSUNITS")
        return CadInspection(
            parser=self.name,
            parser_version=self.version,
            declared_insunits=int(insunits) if insunits is not None else None,
            layers={name: sum(c.values()) for name, c in sorted(per_layer.items())},
            entity_counts=dict(sorted(types.items())),
            extents=_extents(ext),
            warnings=warnings,
            source_format=f"dxf {doc.dxfversion}",
            layer_entity_types={n: dict(sorted(c.items())) for n, c in sorted(per_layer.items())},
            header=header,
            geodata=geodata,
            declared_epsg=declared_epsg,
        )

    # ------------------------------------------------------------------ extract

    def extract_cad(self, path: Path, layer_roles: dict[str, str]) -> CadExtraction:
        doc, warnings = self._read(path)
        raw = self._extract(doc)
        return CadExtraction(
            points=raw.points,
            polylines=raw.polylines,
            layer_roles=dict(layer_roles),
            inspection=self._inspection(doc, warnings, raw),
            unsupported_entities=raw.unsupported_entities,
        )

    def _extract(self, doc: Any) -> CadExtraction:
        points: list[RawPoint] = []
        polylines: list[RawPolyline] = []
        unsupported: Counter[str] = Counter()
        for e in doc.modelspace():
            kind = e.dxftype()
            if kind in POINT_TYPES:
                points.append(_raw_point(e))
            elif kind in LINE_TYPES:
                line = _raw_polyline(e)
                if line is None:
                    unsupported[f"{kind} (mesh/polyface)"] += 1
                else:
                    polylines.append(line)
            else:
                unsupported[kind] += 1
        return CadExtraction(
            points=points,
            polylines=polylines,
            unsupported_entities=dict(sorted(unsupported.items())),
        )


def _raw_point(e: DXFGraphic) -> RawPoint:
    kind = e.dxftype()
    text = None
    block = None
    if kind == "POINT":
        loc = e.dxf.location
    elif kind == "CIRCLE":
        loc = e.dxf.center
    else:
        loc = e.dxf.insert
    if kind == "TEXT":
        text = e.dxf.text
    elif kind == "MTEXT":
        text = e.plain_text()
    elif kind == "INSERT":
        block = e.dxf.name
        attribs = [f"{a.dxf.tag}={a.dxf.text}" for a in e.attribs]
        text = "; ".join(attribs) if attribs else None
    return RawPoint(
        xy=(float(loc.x), float(loc.y)),
        z=float(loc.z),
        layer=e.dxf.layer,
        text=text,
        handle=e.dxf.handle,
        entity_type=kind,
        block_name=block,
    )


def _raw_polyline(e: DXFGraphic) -> RawPolyline | None:
    kind = e.dxftype()
    if kind == "LINE":
        s, t = e.dxf.start, e.dxf.end
        zs = [float(s.z), float(t.z)]
        return RawPolyline(
            points=[(float(s.x), float(s.y)), (float(t.x), float(t.y))],
            closed=False,
            elevation=zs[0] if zs[0] == zs[1] else None,
            layer=e.dxf.layer,
            handle=e.dxf.handle,
            entity_type=kind,
            zs=zs,
        )
    if kind == "LWPOLYLINE":
        pts = [(float(x), float(y)) for x, y in e.get_points("xy")]
        return RawPolyline(
            points=pts,
            closed=bool(e.closed),
            elevation=float(e.dxf.elevation),
            layer=e.dxf.layer,
            handle=e.dxf.handle,
            entity_type=kind,
            has_arcs=bool(e.has_arc),
        )
    # POLYLINE: 2D or 3D; meshes and polyface meshes are not survey linework.
    if e.is_poly_face_mesh or e.is_polygon_mesh:
        return None
    verts = list(e.points())
    pts = [(float(v.x), float(v.y)) for v in verts]
    if e.is_3d_polyline:
        zs = [float(v.z) for v in verts]
        elevation = zs[0] if zs and all(z == zs[0] for z in zs) else None
    else:
        zs = []
        elevation = float(e.dxf.elevation.z)
    return RawPolyline(
        points=pts,
        closed=bool(e.is_closed),
        elevation=elevation,
        layer=e.dxf.layer,
        handle=e.dxf.handle,
        entity_type=kind,
        zs=zs,
        has_arcs=any(v.dxf.get("bulge", 0.0) for v in e.vertices),
    )


def _extents(ext: CadExtraction) -> tuple[float, float, float, float] | None:
    xs = [p.xy[0] for p in ext.points] + [x for pl in ext.polylines for x, _ in pl.points]
    ys = [p.xy[1] for p in ext.points] + [y for pl in ext.polylines for _, y in pl.points]
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _geodata_summary(msp: Any, warnings: list[str]) -> tuple[dict[str, object] | None, int | None]:
    try:
        geo = msp.get_geodata()
    except Exception as exc:  # malformed GEODATA must not stop an inspection
        warnings.append(f"GEODATA object could not be read: {exc}")
        return None, None
    if geo is None:
        return None, None
    ctype = geo.dxf.coordinate_type
    summary: dict[str, object] = {
        "coordinate_type": GEODATA_COORDINATE_TYPES.get(ctype, str(ctype)),
        "design_point": _plain(geo.dxf.design_point),
        "reference_point": _plain(geo.dxf.reference_point),
        "north_direction": _plain(geo.dxf.north_direction),
        "horizontal_unit_scale": geo.dxf.horizontal_unit_scale,
        "vertical_unit_scale": geo.dxf.vertical_unit_scale,
        "horizontal_units": geo.dxf.horizontal_units,
        "vertical_units": geo.dxf.vertical_units,
    }
    epsg = None
    try:
        epsg, _axis = geo.get_crs()
    except Exception as exc:  # unknown XML dialects are reported, not guessed
        warnings.append(f"GEODATA coordinate system definition not understood: {exc}")
    summary["declared_epsg"] = epsg
    return summary, epsg
