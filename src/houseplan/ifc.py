"""IFC4 building model generated from the design spec, in millimetres.

The spec stays the source of truth; this file is regenerated from it on every
build and is never edited by hand. Walls are extruded from the same jointed
outlines the plan uses, so plan and model cannot disagree.
"""

from __future__ import annotations

import numpy as np
import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit

from .geometry import LevelGeom, faces_of, frame_of
from .model import Design, OpeningKind, WallKind


def _placement(model, product, x=0.0, y=0.0, z=0.0, ux=1.0, uy=0.0):
    m = np.eye(4)
    m[:3, 0] = (ux, uy, 0)
    m[:3, 1] = (-uy, ux, 0)
    m[:3, 3] = (x, y, z)
    ifcopenshell.api.geometry.edit_object_placement(model, product=product, matrix=m, is_si=False)


def _extrusion(model, body, coords, depth):
    pts = [model.createIfcCartesianPoint((float(x), float(y))) for x, y in coords]
    if pts[0].Coordinates != pts[-1].Coordinates:
        pts.append(pts[0])
    profile = model.createIfcArbitraryClosedProfileDef("AREA", None, model.createIfcPolyline(pts))
    solid = model.createIfcExtrudedAreaSolid(profile, None, model.createIfcDirection((0.0, 0.0, 1.0)), float(depth))
    return model.createIfcShapeRepresentation(body, "Body", "SweptSolid", [solid])


def build_ifc(design: Design, geo: dict[str, LevelGeom]):
    model = ifcopenshell.api.project.create_file(version="IFC4")
    project = ifcopenshell.api.root.create_entity(model, ifc_class="IfcProject", name=design.project.name)
    length = ifcopenshell.api.unit.add_si_unit(model, unit_type="LENGTHUNIT", prefix="MILLI")
    area = ifcopenshell.api.unit.add_si_unit(model, unit_type="AREAUNIT")
    volume = ifcopenshell.api.unit.add_si_unit(model, unit_type="VOLUMEUNIT")
    ifcopenshell.api.unit.assign_unit(model, units=[length, area, volume])
    ctx = ifcopenshell.api.context.add_context(model, context_type="Model")
    body = ifcopenshell.api.context.add_context(model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)

    site = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuilding", name=design.project.name)
    ifcopenshell.api.aggregate.assign_object(model, relating_object=project, products=[site])
    ifcopenshell.api.aggregate.assign_object(model, relating_object=site, products=[building])
    if design.project.datum.survey_z_mm is not None:
        building.ElevationOfRefHeight = float(design.project.datum.survey_z_mm)

    for level in sorted(design.levels, key=lambda l: l.ffl):
        lg = geo[level.id]
        storey = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuildingStorey", name=level.name)
        storey.Elevation = float(level.ffl)
        ifcopenshell.api.aggregate.assign_object(model, relating_object=building, products=[storey])
        _placement(model, storey, z=level.ffl)
        ifcopenshell.api.pset.edit_pset(model, pset=ifcopenshell.api.pset.add_pset(model, product=storey, name="Pset_BuildingStoreyCommon"), properties={
            "EntranceLevel": level.ffl == 0,
            "AboveGround": level.ffl >= 0,
        })
        contained = []

        for wg in lg.walls.values():
            w = wg.wall
            wall = ifcopenshell.api.root.create_entity(model, ifc_class="IfcWall", name=w.id)
            _placement(model, wall, z=level.ffl)
            ifcopenshell.api.geometry.assign_representation(model, product=wall, representation=_extrusion(model, body, wg.body.exterior.coords, level.floor_to_floor - level.slab))
            ifcopenshell.api.pset.edit_pset(model, pset=ifcopenshell.api.pset.add_pset(model, product=wall, name="Pset_WallCommon"), properties={
                "IsExternal": w.kind is WallKind.exterior,
                "LoadBearing": w.loadbearing,
                "Reference": w.id,
            })
            contained.append(wall)
            for og in (g for g in lg.openings.values() if g.opening.wall == w.id):
                o = og.opening
                f = frame_of(w)
                a, b = faces_of(w)
                sx, sy = f.at(o.offset, a - 10)
                opening = ifcopenshell.api.root.create_entity(model, ifc_class="IfcOpeningElement", name=o.id)
                _placement(model, opening, sx, sy, level.ffl + o.sill, f.ux, f.uy)
                rect = [(0, 0), (o.width, 0), (o.width, b - a + 20), (0, b - a + 20)]
                ifcopenshell.api.geometry.assign_representation(model, product=opening, representation=_extrusion(model, body, rect, o.height))
                ifcopenshell.api.feature.add_feature(model, feature=opening, element=wall)
                if o.kind is OpeningKind.opening:
                    continue
                cls = "IfcDoor" if o.kind is OpeningKind.door else "IfcWindow"
                fill = ifcopenshell.api.root.create_entity(model, ifc_class=cls, name=o.id)
                fill.OverallWidth = float(o.width)
                fill.OverallHeight = float(o.height)
                _placement(model, fill, sx, sy, level.ffl + o.sill, f.ux, f.uy)
                ifcopenshell.api.feature.add_filling(model, opening=opening, element=fill)
                pset = "Pset_DoorCommon" if cls == "IfcDoor" else "Pset_WindowCommon"
                ifcopenshell.api.pset.edit_pset(model, pset=ifcopenshell.api.pset.add_pset(model, product=fill, name=pset), properties={
                    "IsExternal": w.kind is WallKind.exterior,
                    "Reference": o.id,
                })
                contained.append(fill)

        for rg in lg.rooms.values():
            if rg.outline is None:
                continue
            space = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSpace", name=rg.room.id)
            space.LongName = rg.room.name
            if rg.room.name_fa:
                space.Description = rg.room.name_fa
            _placement(model, space, z=level.ffl)
            ifcopenshell.api.geometry.assign_representation(model, product=space, representation=_extrusion(model, body, rg.outline.exterior.coords, level.clear_height))
            ifcopenshell.api.pset.edit_pset(model, pset=ifcopenshell.api.pset.add_pset(model, product=space, name="Pset_SpaceCommon"), properties={
                "Reference": rg.room.use.value,
                "IsExternal": False,
            })
            ifcopenshell.api.pset.edit_qto(model, qto=ifcopenshell.api.pset.add_qto(model, product=space, name="Qto_SpaceBaseQuantities"), properties={
                "NetFloorArea": round(rg.area_mm2 / 1e6, 6),
                "NetPerimeter": round(rg.outline.exterior.length, 3),
                "Height": float(level.clear_height),
            })
            ifcopenshell.api.aggregate.assign_object(model, relating_object=storey, products=[space])

        if contained:
            ifcopenshell.api.spatial.assign_container(model, relating_structure=storey, products=contained)
    return model
