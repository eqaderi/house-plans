import React, { useState } from "react";
import type { ReviewerPlanEntry, Site } from "../types/schemas";
import { PlanCanvas } from "./PlanCanvas";

interface ComparisonViewProps {
  plans: ReviewerPlanEntry[];
  site?: Site | null;
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({ plans, site }) => {
  const [leftOptionIdx, setLeftOptionIdx] = useState<number>(0);
  const [rightOptionIdx, setRightOptionIdx] = useState<number>(plans.length > 1 ? 1 : 0);
  const [activeLevelId, setActiveLevelId] = useState<string>("lvl-ground");
  const [viewMode, setViewMode] = useState<"side-by-side" | "table">("side-by-side");
  const [scale, setScale] = useState<number>(30);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 200, y: 200 });

  const handleTransformChange = (newScale: number, newPan: { x: number; y: number }) => {
    setScale(newScale);
    setPan(newPan);
  };

  if (plans.length === 0) {
    return <div style={{ padding: 24, color: "#94a3b8" }}>No plans available for comparison.</div>;
  }

  const leftPlan = plans[leftOptionIdx] || plans[0];
  const rightPlan = plans[rightOptionIdx] || plans[0];
  const allLevels = leftPlan?.plan?.model?.levels || [];

  // Collect all unique metric names across all plans
  const allMetricNames = Array.from(
    new Set(
      plans.flatMap((p) => (p.evaluation?.metrics ? p.evaluation.metrics.map((m) => m.metric) : []))
    )
  ).sort();

  return (
    <div
      data-testid="comparison-view"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#0f172a",
        color: "#f8fafc",
      }}
    >
      {/* View Switcher Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "10px 16px",
          background: "#1e293b",
          borderBottom: "1px solid #334155",
        }}
      >
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ fontWeight: 700, color: "#38bdf8" }}>Concept Comparison</span>
          <div style={{ display: "flex", background: "#0f172a", borderRadius: 4, padding: 2 }}>
            <button
              onClick={() => setViewMode("side-by-side")}
              style={{
                padding: "4px 10px",
                background: viewMode === "side-by-side" ? "#38bdf8" : "transparent",
                color: viewMode === "side-by-side" ? "#0f172a" : "#94a3b8",
                fontWeight: 600,
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              Side-by-Side Canvas
            </button>
            <button
              onClick={() => setViewMode("table")}
              style={{
                padding: "4px 10px",
                background: viewMode === "table" ? "#38bdf8" : "transparent",
                color: viewMode === "table" ? "#0f172a" : "#94a3b8",
                fontWeight: 600,
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              Metrics Table
            </button>
          </div>

          {viewMode === "side-by-side" && allLevels.length > 1 && (
            <div style={{ display: "flex", gap: 4, alignItems: "center", marginLeft: 8 }}>
              <span style={{ fontSize: 11, color: "#94a3b8" }}>Level:</span>
              {allLevels.map((lvl) => (
                <button
                  key={lvl.id}
                  onClick={() => setActiveLevelId(lvl.id)}
                  style={{
                    padding: "2px 8px",
                    background: activeLevelId === lvl.id ? "#38bdf8" : "#0f172a",
                    color: activeLevelId === lvl.id ? "#0f172a" : "#94a3b8",
                    border: "1px solid #334155",
                    borderRadius: 3,
                    fontSize: 11,
                    cursor: "pointer",
                  }}
                >
                  {lvl.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {viewMode === "side-by-side" && (
          <div style={{ display: "flex", gap: 16 }}>
            <div>
              <label style={{ fontSize: 11, color: "#94a3b8", marginRight: 6 }}>Left:</label>
              <select
                value={leftOptionIdx}
                onChange={(e) => setLeftOptionIdx(Number(e.target.value))}
                style={{ background: "#0f172a", color: "#fff", border: "1px solid #334155", padding: "4px 8px", borderRadius: 4 }}
              >
                {plans.map((p, idx) => (
                  <option key={p.option_id} value={idx}>
                    {p.label || p.option_id} (v{p.version || 1})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 11, color: "#94a3b8", marginRight: 6 }}>Right:</label>
              <select
                value={rightOptionIdx}
                onChange={(e) => setRightOptionIdx(Number(e.target.value))}
                style={{ background: "#0f172a", color: "#fff", border: "1px solid #334155", padding: "4px 8px", borderRadius: 4 }}
              >
                {plans.map((p, idx) => (
                  <option key={p.option_id} value={idx}>
                    {p.label || p.option_id} (v{p.version || 1})
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Main View Area */}
      {viewMode === "side-by-side" ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", height: "calc(100% - 48px)" }}>
          <div style={{ borderRight: "1px solid #334155", position: "relative" }}>
            <div
              style={{
                position: "absolute",
                top: 8,
                left: 8,
                zIndex: 10,
                background: "rgba(15, 23, 42, 0.8)",
                padding: "4px 8px",
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 600,
                color: "#38bdf8",
              }}
            >
              {leftPlan.label} ({leftPlan.strategy})
            </div>
            <PlanCanvas
              model={leftPlan.plan.model}
              site={site}
              activeLevelId={activeLevelId}
              selectedId={null}
              onSelectElement={() => {}}
              scale={scale}
              pan={pan}
              onTransformChange={handleTransformChange}
            />
          </div>
          <div style={{ position: "relative" }}>
            <div
              style={{
                position: "absolute",
                top: 8,
                left: 8,
                zIndex: 10,
                background: "rgba(15, 23, 42, 0.8)",
                padding: "4px 8px",
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 600,
                color: "#38bdf8",
              }}
            >
              {rightPlan.label} ({rightPlan.strategy})
            </div>
            <PlanCanvas
              model={rightPlan.plan.model}
              site={site}
              activeLevelId={activeLevelId}
              selectedId={null}
              onSelectElement={() => {}}
              scale={scale}
              pan={pan}
              onTransformChange={handleTransformChange}
            />
          </div>
        </div>
      ) : (
        /* Alternative Metrics Table */
        <div style={{ padding: 16, overflowY: "auto", flex: 1 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #334155" }}>
                <th style={{ textAlign: "left", padding: "8px 12px", color: "#94a3b8" }}>Metric</th>
                {plans.map((p) => (
                  <th key={p.option_id} style={{ textAlign: "left", padding: "8px 12px" }}>
                    <div style={{ color: "#38bdf8", fontWeight: 700 }}>{p.label || p.option_id}</div>
                    <div style={{ fontSize: 10, color: "#94a3b8" }}>{p.strategy || "—"}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {allMetricNames.map((name) => (
                <tr key={name} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "8px 12px", fontWeight: 600 }}>{name}</td>
                  {plans.map((p) => {
                    const m = p.evaluation?.metrics?.find((claim) => claim.metric === name);
                    return (
                      <td key={p.option_id} style={{ padding: "8px 12px" }}>
                        {m ? (
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span style={{ fontFamily: "monospace", fontWeight: 600 }}>
                              {m.value === null ? "null" : typeof m.value === "number" ? m.value.toFixed(1) : String(m.value)}
                              {m.unit ? ` ${m.unit}` : ""}
                            </span>
                            <span style={{ fontSize: 9, textTransform: "uppercase", color: "#94a3b8" }}>
                              [{m.status}]
                            </span>
                          </div>
                        ) : (
                          <span style={{ color: "#64748b" }}>—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
