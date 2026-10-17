"""The architectural design brief (design_brief.yaml).

The interview produces data, not prose: every learned item is a
:class:`BriefFact` with a topic, an epistemic status and a source.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, StrictModel
from .epistemics import Epistemic
from .provenance import Provenance
from .records import Contradiction


class BriefTopic(StrEnum):
    """Topics the adaptive interview investigates (MASTER_SPEC, owner interview)."""

    HOUSEHOLD = "household"
    AGES = "ages"
    FUTURE_CHILDREN = "future_children"
    MULTIGENERATIONAL = "multigenerational"
    LONG_TERM_GUESTS = "long_term_guests"
    ACCESSIBILITY = "accessibility"
    LIFESTYLE = "lifestyle"
    SLEEP_PATTERNS = "sleep_patterns"
    ENTERTAINING = "entertaining"
    PRIVACY = "privacy"
    CULTURAL_PRACTICES = "cultural_practices"
    RELIGIOUS_NEEDS = "religious_needs"
    GUEST_FAMILY_SEPARATION = "guest_family_separation"
    COOKING = "cooking"
    KITCHEN_TYPE = "kitchen_type"
    DINING = "dining"
    BEDROOMS_BATHROOMS = "bedrooms_bathrooms"
    WORK_STUDY = "work_study"
    HOBBIES = "hobbies"
    GYM = "gym"
    STORAGE = "storage"
    LAUNDRY = "laundry"
    SERVICE_SPACES = "service_spaces"
    PETS = "pets"
    VEHICLES = "vehicles"
    EV_CHARGING = "ev_charging"
    OUTDOOR_LIVING = "outdoor_living"
    GARDEN = "garden"
    POOL = "pool"
    VIEWS = "views"
    UNDESIRABLE_VIEWS = "undesirable_views"
    NOISE = "noise"
    SECURITY = "security"
    SMART_HOME = "smart_home"
    MATERIALS_STYLE = "materials_style"
    MAINTENANCE = "maintenance"
    CLIMATE_COMFORT = "climate_comfort"
    DAYLIGHT = "daylight"
    NATURAL_VENTILATION = "natural_ventilation"
    SUSTAINABILITY = "sustainability"
    BUDGET = "budget"
    TARGET_AREA = "target_area"
    SCHEDULE = "schedule"
    FUTURE_EXPANSION = "future_expansion"
    PRIORITIES = "priorities"


class Priority(StrEnum):
    MUST = "must"
    SHOULD = "should"
    COULD = "could"
    WONT = "wont"


class FactSourceKind(StrEnum):
    OWNER_ANSWER = "owner_answer"
    DOCUMENT = "document"
    AGENT_INFERENCE = "agent_inference"
    DEFAULT = "default"


class FactSource(StrictModel):
    kind: FactSourceKind
    #: Interview round, question id or document reference.
    ref: str | None = None
    interview_round: int | None = Field(default=None, ge=1)


FactValue = str | int | float | bool | list[str] | None


class BriefFact(StrictModel):
    id: Id
    topic: BriefTopic
    #: Machine key within the topic, e.g. "kitchen_layout".
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    statement: str = Field(min_length=1)
    value: FactValue = None
    status: Epistemic
    priority: Priority | None = None
    source: FactSource

    @model_validator(mode="after")
    def _inference_needs_agent_source(self) -> BriefFact:
        if self.status is Epistemic.INFERENCE and self.source.kind is FactSourceKind.OWNER_ANSWER:
            raise ValueError("an owner answer is not an inference; record the answer as stated")
        if (
            self.status in (Epistemic.VERIFIED_FACT, Epistemic.PREFERENCE)
            and self.source.kind is FactSourceKind.AGENT_INFERENCE
        ):
            raise ValueError("an agent inference cannot be recorded as a fact or a preference")
        return self


class MemberRole(StrEnum):
    ADULT = "adult"
    CHILD = "child"
    ELDER = "elder"
    LONG_TERM_GUEST = "long_term_guest"
    STAFF = "staff"
    EXPECTED_CHILD = "expected_child"


class HouseholdMember(StrictModel):
    id: Id
    role: MemberRole
    label: str
    #: None means UNKNOWN; never invented.
    age_years: int | None = Field(default=None, ge=0, le=130)
    needs: list[str] = Field(default_factory=list)


class Money(StrictModel):
    amount: float = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class DesignBrief(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    project_id: Id
    household: list[HouseholdMember] = Field(default_factory=list)
    facts: list[BriefFact] = Field(default_factory=list)
    #: None means UNKNOWN.
    budget: Money | None = None
    target_gross_area_m2: float | None = Field(default=None, gt=0)
    contradictions: list[Contradiction] = Field(default_factory=list)
    interview_rounds_completed: int = Field(default=0, ge=0)
    provenance: Provenance

    @model_validator(mode="after")
    def _references_resolve(self) -> DesignBrief:
        ids = [f.id for f in self.facts] + [m.id for m in self.household]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate ids in brief: {sorted(dupes)}")
        fact_ids = {f.id for f in self.facts}
        for c in self.contradictions:
            missing = set(c.fact_ids) - fact_ids
            if missing:
                raise ValueError(f"contradiction {c.id} cites unknown facts {sorted(missing)}")
        return self

    def facts_for(self, topic: BriefTopic) -> list[BriefFact]:
        return [f for f in self.facts if f.topic is topic]

    def unresolved_contradictions(self) -> list[Contradiction]:
        return [c for c in self.contradictions if not c.resolved]
