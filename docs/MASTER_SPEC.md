You are the lead software architect, computational-design engineer,
AEC interoperability engineer, GIS/CAD engineer, and AI-agent engineer
for a new open-ended project called HOUSE DESIGN AI.

Your task is to build the repository and a working vertical slice of the
product described below.

Do not build a demo that merely generates floor-plan images.
Do not build a front-end mockup with fake data.
Do not make an LLM-generated PNG the source of truth.

The product must be a real, testable, model-provider-neutral architectural
design system whose canonical outputs are structured semantic geometry.

======================================================================
MISSION
======================================================================

The eventual product will help a non-architect homeowner explore the
design of a real house on a real surveyed site.

The normal input will include:

- a survey DWG or DXF;
- parcel boundaries;
- surveyed X/Y coordinates, potentially UTM;
- elevations/contours/spot levels;
- possibly roads, easements, existing structures, utilities and trees;
- optional site photos and other contextual information;
- an owner's requirements gathered through an adaptive interview.

The product must:

1. understand and validate the site;
2. interview the homeowner;
3. turn the interview into a structured architectural brief;
4. create a structured space program;
5. distinguish hard constraints from soft preferences;
6. generate multiple meaningfully different floor-plan concepts;
7. evaluate them quantitatively and qualitatively;
8. allow conversational revisions;
9. preserve all revisions and design decisions;
10. allow a human to approve/freeze a plan;
11. convert the approved semantic plan into editable 3D;
12. build and inspect that model in Blender;
13. export the approved Blender scene to Unreal Engine;
14. create a walkable first-person Unreal experience.

The target workflow is:

survey
→ verified site
→ owner interview
→ approved program
→ adjacency concepts
→ alternative floor plans
→ multidisciplinary evaluation
→ human iteration
→ approved plan
→ semantic/BIM model
→ Blender
→ Blender validation
→ Unreal Engine
→ interactive walkthrough

======================================================================
CORE PRINCIPLE: ONE MODEL, MANY VIEWS
======================================================================

There MUST NOT be independent representations in which:

- the floor-plan image says one thing;
- Blender says something different;
- Unreal says something different.

Create one canonical semantic house model.

2D plans, schedules, BIM exports, Blender geometry and Unreal geometry
must be derived from that canonical representation.

At minimum the domain model must represent:

- site;
- coordinate systems;
- levels;
- spaces/rooms;
- room polygons;
- walls;
- slabs/floors;
- ceilings;
- doors;
- windows;
- stairs;
- circulation;
- zones;
- fixtures;
- room relationships;
- materials references;
- provenance;
- constraints;
- assumptions;
- unresolved issues.

Use stable IDs throughout the pipeline.

======================================================================
CAD / SITE INGESTION
======================================================================

Treat DWG as a CAD format and UTM as a coordinate-reference system.

NEVER infer or silently guess the authoritative coordinate-reference
system solely from coordinate magnitudes.

Implement a CAD ingestion abstraction.

Suggested adapters:

- DXF via ezdxf;
- DWG via a configurable GDAL/OGR adapter when available;
- optional DWG→DXF conversion adapter through an external converter.

The rest of the application must not depend on a particular CAD backend.

Implement:

inspect_cad()
extract_cad()
classify_layers()
extract_boundary()
extract_contours()
extract_spot_elevations()
build_terrain()
set_coordinate_reference_system()
create_local_coordinate_system()

Every import must create provenance including:

- original filename;
- SHA-256;
- drawing units;
- parser;
- parser version if available;
- horizontal CRS status;
- EPSG if confirmed;
- vertical datum/status;
- local origin;
- warnings;
- unrecognized layers/entities.

If CRS or units are ambiguous, mark SITE_NEEDS_VERIFICATION and stop.
Never silently continue.

Preserve the original input as immutable.

Create a synthetic DXF fixture so the entire pipeline is testable without
a private real survey.

======================================================================
OWNER INTERVIEW / ARCHITECTURAL PROGRAMMING
======================================================================

