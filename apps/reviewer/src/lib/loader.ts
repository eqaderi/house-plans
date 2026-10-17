/**
 * Schema-validated loading of ReviewerBundle, PlanVersion and HouseModel.
 * Provides clear, human-readable errors with exact path locations on failure.
 */

import type { ReviewerBundle } from "../types/schemas";

export interface BundleLoadSuccess {
  success: true;
  bundle: ReviewerBundle;
}

export interface BundleLoadFailure {
  success: false;
  errors: string[];
}

export type BundleLoadResult = BundleLoadSuccess | BundleLoadFailure;

/**
 * Validates that an unknown object conforms to the expected ReviewerBundle structure.
 */
export function validateReviewerBundle(data: unknown): BundleLoadResult {
  const errors: string[] = [];

  if (!data || typeof data !== "object") {
    return { success: false, errors: ["Bundle payload must be a non-null object"] };
  }

  const obj = data as Record<string, unknown>;

  // Schema version
  if (typeof obj.schema_version !== "string" || !obj.schema_version.trim()) {
    errors.push("schema_version: missing or not a valid string");
  }

  // Project
  if (!obj.project || typeof obj.project !== "object") {
    errors.push("project: missing project object");
  } else {
    const proj = obj.project as Record<string, unknown>;
    if (typeof proj.name !== "string" || !proj.name.trim()) {
      errors.push("project.name: missing or empty project name");
    }
    if (typeof proj.state !== "string" || !proj.state.trim()) {
      errors.push("project.state: missing or empty project state");
    }
  }

  // Gates
  if (!obj.gates || typeof obj.gates !== "object") {
    errors.push("gates: missing gates object");
  }

  // Plans
  if (!Array.isArray(obj.plans)) {
    errors.push("plans: missing plans array");
  } else {
    obj.plans.forEach((planEntry: unknown, idx: number) => {
      const path = `plans[${idx}]`;
      if (!planEntry || typeof planEntry !== "object") {
        errors.push(`${path}: must be an object`);
        return;
      }

      const pe = planEntry as Record<string, unknown>;
      if (typeof pe.option_id !== "string" || !pe.option_id.trim()) {
        errors.push(`${path}.option_id: missing or empty option_id`);
      }

      if (!pe.plan || typeof pe.plan !== "object") {
        errors.push(`${path}.plan: missing PlanVersion object`);
        return;
      }

      const planObj = pe.plan as Record<string, unknown>;
      if (!planObj.model || typeof planObj.model !== "object") {
        errors.push(`${path}.plan.model: missing HouseModel object`);
        return;
      }

      const model = planObj.model as Record<string, unknown>;
      if (!Array.isArray(model.spaces)) {
        errors.push(`${path}.plan.model.spaces: missing spaces array`);
      } else {
        model.spaces.forEach((sp: unknown, sIdx: number) => {
          const spPath = `${path}.plan.model.spaces[${sIdx}]`;
          if (!sp || typeof sp !== "object") {
            errors.push(`${spPath}: space must be an object`);
            return;
          }
          const spObj = sp as Record<string, unknown>;
          if (typeof spObj.id !== "string" || !spObj.id.trim()) {
            errors.push(`${spPath}.id: space missing id`);
          }
        });
      }

      if (!Array.isArray(model.levels)) {
        errors.push(`${path}.plan.model.levels: missing levels array`);
      }
    });
  }

  if (errors.length > 0) {
    return { success: false, errors };
  }

  return { success: true, bundle: data as ReviewerBundle };
}

/**
 * Parse and validate a bundle JSON string.
 */
export function parseReviewerBundleJson(jsonStr: string): BundleLoadResult {
  try {
    const parsed = JSON.parse(jsonStr);
    return validateReviewerBundle(parsed);
  } catch (err) {
    return {
      success: false,
      errors: [`JSON parse error: ${err instanceof Error ? err.message : String(err)}`],
    };
  }
}
