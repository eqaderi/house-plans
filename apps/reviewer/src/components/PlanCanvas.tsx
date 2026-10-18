import React, { useState, useRef } from "react";
import type { HouseModel, Site, Space, Wall, Opening, Stair } from "../types/schemas";
import { computeBoundingBox, formatDimM, distanceM } from "../lib/geometry";
import { getSpacePrivacyColor } from "../lib/styling";
import { DATA_ATTRS } from "../constants";

interface PlanCanvasProps {
  model: HouseModel;
  site?: Site | null;
  activeLevelId: string;
  selectedId: string | null;
  onSelectElement: (id: string, kind: string) => void;
  showDimensions?: boolean;
  showLabels?: boolean;
  showPrivacy?: boolean;
  showSite?: boolean;
  highlightedIds?: string[];
  scale?: number;
  pan?: { x: number; y: number };
  onTransformChange?: (scale: number, pan: { x: number; y: number }) => void;
}

export const PlanCanvas: React.FC<PlanCanvasProps> = ({
  model,
  site,
  activeLevelId,
  selectedId,
  onSelectElement,
  showDimensions = true,
  showLabels = true,
  showPrivacy = false,
  showSite = true,
  highlightedIds = [],
  scale: controlledScale,
  pan: controlledPan,
  onTransformChange,
}) => {
  const [internalScale, setInternalScale] = useState<number>(30); // pixels per metre
  const [internalPan, setInternalPan] = useState<{ x: number; y: number }>({ x: 200, y: 200 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStart = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const currentScale = controlledScale !== undefined ? controlledScale : internalScale;
  const currentPan = controlledPan !== undefined ? controlledPan : internalPan;

  const setScale = (updater: number | ((prev: number) => number)) => {
    const nextVal = typeof updater === "function" ? updater(currentScale) : updater;
    const clamped = Math.max(10, Math.min(100, nextVal));
    if (controlledScale === undefined) {
      setInternalScale(clamped);
    }
    onTransformChange?.(clamped, currentPan);
  };

  const setPan = (updater: { x: number; y: number } | ((prev: { x: number; y: number }) => { x: number; y: number })) => {
    const nextVal = typeof updater === "function" ? updater(currentPan) : updater;
    if (controlledPan === undefined) {
      setInternalPan(nextVal);
    }
    onTransformChange?.(currentScale, nextVal);
  };

  // Filter entities by active level
  const spaces = (model.spaces || []).filter(
    (s: Space) => !s.level_id || s.level_id === activeLevelId
  );
  const walls = (model.walls || []).filter(
    (w: Wall) => !w.level_id || w.level_id === activeLevelId
  );
  const wallMap = new Map<string, Wall>();
  walls.forEach((w) => wallMap.set(w.id, w));

  const openings = (model.openings || []).filter((o: Opening) => wallMap.has(o.host_wall_id));
  const stairs = (model.stairs || []).filter(
    (st: Stair) => st.from_level_id === activeLevelId || st.to_level_id === activeLevelId
  );

  // Check site CRS confirmation status
  const crsConfirmed =
    site?.coordinates?.horizontal_crs?.status === "user_confirmed" ||
    site?.coordinates?.horizontal_crs?.status === "local_only_confirmed";

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true);
      dragStart.current = { x: e.clientX - currentPan.x, y: e.clientY - currentPan.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({ x: e.clientX - dragStart.current.x, y: e.clientY - dragStart.current.y });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setScale((prev) => Math.max(10, Math.min(100, prev * factor)));
  };

  const toPx = (m: number) => m * currentScale;
  const toYPx = (m: number) => -m * currentScale;

  return (
    <div
      data-testid="plan-canvas"
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "hidden",
        background: "#0f172a",
        cursor: isDragging ? "grabbing" : "grab",
        userSelect: "none",
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Zoom / Pan Controls Overlay */}
      <div
        style={{
          position: "absolute",
          top: 16,
          right: 16,
          display: "flex",
          gap: 6,
          zIndex: 10,
          background: "rgba(15, 23, 42, 0.85)",
          padding: 6,
          borderRadius: 6,
          border: "1px solid #334155",
        }}
      >
        <button
          onClick={() => setScale((s) => Math.min(100, s * 1.2))}
          style={{ padding: "4px 8px", cursor: "pointer", background: "#334155", color: "#fff", border: "none", borderRadius: 4 }}
        >
          +
        </button>
        <button
          onClick={() => setScale((s) => Math.max(10, s * 0.8))}
          style={{ padding: "4px 8px", cursor: "pointer", background: "#334155", color: "#fff", border: "none", borderRadius: 4 }}
        >
          -
        </button>
        <button
          onClick={() => {
            setScale(30);
            setPan({ x: 200, y: 200 });
          }}
          style={{ padding: "4px 8px", cursor: "pointer", background: "#334155", color: "#fff", border: "none", borderRadius: 4 }}
        >
          Reset
        </button>
      </div>

      {/* North Arrow / Orientation Badge */}
      <div
        data-testid="north-indicator"
        style={{
          position: "absolute",
          bottom: 16,
          right: 16,
          display: "flex",
          alignItems: "center",
          gap: 8,
          zIndex: 10,
          background: "rgba(15, 23, 42, 0.85)",
          padding: "6px 12px",
          borderRadius: 6,
          border: "1px solid #334155",
          color: "#f8fafc",
          fontSize: 12,
        }}
      >
        {crsConfirmed ? (
          <>
            <svg width="24" height="24" viewBox="0 0 24 24">
              <path d="M12 2L17 20L12 16L7 20L12 2Z" fill="#38bdf8" />
            </svg>
            <span style={{ fontWeight: 600 }}>North (Confirmed)</span>
          </>
        ) : (
          <span style={{ color: "#fbbf24" }}>⚠️ Orientation unconfirmed / North unknown</span>
        )}
      </div>

      <svg
        style={{ width: "100%", height: "100%" }}
        data-testid="plan-svg"
      >
        <g transform={`translate(${currentPan.x}, ${currentPan.y})`}>
          {/* Site boundary overlay */}
          {showSite && site?.boundary?.outer && (
            <polygon
              data-id="site-parcel-boundary"
              data-kind={DATA_ATTRS.KINDS.PARCEL}
              points={(site.boundary.outer as [number, number][]).map(([x, y]) => `${toPx(x)},${toYPx(y)}`).join(" ")}
              fill="rgba(56, 189, 248, 0.03)"
              stroke="#38bdf8"
              strokeWidth="2"
              strokeDasharray="4 4"
            />
          )}

          {/* Site buildable envelope overlay */}
          {showSite &&
            (() => {
              const envOuter = (site?.buildable_envelope?.polygon?.outer ||
                (site?.buildable_envelope as any)?.outer) as [number, number][] | undefined;
              if (!envOuter || envOuter.length === 0) return null;
              return (
                <polygon
                  data-id="site-buildable-envelope"
                  data-kind={DATA_ATTRS.KINDS.ENVELOPE}
                  points={envOuter.map(([x, y]) => `${toPx(x)},${toYPx(y)}`).join(" ")}
                  fill="rgba(234, 179, 8, 0.04)"
                  stroke="#eab308"
                  strokeWidth="1.5"
                  strokeDasharray="6 3"
                />
              );
            })()}

          {/* Spaces / Rooms */}
          {spaces.map((sp: Space) => {
            const isSelected = selectedId === sp.id;
            const isHighlighted = highlightedIds.includes(sp.id);
            const polyPoints = (sp.boundary?.outer || []) as [number, number][];
            const bbox = polyPoints.length > 0 ? computeBoundingBox(polyPoints) : null;

            // Zone / Privacy color
            const fillColor = showPrivacy
              ? getSpacePrivacyColor(sp)
              : "rgba(71, 85, 105, 0.25)";

            return (
              <g
                key={sp.id}
                data-id={sp.id}
                data-kind="space"
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectElement(sp.id, "space");
                }}
              >
                {polyPoints.length > 0 && (
                  <polygon
                    data-id={sp.id}
                    data-kind="space"
                    points={polyPoints.map(([x, y]) => `${toPx(x)},${toYPx(y)}`).join(" ")}
                    fill={isSelected ? "rgba(56, 189, 248, 0.4)" : isHighlighted ? "rgba(239, 68, 68, 0.35)" : fillColor}
                    stroke={isSelected ? "#38bdf8" : isHighlighted ? "#ef4444" : "#94a3b8"}
                    strokeWidth={isSelected || isHighlighted ? 3 : 1}
                  />
                )}
                {/* Space Label */}
                {showLabels && bbox && (
                  <text
                    x={toPx(bbox.minX + bbox.width / 2)}
                    y={toYPx(bbox.minY + bbox.height / 2)}
                    fill="#f8fafc"
                    fontSize="12"
                    fontWeight="600"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    pointerEvents="none"
                  >
                    {sp.name || sp.id}
                  </text>
                )}
                {/* Dimensions */}
                {showDimensions && bbox && (
                  <text
                    x={toPx(bbox.minX + bbox.width / 2)}
                    y={toYPx(bbox.minY + bbox.height / 2) + 14}
                    fill="#94a3b8"
                    fontSize="10"
                    textAnchor="middle"
                    pointerEvents="none"
                  >
                    {formatDimM(bbox.width)} × {formatDimM(bbox.height)}
                  </text>
                )}
              </g>
            );
          })}

          {/* Walls */}
          {walls.map((w: Wall) => {
            const isSelected = selectedId === w.id;
            const isHighlighted = highlightedIds.includes(w.id);
            const thickness = w.kind === "retaining" ? 6 : w.kind === "exterior" ? 5 : 3;

            return (
              <line
                key={w.id}
                data-id={w.id}
                data-kind="wall"
                x1={toPx(w.start[0])}
                y1={toYPx(w.start[1])}
                x2={toPx(w.end[0])}
                y2={toYPx(w.end[1])}
                stroke={isSelected ? "#38bdf8" : isHighlighted ? "#ef4444" : w.kind === "retaining" ? "#f97316" : "#cbd5e1"}
                strokeWidth={thickness}
                strokeLinecap="round"
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectElement(w.id, "wall");
                }}
              />
            );
          })}

          {/* Openings (Doors and Windows) */}
          {openings.map((o: Opening) => {
            const hostWall = wallMap.get(o.host_wall_id);
            if (!hostWall) return null;

            const isSelected = selectedId === o.id;
            const isHighlighted = highlightedIds.includes(o.id);
            const dx = hostWall.end[0] - hostWall.start[0];
            const dy = hostWall.end[1] - hostWall.start[1];
            const wallLen = distanceM([hostWall.start[0], hostWall.start[1]], [hostWall.end[0], hostWall.end[1]]);
            if (wallLen <= 0) return null;

            const ux = dx / wallLen;
            const uy = dy / wallLen;
            const opStart: [number, number] = [
              hostWall.start[0] + ux * o.offset_m,
              hostWall.start[1] + uy * o.offset_m,
            ];
            const opEnd: [number, number] = [
              opStart[0] + ux * o.width_m,
              opStart[1] + uy * o.width_m,
            ];

            const isDoor = o.kind === "door";

            return (
              <g
                key={o.id}
                data-id={o.id}
                data-kind={isDoor ? "door" : "window"}
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectElement(o.id, isDoor ? "door" : "window");
                }}
              >
                <line
                  x1={toPx(opStart[0])}
                  y1={toYPx(opStart[1])}
                  x2={toPx(opEnd[0])}
                  y2={toYPx(opEnd[1])}
                  stroke={isSelected ? "#38bdf8" : isHighlighted ? "#ef4444" : isDoor ? "#f8fafc" : "#0284c7"}
                  strokeWidth={isDoor ? 2 : 4}
                  strokeDasharray={isDoor ? "2 2" : "none"}
                />
              </g>
            );
          })}

          {/* Stairs */}
          {stairs.map((st: Stair) => {
            const isSelected = selectedId === st.id;
            const isHighlighted = highlightedIds.includes(st.id);
            const polyPoints = (st.footprint?.outer || []) as [number, number][];
            const bbox = polyPoints.length > 0 ? computeBoundingBox(polyPoints) : null;

            return (
              <g
                key={st.id}
                data-id={st.id}
                data-kind="stair"
                style={{ cursor: "pointer" }}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectElement(st.id, "stair");
                }}
              >
                {polyPoints.length > 0 && (
                  <polygon
                    points={polyPoints.map(([x, y]) => `${toPx(x)},${toYPx(y)}`).join(" ")}
                    fill={isSelected ? "rgba(56, 189, 248, 0.3)" : isHighlighted ? "rgba(239, 68, 68, 0.3)" : "rgba(245, 158, 11, 0.15)"}
                    stroke={isSelected ? "#38bdf8" : "#f59e0b"}
                    strokeWidth="2"
                  />
                )}
                {bbox && (
                  <text
                    x={toPx(bbox.minX + bbox.width / 2)}
                    y={toYPx(bbox.minY + bbox.height / 2)}
                    fill="#fbbf24"
                    fontSize="11"
                    textAnchor="middle"
                    pointerEvents="none"
                  >
                    Stairs ↗
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
};
