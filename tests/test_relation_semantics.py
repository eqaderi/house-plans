"""Tests for shared relation semantics between solver and evaluator (Stage S7).

Verifies ADR 0020, S7-01, S7-02, S7-03, S7-04, and S7-05.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path

from house_ai.constants.relations import SHARED_WALL_MIN_M
from house_ai.constraints.compiler import compile_constraints
from house_ai.domain.base import EXTERIOR
from house_ai.domain.brief import DesignBrief
from house_ai.domain.codepack import CodePack
from house_ai.domain.model import HouseModel
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import (
    SpaceFunction,
    SpaceProgram,
    SpaceRelationship,
    SpaceRelationshipKind,
    Strength,
)
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, ArtifactRef
from house_ai.domain.relations import (
    is_relation_satisfied,
    shared_wall_length,
)
from house_ai.domain.site import Site
from house_ai.evaluation.explain import explanation_markdown, soft_objectives_report
from house_ai.evaluation.report import evaluate_plan
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.storage.hashing import content_hash, load_document

Kind = SpaceRelationshipKind

REPO = Path(__file__).resolve().parents[1]
HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"
BUNGALOW = REPO / "examples" / "projects" / "synthetic-bungalow"
WHEN = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
TOOL = Actor(kind=ActorKind.SYSTEM, id="house-ai")


def _ref(plan: PlanVersion) -> ArtifactRef:
    return ArtifactRef(
        kind=ArtifactKind.PLAN,
        id=plan.option_id,
        version=1,
        sha256=content_hash(plan),
    )


def _load(folder: Path) -> tuple[Site, SpaceProgram]:
    site = Site.model_validate(load_document(folder / "site.yaml"))
    program = SpaceProgram.model_validate(load_document(folder / "space_program.yaml"))
    return site, program


def _build_simple_two_room_model(
    *,
    wall_length: float = 2.0,
    has_door: bool = False,
    is_exterior: bool = False,
) -> HouseModel:
    """Build a deterministic two-space model on level l0.

    Space 'sp-a' is at [0, 0] to [4, 3].
    Space 'sp-b' shares a wall of length wall_length along y=3, from x=0 to x=wall_length.
    If is_exterior is True, sp-b is not included and sp-a faces exterior.
    """
    spaces = [
        {
            "id": "sp-a",
            "name": "Room A",
            "function": "living",
            "level_id": "l0",
            "boundary": {"outer": [[0, 0], [4, 0], [4, 3], [0, 3]]},
        }
    ]
    walls = [
        {
            "id": "w-ext-a",
            "level_id": "l0",
            "start": [0, 0],
            "end": [4, 0],
            "thickness_m": 0.3,
            "height_m": 2.8,
            "kind": "exterior",
        }
    ]
    openings = []

    if not is_exterior:
        spaces.append(
            {
                "id": "sp-b",
                "name": "Room B",
                "function": "dining",
                "level_id": "l0",
                "boundary": {
                    "outer": [
                        [0, 3],
                        [wall_length, 3],
                        [wall_length, 6],
                        [0, 6],
                    ]
                },
            }
        )
        walls.append(
            {
                "id": "w-shared",
                "level_id": "l0",
                "start": [0, 3],
                "end": [wall_length, 3],
                "thickness_m": 0.15,
                "height_m": 2.8,
                "kind": "interior",
            }
        )
        if has_door:
            openings.append(
                {
                    "id": "d-ab",
                    "host_wall_id": "w-shared",
                    "kind": "door",
                    "offset_m": 0.2,
                    "width_m": 0.8,
                    "height_m": 2.1,
                    "connects": ["sp-a", "sp-b"],
                }
            )
    else:
        if has_door:
            openings.append(
                {
                    "id": "d-front",
                    "host_wall_id": "w-ext-a",
                    "kind": "door",
                    "offset_m": 1.0,
                    "width_m": 1.0,
                    "height_m": 2.1,
                    "connects": ["sp-a", EXTERIOR],
                }
            )

    doc = {
        "id": "test-model",
        "name": "Test two-room model",
        "coordinate_system_id": "local",
        "levels": [{"id": "l0", "name": "Ground", "elevation_m": 0.0}],
        "spaces": spaces,
        "walls": walls,
        "openings": openings,
    }
    return HouseModel.model_validate(doc)


# --- S7-01: Shared relation semantics


def test_relation_semantics_adr_0020_exists_and_covers_requirements():
    """Kept as a documentation contract, not behaviour: ADR 0020 is the shared definition
    the solver and evaluator cite, so every relation kind the code accepts must be defined
    there. Taken from the enum, a new kind without its ADR definition fails here."""
    adr_path = REPO / "docs" / "adr" / "0020-relation-semantics-between-solver-and-evaluator.md"
    assert adr_path.exists(), "ADR 0020 must exist"
    text = adr_path.read_text(encoding="utf-8")
    for keyword in (*(k.name for k in SpaceRelationshipKind), "hall", "EXTERIOR"):
        assert keyword in text, f"ADR 0020 must define {keyword}"


def test_adjacent_semantics_thresholds():
    # Sharing 1.5m >= SHARED_WALL_MIN_M (0.9m) -> ADJACENT satisfied
    m_touch = _build_simple_two_room_model(wall_length=1.5, has_door=False)
    graph = {"sp-a": set(), "sp-b": set()}
    ok, method = is_relation_satisfied(Kind.ADJACENT, m_touch, graph, ["sp-a"], ["sp-b"])
    assert ok is True
    assert method == "shared_boundary"

    # Sharing 0.5m < SHARED_WALL_MIN_M (0.9m) -> ADJACENT not satisfied
    m_narrow = _build_simple_two_room_model(wall_length=0.5, has_door=False)
    ok_narrow, _ = is_relation_satisfied(
        SpaceRelationshipKind.ADJACENT, m_narrow, graph, ["sp-a"], ["sp-b"]
    )
    assert ok_narrow is False

    # Exterior adjacency: sp-a has 4.0m exterior wall >= 1.0m
    m_ext = _build_simple_two_room_model(is_exterior=True)
    ok_ext, _ = is_relation_satisfied(Kind.ADJACENT, m_ext, graph, ["sp-a"], [EXTERIOR])
    assert ok_ext is True


def test_connected_semantics():
    # Direct door connects sp-a and sp-b
    m_door = _build_simple_two_room_model(wall_length=2.0, has_door=True)
    graph = {"sp-a": {"sp-b"}, "sp-b": {"sp-a"}}
    ok, method = is_relation_satisfied(Kind.CONNECTED, m_door, graph, ["sp-a"], ["sp-b"])
    assert ok is True
    assert method == "graph_analysis"

    # Touching but no door -> CONNECTED is False
    m_no_door = _build_simple_two_room_model(wall_length=2.0, has_door=False)
    graph_no = {"sp-a": set(), "sp-b": set()}
    ok_no, _ = is_relation_satisfied(
        SpaceRelationshipKind.CONNECTED, m_no_door, graph_no, ["sp-a"], ["sp-b"]
    )
    assert ok_no is False

    # Exterior door connects to EXTERIOR
    m_ext_door = _build_simple_two_room_model(has_door=True, is_exterior=True)
    graph_ext = {"sp-a": {EXTERIOR}, EXTERIOR: {"sp-a"}}
    ok_ext, _ = is_relation_satisfied(
        SpaceRelationshipKind.CONNECTED, m_ext_door, graph_ext, ["sp-a"], [EXTERIOR]
    )
    assert ok_ext is True


def test_near_semantics_hops():
    # 2 hops: sp-a -> sp-hall -> sp-b
    graph_2 = {"sp-a": {"sp-hall"}, "sp-hall": {"sp-a", "sp-b"}, "sp-b": {"sp-hall"}}
    m = _build_simple_two_room_model(wall_length=2.0)
    ok, method = is_relation_satisfied(Kind.NEAR, m, graph_2, ["sp-a"], ["sp-b"])
    assert ok is True
    assert method == "graph_analysis"

    # 3 hops: sp-a -> h1 -> h2 -> sp-b (> NEAR_MAX_HOPS 2)
    graph_3 = {
        "sp-a": {"h1"},
        "h1": {"sp-a", "h2"},
        "h2": {"h1", "sp-b"},
        "sp-b": {"h2"},
    }
    ok_far, _ = is_relation_satisfied(Kind.NEAR, m, graph_3, ["sp-a"], ["sp-b"])
    assert ok_far is False


def test_separated_and_acoustic_separation():
    # Sharing a 2m wall fails SEPARATED and ACOUSTIC_SEPARATION
    m_touch = _build_simple_two_room_model(wall_length=2.0, has_door=False)
    graph = {"sp-a": set(), "sp-b": set()}
    ok_sep, _ = is_relation_satisfied(Kind.SEPARATED, m_touch, graph, ["sp-a"], ["sp-b"])
    assert ok_sep is False

    ok_ac, _ = is_relation_satisfied(
        SpaceRelationshipKind.ACOUSTIC_SEPARATION, m_touch, graph, ["sp-a"], ["sp-b"]
    )
    assert ok_ac is False

    # Sharing 0.05m (<= 0.1m tolerance) passes
    m_tiny = _build_simple_two_room_model(wall_length=0.05, has_door=False)
    ok_sep_tiny, _ = is_relation_satisfied(
        SpaceRelationshipKind.SEPARATED, m_tiny, graph, ["sp-a"], ["sp-b"]
    )
    assert ok_sep_tiny is True


def test_visual_reported_as_line_of_sight_analysis():
    m = _build_simple_two_room_model()
    graph = {"sp-a": set(), "sp-b": set()}
    ok, method = is_relation_satisfied(Kind.VISUAL, m, graph, ["sp-a"], ["sp-b"])
    assert ok is None
    assert method == "line_of_sight_analysis"


# --- S7-02: Solver enforces CodePack hard constraints


def test_solver_enforces_compiled_codepack_hard_constraints():
    site, program = _load(HILLSIDE)

    # Synthetic CodePack: requires living room min_area_m2 = 45.0 (program item had 30.0)
    codepack_doc = copy.deepcopy(load_document(BUNGALOW / "codepacks" / "synthetic-codepack.yaml"))
    codepack_doc["rule_ids"] = ["r-living-large"]
    codepack_doc["rules"] = [
        {
            "id": "r-living-large",
            "title": "Living room spaciousness",
            "summary": "Living room at least 45 m2 and width 4.5m",
            "citation": "synthetic §1",
            "parameters": {"function": "living", "min_area_m2": 45.0, "min_width_m": 4.5},
        }
    ]
    codepack_doc["verification_status"] = "verified_by_professional"
    codepack_doc["verified_by"] = {"kind": "human", "id": "architect-1"}
    codepack_doc["verified_at"] = "2026-10-18T12:00:00Z"
    pack = CodePack.model_validate(codepack_doc)
    compilation = compile_constraints(program, site, created_at=WHEN, actor=TOOL, codepack=pack)
    cs = compilation.constraints

    # Generate a compact concept with the compiled constraints. (Linear cannot hold a 45 m² living
    # beside the separate two-car garage on this envelope since S10-19.)
    req = GenerationRequest(
        site=site,
        program=program,
        constraints=cs,
        site_ref=None,
        program_ref=None,
        created_at=WHEN,
        strategies=["compact"],
        seed=0,
    )
    cands = CpSatPlanGenerator().candidates(req)
    cand = next(c for c in cands if c.strategy == "compact")
    assert cand.plan is not None, f"Expected feasible plan: {cand.reason}"

    # Living room must be >= 45.0 m² and width >= 4.5 m
    living = next(s for s in cand.plan.model.spaces if s.function is SpaceFunction.LIVING)
    assert living.area_m2 >= 45.0
    poly = living.boundary.to_shapely()
    minx, miny, maxx, maxy = poly.bounds
    width = min(maxx - minx, maxy - miny)
    assert width >= 4.5

    # Evaluation with the constraints passes without min area/dimension violations
    report = evaluate_plan(
        cand.plan,
        _ref(cand.plan),
        site=site,
        program=program,
        constraints=cs,
        codepack=pack,
        created_at=WHEN,
    )
    codes = {v.code for v in report.hard_violations}
    assert "min_area_violation" not in codes
    assert "min_dimension_violation" not in codes


# --- S7-03: Soft objectives reported in explanation


def test_soft_objectives_reported_in_explanation():
    site, program = _load(HILLSIDE)
    raw_brief = load_document(HILLSIDE / "design_brief.yaml")
    # Add facts to compile the soft objectives named in task S7-03
    extra_facts = [
        {
            "id": "f-views",
            "topic": "views",
            "key": "views",
            "statement": "synthetic views preference",
            "value": True,
            "status": "preference",
            "source": {"kind": "owner_answer", "ref": "q-views"},
        },
        {
            "id": "f-cross_ventilation",
            "topic": "natural_ventilation",
            "key": "cross_ventilation",
            "statement": "synthetic cross ventilation preference",
            "value": True,
            "status": "preference",
            "source": {"kind": "owner_answer", "ref": "q-cross_ventilation"},
        },
        {
            "id": "f-outdoor",
            "topic": "outdoor_living",
            "key": "outdoor",
            "statement": "synthetic outdoor preference",
            "value": True,
            "status": "preference",
            "source": {"kind": "owner_answer", "ref": "q-outdoor"},
        },
        {
            "id": "f-cooking",
            "topic": "cooking",
            "key": "cooking",
            "statement": "synthetic kitchen preference",
            "value": True,
            "status": "preference",
            "source": {"kind": "owner_answer", "ref": "q-cooking"},
        },
        {
            "id": "f-storage_room",
            "topic": "storage",
            "key": "storage_room",
            "statement": "synthetic storage preference",
            "value": True,
            "status": "preference",
            "source": {"kind": "owner_answer", "ref": "q-storage_room"},
        },
    ]
    target_keys = {"views", "cross_ventilation", "outdoor", "cooking", "storage_room"}
    raw_brief["facts"] = [
        f for f in raw_brief.get("facts", []) if f.get("key") not in target_keys
    ] + extra_facts
    brief = DesignBrief.model_validate(raw_brief)

    compilation = compile_constraints(program, site, brief=brief, created_at=WHEN, actor=TOOL)
    cs = compilation.constraints

    objs = soft_objectives_report(cs)
    names = {name for name, status, detail, weight in objs}

    # All 7 specific objectives named in task S7-03 must be present
    assert "circulation_efficiency" in names
    assert "site_response" in names
    assert "views" in names
    assert "cross_ventilation" in names
    assert "indoor_outdoor" in names
    assert "kitchen_functionality" in names
    assert "storage" in names

    # circulation_efficiency and site_response are optimised in solver
    by_name = {name: (status, detail) for name, status, detail, _ in objs}
    assert by_name["circulation_efficiency"][0] == "optimised"
    assert by_name["site_response"][0] == "optimised"

    # The other five are reported as not_optimised
    for unopt in (
        "views",
        "cross_ventilation",
        "indoor_outdoor",
        "kitchen_functionality",
        "storage",
    ):
        assert by_name[unopt][0] == "not_optimised"

    # The explanation of a plan lists the compiled soft objectives section. The section
    # comes from the constraint set, so the committed linear concept serves; no solve needed.
    plan = PlanVersion.model_validate(
        load_document(HILLSIDE / "concepts" / "concept-linear" / "exploratory" / "plan.json")
    )
    rep = evaluate_plan(
        plan,
        _ref(plan),
        site=site,
        program=program,
        constraints=cs,
        codepack=None,
        created_at=WHEN,
    )
    text = explanation_markdown(plan, 1, rep, program, constraints=cs)
    assert "## Compiled soft objectives" in text
    assert "`circulation_efficiency` | `optimised`" in text
    assert "`cross_ventilation` | `not_optimised`" in text


# --- S7-04: Soft CONNECTED relations produce doors when touching


def test_soft_connected_produces_doors_when_touching():
    site, program = _load(HILLSIDE)

    # The two child bedrooms share a 5.4 m wall in the linear concept and no relation of the
    # program links them, so only a soft CONNECTED request can give them a door.
    pair = {"pi-bed-child-1", "pi-bed-child-2"}
    assert not [
        r for r in program.space_relationships if {r.a, r.b} == pair
    ], "the pair must have no relation of its own"
    adj = SpaceRelationship(
        id="adj-soft-children",
        a="pi-bed-child-1",
        b="pi-bed-child-2",
        kind=SpaceRelationshipKind.CONNECTED,
        strength=Strength.SOFT,
        weight=2.0,
        rationale="shared children's door",
    )
    mod_program = program.model_copy(
        update={"space_relationships": [*program.space_relationships, adj]}
    )
    cs = compile_constraints(mod_program, site, created_at=WHEN, actor=TOOL).constraints

    req = GenerationRequest(
        site=site,
        program=mod_program,
        constraints=cs,
        site_ref=None,
        program_ref=None,
        created_at=WHEN,
        strategies=["linear"],
        seed=0,
    )
    [cand] = CpSatPlanGenerator().candidates(req)
    assert cand.plan is not None
    model = cand.plan.model

    a = next(s for s in model.spaces if s.program_item_id == "pi-bed-child-1")
    b = next(s for s in model.spaces if s.program_item_id == "pi-bed-child-2")
    assert a.level_id == b.level_id
    assert shared_wall_length(model, a.id, b.id) >= SHARED_WALL_MIN_M
    (door,) = [o for o in model.openings if {a.id, b.id} <= set(o.connects)]
    assert door.is_passable, "Touching spaces with soft CONNECTED must have a door"

    # Evaluator must agree that it is satisfied
    rep = evaluate_plan(
        cand.plan,
        _ref(cand.plan),
        site=site,
        program=mod_program,
        constraints=cs,
        codepack=None,
        created_at=WHEN,
    )
    (claim,) = [
        m
        for m in rep.metrics
        if m.metric == "adjacency_satisfied" and "adj-soft-children" in m.subject_ids
    ]
    assert claim.value is True


# --- S7-05: Solver and evaluator agreement across strategies

#: Default strategies with a layout on synthetic-hillside; courtyard has no room for its
#: second pavilion (asserted below).
FEASIBLE = ["compact", "split_level", "linear", "two_wing", "split_walkout"]


def test_solver_evaluator_agreement_across_all_strategies():
    site, program = _load(HILLSIDE)
    cs = compile_constraints(program, site, created_at=WHEN, actor=TOOL).constraints

    req = GenerationRequest(
        site=site,
        program=program,
        constraints=cs,
        site_ref=None,
        program_ref=None,
        created_at=WHEN,
        strategies=[*FEASIBLE, "courtyard"],
        seed=0,
    )
    cands = {c.strategy: c for c in CpSatPlanGenerator().candidates(req)}
    assert [s for s, c in cands.items() if c.plan is not None] == FEASIBLE
    assert "no room for a second pavilion" in (cands["courtyard"].reason or "")
    for strategy in FEASIBLE:
        c = cands[strategy]
        rep = evaluate_plan(
            c.plan,
            _ref(c.plan),
            site=site,
            program=program,
            constraints=cs,
            codepack=None,
            created_at=WHEN,
        )
        # The solver enforced every hard constraint, so the evaluator finds none broken.
        broken = [(v.code, v.constraint_id) for v in rep.hard_violations]
        assert broken == [], f"Strategy {strategy} breaks hard constraints: {broken}"
        # And it agrees on each hard relation: every one is measured as satisfied.
        hard_rel = [r.id for r in program.space_relationships if r.strength is Strength.HARD]
        for rel_id in hard_rel:
            claims = [
                m
                for m in rep.metrics
                if m.metric == "adjacency_satisfied" and rel_id in m.subject_ids
            ]
            assert claims and all(m.value is True for m in claims), (strategy, rel_id)
