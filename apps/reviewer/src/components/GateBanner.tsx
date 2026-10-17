import React from "react";
import type { GateApprovalInfo } from "../types/schemas";

interface GateBannerProps {
  gates: Record<string, GateApprovalInfo>;
}

export const GateBanner: React.FC<GateBannerProps> = ({ gates }) => {
  const gateKeys = ["site", "program", "plan", "model"];

  return (
    <div
      data-testid="gate-banner"
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "12px",
        padding: "10px 16px",
        background: "#1e293b",
        color: "#f8fafc",
        borderBottom: "1px solid #334155",
        fontSize: "13px",
      }}
    >
      <div style={{ fontWeight: 600, display: "flex", alignItems: "center" }}>
        Human Approval Gates:
      </div>
      {gateKeys.map((key) => {
        const info = gates[key];
        if (!info) return null;
        const isApproved = info.approved;

        return (
          <div
            key={key}
            data-testid={`gate-indicator-${key}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "4px",
              background: isApproved ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${isApproved ? "#22c55e" : "#ef4444"}`,
            }}
          >
            <span style={{ fontWeight: 600 }}>{info.name}:</span>
            <span
              style={{
                color: isApproved ? "#4ade80" : "#f87171",
                fontWeight: 700,
                textTransform: "uppercase",
                fontSize: "11px",
              }}
            >
              {isApproved ? "Approved" : "Pending"}
            </span>
            {!isApproved && (
              <span
                style={{
                  fontSize: "10px",
                  color: "#cbd5e1",
                  fontFamily: "monospace",
                  background: "rgba(0,0,0,0.3)",
                  padding: "2px 6px",
                  borderRadius: "2px",
                }}
              >
                CLI: <code>{info.approve_command || `house-ai workflow approve <project> ${key}`}</code>
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};
