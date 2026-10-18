import React from "react";
import type { HouseModel, SpaceProgram, Space, EvaluationReport } from "../types/schemas";
import { computePolygonAreaM2, formatAreaM2 } from "../lib/geometry";

interface RoomScheduleProps {
  model: HouseModel;
  program?: SpaceProgram | null;
  evaluation?: EvaluationReport | null;
  onSelectSpace?: (id: string) => void;
}

export const RoomSchedule: React.FC<RoomScheduleProps> = ({ model, program, evaluation, onSelectSpace }) => {
  const spaces = model.spaces || [];

  // Group spaces by level_id
  const spacesByLevel: Record<string, Space[]> = {};
  spaces.forEach((sp: Space) => {
    const lvl = sp.level_id || "ground";
    if (!spacesByLevel[lvl]) spacesByLevel[lvl] = [];
    spacesByLevel[lvl].push(sp);
  });

  // Calculate areas and program targets
  const programItemsMap = new Map<string, number>();
  if (program && program.items) {
    program.items.forEach((item: any) => {
      if (item.target_area_m2) {
        programItemsMap.set(item.id, item.target_area_m2);
      }
    });
  }

  let totalGrossAreaM2 = 0;
  const netAreas = new Map<string, number>();
  const incomplete = new Set<string>();
  for (const metric of evaluation?.metrics || []) {
    if (metric.evaluator !== "NetAreaEvaluator" || metric.subject_ids?.length !== 1) continue;
    // Inferred when the wall model is incomplete (marked with *); never shown when not checked.
    if (metric.metric === "net_area_m2" && (metric.status === "measured" || metric.status === "inferred") && typeof metric.value === "number") {
      netAreas.set(metric.subject_ids[0], metric.value);
    }
    if (metric.metric === "net_wall_basis_complete" && metric.value === false) {
      incomplete.add(metric.subject_ids[0]);
    }
  }
  const netComplete = spaces.length > 0 && spaces.every((sp) => netAreas.has(sp.id));
  const totalNet = spaces.reduce((sum, sp) => sum + (netAreas.get(sp.id) || 0), 0);

  return (
    <div
      data-testid="room-schedule"
      style={{
        padding: 16,
        background: "#1e293b",
        color: "#f8fafc",
        fontSize: 12,
        overflowX: "auto",
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12, color: "#38bdf8" }}>
        Room Schedule (Centreline Gross and Modelled Net)
      </div>

      {Object.entries(spacesByLevel).map(([lvlId, lvlSpaces]) => {
        let levelAreaM2 = 0;

        return (
          <div key={lvlId} style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 600, color: "#94a3b8", borderBottom: "1px solid #334155", paddingBottom: 4, marginBottom: 6 }}>
              Level: {lvlId}
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
              <thead>
                <tr style={{ color: "#64748b", borderBottom: "1px solid #334155" }}>
                  <th style={{ padding: "4px 8px" }}>ID</th>
                  <th style={{ padding: "4px 8px" }}>Name</th>
                  <th style={{ padding: "4px 8px" }}>Gross Area</th>
                  <th style={{ padding: "4px 8px" }}>Net Area</th>
                  <th style={{ padding: "4px 8px" }}>Program Target</th>
                  <th style={{ padding: "4px 8px" }}>Delta</th>
                </tr>
              </thead>
              <tbody>
                {lvlSpaces.map((sp: Space) => {
                  const poly = (sp.boundary?.outer || []) as [number, number][];
                  const area = (poly.length > 0 ? computePolygonAreaM2(poly) : 0)
                    - (sp.boundary?.holes || []).reduce((sum, ring) => sum + computePolygonAreaM2(ring as [number, number][]), 0);
                  levelAreaM2 += area;
                  totalGrossAreaM2 += area;

                  // Look for target area
                  const target = sp.program_item_id ? programItemsMap.get(sp.program_item_id) : undefined;
                  const delta = target ? area - target : null;
                  const deltaPct = target ? ((delta! / target) * 100).toFixed(0) : null;

                  return (
                    <tr
                      key={sp.id}
                      onClick={() => onSelectSpace && onSelectSpace(sp.id)}
                      style={{
                        cursor: "pointer",
                        borderBottom: "1px solid rgba(51, 65, 85, 0.5)",
                      }}
                    >
                      <td style={{ padding: "4px 8px", fontFamily: "monospace", color: "#38bdf8" }}>{sp.id}</td>
                      <td style={{ padding: "4px 8px" }}>{sp.name || "—"}</td>
                      <td style={{ padding: "4px 8px", fontWeight: 600 }}>{formatAreaM2(area)}</td>
                      <td style={{ padding: "4px 8px" }} title={incomplete.has(sp.id) ? "Incomplete wall model; net area subtracts modelled walls only" : "From net-area evaluation; includes floor-level doorway recesses"}>
                        {netAreas.has(sp.id) ? formatAreaM2(netAreas.get(sp.id)!) : "not checked"}
                        {incomplete.has(sp.id) ? " *" : ""}
                      </td>
                      <td style={{ padding: "4px 8px", color: "#94a3b8" }}>{target ? formatAreaM2(target) : "—"}</td>
                      <td
                        style={{
                          padding: "4px 8px",
                          color: delta === null ? "#64748b" : delta >= 0 ? "#4ade80" : "#f87171",
                        }}
                      >
                        {delta !== null ? `${delta >= 0 ? "+" : ""}${formatAreaM2(delta)} (${deltaPct}%)` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr style={{ fontWeight: 600, color: "#cbd5e1", borderTop: "1px solid #475569" }}>
                  <td colSpan={2} style={{ padding: "6px 8px" }}>Level Total</td>
                  <td style={{ padding: "6px 8px" }}>{formatAreaM2(levelAreaM2)}</td>
                  <td style={{ padding: "6px 8px" }}>{lvlSpaces.every((sp) => netAreas.has(sp.id)) ? formatAreaM2(lvlSpaces.reduce((sum, sp) => sum + netAreas.get(sp.id)!, 0)) : "not checked"}</td>
                  <td colSpan={2} />
                </tr>
              </tfoot>
            </table>
          </div>
        );
      })}

      <div
        style={{
          borderTop: "2px solid #475569",
          paddingTop: 8,
          display: "flex",
          justifyContent: "space-between",
          fontWeight: 700,
          fontSize: 13,
        }}
      >
        <span>Total Building Gross Area:</span>
        <span style={{ color: "#38bdf8" }}>{formatAreaM2(totalGrossAreaM2)}</span>
      </div>
      <div style={{ paddingTop: 8 }}>
        Total Modelled Net Area: {netComplete ? formatAreaM2(totalNet) : "not checked"}
        {incomplete.size > 0 && <div>* Incomplete wall model; see net-area findings.</div>}
      </div>
    </div>
  );
};
