/** Map named calculation bands to the three dashboard color levels. */
export type TierClass = "tier-none" | "tier-enter" | "tier-key";

export function tierClass(label: string | undefined | null): TierClass {
  if (!label) return "tier-none";
  if (label.includes("极端") || label.includes("深度") || label.includes("深部")) return "tier-key";
  if (label.includes("观察") || label.includes("定投")) return "tier-enter";
  return "tier-none";
}
