import React, { useState, useEffect } from "react";
import type { ReviewerBundle } from "./types/schemas";
import { parseReviewerBundleJson, validateReviewerBundle } from "./lib/loader";
import { GateBanner } from "./components/GateBanner";
import { PlanCanvas } from "./components/PlanCanvas";
import { PropertyPanel } from "./components/PropertyPanel";
import { RoomSchedule } from "./components/RoomSchedule";
import { FindingsPanel } from "./components/FindingsPanel";
import { MetricMatrix } from "./components/MetricMatrix";
import { TerrainSection } from "./components/TerrainSection";
import { ComparisonView } from "./components/ComparisonView";
import { VersionDiff } from "./components/VersionDiff";
import { RevisionTimeline } from "./components/RevisionTimeline";
import { FeedbackPanel } from "./components/FeedbackPanel";

// Fallback demo bundle for immediate rendering
const DEMO_BUNDLE: ReviewerBundle = {
  schema_version: "1.0.0",
  project: {
    name: "synthetic-hillside",
    state: "CONCEPT_REVIEW",
  },
  gates: {
    site: {
      name: "Site Gate",
      approved: true,
      approved_at: "2026-10-17T12:00:00Z",
      approved_by: "human:example-owner",
      approve_command: "house-ai workflow approve synthetic-hillside site --id site --approver <name>",
      description: "Requires human confirmation of horizontal/vertical CRS and human approval.",
    },
    program: {
      name: "Program Gate",
      approved: true,
      approved_at: "2026-10-17T12:00:00Z",
      approved_by: "human:example-owner",
      approve_command: "house-ai workflow approve synthetic-hillside program --id program --approver <name>",
      description: "Requires human review of space program and architectural brief.",
    },
    plan: {
      name: "Plan Gate",
      approved: false,
      approve_command: "house-ai workflow approve synthetic-hillside plan --id concept-compact --version 1 --approver <name>",
      description: "Requires human approval of a specific evaluated plan version.",
    },
    model: {
      name: "Model Gate",
      approved: false,
      approve_command: "house-ai workflow approve synthetic-hillside model --id <model-id> --approver <name>",
      description: "Requires human approval of 3D Blender/BIM model.",
    },
  },
  site: {
    id: "site-demo",
    name: "Demo Site",
    project_id: "synthetic-hillside",
    classification: "synthetic",
    provenance: {
      created_at: "2026-10-17T12:00:00Z",
      created_by: { kind: "agent", id: "agent:demo" },
      method: "demo",
    },
    boundary: {
      outer: [
        [-2, -2],
        [15, -2],
        [15, 12],
        [-2, 12],
      ],
    },
    buildable_envelope: {
      basis: "Setback 1.5m",
      status: "verified_fact",
      polygon: {
        outer: [
          [-0.5, -0.5],
          [13.5, -0.5],
          [13.5, 10.5],
          [-0.5, 10.5],
        ],
      },
    },
    coordinates: {
      horizontal_crs: {
        status: "user_confirmed",
      },
    },
  },
  plans: [
    {
      option_id: "concept-compact",
      label: "Compact",
      strategy: "compact",
      version: 1,
      is_exploratory: false,
      plan: {
        schema_version: "0.1.0",
        option_id: "concept-compact",
        label: "Compact",
        strategy: "compact",
        provenance: {
          created_at: "2026-10-17T12:00:00Z",
          created_by: { kind: "agent", id: "agent:gemini" },
          method: "plan_generation",
          tool: "house-ai plan generate",
          inputs: [],
        },
        model: {
          schema_version: "0.1.0",
          id: "model-compact",
          name: "Compact Model",
          coordinate_system_id: "local",
          levels: [
            { id: "lvl-ground", name: "Ground Level", elevation_m: 0.0 },
            { id: "lvl-upper", name: "Upper Level", elevation_m: 3.0 },
          ],
          spaces: [
            {
              id: "sp-living",
              name: "Living Room",
              level_id: "lvl-ground",
              function: "living",
              boundary: {
                outer: [
                  [0, 0],
                  [6, 0],
                  [6, 5],
                  [0, 5],
                ],
              },
            },
            {
              id: "sp-kitchen",
              name: "Kitchen",
              level_id: "lvl-ground",
              function: "kitchen",
              boundary: {
                outer: [
                  [6, 0],
                  [10, 0],
                  [10, 4],
                  [6, 4],
                ],
              },
            },
            {
              id: "sp-dining",
              name: "Dining",
              level_id: "lvl-ground",
              function: "dining",
              boundary: {
                outer: [
                  [6, 4],
                  [10, 4],
                  [10, 7],
                  [6, 7],
                ],
              },
            },
            {
              id: "sp-bed-1",
              name: "Primary Bedroom",
              level_id: "lvl-upper",
              function: "bedroom",
              boundary: {
                outer: [
                  [0, 0],
                  [5, 0],
                  [5, 4],
                  [0, 4],
                ],
              },
            },
          ],
          walls: [
            { id: "w-ext-1", level_id: "lvl-ground", kind: "exterior", start: [0, 0], end: [10, 0], thickness_m: 0.3, height_m: 2.8 },
            { id: "w-ext-2", level_id: "lvl-ground", kind: "exterior", start: [10, 0], end: [10, 7], thickness_m: 0.3, height_m: 2.8 },
            { id: "w-ext-3", level_id: "lvl-ground", kind: "exterior", start: [10, 7], end: [6, 7], thickness_m: 0.3, height_m: 2.8 },
            { id: "w-ext-4", level_id: "lvl-ground", kind: "exterior", start: [6, 7], end: [6, 5], thickness_m: 0.3, height_m: 2.8 },
            { id: "w-ext-5", level_id: "lvl-ground", kind: "exterior", start: [6, 5], end: [0, 5], thickness_m: 0.3, height_m: 2.8 },
            { id: "w-ext-6", level_id: "lvl-ground", kind: "exterior", start: [0, 5], end: [0, 0], thickness_m: 0.3, height_m: 2.8 },
            { id: "w-int-1", level_id: "lvl-ground", kind: "interior", start: [6, 0], end: [6, 5], thickness_m: 0.15, height_m: 2.8 },
          ],
          openings: [
            { id: "d-entry", host_wall_id: "w-ext-1", kind: "door", offset_m: 2.0, width_m: 1.0, height_m: 2.1, connects: [] },
            { id: "d-kitchen", host_wall_id: "w-int-1", kind: "door", offset_m: 2.0, width_m: 0.9, height_m: 2.1, connects: [] },
            { id: "win-liv", host_wall_id: "w-ext-1", kind: "window", offset_m: 3.5, width_m: 2.0, height_m: 1.5, connects: [] },
            { id: "win-kitch", host_wall_id: "w-ext-2", kind: "window", offset_m: 1.0, width_m: 2.0, height_m: 1.5, connects: [] },
          ],
          stairs: [
            {
              id: "st-main",
              from_level_id: "lvl-ground",
              to_level_id: "lvl-upper",
              bottom_space_id: "sp-living",
              top_space_id: "sp-bed-1",
              width_m: 1.0,
              kind: "straight",
              footprint: {
                outer: [
                  [0, 3],
                  [2, 3],
                  [2, 5],
                  [0, 5],
                ],
              },
            },
          ],
        },
      },
      evaluation: {
        schema_version: "0.1.0",
        id: "eval-compact-1",
        plan_ref: { kind: "plan", id: "concept-compact", version: 1, sha256: "0".repeat(64) },
        provenance: {
          created_at: "2026-10-17T00:00:00Z",
          created_by: { kind: "agent", id: "agent:demo" },
          method: "demo_scaffold",
        },
        evaluators: [],
        compliance: { status: "conceptual_best_practice_only" },
        metrics: [
          {
            evaluator: "evaluator:geometry",
            evaluator_version: "0.1.0",
            metric: "gross_internal_area_m2",
            value: 72.0,
            unit: "m²",
            status: "measured",
            method: "geometry_polygon_sum",
          },
          {
            evaluator: "evaluator:hillside",
            evaluator_version: "0.1.0",
            metric: "max_cut_depth_m",
            value: 1.8,
            unit: "m",
            status: "inferred",
            method: "terrain_mesh_sampling",
          },
          {
            evaluator: "evaluator:hillside",
            evaluator_version: "0.1.0",
            metric: "excavation_volume_m3",
            value: 115.0,
            unit: "m³",
            status: "inferred",
            method: "grid_cut_fill",
          },
          {
            evaluator: "evaluator:daylight",
            evaluator_version: "0.1.0",
            metric: "daylight_ratio",
            value: 0.85,
            status: "ai_judgment",
            method: "window_count_heuristic",
          },
        ],
        violations: [],
      },
    },
  ],
};

