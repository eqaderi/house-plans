"""Generate analytical, synthetic HouseModels and a deliberately narrow ArchLang view.

Run with the project Python. No private project data or npm dependency is loaded here.
The fixture is a fabricated 7 x 4 m two-room diagram, not a design proposal.
"""

from __future__ import annotations

import json
from pathlib import Path

from house_ai.domain.geometry import Polygon2D
from house_ai.domain.integrity import check_model
from house_ai.domain.model import Fixture, HouseModel, Level, Opening, Space, Wall

OUT = Path(__file__).parent / "fixtures"


def fixture() -> HouseModel:
    """Analytical rectangles with a shared centerline and two explicit door edges."""
    wall_data = [
        ("south", (0, 0), (7, 0), "exterior", 0.2),
        ("east", (7, 0), (7, 4), "exterior", 0.2),
        ("north", (7, 4), (0, 4), "exterior", 0.2),
        ("west", (0, 4), (0, 0), "exterior", 0.2),
        ("partition", (4, 0), (4, 4), "interior", 0.1),
    ]
    return HouseModel(
        id="synthetic-archlang",
        name="Synthetic two room diagnostic",
        coordinate_system_id="synthetic-local",
        levels=[
            Level(
                id="ground",
                name="Ground",
                elevation_m=0,
                floor_to_floor_m=3,
            )
        ],
        spaces=[
            Space(
                id="living",
                name="Living",
                function="living",
                level_id="ground",
                boundary=Polygon2D.rectangle(0, 0, 4, 4),
            ),
            Space(
                id="bedroom",
                name="Bedroom",
                function="bedroom",
                level_id="ground",
                boundary=Polygon2D.rectangle(4, 0, 7, 4),
            ),
        ],
        walls=[
            Wall(id=wid, level_id="ground", start=a, end=b, kind=kind, thickness_m=t, height_m=3)
            for wid, a, b, kind, t in wall_data
        ],
        openings=[
            Opening(
                id="front",
                kind="door",
                host_wall_id="south",
                offset_m=1.5,
                width_m=1,
                height_m=2.1,
                connects=("exterior", "living"),
                opens_into="living",
                operation="swing_left",
            ),
            Opening(
                id="beddoor",
                kind="door",
                host_wall_id="partition",
                offset_m=1.55,
                width_m=0.9,
                height_m=2.1,
                connects=("living", "bedroom"),
                opens_into="bedroom",
                operation="swing_left",
            ),
            Opening(
                id="livingwin",
                kind="window",
                host_wall_id="west",
                offset_m=1.3,
                width_m=1.4,
                sill_m=0.9,
                height_m=1.2,
                connects=("exterior", "living"),
                operation="fixed",
            ),
            Opening(
                id="bedwin",
                kind="window",
                host_wall_id="east",
                offset_m=1.4,
                width_m=1.2,
                sill_m=0.9,
                height_m=1.2,
                connects=("bedroom", "exterior"),
                operation="fixed",
            ),
        ],
    )


def export(model: HouseModel) -> str:  # noqa: C901
    """Restricted diagnostic adapter; refuse geometry/semantics not covered by this trial.

    HouseModel y-up metres -> screen y-down mm by (x, y) -> (1000*x, -1000*y).
    Reflection preserves all distances; source y may be negative, which ArchLang accepts.
    ArchLang's hosted opening position is its midpoint, HouseModel's is its near edge.
    """
    if len(model.levels) != 1 or model.levels[0].elevation_m != 0:
        raise ValueError("Trial adapter only supports one level at elevation zero")
    if any(
        (
            model.slabs,
            model.ceilings,
            model.stairs,
            model.zones,
            model.relationships,
            model.materials,
            model.assumptions,
            model.issues,
        )
    ):
        raise ValueError("Trial adapter refuses unsupported semantic collections")

    def mm(value: float) -> str:
        return f"{value * 1000:.9g}"

    def pt(point: tuple[float, float]) -> str:
        return f"({mm(point[0])},{mm(-point[1])})"

    lines = [f"plan {json.dumps(model.name)} {{", "  units mm", "  grid 1", "  height 3000"]
    for space in model.spaces:
        if space.boundary.holes or space.function.value not in {"living", "bedroom"}:
            raise ValueError("Unsupported room shape/function")
        points = " ".join(pt(point) for point in space.boundary.outer)
        lines.append(
            f"  room id={space.id} polygon {points} "
            f"label {json.dumps(space.name)} uses {space.function.value}"
        )
    for wall in model.walls:
        if wall.kind.value not in {"exterior", "interior"} or wall.base_offset_m != 0:
            raise ValueError("Unsupported wall kind/base offset")
        category = "partition" if wall.kind.value == "interior" else "exterior"
        lines.append(
            f"  wall id={wall.id} {category} thickness {mm(wall.thickness_m)} "
            f"height {mm(wall.height_m)} {{ {pt(wall.start)} {pt(wall.end)} }}"
        )
    for opening in model.openings:
        position = mm(opening.offset_m + opening.width_m / 2)
        text = (
            f"  {opening.kind.value} id={opening.id} on {opening.host_wall_id} "
            f"at {position} width {mm(opening.width_m)}"
        )
        if opening.kind.value == "door":
            if opening.operation.value != "swing_left" or opening.opens_into is None:
                raise ValueError("Trial supports only explicitly directed swing_left doors")
            # Reflection flips handedness; hinge at host's start remains invariant.
            text += f" hinge near start swing into {opening.opens_into}"
        elif opening.kind.value == "window":
            if opening.operation.value != "fixed":
                raise ValueError("Window operation is not represented in ArchLang")
            text += f" sill {mm(opening.sill_m)}"
        text += f" head {mm(opening.sill_m + opening.height_m)}"
        lines.append(text)
    for piece in model.fixtures:
        if piece.rotation_deg != 0 or piece.fixture_type != "sofa":
            raise ValueError("Only an unrotated sofa is covered in this experiment")
        # Furniture uses top-left, whereas canonical fixtures use center coordinates.
        corner = (piece.position[0] - piece.width_m / 2, piece.position[1] + piece.depth_m / 2)
        lines.append(
            f"  furniture id={piece.id} sofa at {pt(corner)} "
            f"size {mm(piece.width_m)}x{mm(piece.depth_m)} in {piece.space_id}"
        )
    return "\n".join([*lines, "}", ""])


def main() -> None:
    OUT.mkdir(exist_ok=True)
    baseline = fixture()
    assert not check_model(baseline), check_model(baseline)
    cases = {"clean": baseline}
    for name, removed in [("unreachable", "beddoor"), ("windowless", "bedwin")]:
        variant = baseline.model_copy(deep=True)
        variant.openings = [op for op in variant.openings if op.id != removed]
        cases[name] = variant
    blocked = baseline.model_copy(deep=True)
    blocked.fixtures = [
        Fixture(
            id="blocker",
            fixture_type="sofa",
            space_id="living",
            position=(2, 0.6),
            width_m=1.6,
            depth_m=0.8,
        )
    ]
    cases["blocked-entry"] = blocked
    canonical = {}
    for name, model in cases.items():
        (OUT / f"{name}.json").write_text(model.model_dump_json(indent=2) + "\n")
        (OUT / f"{name}.arch").write_text(export(model))
        canonical[name] = [finding.model_dump(mode="json") for finding in check_model(model)]
    (OUT / "canonical-findings.json").write_text(json.dumps(canonical, indent=2) + "\n")


if __name__ == "__main__":
    main()
