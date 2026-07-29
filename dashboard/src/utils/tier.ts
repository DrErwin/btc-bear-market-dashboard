/** Stable calibration ids keep colour independent from editorial labels. */
export type TierClass = "tier-none" | "tier-enter" | "tier-key";

export function tierClass(tierId?: string | null, legacyLabel?: string | null): TierClass {
  const stable = String(tierId ?? "").trim();
  if (stable === "extreme_pressure" || stable === "deep_pressure") return "tier-key";
  if (stable === "observation") return "tier-enter";
  // Only old packets use the label fallback; v0.4 packets always provide id.
  const label = String(legacyLabel ?? "");
  if (label.includes("极端") || label.includes("深度") || label.includes("深部")) return "tier-key";
  if (label.includes("观察")) return "tier-enter";
  return "tier-none";
}