export const App: React.FC = () => {
  const [bundle, setBundle] = useState<ReviewerBundle>(DEMO_BUNDLE);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedOptionId, setSelectedOptionId] = useState<string>("concept-compact");
  const [activeLevelId, setActiveLevelId] = useState<string>("lvl-ground");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedKind, setSelectedKind] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    "plan" | "comparison" | "schedule" | "findings" | "metrics" | "section" | "history" | "feedback"
  >("plan");

  // Overlays
  const [showDimensions, setShowDimensions] = useState<boolean>(true);
  const [showLabels, setShowLabels] = useState<boolean>(true);
  const [showPrivacy, setShowPrivacy] = useState<boolean>(false);
  const [showSite, setShowSite] = useState<boolean>(true);

  // Active plan entry
  const activePlanEntry =
    bundle.plans.find((p) => p.option_id === selectedOptionId) || bundle.plans[0];
  const activeModel = activePlanEntry?.plan.model;
  const levels = activeModel?.levels || [];

  // Load bundle from URL parameter (?bundle=/path/to/bundle.json) if provided
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const bundleUrl = params.get("bundle");
    if (bundleUrl) {
      fetch(bundleUrl)
        .then((r) => r.json())
        .then((data) => {
          const res = validateReviewerBundle(data);
          if (res.success) {
            setBundle(res.bundle);
            setLoadError(null);
            if (res.bundle.plans.length > 0) {
              setSelectedOptionId(res.bundle.plans[0].option_id);
            }
          } else {
            setLoadError(res.errors.join("; "));
          }
        })
        .catch((err) => {
          setLoadError(`Failed to load bundle: ${err instanceof Error ? err.message : String(err)}`);
        });
    }
  }, []);

  // Update active level if not in current model
  useEffect(() => {
    if (levels.length > 0 && !levels.some((l) => l.id === activeLevelId)) {
      setActiveLevelId(levels[0].id);
    }
  }, [selectedOptionId, levels, activeLevelId]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      const res = parseReviewerBundleJson(content);
      if (res.success) {
        setBundle(res.bundle);
        setLoadError(null);
        if (res.bundle.plans.length > 0) {
          setSelectedOptionId(res.bundle.plans[0].option_id);
        }
      } else {
        setLoadError(res.errors.join("; "));
      }
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", width: "100vw", overflow: "hidden" }}>
      {/* Top Header */}
      <header
        style={{
          background: "#0f172a",
          borderBottom: "1px solid #334155",
          padding: "10px 16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 16, fontWeight: 800, color: "#38bdf8", letterSpacing: 0.5 }}>
            HOUSE DESIGN AI
          </span>
          <span style={{ color: "#64748b" }}>/</span>
          <span style={{ fontWeight: 600, color: "#f8fafc" }}>{bundle.project.name}</span>
          <span
            style={{
              fontSize: 11,
              padding: "2px 6px",
              borderRadius: 4,
              background: "#334155",
              color: "#94a3b8",
              fontFamily: "monospace",
            }}
          >
            {bundle.project.state}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <label
            style={{
              fontSize: 12,
              background: "#1e293b",
              border: "1px solid #475569",
              padding: "4px 10px",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            📁 Load Bundle.json
            <input type="file" accept=".json" onChange={handleFileUpload} style={{ display: "none" }} />
          </label>
        </div>
      </header>

      {/* Human Approval Gates Banner */}
      <GateBanner gates={bundle.gates} />

      {loadError && (
        <div style={{ background: "#7f1d1d", color: "#fca5a5", padding: "8px 16px", fontSize: 12 }}>
          ⚠️ Bundle Load Error: {loadError}
        </div>
      )}

      {/* Exploratory Warning Banner */}
      {activePlanEntry?.is_exploratory && (
        <div style={{ background: "#78350f", color: "#fde68a", padding: "6px 16px", fontSize: 12, fontWeight: 600 }}>
          ⚠️ EXPLORATORY CONCEPT: Preview only. Not stored in ProjectStore, site/program not approved.
        </div>
      )}

      {/* Main App Layout */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left Sidebar Controls */}
        <aside
          style={{
            width: 320,
            background: "#1e293b",
            borderRight: "1px solid #334155",
            display: "flex",
            flexDirection: "column",
            overflowY: "auto",
          }}
        >
          {/* Concept Selector & Level Switcher */}
          <div style={{ padding: 16, borderBottom: "1px solid #334155" }}>
            <label style={{ display: "block", fontSize: 11, color: "#94a3b8", marginBottom: 4, fontWeight: 600 }}>
              PLAN CONCEPT:
            </label>
            <select
              data-testid="concept-select"
              value={selectedOptionId}
              onChange={(e) => setSelectedOptionId(e.target.value)}
              style={{
                width: "100%",
                background: "#0f172a",
                border: "1px solid #475569",
                color: "#fff",
                padding: "6px 8px",
                borderRadius: 4,
                marginBottom: 12,
              }}
            >
              {bundle.plans.map((p) => (
                <option key={p.option_id} value={p.option_id}>
                  {p.label || p.option_id} ({p.strategy || "concept"}) {p.version ? `v${p.version}` : ""}
                </option>
              ))}
            </select>

            {levels.length > 0 && (
              <>
                <label style={{ display: "block", fontSize: 11, color: "#94a3b8", marginBottom: 4, fontWeight: 600 }}>
                  FLOOR LEVEL:
                </label>
                <div style={{ display: "flex", gap: 6 }}>
                  {levels.map((lvl) => (
                    <button
                      key={lvl.id}
                      data-testid={`level-btn-${lvl.id}`}
                      onClick={() => setActiveLevelId(lvl.id)}
                      style={{
                        flex: 1,
                        padding: "6px 4px",
                        background: activeLevelId === lvl.id ? "#38bdf8" : "#0f172a",
                        color: activeLevelId === lvl.id ? "#0f172a" : "#cbd5e1",
                        fontWeight: 600,
                        border: "1px solid #475569",
                        borderRadius: 4,
                        cursor: "pointer",
                        fontSize: 11,
                      }}
                    >
                      {lvl.name || lvl.id}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Navigation Tabs */}
          <nav style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2, padding: 8, background: "#0f172a" }}>
            {(
              [
                ["plan", "Plan View"],
                ["comparison", "Comparison"],
                ["schedule", "Schedule"],
                ["findings", "Findings"],
                ["metrics", "Metrics"],
                ["section", "Section"],
                ["history", "History"],
                ["feedback", "Feedback"],
              ] as const
            ).map(([tabId, label]) => (
              <button
                key={tabId}
                data-testid={`tab-${tabId}`}
                onClick={() => setActiveTab(tabId)}
                style={{
                  padding: "6px 8px",
                  background: activeTab === tabId ? "#334155" : "transparent",
                  color: activeTab === tabId ? "#38bdf8" : "#94a3b8",
                  fontWeight: activeTab === tabId ? 700 : 500,
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 11,
                  textAlign: "center",
                }}
              >
                {label}
              </button>
            ))}
          </nav>

          {/* Overlays Toggle in Plan Tab */}
          {activeTab === "plan" && (
            <div style={{ padding: 16, borderBottom: "1px solid #334155" }}>
              <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 700, marginBottom: 8 }}>
                OVERLAYS & VIEW CONTROLS
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={showDimensions}
                    onChange={(e) => setShowDimensions(e.target.checked)}
                  />
                  Dimensions
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={showLabels}
                    onChange={(e) => setShowLabels(e.target.checked)}
                  />
                  Room Labels
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={showPrivacy}
                    onChange={(e) => setShowPrivacy(e.target.checked)}
                  />
                  Privacy & Zoning Fills
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={showSite}
                    onChange={(e) => setShowSite(e.target.checked)}
                  />
                  Site & Parcel Boundaries
                </label>
              </div>
            </div>
          )}

          {/* Context Tab Content or Property Panel */}
          <div style={{ flex: 1, overflowY: "auto" }}>
            {activeTab === "plan" && (
              <PropertyPanel
                selectedId={selectedId}
                selectedKind={selectedKind}
                model={activeModel}
                onAddComment={() => setActiveTab("feedback")}
                onProposeRevision={() => setActiveTab("feedback")}
              />
            )}
            {activeTab === "schedule" && (
              <RoomSchedule
                model={activeModel}
                program={bundle.program}
                evaluation={activePlanEntry?.evaluation}
                onSelectSpace={(id) => {
                  setSelectedId(id);
                  setSelectedKind("space");
                  setActiveTab("plan");
                }}
              />
            )}
            {activeTab === "findings" && (
              <FindingsPanel
                evaluation={activePlanEntry?.evaluation}
                onSelectSubject={(subId) => {
                  setSelectedId(subId);
                  setSelectedKind("space");
                  setActiveTab("plan");
                }}
              />
            )}
            {activeTab === "metrics" && <MetricMatrix evaluation={activePlanEntry?.evaluation} />}
            {activeTab === "section" && <TerrainSection model={activeModel} site={bundle.site} />}
            {activeTab === "history" && (
              <div>
                <RevisionTimeline
                  plans={bundle.plans}
                  selectedOptionId={selectedOptionId}
                  onSelectVersion={(optId) => setSelectedOptionId(optId)}
                />
                <VersionDiff revision={activePlanEntry?.revision} />
              </div>
            )}
            {activeTab === "feedback" && (
              <FeedbackPanel
                projectName={bundle.project.name}
                optionId={selectedOptionId}
                planVersion={activePlanEntry?.version || 1}
                selectedId={selectedId}
              />
            )}
          </div>
        </aside>

        {/* Main Content Area */}
        <main style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          {activeTab === "comparison" ? (
            <ComparisonView plans={bundle.plans} site={bundle.site} />
          ) : (
            <PlanCanvas
              model={activeModel}
              site={bundle.site}
              activeLevelId={activeLevelId}
              selectedId={selectedId}
              onSelectElement={(id, kind) => {
                setSelectedId(id);
                setSelectedKind(kind);
              }}
              showDimensions={showDimensions}
              showLabels={showLabels}
              showPrivacy={showPrivacy}
              showSite={showSite}
              highlightedIds={[]}
            />
          )}
        </main>
      </div>
    </div>
  );
};
