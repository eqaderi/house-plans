"""One table of Revision operation verbs: parser, serialiser and the files that use them.

No store and no solver: these tests exercise the domain module alone.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from house_ai.cli.main import main
from house_ai.domain.revision_ops import (
    REVISION_VERBS,
    RevisionOp,
    RevisionOpError,
    RevisionOpsFile,
    RevisionVerb,
)

REPO = Path(__file__).resolve().parents[1]

#: Operation strings as earlier Plan versions recorded them (CLI flags, combine, reviewer).
STORED = [
    "area:pi-kitchen=16",
    "area:sp-study-1-1=14",
    "area:pi-kitchen=18.0",
    "area:pi-kitchen=14.123456",
    "level:pi-study-1=lower",
    "level:sp-living=not_entry",
    "level:sp-bed-1=any",
    "level:sp-bed-1=ground",
    "separate:pi-bed-main,pi-bed-child-1",
    "adjacent:sp-bed-child-1,sp-bed-main",
    "near:pi-kitchen,pi-dining",
    "connect:sp-kitchen,sp-dining",
    "stair:perimeter",
    "outdoor:sp-living,terrace",
    "outdoor:sp-living",
    "rethink:all",
    "rethink:z-night",
    "strategy:compact",
    "proposal:design/proposals/two-wing.yaml",
]


@pytest.mark.parametrize("text", STORED)
def test_stored_operation_strings_parse_and_serialise_unchanged(text: str) -> None:
    op = RevisionOp.parse(text)
    assert str(op) == text


def test_parse_reads_verb_target_and_value() -> None:
    area = RevisionOp.parse("area:pi-kitchen=16")
    assert (area.op_type, area.target, area.area_m2) == (RevisionVerb.AREA, "pi-kitchen", 16.0)
    sep = RevisionOp.parse("separate:pi-living,pi-bed-main")
    assert sep.names == ("pi-living", "pi-bed-main")
    out = RevisionOp.parse("outdoor:sp-living,balcony")
    assert (out.target, out.value, out.names) == ("sp-living", "balcony", ("sp-living",))
    assert RevisionOp.parse("outdoor:sp-living").outdoor_kind == "terrace"
    assert RevisionOp.parse("stair:rear").names == ()
    assert RevisionOp.parse("rethink:all").names == ()
    assert RevisionOp.parse("rethink:z-night").names == ("z-night",)


@pytest.mark.parametrize("text", ["orientation:sp-living=south", "daylight:sp-living", "void:a,b"])
def test_unknown_verb_is_refused_with_one_message(text: str) -> None:
    with pytest.raises(RevisionOpError) as err:
        RevisionOp.parse(text)
    verb = text.partition(":")[0]
    assert str(err.value) == (
        f"unknown revision operation {verb!r} in {text!r}; known: "
        "adjacent, area, connect, level, near, outdoor, proposal, rethink, separate, stair, "
        "strategy"
    )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("area:pi-kitchen", "'area:pi-kitchen': area needs SPACE=M2"),
        ("area:pi-kitchen=big", "'area:pi-kitchen=big': area needs SPACE=M2"),
        ("area:pi-kitchen=-3", "'area:pi-kitchen=-3': area needs SPACE=M2"),
        ("level:sp-x=sideways", "'level:sp-x=sideways': level must be one of "
         "['any', 'entry', 'ground', 'lower', 'not_entry', 'upper']"),
        ("separate:sp-a", "'separate:sp-a': separate needs SPACE,SPACE"),
        ("connect:sp-a,", "'connect:sp-a,': connect needs SPACE,SPACE"),
        ("stair:attic", "'stair:attic': stair must be one of "
         "['central', 'entry', 'perimeter', 'rear']"),
        ("outdoor:sp-living,garden", "'outdoor:sp-living,garden': outdoor must be one of "
         "['balcony', 'courtyard', 'terrace']"),
        ("strategy:spiral", "'strategy:spiral': strategy must be one of"),
        ("rethink:", "'rethink:': rethink needs SPACE|ZONE|all"),
        ("area", "'area': a revision operation is VERB:TARGET"),
    ],
)
def test_illegal_targets_are_refused_at_parse_time(text: str, message: str) -> None:
    with pytest.raises(RevisionOpError) as err:
        RevisionOp.parse(text)
    assert message in str(err.value)


def test_reviewer_file_parses_through_the_table() -> None:
    data = {
        "project": "synthetic-hillside",
        "option": "concept-compact",
        "plan_version": 1,
        "verbatim_request": "Make the living room face south",
        "author": "homeowner:owner",
        "operations": [{"op_type": "orientation", "target": "sp-living", "value": "south"}],
    }
    with pytest.raises(ValidationError) as err:
        RevisionOpsFile.model_validate(data)
    assert "unknown revision operation 'orientation'" in str(err.value)
    data["operations"] = [
        {"op_type": "area", "target": "pi-kitchen", "value": 18.0},
        {"op_type": "outdoor", "target": "sp-living", "value": "balcony"},
        {"op_type": "level", "target": "sp-study-1", "value": "upper"},
    ]
    ops = RevisionOpsFile.model_validate(data).to_cli_ops()
    assert ops == ["area:pi-kitchen=18.0", "outdoor:sp-living,balcony", "level:sp-study-1=upper"]
    data["operations"] = [{"op_type": "level", "target": "sp-study-1", "value": "attic"}]
    with pytest.raises(ValidationError, match="level must be one of"):
        RevisionOpsFile.model_validate(data)


def test_reviewer_offers_only_verbs_the_table_knows() -> None:
    source = (REPO / "apps/reviewer/src/constants/index.ts").read_text("utf-8")
    block = source.split("export const REVISION_OPS", 1)[1].split("] as const", 1)[0]
    offered = set(re.findall(r'value: "([a-z_]+)"', block))
    assert offered, "the reviewer offers no revision operations"
    assert offered <= {v.value for v in REVISION_VERBS}
    assert not offered & {"orientation", "daylight"}


def test_every_verb_has_a_rule_and_the_constants_hold_no_second_list() -> None:
    import house_ai.constants.reviewer as reviewer_constants

    assert set(REVISION_VERBS) == set(RevisionVerb)
    assert not hasattr(reviewer_constants, "SUPPORTED_REVISION_OPS")
    assert not hasattr(reviewer_constants, "OP_ORIENTATION")
    assert not hasattr(reviewer_constants, "OP_DAYLIGHT")


def test_cli_refuses_an_illegal_level_word_before_opening_the_project(tmp_path) -> None:
    code = main(
        ["plan", "revise", str(tmp_path / "nowhere"), "concept-compact", "Put it in the attic",
         "--level", "sp-study-1=attic", "--actor", "agent:claude-code"]
    )
    assert code == 1
    assert not (tmp_path / "nowhere").exists()
