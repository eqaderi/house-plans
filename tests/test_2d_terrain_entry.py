"""S10-13: solve road access and Z together, with synthetic analytical terrain."""

from types import SimpleNamespace

import pytest
from ortools.sat.python import cp_model

from house_ai.domain.base import EXTERIOR
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.program import SpaceFunction as S
from house_ai.domain.proposal import ConceptProposal
from house_ai.generation.frame import Ground, design_frame
from house_ai.generation.terrain_levels import placement_level_variables
from house_ai.storage.hashing import load_document

from .conftest import REPO
from .test_plan_generation import HILLSIDE, _generate, _load


@pytest.mark.parametrize("sign", [-1, 1])
def test_2d_levels_follow_analytical_road_terrain_in_the_solve(sign):
    # z = 12 + sign * (0.5*u + 0.4*v). Entry center = 3.7 m,
    # front = 0.1 m, terrain sample 0.5 m roadward = -0.4 m.
    ground = SimpleNamespace(surface=True, at=lambda u, v: 12 + sign * (0.5 * u + 0.4 * v))
    md = cp_model.CpModel()
    x, xe = md.NewIntVar(0, 100, "x"), md.NewIntVar(0, 100, "xe")
    md.Add(x == 23)
    md.Add(xe == 51)
    z = placement_level_variables(md, ["lv-entry", "lv-lower", "lv-upper"], x, xe, 1, 100, ground)
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    assert solver.Solve(md) == cp_model.OPTIMAL
    assert solver.Value(z["lv-entry"]) / 100 == pytest.approx(12 + sign * 1.69)
    assert solver.Value(z["lv-lower"]) == solver.Value(z["lv-entry"]) - 300
    assert solver.Value(z["lv-upper"]) == solver.Value(z["lv-entry"]) + 300


def test_demo_proposal_enters_at_road_with_contiguous_open_plan():
    site, program = _load(HILLSIDE)
    proposal = ConceptProposal.model_validate(
        load_document(REPO / "examples/readiness/proposal.yaml")
    )
    (candidate,) = _generate(site, program, proposal=proposal)
    assert candidate.plan is not None, candidate.reason
    model = candidate.plan.model
    assert not errors(check_model(model, site, program))
    frame = design_frame(site)
    entry = next(s for s in model.spaces if s.function is S.ENTRY)
    door = next(
        o for o in model.openings if o.is_passable and set(o.connects) == {entry.id, EXTERIOR}
    )
    wall = model.wall(door.host_wall_id)
    a, b = frame.to_design(wall.start), frame.to_design(wall.end)
    assert a[1] == pytest.approx(1.1, abs=1e-6)
    assert b[1] == pytest.approx(1.1, abs=1e-6)
    u = (a[0] + b[0]) / 2
    expected = Ground(site, frame).at(u, 0.6)
    assert model.level(entry.level_id).elevation_m == pytest.approx(round(expected, 2), abs=0.01)
    assert 11.4 <= model.level(entry.level_id).elevation_m <= 12.0
    (composite,) = model.composite_spaces
    assert len(composite.space_ids) == 3
    assert composite.boundary.area_m2 == pytest.approx(
        sum(model.space(s).area_m2 for s in composite.space_ids), abs=1e-4
    )
    assert not any(i.id.startswith("iss-open-plan-split") for i in model.issues)


def test_rotated_open_plan_keeps_shared_edges_at_t_junctions():
    area = 20.0
    import math

    from house_ai.generation.assemble2d import assemble_2d
    from house_ai.generation.frame import DesignFrame
    from house_ai.generation.solver2d import PlacedRoom2D, Solution2D

    from .conftest import AGENT

    site, program = _load(HILLSIDE)
    angle = math.radians(1)
    frame = DesignFrame(
        (0.123, 0.456),
        (math.cos(angle), math.sin(angle)),
        (-math.sin(angle), math.cos(angle)),
        "synthetic rotation",
        None,
        None,
    )
    rooms = [
        PlacedRoom2D(
            "sp-living", "Living", S.LIVING, "lv-entry", 0, 0, 30, 40, "pi-living", "z-day"
        ),
        PlacedRoom2D(
            "sp-dining", "Dining", S.DINING, "lv-entry", 30, 0, 50, 20, "pi-dining", "z-day"
        ),
        PlacedRoom2D(
            "sp-kitchen", "Kitchen", S.KITCHEN, "lv-entry", 30, 20, 50, 40, "pi-kitchen", "z-day"
        ),
    ]
    sol = Solution2D("FEASIBLE", 0, rooms, [], ["lv-entry"], 0, 0, 0, "test", "open_plan", 0)
    model = assemble_2d(sol, site, frame, Ground(site, frame), program, AGENT)
    (group,) = model.composite_spaces
    assert group.boundary.area_m2 == pytest.approx(area, abs=1e-5)
    assert not [f for f in check_model(model) if f.code == "invalid_composite_space"]
    from shapely.ops import unary_union

    union = unary_union([s.boundary.to_shapely() for s in model.spaces])
    assert union.geom_type == "Polygon"
    assert union.area == pytest.approx(area, abs=1e-5)
