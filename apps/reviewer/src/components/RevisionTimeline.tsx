import React from "react";
import type { ReviewerPlanEntry } from "../types/schemas";

interface RevisionTimelineProps {
  plans: ReviewerPlanEntry[];
  selectedOptionId: string;
  onSelectVersion?: (optionId: string, version: number) => void;
}

export const RevisionTimeline: React.FC<RevisionTimelineProps> = ({
  plans,
  selectedOptionId,
  onSelectVersion,
}) => {
  // Filter plans matching this option
  const optionPlans = plans
    .filter((p) => p.option_id === selectedOptionId)
    .sort((a, b) => (a.version || 1) - (b.version || 1));

  if (optionPlans.length === 0) {
    return <div style={{ padding: 16, color: "#94a3b8" }}>No versions found for {selectedOptionId}.</div>;
  }

  return (
    <div
      data-testid="revision-timeline"
      style={{
        padding: 16,
        background: "#1e293b",
        color: "#f8fafc",
        fontSize: 12,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 14, color: "#38bdf8" }}>
        Revision History ({selectedOptionId})
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {optionPlans.map((p) => {
          const v = p.version || 1;
          const cr = p.plan.change_request;
          const ops = p.plan.generation?.revision_ops || [];

          return (
            <div
              key={v}
              style={{
                background: "rgba(15, 23, 42, 0.7)",
                border: "1px solid #334155",
                borderRadius: 6,
                padding: "10px 12px",
                cursor: onSelectVersion ? "pointer" : "default",
              }}
              onClick={() => onSelectVersion && onSelectVersion(p.option_id, v)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontWeight: 700, color: "#38bdf8", fontSize: 13 }}>
                  Version {v} {v === 1 && "(Initial Concept)"}
                </span>
                <span style={{ color: "#94a3b8", fontSize: 11 }}>
                  {p.plan.provenance?.created_at?.slice(0, 10) || "—"}
                </span>
              </div>

              {cr?.text && (
                <div style={{ fontStyle: "italic", color: "#e2e8f0", margin: "4px 0" }}>
                  "{cr.text}"
                </div>
              )}

              {ops.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <div style={{ fontSize: 10, color: "#94a3b8", fontWeight: 600 }}>Applied Operations:</div>
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 2 }}>
                    {ops.map((op, idx) => (
                      <span
                        key={idx}
                        style={{
                          fontSize: 10,
                          background: "#0f172a",
                          border: "1px solid #475569",
                          padding: "1px 6px",
                          borderRadius: 3,
                          fontFamily: "monospace",
                          color: "#4ade80",
                        }}
                      >
                        {op}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
