"""Read the generated files back and compare them with the spec.

A drawing is only trusted after its numbers have been measured out of the
file it was written to, not out of the code that wrote it.
"""

from __future__ import annotations

from collections import defaultdict

import ezdxf
from ezdxf import bbox
from shapely.geometry import LineString, box
from shapely.ops import unary_union
import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.validate

from .checks import Finding
from .geometry import LevelGeom
from .model import Design

TOL = 0.5  # mm
TEXT_GAP = 1.0  # mm on paper between any two texts


def _shoelace(coords) -> float:
    s = 0.0
    for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
        s += x0 * y1 - x1 * y0
    return abs(s) / 2


def _texts(msp):
    """Every piece of text on the sheet with its true extents, including the
    text inside dimension blocks."""
    def entry(e, layer):
        b = bbox.extents([e], fast=False)
        if not b.has_data:
            return None
        text = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
        return layer, text, box(b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)

    found = [entry(e, e.dxf.layer) for e in msp.query("TEXT MTEXT")]
    for dim in msp.query("DIMENSION"):
        found += [entry(v, dim.dxf.layer) for v in dim.virtual_entities() if v.dxftype() in ("TEXT", "MTEXT")]
    return [f for f in found if f is not None]


def verify_text(path: str, lg: LevelGeom, scale: int) -> list[Finding]:
    """No two texts may overlap, and none may come closer than
    TEXT_GAP mm on paper; room labels must sit inside their room."""
    out: list[Finding] = []
    texts = _texts(ezdxf.readfile(path).modelspace())
    pad = TEXT_GAP * scale / 2
    for i, (la, ta, a) in enumerate(texts):
        for lb, tb, b in texts[i + 1 :]:
            if a.intersects(b):
                out.append(Finding("DXF_TEXT_OVERLAP", "error", f"{ta!r}/{tb!r}", f"texts on {la} and {lb} overlap"))
            elif a.buffer(pad).intersects(b.buffer(pad)):
                gap = a.distance(b) / scale
                out.append(Finding("DXF_TEXT_CROWDED", "warning", f"{ta!r}/{tb!r}", f"only {gap:.1f} mm apart on paper (< {TEXT_GAP} mm)"))
    msp = ezdxf.readfile(path).modelspace()
    lines = []
    for idx, dim in enumerate(msp.query("DIMENSION")):
        for v in dim.virtual_entities():
            if v.dxftype() == "LINE":
                lines.append((idx, LineString([(v.dxf.start.x, v.dxf.start.y), (v.dxf.end.x, v.dxf.end.y)])))
    for idx, dim in enumerate(msp.query("DIMENSION")):
        for v in dim.virtual_entities():
            if v.dxftype() not in ("TEXT", "MTEXT"):
                continue
            b = bbox.extents([v], fast=False)
            tb = box(b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)
            text = v.plain_text() if v.dxftype() == "MTEXT" else v.dxf.text
            if any(j != idx and tb.intersects(ln) for j, ln in lines):
                out.append(Finding("DIM_TEXT_CROSSED", "error", repr(text), "a line of another dimension runs through this dimension text"))
    rooms = unary_union([rg.outline.buffer(-0.5 * scale) for rg in lg.rooms.values() if rg.outline is not None] + [b.buffer(-0.5 * scale) for b in lg.balconies.values()])
    walls = lg.walls_union
    for layer, text, b in texts:
        if layer == "A-AREA-IDEN" and not rooms.contains(b):
            out.append(Finding("LABEL_OUTSIDE_ROOM", "warning", repr(text), "room label crosses a wall or leaves its room; the room may be too small to label at this scale"))
        elif layer == "A-ANNO-DIMS" and b.intersects(walls):
            out.append(Finding("DIM_TEXT_ON_WALL", "error", repr(text), "dimension text sits on a wall"))
    return out


