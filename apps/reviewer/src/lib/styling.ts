import type { Space } from "../types/schemas";
import { PRIVACY_COLORS } from "../constants";

/**
 * Computes privacy / zoning fill color for a given space, checking zone_id, canonical function,
 * and falling back to room name keywords.
 */
export function getSpacePrivacyColor(sp: Space): string {
  // 1. Check zone_id
  const zone = (sp.zone_id || "").toLowerCase();
  if (zone.includes("night") || zone.includes("priv")) {
    return PRIVACY_COLORS.PRIVATE;
  }
  if (zone.includes("day") || zone.includes("pub")) {
    return PRIVACY_COLORS.PUBLIC;
  }
  if (zone.includes("serv")) {
    return PRIVACY_COLORS.SERVICE;
  }

  // 2. Check canonical function
  const fn = (sp.function || "").toLowerCase();
  const privateFunctions = new Set(["bedroom", "bathroom", "wc", "ablution", "guest_suite"]);
  const publicFunctions = new Set(["living", "family", "reception", "dining", "entry", "hall", "corridor", "terrace", "balcony"]);
  const serviceFunctions = new Set(["kitchen", "pantry", "storage", "laundry", "mechanical", "garage"]);
  const semiPrivateFunctions = new Set(["study", "gym", "play", "prayer"]);

  if (privateFunctions.has(fn)) return PRIVACY_COLORS.PRIVATE;
  if (publicFunctions.has(fn)) return PRIVACY_COLORS.PUBLIC;
  if (serviceFunctions.has(fn)) return PRIVACY_COLORS.SERVICE;
  if (semiPrivateFunctions.has(fn)) return PRIVACY_COLORS.SEMI_PRIVATE;

  // 3. Fallback to room name matching
  const nameLower = (sp.name || "").toLowerCase();
  if (nameLower.includes("bed") || nameLower.includes("bath") || nameLower.includes("wc")) {
    return PRIVACY_COLORS.PRIVATE;
  }
  if (nameLower.includes("liv") || nameLower.includes("din") || nameLower.includes("entry") || nameLower.includes("hall")) {
    return PRIVACY_COLORS.PUBLIC;
  }
  if (nameLower.includes("kitch") || nameLower.includes("pant") || nameLower.includes("stor") || nameLower.includes("laund") || nameLower.includes("mech")) {
    return PRIVACY_COLORS.SERVICE;
  }
  if (nameLower.includes("stud") || nameLower.includes("gym") || nameLower.includes("play") || nameLower.includes("pray")) {
    return PRIVACY_COLORS.SEMI_PRIVATE;
  }

  return PRIVACY_COLORS.DEFAULT;
}