Implement an adaptive interview engine that is directly operable by coding
agents (Claude Code, Gemini CLI, OpenAI Codex) through documented CLI commands
and structured data interfaces, WITHOUT requiring a separately billed Anthropic,
OpenAI, or Gemini API key for the core workflow.

The intended primary architecture is:

HOMEOWNER
   ↓
CLAUDE CODE / GEMINI CLI / CODEX
   ↓
HOUSE DESIGN TOOLS (`house-ai` CLI & structured interfaces)
   ↓
STRUCTURED REQUIREMENTS AND VALIDATION
   ↓
FLOOR PLANS
   ↓
BLENDER / IFC
   ↓
UNREAL ENGINE

It must investigate, as relevant:

- household members;
- ages;
- future children;
- multigenerational living;
- long-term guests;
- accessibility and aging in place;
- lifestyle;
- waking/sleeping patterns;
- entertaining;
- privacy;
- cultural practices;
- religious/ritual needs;
- guest/family separation;
- cooking habits;
- kitchen type;
- dining;
- bedrooms/bathrooms;
- work/study;
- hobbies;
- gym;
- storage;
- laundry;
- mechanical/service spaces;
- pets;
- vehicles;
- EV charging;
- outdoor living;
- garden;
- pool;
- views;
- undesirable views;
- noise;
- security;
- smart-home requirements;
- materials/style;
- maintenance tolerance;
- climate/comfort preferences;
- daylight;
- natural ventilation;
- sustainability;
- budget;
- target area;
- schedule;
- future expansion;
- priorities and trade-offs.

Do not ask 50 questions at once.

Ask a small number of high-information questions per round.
Use the predefined question bank as a completeness checklist, while allowing
the coding agent to ask natural, adaptive architectural follow-up questions
(and understand Persian, English, or mixed-language homeowner conversations)
without requiring the deterministic parser to understand every natural-language
expression.

After each round:

1. record the homeowner's EXACT original words verbatim;
2. propose structured slot interpretations (`inference`) and update the brief;
3. show what was learned and ask the homeowner to confirm or correct it;
4. label assumptions;
5. detect contradictions and missing information;
6. ask the next most useful questions.

The interview output must be data, not just prose.

Create:

design_brief.yaml
space_program.yaml
assumptions.yaml
open_questions.yaml

======================================================================
CONSTRAINT ARCHITECTURE
======================================================================

Implement explicit HARD and SOFT constraints.

HARD means a candidate is invalid if violated.
SOFT means it contributes to a multi-objective score.

Examples of hard geometric constraints:

- rooms do not overlap;
- geometry lies inside the active buildable envelope;
- required adjacencies/connections exist;
- doors connect valid spaces;
- circulation is traversable;
- openings belong to walls;
- geometry is valid;
- floor areas and dimensions satisfy project-specific configured minima.

Do not invent universal code rules.

Building regulations vary by jurisdiction and edition.

Create a versioned CodePack interface:

CodePack
jurisdiction
authority
edition
effective_date
source
rule_ids
verification_status

No result may say "code compliant" unless the relevant jurisdiction,
edition and rule set have been explicitly loaded and validated.

Otherwise say:

"not checked"
or
"conceptual best-practice check only".

Soft objectives should support:

- adjacency quality;
- circulation efficiency;
- privacy;
- acoustic zoning;
- daylight opportunity;
- orientation;
- views;
- cross-ventilation opportunity;
- indoor/outdoor relationship;
- kitchen functionality;
- furniture usability;
- storage;
- consolidated plumbing/wet zones;
- structural regularity;
- envelope simplicity;
- adaptability;
- construction complexity;
- cost proxy;
- site response;
- landscape quality;
- cultural fit.

======================================================================
FLOOR-PLAN GENERATION
======================================================================

Do not ask an LLM to invent arbitrary coordinates and trust them.

Use a hybrid architecture:

LLM
→ program reasoning / topology proposals / adjacency graph
→ formal solver
→ valid vector geometry
→ deterministic checks
→ AI critique

