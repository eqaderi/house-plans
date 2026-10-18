import React from "react";
import type { RevisionReport, AreaChange } from "../types/schemas";

interface VersionDiffProps {
  revision?: RevisionReport | null;
}

export const VersionDiff: React.FC<VersionDiffProps> = ({ revision }) => {
  if (!revision) {
    return (
      <div style={{ padding: 16, color: "#94a3b8", fontSize: 13 }}>
        No revision history for this version (it is the initial concept).
      </div>
    );
  }

  return (
    <div
      data-testid="version-diff"
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
        Revision Diff: v{revision.from_version?.version} → v{revision.to_version?.version}
      </div>

      <div style={{ background: "rgba(51, 65, 85, 0.4)", padding: "8px 12px", borderRadius: 4 }}>
        <div style={{ color: "#94a3b8", fontSize: 11 }}>Homeowner verbatim request:</div>
        <div style={{ fontStyle: "italic", marginTop: 2, fontWeight: 600 }}>
          "{revision.requested_change}"
        </div>
      </div>

      {/* Changed Spaces */}
      {revision.rooms_changed && revision.rooms_changed.length > 0 && (
        <div>
          <div style={{ fontWeight: 600, color: "#94a3b8", marginBottom: 4 }}>Changed Rooms:</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {revision.rooms_changed.map((r: string) => (
              <span
                key={r}
                style={{
                  background: "#334155",
                  padding: "2px 8px",
                  borderRadius: 4,
                  fontFamily: "monospace",
                }}
              >
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Area Changes */}
      {revision.area_changes && revision.area_changes.length > 0 && (
        <div>
          <div style={{ fontWeight: 600, color: "#94a3b8", marginBottom: 4 }}>Area Changes:</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {revision.area_changes.map((c: AreaChange, idx: number) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "4px 8px",
                  background: "rgba(30, 41, 59, 0.6)",
                  borderRadius: 4,
                }}
              >
                <span style={{ fontFamily: "monospace", color: "#38bdf8" }}>{c.space_id}</span>
                <span>
                  {c.before_m2?.toFixed(1) || "—"} m² →{" "}
                  <strong style={{ color: "#4ade80" }}>{c.after_m2?.toFixed(1) || "—"} m²</strong>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resolved Violations */}
      {revision.resolved_violations && revision.resolved_violations.length > 0 && (
        <div>
          <div style={{ fontWeight: 600, color: "#4ade80", marginBottom: 4 }}>
            ✓ Resolved Violations ({revision.resolved_violations.length}):
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, color: "#86efac" }}>
            {revision.resolved_violations.map((v: string, idx: number) => (
              <li key={idx}>{v}</li>
            ))}
          </ul>
        </div>
      )}

      {/* New Violations */}
      {revision.new_violations && revision.new_violations.length > 0 && (
        <div>
          <div style={{ fontWeight: 600, color: "#f87171", marginBottom: 4 }}>
            ⚠ New Violations ({revision.new_violations.length}):
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, color: "#fca5a5" }}>
            {revision.new_violations.map((v: string, idx: number) => (
              <li key={idx}>{v}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