def verify_dxf(path: str, lg: LevelGeom) -> list[Finding]:
    out: list[Finding] = []
    doc = ezdxf.readfile(path)
    if doc.header.get("$INSUNITS") != 4:
        out.append(Finding("DXF_UNITS", "error", path, "$INSUNITS is not 4 (millimetres)"))
    chains: dict[tuple, list[float]] = defaultdict(list)
    for dim in doc.modelspace().query("DIMENSION"):
        m = dim.get_measurement()
        d = dim.dxf
        key = (round(d.angle, 3), round(d.defpoint.y if round(d.angle) == 0 else d.defpoint.x, 1))
        chains[key].append(m)
    if not chains:
        out.append(Finding("DXF_NO_DIMS", "warning", path, "no dimensions found"))
        return out
    minx, miny, maxx, maxy = lg.footprint.bounds
    by_axis: dict[float, list[list[float]]] = defaultdict(list)
    for (angle, _), values in chains.items():
        by_axis[angle].append(values)
    for angle, groups in by_axis.items():
        overall = maxx - minx if round(angle) == 0 else maxy - miny
        totals = sorted(sum(v) for v in groups)
        for t in totals:
            if abs(t - overall) > TOL:
                out.append(Finding("DXF_CHAIN_OPEN", "error", path, f"a dimension chain at {angle}° sums to {t:.2f} mm, footprint is {overall:.2f} mm"))
    return out


def verify_ifc(path: str, design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    model = ifcopenshell.open(path)
    walls = {w.Name for w in model.by_type("IfcWall")}
    if walls != {w.id for w in design.walls}:
        out.append(Finding("IFC_WALLS", "error", path, f"wall ids differ: {sorted(walls ^ {w.id for w in design.walls})}"))
    expected = {(r.id): rg.area_mm2 for lg in geo.values() for r_id, rg in lg.rooms.items() for r in [rg.room] if rg.outline is not None}
    for space in model.by_type("IfcSpace"):
        rep = space.Representation.Representations[0].Items[0]
        coords = [p.Coordinates for p in rep.SweptArea.OuterCurve.Points]
        got = _shoelace(coords)
        want = expected.get(space.Name)
        if want is None:
            out.append(Finding("IFC_SPACE_UNKNOWN", "error", space.Name, "space not in the spec"))
        elif abs(got - want) > 1.0 and not geo_has_islands(geo, space.Name):
            out.append(Finding("IFC_SPACE_AREA", "error", space.Name, f"IFC area {got / 1e6:.4f} m² vs spec {want / 1e6:.4f} m²"))
        if want is not None:
            qto = ifcopenshell.util.element.get_pset(space, "Qto_SpaceBaseQuantities") or {}
            net = qto.get("NetFloorArea")
            if net is None or abs(net - want / 1e6) > 1e-4:
                out.append(Finding("IFC_SPACE_QTO", "error", space.Name, f"NetFloorArea {net} vs spec {want / 1e6:.4f} m²"))
    slabs = sorted(s.Name for s in model.by_type("IfcSlab"))
    if slabs != sorted(b.id for b in design.balconies):
        out.append(Finding("IFC_BALCONIES", "error", path, f"balcony slabs {slabs} vs spec {sorted(b.id for b in design.balconies)}"))
    n_open = len(model.by_type("IfcOpeningElement"))
    if n_open != len(design.openings):
        out.append(Finding("IFC_OPENINGS", "error", path, f"{n_open} openings in IFC, {len(design.openings)} in spec"))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, logger, express_rules=True)
    for st in logger.statements[:20]:
        out.append(Finding("IFC_SCHEMA", "error", path, str(st.get("message", st))[:300]))
    ids = [e.GlobalId for e in model.by_type("IfcRoot")]
    if len(ids) != len(set(ids)):
        out.append(Finding("IFC_GUID_DUPLICATE", "error", path, "GlobalIds are not unique"))
    for storey in model.by_type("IfcBuildingStorey"):
        lv = next((l for l in design.levels if l.name == storey.Name), None)
        if lv is None or abs(storey.Elevation - lv.ffl) > TOL:
            out.append(Finding("IFC_STOREY", "error", storey.Name, "storey elevation does not match the spec"))
    return out


def geo_has_islands(geo: dict[str, LevelGeom], room_id: str) -> bool:
    for lg in geo.values():
        rg = lg.rooms.get(room_id)
        if rg is not None and rg.outline is not None:
            return len(rg.outline.interiors) > 0
    return False
