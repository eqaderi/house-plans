import { describe, it, expect } from "vitest";
import {
  computeBoundingBox,
  computePolygonAreaM2,
  distanceM,
  fitTransform,
  formatDimM,
  formatAreaM2,
  MAX_SCALE_PX_PER_M,
  MIN_SCALE_PX_PER_M,
  spacesBoundingBox,
  unionBoundingBox,
} from "./geometry";

describe("Geometric calculations (Task S4-10)", () => {
  it("computes exact bounding box for a rectangular polygon", () => {
    const points: [number, number][] = [
      [2, 3],
      [8, 3],
      [8, 7],
      [2, 7],
    ];
    const bbox = computeBoundingBox(points);
    expect(bbox.minX).toBe(2);
    expect(bbox.minY).toBe(3);
    expect(bbox.maxX).toBe(8);
    expect(bbox.maxY).toBe(7);
    expect(bbox.width).toBe(6);
    expect(bbox.height).toBe(4);
  });

  it("computes polygon area via Shoelace formula", () => {
    // 4m x 5m rectangle -> 20 m2
    const rect: [number, number][] = [
      [0, 0],
      [4, 0],
      [4, 5],
      [0, 5],
    ];
    expect(computePolygonAreaM2(rect)).toBe(20.0);

    // Right-angled triangle: base 3m, height 4m -> 6 m2
    const triangle: [number, number][] = [
      [0, 0],
      [3, 0],
      [0, 4],
    ];
    expect(computePolygonAreaM2(triangle)).toBe(6.0);
  });

  it("computes euclidean distance between points", () => {
    expect(distanceM([0, 0], [3, 4])).toBe(5.0);
  });

  it("formats dimensions and areas correctly", () => {
    expect(formatDimM(3.456)).toBe("3.46 m");
    expect(formatAreaM2(25.38)).toBe("25.4 m²");
  });
});

describe("Fit the plan into the viewport (S10-02)", () => {
  const box = computeBoundingBox([
    [10, 20],
    [30, 30],
  ]);

  it("centres the box and fits its limiting side", () => {
    // 800 x 600 px, 48 px margins: 704 / 20 m = 35.2, 504 / 10 m = 50.4 -> 35.2 px/m.
    const t = fitTransform(box, 800, 600);
    expect(t.scale).toBeCloseTo(35.2, 9);
    // Centre (20, 25) lands on (400, 300): 400 - 20 * 35.2 and 300 + 25 * 35.2.
    expect(t.pan.x).toBeCloseTo(-304, 9);
    expect(t.pan.y).toBeCloseTo(1180, 9);
    const left = t.pan.x + 10 * t.scale;
    const top = t.pan.y - 30 * t.scale;
    expect(left).toBeCloseTo(48, 9);
    expect(top).toBeGreaterThanOrEqual(48);
  });

  it("keeps the zoom limits", () => {
    const tiny = computeBoundingBox([
      [0, 0],
      [1, 1],
    ]);
    expect(fitTransform(tiny, 800, 600).scale).toBe(MAX_SCALE_PX_PER_M);
    const huge = computeBoundingBox([
      [0, 0],
      [500, 500],
    ]);
    expect(fitTransform(huge, 800, 600).scale).toBe(MIN_SCALE_PX_PER_M);
  });

  it("unions space outlines across levels and boxes", () => {
    const spaces = [
      { boundary: { outer: [[0, 0], [4, 3]] } },
      { boundary: { outer: [[10, -2], [12, 1]] } },
      { boundary: null },
    ];
    const b = spacesBoundingBox(spaces)!;
    expect([b.minX, b.minY, b.maxX, b.maxY]).toEqual([0, -2, 12, 3]);
    expect(spacesBoundingBox([])).toBeNull();
    const u = unionBoundingBox(b, box)!;
    expect([u.minX, u.minY, u.maxX, u.maxY]).toEqual([0, -2, 30, 30]);
    expect(unionBoundingBox(null, b)).toBe(b);
  });
});
