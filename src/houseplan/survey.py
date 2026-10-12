"""First look at a survey DXF: units, layers, extents, closed outlines and
measured heights. Read-only; everything it prints comes from the file."""

from __future__ import annotations

from collections import Counter

import ezdxf
from ezdxf import bbox
from shapely.geometry import Polygon

UNITS = {0: "unitless", 1: "inches", 2: "feet", 4: "millimetres", 5: "centimetres", 6: "metres"}


def _zs(e) -> list[float]:
    t = e.dxftype()
    if t == "POINT":
        return [e.dxf.location.z]
    if t == "INSERT":
        return [e.dxf.insert.z]
    if t in ("TEXT", "MTEXT"):
        return [e.dxf.insert.z]
    if t == "LINE":
        return [e.dxf.start.z, e.dxf.end.z]
    if t == "LWPOLYLINE":
        return [e.dxf.elevation]
    if t == "POLYLINE":
        return [v.dxf.location.z for v in e.vertices]
    if t == "3DFACE":
        return [e.dxf.vtx0.z, e.dxf.vtx1.z, e.dxf.vtx2.z, e.dxf.vtx3.z]
    return []


def _outline(e) -> Polygon | None:
    t = e.dxftype()
    if t == "LWPOLYLINE" and e.closed:
        pts = [(x, y) for x, y, *_ in e.get_points()]
    elif t == "POLYLINE" and e.is_closed:
        pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
    else:
        return None
    if len(pts) < 3:
        return None
    p = Polygon(pts)
    return p if p.is_valid and p.area > 0 else None


def survey(path: str, top: int = 10) -> int:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    units = doc.header.get("$INSUNITS", 0)
    print(f"file      {path}")
    print(f"units     $INSUNITS={units} ({UNITS.get(units, 'other')}) — confirm with one known distance before trusting it")
    ext = bbox.extents(msp, fast=True)
    if ext.has_data:
        print(f"extents   ({ext.extmin.x:.3f}, {ext.extmin.y:.3f}) .. ({ext.extmax.x:.3f}, {ext.extmax.y:.3f})  size {ext.size.x:.3f} x {ext.size.y:.3f}")

    per_layer: dict[str, Counter] = {}
    zs: dict[str, list[float]] = {}
    outlines: list[tuple[float, str, Polygon]] = []
    for e in msp:
        layer = e.dxf.layer
        per_layer.setdefault(layer, Counter())[e.dxftype()] += 1
        z = [v for v in _zs(e) if v != 0.0]
        if z:
            zs.setdefault(layer, []).extend(z)
        o = _outline(e)
        if o is not None:
            outlines.append((o.area, layer, o))

    print("\nlayers")
    for layer in sorted(per_layer):
        kinds = ", ".join(f"{k}×{n}" for k, n in per_layer[layer].most_common())
        print(f"  {layer:30} {kinds}")

    print("\nnon-zero heights by layer (measured entities only; contours are lines, not measurements)")
    if not zs:
        print("  none — heights may be in text labels or blocks attributes; inspect those layers")
    for layer, values in sorted(zs.items()):
        print(f"  {layer:30} n={len(values):6}  min={min(values):.3f}  max={max(values):.3f}")

    print(f"\nlargest closed outlines (candidate plot / building boundaries), area in drawing units²")
    for area, layer, o in sorted(outlines, key=lambda t: -t[0])[:top]:
        minx, miny, maxx, maxy = o.bounds
        print(f"  {area:16.3f}  {layer:24} {len(o.exterior.coords) - 1:4} vertices  bbox ({minx:.2f}, {miny:.2f}) .. ({maxx:.2f}, {maxy:.2f})")
    return 0
