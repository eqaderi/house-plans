"""Schema registry: one place that names every canonical schema.

``SCHEMAS`` drives JSON Schema export (schemas/*.schema.json) and the CLI
``validate`` command. ``ARTIFACT_MODELS`` tells the project store which model
validates each artifact kind.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from .agents import AgentRoster
from .benchmark import BenchmarkFixture
from .brief import DesignBrief
from .build import BuildRecord, SceneManifest
from .codepack import CodePack
from .constraints import ConstraintSet
from .evaluation import EvaluationReport
from .hillside import HillsideSettings, SectionLine
from .interview import InterviewSession
from .model import HouseModel
from .plan import ChangeRequest, PlanVersion, RevisionReport
from .program import SpaceProgram
from .proposal import ConceptProposal
from .provenance import ArtifactKind, SourceDocument
from .records import AssumptionsFile, OpenQuestionsFile, OwnerStatementsFile
from .revision_ops import RevisionOpsFile
from .site import CadImportProvenance, Site
from .usability import FurnitureTemplate
from .visual_critique import VisualCritiqueFile
from .workflow import Approval, Blocker, ProjectManifest, WorkflowEvent

ARTIFACT_MODELS: dict[ArtifactKind, type[BaseModel]] = {
    ArtifactKind.SOURCE_DOCUMENT: SourceDocument,
    ArtifactKind.CAD_IMPORT: CadImportProvenance,
    ArtifactKind.SITE: Site,
    ArtifactKind.DESIGN_BRIEF: DesignBrief,
    ArtifactKind.SPACE_PROGRAM: SpaceProgram,
    ArtifactKind.ASSUMPTIONS: AssumptionsFile,
    ArtifactKind.OPEN_QUESTIONS: OpenQuestionsFile,
    ArtifactKind.CONSTRAINT_SET: ConstraintSet,
    ArtifactKind.CODEPACK: CodePack,
    ArtifactKind.PLAN: PlanVersion,
    ArtifactKind.EVALUATION_REPORT: EvaluationReport,
    ArtifactKind.REVISION_REPORT: RevisionReport,
    ArtifactKind.BUILD_RECORD: BuildRecord,
    ArtifactKind.INTERVIEW_SESSION: InterviewSession,
    ArtifactKind.OWNER_STATEMENTS: OwnerStatementsFile,
    ArtifactKind.CONCEPT_PROPOSAL: ConceptProposal,
}

SCHEMAS: dict[str, type[BaseModel]] = {
    "section_line": SectionLine,
    "hillside_settings": HillsideSettings,
    "furniture_template": FurnitureTemplate,
    **{kind.value: model for kind, model in ARTIFACT_MODELS.items()},
    "house_model": HouseModel,
    "scene_manifest": SceneManifest,
    "change_request": ChangeRequest,
    "approval": Approval,
    "blocker": Blocker,
    "workflow_event": WorkflowEvent,
    "project_manifest": ProjectManifest,
    "agent_roster": AgentRoster,
    "benchmark_fixture": BenchmarkFixture,
    "revision_ops": RevisionOpsFile,
    "visual_critique": VisualCritiqueFile,
}


def json_schema(name: str) -> dict:
    schema = SCHEMAS[name].model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"https://house-ai.local/schemas/{name}.schema.json"
    return schema


def render_schema(name: str) -> str:
    return json.dumps(json_schema(name), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_schemas(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in sorted(SCHEMAS):
        path = out_dir / f"{name}.schema.json"
        path.write_text(render_schema(name), encoding="utf-8")
        written.append(path)
    return written


def stale_schemas(out_dir: Path) -> list[str]:
    """Names whose committed schema file is missing or differs from the code."""
    stale = []
    for name in sorted(SCHEMAS):
        path = out_dir / f"{name}.schema.json"
        if not path.exists() or path.read_text(encoding="utf-8") != render_schema(name):
            stale.append(name)
    expected = {f"{n}.schema.json" for n in SCHEMAS}
    stale += sorted(p.name for p in out_dir.glob("*.schema.json") if p.name not in expected)
    return stale
