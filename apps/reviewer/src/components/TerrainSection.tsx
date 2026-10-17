import React from "react";
import type { HouseModel } from "../types/schemas";

interface TerrainSectionProps {
  model: HouseModel;
}

export const TerrainSection: React.FC<TerrainSectionProps> = ({ model }) => {
  const levels = model.levels || [];
  const retainingWalls = (model.walls || []).filter((w) => w.kind === "retaining");

  // Sorted levels by elevation_m
  const sortedLevels = [...levels].sort((a, b) => (b.elevation_m || 0) - (a.elevation_m || 0));

  return (
    <div
      data-testid="terrain-section"
      style={{
        padding: 16,
        background: "#1e293b",
        color: "#f8fafc",
        fontSize: 12,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: "#38bdf8" }}>Terrain & Levels Section</div>
        <div
          style={{
            fontSize: 10,
            textTransform: "uppercase",
            fontWeight: 700,
            background: "rgba(245, 158, 11, 0.2)",
            color: "#fbbf24",
            padding: "2px 6px",
            borderRadius: 3,
            border: "1px solid #f59e0b",
          }}
        >
          Schematic (Pending Stage S8)
        </div>
      </div>

      {/* SVG Section Diagram */}
      <svg
        width="100%"
        height="180"
        viewBox="0 0 500 180"
        style={{ background: "#0f172a", borderRadius: 6, border: "1px solid #334155" }}
      >
        {/* Ground slope polyline */}
        <polyline
          points="20,160 150,130 300,70 480,30"
          fill="none"
          stroke="#78716c"
          strokeWidth="3"
          strokeDasharray="4 2"
        />
        <text x="30" y="150" fill="#a8a29e" fontSize="10">Ground profile</text>

        {/* Level bands */}
        {sortedLevels.map((lvl, idx) => {
          const y = 50 + idx * 45;
          return (
            <g key={lvl.id}>
              {/* Level line */}
              <line x1="80" y1={y} x2="420" y2={y} stroke="#38bdf8" strokeWidth="2" />
              {/* Level label & elevation */}
              <text x="70" y={y + 4} fill="#f8fafc" fontSize="11" fontWeight="600" textAnchor="end">
                {lvl.name || lvl.id}
              </text>
              <text x="430" y={y + 4} fill="#38bdf8" fontSize="11" fontWeight="700">
                z = {(lvl.elevation_m || 0).toFixed(1)} m
              </text>
            </g>
          );
        })}

        {/* Retaining wall indicators */}
        {retainingWalls.length > 0 && (
          <g>
            <rect x="290" y="50" width="8" height="45" fill="#f97316" />
            <text x="305" y="75" fill="#fb923c" fontSize="10" fontWeight="600">
              Retaining Wall ({retainingWalls.length})
            </text>
          </g>
        )}
      </svg>
    </div>
  );
};
