"""Constants for agent skills."""

from __future__ import annotations

SKILL_SITE_SURVEY_REVIEW = "site-survey-review"
SKILL_ARCHITECTURAL_PROGRAMMING = "architectural-programming"
SKILL_GENERATE_CONCEPTS = "generate-concepts"
SKILL_CRITIQUE_PLAN = "critique-plan"

CANONICAL_SKILL_NAMES = (
    SKILL_SITE_SURVEY_REVIEW,
    SKILL_ARCHITECTURAL_PROGRAMMING,
    SKILL_GENERATE_CONCEPTS,
    SKILL_CRITIQUE_PLAN,
)

CANONICAL_SKILLS_DIR = "skills"
PROVIDER_SKILLS_DIRS = (
    ".claude/skills",
    ".agents/skills",
)

REQUIRED_SKILL_FRONTMATTER = (
    "name",
    "description",
)

REQUIRED_SKILL_SECTIONS = (
    "Purpose",
    "When to invoke",
    "Inputs",
    "Outputs",
    "Exact commands",
    "Required validations",
    "Human-approval boundaries",
    "Failure handling",
)
