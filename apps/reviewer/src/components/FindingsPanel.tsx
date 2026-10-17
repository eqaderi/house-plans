import React from "react";
import type { EvaluationReport, Violation } from "../types/schemas";

interface FindingsPanelProps {
  evaluation?: EvaluationReport | null;
  onSelectSubject?: (subjectId: string) => void;
}

export const FindingsPanel: React.FC<FindingsPanelProps> = ({ evaluation, onSelectSubject }) => {
  if (!evaluation) {
    return <div style={{ padding: 16, color: "#94a3b8", fontSize: 13 }}>No evaluation report available.</div>;
  }

  const allViolations = evaluation.violations || [];
  const hardViolations = allViolations.filter((v: Violation) => v.strength === "hard");
  const softViolations = allViolations.filter((v: Violation) => v.strength === "soft");

  const complianceText = evaluation.compliance?.status || (hardViolations.length === 0 ? "COMPLIANT" : "VIOLATIONS");

  return (
    <div
      data-testid="findings-panel"
      style={{
        padding: 16,
        background: "#1e293b",
        color: "#f8fafc",
        fontSize: 12,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: "#38bdf8" }}>Evaluator Findings</div>
        <div
          style={{
            fontSize: 11,
            padding: "2px 8px",
            borderRadius: 4,
            fontWeight: 700,
            textTransform: "uppercase",
            background: hardViolations.length === 0 ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)",
            color: hardViolations.length === 0 ? "#4ade80" : "#f87171",
          }}
        >
          {complianceText}
        </div>
      </div>

      {/* Hard Violations */}
      <div>
        <div style={{ fontWeight: 600, color: "#f87171", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
          <span>⛔ Hard Violations</span>
          <span style={{ fontSize: 11, background: "#ef4444", color: "#fff", padding: "1px 6px", borderRadius: 10 }}>
            {hardViolations.length}
          </span>
        </div>
        {hardViolations.length === 0 ? (
          <div style={{ color: "#64748b", fontStyle: "italic" }}>No blocking hard violations.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {hardViolations.map((v: Violation, idx: number) => (
              <div
                key={v.id || idx}
                style={{
                  background: "rgba(239, 68, 68, 0.1)",
                  borderLeft: "3px solid #ef4444",
                  padding: "6px 8px",
                  borderRadius: "0 4px 4px 0",
                }}
              >
                <div style={{ fontWeight: 600, color: "#fca5a5" }}>{v.code}</div>
                <div style={{ color: "#e2e8f0" }}>{v.message}</div>
                {v.subject_ids && v.subject_ids.length > 0 && (
                  <div style={{ marginTop: 4, display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {v.subject_ids.map((sub: string) => (
                      <span
                        key={sub}
                        onClick={() => onSelectSubject && onSelectSubject(sub)}
                        style={{
                          fontSize: 10,
                          fontFamily: "monospace",
                          background: "#ef4444",
                          color: "#fff",
                          padding: "1px 5px",
                          borderRadius: 3,
                          cursor: "pointer",
                        }}
                      >
                        {sub}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Soft Warnings */}
      <div>
        <div style={{ fontWeight: 600, color: "#fbbf24", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
          <span>⚠️ Soft Warnings</span>
          <span style={{ fontSize: 11, background: "#f59e0b", color: "#fff", padding: "1px 6px", borderRadius: 10 }}>
            {softViolations.length}
          </span>
        </div>
        {softViolations.length === 0 ? (
          <div style={{ color: "#64748b", fontStyle: "italic" }}>No soft warnings.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {softViolations.map((v: Violation, idx: number) => (
              <div
                key={v.id || idx}
                style={{
                  background: "rgba(245, 158, 11, 0.1)",
                  borderLeft: "3px solid #f59e0b",
                  padding: "6px 8px",
                  borderRadius: "0 4px 4px 0",
                }}
              >
                <div style={{ fontWeight: 600, color: "#fde68a" }}>{v.code}</div>
                <div style={{ color: "#e2e8f0" }}>{v.message}</div>
                {v.subject_ids && v.subject_ids.length > 0 && (
                  <div style={{ marginTop: 4, display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {v.subject_ids.map((sub: string) => (
                      <span
                        key={sub}
                        onClick={() => onSelectSubject && onSelectSubject(sub)}
                        style={{
                          fontSize: 10,
                          fontFamily: "monospace",
                          background: "#d97706",
                          color: "#fff",
                          padding: "1px 5px",
                          borderRadius: 3,
                          cursor: "pointer",
                        }}
                      >
                        {sub}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
