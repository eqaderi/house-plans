import React from "react";
import type { HouseModel, Space, Wall, Opening, Stair } from "../types/schemas";
import { computeBoundingBox, computePolygonAreaM2, formatDimM, formatAreaM2 } from "../lib/geometry";

interface PropertyPanelProps {
  selectedId: string | null;
  selectedKind: string | null;
  model: HouseModel;
  onAddComment?: (elementId: string) => void;
  onProposeRevision?: (elementId: string) => void;
}

export const PropertyPanel: React.FC<PropertyPanelProps> = ({
  selectedId,
  selectedKind,
  model,
  onAddComment,
  onProposeRevision,
}) => {
  if (!selectedId || !selectedKind) {
    return (
      <div style={{ padding: 16, color: "#94a3b8", fontSize: 13 }}>
        Click any room, wall, opening or stair in the plan to inspect its properties.
      </div>
    );
  }

  let elementData: any = null;
  if (selectedKind === "space") {
    elementData = (model.spaces || []).find((s: Space) => s.id === selectedId);
  } else if (selectedKind === "wall") {
    elementData = (model.walls || []).find((w: Wall) => w.id === selectedId);
  } else if (selectedKind === "door" || selectedKind === "window" || selectedKind === "opening") {
    elementData = (model.openings || []).find((o: Opening) => o.id === selectedId);
  } else if (selectedKind === "stair") {
    elementData = (model.stairs || []).find((st: Stair) => st.id === selectedId);
  }

  if (!elementData) {
    return (
      <div style={{ padding: 16, color: "#ef4444", fontSize: 13 }}>
        Element {selectedId} ({selectedKind}) not found in model.
      </div>
    );
  }

  let areaM2: number | null = null;
  let dims: { width: number; height: number } | null = null;
  const polyPoints = (elementData.boundary?.outer || elementData.footprint?.outer) as [number, number][] | undefined;
  if (polyPoints && polyPoints.length > 0) {
    areaM2 = computePolygonAreaM2(polyPoints);
    const bbox = computeBoundingBox(polyPoints);
    dims = { width: bbox.width, height: bbox.height };
  }

  return (
    <div
      data-testid="property-panel"
      style={{
        padding: 16,
        background: "#1e293b",
        color: "#f8fafc",
        fontSize: 13,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div style={{ borderBottom: "1px solid #334155", paddingBottom: 8 }}>
        <div style={{ textTransform: "uppercase", fontSize: 11, color: "#94a3b8", fontWeight: 700 }}>
          {selectedKind}
        </div>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#38bdf8", wordBreak: "break-all" }}>
          {selectedId}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {elementData.name && (
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Name</div>
            <div style={{ fontWeight: 600 }}>{elementData.name}</div>
          </div>
        )}
        {elementData.level_id && (
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Level</div>
            <div style={{ fontWeight: 600 }}>{elementData.level_id}</div>
          </div>
        )}
        {elementData.kind && (
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Kind</div>
            <div style={{ fontWeight: 600 }}>{elementData.kind}</div>
          </div>
        )}
        {areaM2 !== null && (
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Gross Area (centreline)</div>
            <div style={{ fontWeight: 600, color: "#4ade80" }}>{formatAreaM2(areaM2)}</div>
          </div>
        )}
        {dims && (
          <div style={{ gridColumn: "span 2" }}>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Dimensions (W × L)</div>
            <div style={{ fontWeight: 600 }}>
              {formatDimM(dims.width)} × {formatDimM(dims.height)}
            </div>
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        {onAddComment && (
          <button
            onClick={() => onAddComment(selectedId)}
            style={{
              flex: 1,
              padding: "6px 12px",
              background: "#334155",
              color: "#f8fafc",
              border: "1px solid #475569",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            Add Comment
          </button>
        )}
        {onProposeRevision && selectedKind === "space" && (
          <button
            onClick={() => onProposeRevision(selectedId)}
            style={{
              flex: 1,
              padding: "6px 12px",
              background: "#0284c7",
              color: "#f8fafc",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            Revise Area
          </button>
        )}
      </div>
    </div>
  );
};