Use Google OR-Tools CP-SAT or another justified optimization engine for
appropriate discrete constraints.

Use robust computational geometry for intersections, containment,
clearances, areas and paths.

The first usable implementation may use orthogonal rectangular rooms.
Design abstractions so later implementations can support polygons,
non-orthogonal geometry and courtyards without replacing the domain model.

Given the same brief, generate at least THREE meaningfully different
concepts, not cosmetic variations.

Example strategies:

- courtyard;
- linear;
- two-wing;
- compact two-story;
- pavilion/clusters.

Each candidate must include:

plan.json
plan.svg
metrics.json
violations.json
assumptions.json
explanation.md

Do not rank candidates solely with one opaque "AI score".

Expose individual metrics and trade-offs.

======================================================================
PLAN EVALUATION
======================================================================

Create modular evaluators.

At minimum implement:

GeometryEvaluator
ProgramEvaluator
AdjacencyEvaluator
CirculationEvaluator
PrivacyEvaluator
SiteEvaluator

Design interfaces for future:

DaylightEvaluator
SolarEvaluator
AccessibilityEvaluator
LifeSafetyEvaluator
StructuralConceptEvaluator
MEPConceptEvaluator
CostEvaluator
EnergyEvaluator
CulturalFitEvaluator

Evaluators must distinguish:

MEASURED
INFERRED
SIMULATED
AI_JUDGMENT
NOT_CHECKED

Every reported claim must carry provenance.

Example:

{
"metric": "guest_private_crossings",
"value": 0,
"method": "graph_analysis",
"status": "measured"
}

======================================================================
HUMAN APPROVAL GATES
======================================================================

Implement explicit workflow states.

NEW_PROJECT
SITE_INGESTION
SITE_NEEDS_VERIFICATION
SITE_APPROVED
INTERVIEWING
PROGRAM_REVIEW
PROGRAM_APPROVED
CONCEPT_GENERATION
CONCEPT_REVIEW
PLAN_APPROVED
BLENDER_BUILD
BLENDER_REVIEW
MODEL_APPROVED
UNREAL_BUILD
UNREAL_REVIEW

Agents may not silently skip an approval gate.

The user must explicitly approve:

1. site truth;
2. program;
3. final floor plan;
4. Blender model before final Unreal production.

======================================================================
REVISION SYSTEM
======================================================================

Every plan iteration must be versioned.

Never overwrite an approved or reviewed design.

Support commands such as:

"make the kitchen larger"
"move the guest suite away from the children's rooms"
"keep the courtyard but completely rethink the bedroom wing"
"generate three alternatives"
"I hate this option; start again from the approved program"
"combine the entrance of B with the courtyard of A"

After each revision report:

- requested change;
- geometry changed;
- rooms changed;
- area changes;
- metric changes;
- new violations;
- resolved violations;
- assumptions.

======================================================================
2D REVIEWER
======================================================================

Build a minimal web reviewer.

It must eventually support synchronized:

- parcel/site;
- terrain;
- floor plan;
- room labels;
- dimensions;
- room areas;
- north;
- circulation paths;
- constraints/issues;
- comparison between versions.

Do not prioritize visual polish over domain correctness.

The first version may use SVG for plans.

======================================================================
BIM
======================================================================

Create an adapter boundary for IFC using IfcOpenShell.

The canonical application model remains ours, but we must be able to map
approved architectural entities into IFC where practical.

The project must not depend completely on proprietary formats.

======================================================================
BLENDER
======================================================================

Generate Blender geometry from the APPROVED canonical plan.

Use deterministic, version-controlled Python scripts.

Do not make manual Blender edits the only source of later geometry.

Generate at least:

- site/terrain;
- slabs;
- walls;
- openings;
- doors;
- windows;
- ceilings/roof placeholder;
- stairs if present;
- basic architectural materials;
- room IDs / metadata.

Organize objects into semantic collections.

Add validation scripts.

Produce review renders:

- orthographic top;
- exterior;
- primary living space;
- kitchen;
- bedroom area;
- clay/solid geometry;
- optional collision/clearance visualization.

