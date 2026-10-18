import React from "react";
import type { EvaluationReport, MetricClaim } from "../types/schemas";

interface MetricMatrixProps {
  evaluation?: EvaluationReport | null;
}

export const MetricMatrix: React.FC<MetricMatrixProps> = ({ evaluation }) => {
  if (!evaluation || !evaluation.metrics || evaluation.metrics.length === 0) {
    return <div style={{ padding: 16, color: "#94a3b8", fontSize: 13 }}>No evaluation metrics available.</div>;
  }

  const metrics: MetricClaim[] = evaluation.metrics;

  const getStatusColor = (status: string) => {
    switch (status) {
      case "measured":
        return { bg: "rgba(34, 197, 94, 0.15)", text: "#4ade80", border: "#22c55e" };
      case "inferred":
        return { bg: "rgba(56, 189, 248, 0.15)", text: "#38bdf8", border: "#0284c7" };
      case "simulated":
        return { bg: "rgba(168, 85, 247, 0.15)", text: "#c084fc", border: "#a855f7" };
      case "ai_judgment":
        return { bg: "rgba(245, 158, 11, 0.15)", text: "#fbbf24", border: "#d97706" };
      case "not_checked":
      default:
        return { bg: "rgba(148, 163, 184, 0.15)", text: "#94a3b8", border: "#64748b" };
    }
  };

  return (
    <div
      data-testid="metric-matrix"
      style={{
        padding: 16,
        background: "#1e293b",
        color: "#f8fafc",
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12, color: "#38bdf8" }}>
        Evaluation Metrics (Epistemic Status)
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {metrics.map((m) => {
          const statusStyle = getStatusColor(m.status);
          const valDisplay =
            m.value === null || m.value === undefined
              ? "null"
              : typeof m.value === "number"
              ? m.value % 1 === 0
                ? m.value
                : m.value.toFixed(2)
              : String(m.value);

          return (
            <div
              key={m.metric}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "rgba(30, 41, 59, 0.7)",
                border: "1px solid #334155",
                padding: "8px 12px",
                borderRadius: 4,
              }}
            >
              <div>
                <div style={{ fontWeight: 600, color: "#e2e8f0" }}>{m.metric}</div>
                <div style={{ color: "#94a3b8", fontSize: 11 }}>method: {m.method}</div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontWeight: 700, fontSize: 13, fontFamily: "monospace" }}>
                  {valDisplay}
                  {m.unit ? ` ${m.unit}` : ""}
                </span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    padding: "2px 6px",
                    borderRadius: 3,
                    background: statusStyle.bg,
                    color: statusStyle.text,
                    border: `1px solid ${statusStyle.border}`,
                  }}
                >
                  {m.status}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
