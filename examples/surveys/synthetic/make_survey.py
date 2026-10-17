"""Generate the SYNTHETIC survey DXF used by tests and the Milestone B demo.

Every number here is fictional and chosen so the expected results can be
checked by hand (see ground_truth.yaml). The drawing does not represent any
real parcel.

Ground truth (drawing in metres, coordinates = E0/N0 + local x/y):

* parcel A(0,0) B(40,0) C(40,30) D(10,40) E(0,30): a 40 x 30 rectangle plus
  a triangle of base 40 and height 10, so area 1200 + 200 = 1400 m²;
* terrain is the plane z = 100 + 0.05 x + 0.1 y: spot heights sample it and
  contours at 101..104 m are its exact level lines, so a TIN built from them
  must reproduce the plane everywhere inside the surveyed hull;
* a road polygon shares edge AB, so the frontage is exactly 40 m;
* deliberately ambiguous entities: a tick mark on the boundary layer, a
  contour with elevation 0, a 3D breakline with varying z on the contour
  layer, a height label with no point, a spot point at z = 0, a text label
  on the road layer, an unmapped layer and an unsupported SPLINE.

Usage: python examples/surveys/synthetic/make_survey.py [out.dxf]
"""

from __future__ import annotations

import sys
from pathlib import Path

import ezdxf

E0, N0 = 500_100.0, 5_400_200.0
EPSG = 25832
PARCEL = [(0.0, 0.0), (40.0, 0.0), (40.0, 30.0), (10.0, 40.0), (0.0, 30.0)]
SPOTS = [
    (0.0, 0.0),
    (40.0, 0.0),
    (40.0, 30.0),
    (10.0, 40.0),
    (0.0, 30.0),
    (20.0, 15.0),
    (30.0, 10.0),
]
SPOT_BLOCK_AT = (10.0, 10.0)
CONTOUR_LEVELS = (101.0, 102.0, 103.0, 104.0)
CONTOUR_XS = (-5.0, 20.0, 45.0)
BUILDING = [(10.0, 10.0), (16.0, 10.0), (16.0, 18.0), (10.0, 18.0)]
ROAD = [(-10.0, -8.0), (50.0, -8.0), (50.0, 0.0), (-10.0, 0.0)]
TREE_AT = (30.0, 25.0)
ACCESS_AT = (20.0, 0.0)

#: Metres per drawing unit, and the matching $INSUNITS code.
UNITS = {"m": (1.0, 6), "mm": (0.001, 4)}

#: The projected-grid GEODATA object declaring an EPSG code, as Civil 3D writes it.
GEODATA_XML = (
    '<?xml version="1.0" encoding="UTF-16" standalone="no" ?>'
    '<Dictionary version="1.0" xmlns="http://www.osgeo.org/mapguide/coordinatesystem">'
    '<ProjectedCoordinateSystem id="ETRS89.UTM-32N"><Name>ETRS89.UTM-32N</Name>'
    "</ProjectedCoordinateSystem>"
    '<Alias id="{epsg}" type="CoordinateSystem"><ObjectId>ETRS89.UTM-32N</ObjectId>'
    "<Namespace>EPSG Code</Namespace></Alias>"
    '<Axis uom="METER"><CoordinateSystemAxis><AxisOrder>1</AxisOrder><AxisName>Easting'
    "</AxisName><AxisAbbreviation>E</AxisAbbreviation><AxisDirection>east</AxisDirection>"
    "</CoordinateSystemAxis><CoordinateSystemAxis><AxisOrder>2</AxisOrder><AxisName>Northing"
    "</AxisName><AxisAbbreviation>N</AxisAbbreviation><AxisDirection>north</AxisDirection>"
    "</CoordinateSystemAxis></Axis></Dictionary>"
)


def plane_z(x: float, y: float) -> float:
    return 100.0 + 0.05 * x + 0.1 * y


def contour_y(level: float, x: float) -> float:
    return 10.0 * (level - 100.0) - 0.5 * x