Create a visual-review loop in which an AI agent can inspect rendered
images and report issues, but visual review must supplement deterministic
geometry tests rather than replace them.

Support Blender MCP as an OPTIONAL interactive agent interface.
The reproducible pipeline itself must remain runnable through scripts.

======================================================================
UNREAL ENGINE
======================================================================

Implement the first transfer pipeline using the proven architectural
pattern:

approved Blender
→ FBX geometry

- JSON scene manifest
  → Unreal importer

scene_manifest.json must support:

- stable object IDs;
- transforms;
- units;
- material assignments;
- source textures;
- lights;
- cameras;
- instances;
- semantic type;
- parent/assembly relationships;
- interaction metadata.

Handle:

- Blender meters;
- Unreal centimeters;
- axis/orientation conversion;
- material translation;
- texture scale;
- collision;
- object instances.

Create Unreal automation that can produce:

- imported architectural scene;
- terrain;
- first-person character;
- human-scale starting position;
- collision;
- basic lighting;
- sky;
- doors that can open;
- room labels/debug mode.

Design future interfaces for:

- drawers;
- switches;
- windows;
- appliances;
- time-of-day;
- material variants.

Preserve georeferencing metadata and support Unreal's GeoReferencing
plugin where appropriate.

Keep a future adapter path open for Datasmith/IFC.

======================================================================
AI PROVIDERS AND AGENT-FIRST INTERFACE
======================================================================

