import { describe, it, expect } from "vitest";
import { validateReviewerBundle, parseReviewerBundleJson } from "./loader";

describe("Reviewer bundle loader validation (Task S4-05)", () => {
  const validMinimalBundle = {
    schema_version: "1.0.0",
    project: {
      name: "synthetic-hillside",
      state: "CONCEPT_REVIEW",
    },
    gates: {
      site: { approved: true, name: "Site Gate", approve_command: "cmd", description: "desc" },
    },
    plans: [
      {
        option_id: "concept-compact",
        label: "Compact",
        is_exploratory: false,
        plan: {
          schema_version: "0.1.0",
          option_id: "concept-compact",
          label: "Compact",
          provenance: {
            created_at: "2026-10-17T12:00:00Z",
            created_by: { kind: "agent", id: "agent:gemini" },
            method: "plan_generation",
            tool: "house-ai plan generate",
            inputs: [],
          },
          model: {
            schema_version: "0.1.0",
            id: "model-compact",
            label: "Model",
            levels: [{ id: "lvl-ground", label: "Ground", z_m: 0 }],
            spaces: [
              {
                id: "sp-kitchen",
                name: "Kitchen",
                level_id: "lvl-ground",
                polygon: [
                  [0, 0],
                  [4, 0],
                  [4, 4],
                  [0, 4],
                ],
              },
            ],
            walls: [],
            doors: [],
            windows: [],
            stairs: [],
          },
        },
      },
    ],
  };

  it("successfully validates a well-formed bundle", () => {
    const result = validateReviewerBundle(validMinimalBundle);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.bundle.project.name).toBe("synthetic-hillside");
      expect(result.bundle.plans[0].option_id).toBe("concept-compact");
    }
  });

  it("rejects non-object inputs with clear message", () => {
    const result = validateReviewerBundle("invalid string");
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.errors).toContain("Bundle payload must be a non-null object");
    }
  });

  it("reports missing project fields with path", () => {
    const corrupt = { ...validMinimalBundle, project: { state: "CONCEPT_REVIEW" } };
    const result = validateReviewerBundle(corrupt);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.errors.some((e) => e.includes("project.name"))).toBe(true);
    }
  });

  it("reports missing plan model spaces with exact index path", () => {
    const corrupt = {
      ...validMinimalBundle,
      plans: [
        {
          option_id: "concept-compact",
          plan: {
            model: {
              levels: [],
              spaces: [{ name: "Missing ID space" }],
            },
          },
        },
      ],
    };
    const result = validateReviewerBundle(corrupt);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.errors.some((e) => e.includes("plans[0].plan.model.spaces[0].id"))).toBe(true);
    }
  });

  it("parses valid JSON string or returns parse error", () => {
    const validJson = JSON.stringify(validMinimalBundle);
    const successRes = parseReviewerBundleJson(validJson);
    expect(successRes.success).toBe(true);

    const badJsonRes = parseReviewerBundleJson("{ not valid json }");
    expect(badJsonRes.success).toBe(false);
    if (!badJsonRes.success) {
      expect(badJsonRes.errors[0]).toContain("JSON parse error");
    }
  });
});