def build_survey(
    path: Path,
    *,
    unit: str = "m",
    declare_units: bool = True,
    geodata: bool = True,
    extra_boundary: bool = False,
    crossing_contour: bool = False,
    conflicting_spot: bool = False,
) -> Path:
    """Write the synthetic survey. Options create the broken variants used in tests."""
    m_per_unit, insunits = UNITS[unit]
    k = 1.0 / m_per_unit

    def g(x: float, y: float) -> tuple[float, float]:
        return ((E0 + x) * k, (N0 + y) * k)

    def g3(x: float, y: float, z: float) -> tuple[float, float, float]:
        return (*g(x, y), z * k)

    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = insunits if declare_units else 0
    doc.header["$MEASUREMENT"] = 1
    for name in (
        "PARCEL_BOUNDARY",
        "CONTOURS",
        "SPOT_HEIGHTS",
        "ROAD",
        "EXIST_BUILDING",
        "TREES",
        "ACCESS",
        "TEXT_ANNO",
        "MISC_XREF",
    ):
        doc.layers.add(name)
    for block in ("SPOT", "TREE"):
        doc.blocks.new(block).add_circle((0, 0), 0.2 * k)
    msp = doc.modelspace()

    msp.add_lwpolyline(
        [g(x, y) for x, y in PARCEL], close=True, dxfattribs={"layer": "PARCEL_BOUNDARY"}
    )
    msp.add_line(g(20.0, -1.0), g(20.0, 1.0), dxfattribs={"layer": "PARCEL_BOUNDARY"})
    if extra_boundary:
        msp.add_lwpolyline(
            [g(50, 0), g(60, 0), g(60, 10), g(50, 10)],
            close=True,
            dxfattribs={"layer": "PARCEL_BOUNDARY"},
        )

    for level in CONTOUR_LEVELS:
        msp.add_lwpolyline(
            [g(x, contour_y(level, x)) for x in CONTOUR_XS],
            dxfattribs={"layer": "CONTOURS", "elevation": level * k},
        )
    msp.add_lwpolyline([g(0, 45), g(40, 45)], dxfattribs={"layer": "CONTOURS", "elevation": 0.0})
    msp.add_polyline3d(
        [g3(5, 5, 100.5), g3(15, 5, 101.0), g3(25, 6, 101.9)], dxfattribs={"layer": "CONTOURS"}
    )
    if crossing_contour:
        msp.add_lwpolyline(
            [g(0, 0), g(40, 40)], dxfattribs={"layer": "CONTOURS", "elevation": 110.0 * k}
        )

    for x, y in SPOTS:
        msp.add_point(g3(x, y, plane_z(x, y)), dxfattribs={"layer": "SPOT_HEIGHTS"})
    bx, by = SPOT_BLOCK_AT
    msp.add_blockref("SPOT", g3(bx, by, plane_z(bx, by)), dxfattribs={"layer": "SPOT_HEIGHTS"})
    msp.add_text("103.25", dxfattribs={"layer": "SPOT_HEIGHTS", "insert": g(25, 25)})
    msp.add_point(g3(35, 35, 0.0), dxfattribs={"layer": "SPOT_HEIGHTS"})
    if conflicting_spot:
        msp.add_point(g3(20, 15, 99.0), dxfattribs={"layer": "SPOT_HEIGHTS"})

    msp.add_lwpolyline([g(x, y) for x, y in ROAD], close=True, dxfattribs={"layer": "ROAD"})
    msp.add_text("Synthetic Road", dxfattribs={"layer": "ROAD", "insert": g(15, -5)})
    msp.add_lwpolyline(
        [g(x, y) for x, y in BUILDING], close=True, dxfattribs={"layer": "EXIST_BUILDING"}
    )
    msp.add_blockref("TREE", g3(*TREE_AT, 0.0), dxfattribs={"layer": "TREES"})
    msp.add_point(g3(*ACCESS_AT, 0.0), dxfattribs={"layer": "ACCESS"})
    msp.add_text(
        "SYNTHETIC SURVEY - NOT A REAL PARCEL",
        dxfattribs={"layer": "TEXT_ANNO", "insert": g(0, 50)},
    )
    msp.add_line(g(60, 60), g(70, 70), dxfattribs={"layer": "MISC_XREF"})
    msp.add_spline(
        [g3(60, 0, 0), g3(65, 5, 0), g3(70, 0, 0), g3(75, 5, 0)], dxfattribs={"layer": "MISC_XREF"}
    )

    if geodata:
        geo = msp.new_geodata()
        geo.dxf.coordinate_type = 2
        geo.dxf.horizontal_unit_scale = m_per_unit
        geo.dxf.vertical_unit_scale = m_per_unit
        geo.dxf.horizontal_units = insunits
        geo.dxf.vertical_units = insunits
        geo.coordinate_system_definition = GEODATA_XML.format(epsg=EPSG)
    path = Path(path)
    doc.saveas(path)
    return path


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("survey.dxf")
    print(build_survey(target))