The domain system must not depend on one model vendor, nor require a paid
API key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`) for the
core workflow.

The primary AI interfaces are interactive coding agents working directly with
the homeowner:

- Claude Code;
- Google Gemini CLI;
- OpenAI Codex.

These agents operate the project through documented `house-ai` CLI commands
and structured data interfaces (`ProjectStore`, JSON/YAML artifacts, and
hash-chained event history), while human approval gates (`site`, `program`,
`plan`, `model`) remain strictly human-only in an interactive terminal.

Create a provider-neutral interface (`ModelProvider`, `DataFlowPolicy`) so
direct SDK adapters (Anthropic, OpenAI, Google Gemini) remain OPTIONAL where
credentials/environment support them. Never design the core workflow around a
paid API key.

The same project files, schemas, workflow states and tools must work
regardless of which agent or optional provider is used.

Provider-specific context files should be SMALL:

AGENTS.md
CLAUDE.md
GEMINI.md

Create one canonical:

docs/AGENT_CONTRACT.md

Those three files should point to the canonical instructions and add only
provider-specific details.

======================================================================
AGENT ROLES
======================================================================

Define modular agent roles, not one magical super-agent:

Orchestrator
Site Analyst
Architectural Programmer
Design Architect
Planning Critic
Building Science Critic
Code Critic
Structural Concept Critic
MEP Concept Critic
Cost/Constructability Critic
Blender Agent
Unreal Agent

Do not invoke every agent for every trivial action.

Use the smallest useful composition.

All agents that change structured project state must return schema-valid
outputs.

======================================================================
PROFESSIONAL / SAFETY BOUNDARY
======================================================================

This is a design exploration and decision-support system.

It MUST NOT claim that an AI-generated concept is:

- permit-ready;
- construction-ready;
- structurally certified;
- code-compliant;
- MEP-engineered;
- geotechnically verified;

unless an appropriate qualified professional or authoritative validation
process has actually supplied that status.

Always separate:

verified fact
inference
assumption
preference
simulation result
professional approval

Create docs/PROFESSIONAL_HANDOFF.md.

The eventual output should help architects/engineers review the work,
not attempt to hide the fact that AI produced design exploration.

======================================================================
TESTING
======================================================================

This is critical.

Create automated tests for:

- schema validation;
- CAD fixture parsing;
- units;
- CRS transformations;
- geometry validity;
- no room overlap;
- containment in envelope;
- adjacency;
- door connectivity;
- circulation graph;
- area calculations;
- deterministic rendering snapshots where practical;
- solver regression;
- serialization round trips;
- Blender generation smoke tests where Blender is available;
- Unreal importer structure where Unreal is available.

Create golden synthetic projects.

CI must be able to run without the user's private DWG.

======================================================================
DATA / PRIVACY
======================================================================

project-data/source and owner-specific project material are private
project data and should be gitignored by default.

Examples and tests must use synthetic or redistributable data.

Never upload private survey data to a model provider implicitly.
Make provider data flow explicit.

======================================================================
REPOSITORY STRUCTURE
======================================================================

Create a clean monorepo broadly following:

docs/
schemas/
src/house_ai/
cad/
geospatial/
interview/
program/
constraints/
generation/
evaluation/
render2d/
bim/
blender/
unreal/
providers/
orchestration/
cli/
agents/
skills/
apps/reviewer/
tests/
examples/
project-data/

Adjust the exact structure if implementation experience reveals a
better organization, but document architectural changes through ADRs.

======================================================================
IMPLEMENTATION STRATEGY
======================================================================

Do not attempt photorealism first.

Build a vertical slice in this order:

MILESTONE A — DOMAIN FOUNDATION

- repository;
- canonical schemas;
- project storage;
- provenance;
- workflow state machine;
- tests.

MILESTONE B — SITE

- synthetic DXF fixture;
- CAD inspection;
- layer extraction;
- units;
- CRS confirmation;
- boundary;
- elevation/terrain;
- site SVG.

MILESTONE C — PROGRAM

- interview engine;
- design brief;
- space program;
- adjacency graph;
- human approval.

MILESTONE D — PLAN

- formal constraint model;
- 3+ alternative plans;
- SVG renderer;
- evaluators;
- plan versioning.

MILESTONE E — REVIEWER

- inspect options;
- display metrics;
- compare versions;
- capture user change requests.

MILESTONE F — BLENDER

- deterministic canonical-plan-to-Blender generator;
- render views;
- geometry validation.

MILESTONE G — UNREAL

- FBX;
- scene manifest;
- importer;
- first-person walkthrough;
- collision.

Only then proceed toward advanced BIM, photorealistic materials,
environmental simulation, automated cost models and expanded code packs.

======================================================================
DEFINITION OF SUCCESS FOR THE FIRST VERTICAL SLICE
======================================================================

Starting from the repository alone, a developer must be able to run a
documented command that:

1. loads the included synthetic survey;
2. creates a site model;
3. loads an example owner brief;
4. creates a space program;
5. generates at least three distinct floor-plan concepts;
6. validates them;
7. renders them as SVG;
8. generates a comparison report;
9. selects one example approved plan;
10. produces the Blender build input;
11. when Blender is installed, creates an editable Blender scene;
12. creates an Unreal transfer manifest;
13. documents how to import/build the Unreal walkthrough.

No fake UI data.
No silently hardcoded successful output.
No image-only floor plans.

======================================================================
HOW TO WORK
======================================================================

First inspect the existing repository.

Then:

1. write docs/PRODUCT_SPEC.md;
2. write docs/ARCHITECTURE.md;
3. write docs/DOMAIN_MODEL.md;
4. write docs/AGENT_CONTRACT.md;
5. create an ADR explaining the canonical semantic model;
6. create schemas;
7. scaffold packages;
8. implement the smallest end-to-end vertical slice;
9. create fixtures;
10. run tests;
11. fix failures;
12. update documentation with exact commands.

Prefer simple, composable components to an enormous autonomous-agent
framework.

Use AI where reasoning is beneficial.
Use deterministic software where correctness is measurable.

When an architectural fact is unknown, model it as UNKNOWN.
Never invent it merely to unblock the pipeline.

When a third-party program is not installed, implement and test the
adapter boundary, provide installation/integration instructions, and keep
the rest of the vertical slice executable.

Record major decisions under docs/adr/.

At the end of each milestone create:

- what works;
- exact command to demonstrate it;
- test results;
- known limitations;
- next milestone.

Begin by inspecting the repository and producing the architecture/domain
documents, then immediately implement the vertical slice rather than
stopping after planning.
