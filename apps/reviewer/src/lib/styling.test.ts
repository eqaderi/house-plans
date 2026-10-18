import { describe, it, expect } from "vitest";
import { getSpacePrivacyColor } from "./styling";
import { PRIVACY_COLORS } from "../constants";
import type { Space } from "../types/schemas";

describe("getSpacePrivacyColor", () => {
  it("uses zone_id when present", () => {
    const sp: Space = {
      id: "sp-1",
      name: "Custom Room",
      function: "other",
      level_id: "lvl-1",
      zone_id: "z-night",
      boundary: { outer: [[0, 0], [1, 0], [1, 1], [0, 1]] },
    };
    expect(getSpacePrivacyColor(sp)).toBe(PRIVACY_COLORS.PRIVATE);
  });

  it("identifies canonical function when zone_id is empty", () => {
    const spBed: Space = {
      id: "sp-2",
      name: "Suite",
      function: "bedroom",
      level_id: "lvl-1",
      boundary: { outer: [] },
    };
    expect(getSpacePrivacyColor(spBed)).toBe(PRIVACY_COLORS.PRIVATE);

    const spLiv: Space = {
      id: "sp-3",
      name: "Main Room",
      function: "living",
      level_id: "lvl-1",
      boundary: { outer: [] },
    };
    expect(getSpacePrivacyColor(spLiv)).toBe(PRIVACY_COLORS.PUBLIC);

    const spKit: Space = {
      id: "sp-4",
      name: "Food Prep",
      function: "kitchen",
      level_id: "lvl-1",
      boundary: { outer: [] },
    };
    expect(getSpacePrivacyColor(spKit)).toBe(PRIVACY_COLORS.SERVICE);
  });

  it("falls back to room name keywords", () => {
    const spFallback: Space = {
      id: "sp-5",
      name: "Master Bedroom",
      function: "other",
      level_id: "lvl-1",
      boundary: { outer: [] },
    };
    expect(getSpacePrivacyColor(spFallback)).toBe(PRIVACY_COLORS.PRIVATE);
  });
});
