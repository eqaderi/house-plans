"""Constants for agent skills."""

from __future__ import annotations

SKILL_SITE_SURVEY_REVIEW = "site-survey-review"
SKILL_ARCHITECTURAL_PROGRAMMING = "architectural-programming"
SKILL_GENERATE_PLAN_OPTIONS = "generate-plan-options"
SKILL_CRITIQUE_PLAN = "critique-plan"
SKILL_VISUAL_REVIEW = "visual-review"

CANONICAL_SKILL_NAMES = (
    SKILL_SITE_SURVEY_REVIEW,
    SKILL_ARCHITECTURAL_PROGRAMMING,
    SKILL_GENERATE_PLAN_OPTIONS,
    SKILL_CRITIQUE_PLAN,
    SKILL_VISUAL_REVIEW,
)

#: The only copy of each skill; Codex, Gemini CLI and Antigravity read it here (ADR 0034).
CANONICAL_SKILLS_DIR = ".agents/skills"
#: Claude Code's skills folder: a symlink to the whole canonical folder.
CLAUDE_SKILLS_LINK = ".claude/skills"

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
