/**
 * Geometric calculations from canonical model coordinates:
 * Dimensions, polygon area (Shoelace formula), bounding boxes, wall lengths.
 */

export interface Point2D {
  x: number;
  y: number;
}

export interface BoundingBox {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
}

/**
 * Calculate the bounding box of a list of 2D points.
 */
export function computeBoundingBox(points: [number, number][]): BoundingBox {
  if (points.length === 0) {
    return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
  }

  let minX = points[0][0];
  let maxX = points[0][0];
  let minY = points[0][1];
  let maxY = points[0][1];

  for (let i = 1; i < points.length; i++) {
    const [x, y] = points[i];
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: Math.abs(maxX - minX),
    height: Math.abs(maxY - minY),
  };
}

/**
 * Calculate the 2D polygon area in square metres using the Shoelace formula.
 */
export function computePolygonAreaM2(points: [number, number][]): number {
  const n = points.length;
  if (n < 3) return 0;

  let area = 0;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    area += points[i][0] * points[j][1];
    area -= points[j][0] * points[i][1];
  }

  return Math.abs(area) / 2.0;
}

/**
 * Calculate euclidean distance between two 2D points in metres.
 */
export function distanceM(p1: [number, number], p2: [number, number]): number {
  const dx = p2[0] - p1[0];
  const dy = p2[1] - p1[1];
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Format a dimension in metres with 2 decimal places.
 */
export function formatDimM(val: number): string {
  return `${val.toFixed(2)} m`;
}

/**
 * Format an area in square metres with 1 decimal place.
 */
export function formatAreaM2(val: number): string {
  return `${val.toFixed(1)} m²`;
}
