import { describe, it, expect } from "vitest";
import {
  computeBoundingBox,
  computePolygonAreaM2,
  distanceM,
  formatDimM,
  formatAreaM2,
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
