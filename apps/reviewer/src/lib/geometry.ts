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

/** Zoom limits of the plan canvas, in pixels per metre. */
export const MIN_SCALE_PX_PER_M = 10;
export const MAX_SCALE_PX_PER_M = 100;

/**
 * Bounding box of every space outline on every level, so switching levels keeps the view.
 * Returns null when the model has no space outlines.
 */
export function spacesBoundingBox(
  spaces: { boundary?: { outer?: unknown } | null }[]
): BoundingBox | null {
  const points = spaces.flatMap((s) => (s.boundary?.outer || []) as [number, number][]);
  return points.length > 0 ? computeBoundingBox(points) : null;
}

/** Smallest box containing both boxes (either may be null). */
export function unionBoundingBox(a: BoundingBox | null, b: BoundingBox | null): BoundingBox | null {
  if (!a || !b) return a || b;
  return computeBoundingBox([
    [a.minX, a.minY],
    [a.maxX, a.maxY],
    [b.minX, b.minY],
    [b.maxX, b.maxY],
  ]);
}

/**
 * Scale and pan that centre `bbox` (model metres, y up) in a viewport of `width` x `height`
 * pixels, leaving `marginPx` on every side. Screen x = pan.x + x * scale and
 * screen y = pan.y - y * scale, as drawn by PlanCanvas.
 */
export function fitTransform(
  bbox: BoundingBox,
  width: number,
  height: number,
  marginPx = 48
): { scale: number; pan: { x: number; y: number } } {
  const usableW = Math.max(width - 2 * marginPx, 1);
  const usableH = Math.max(height - 2 * marginPx, 1);
  const raw = Math.min(usableW / Math.max(bbox.width, 1e-6), usableH / Math.max(bbox.height, 1e-6));
  const scale = Math.max(MIN_SCALE_PX_PER_M, Math.min(MAX_SCALE_PX_PER_M, raw));
  const cx = (bbox.minX + bbox.maxX) / 2;
  const cy = (bbox.minY + bbox.maxY) / 2;
  return { scale, pan: { x: width / 2 - cx * scale, y: height / 2 + cy * scale } };
}
