/** Map a metric's tier_label text to a color-banding class.
 *
 * tiers come from services/data/packet.py::_compute_tier:
 *   未进入观察区 / 进入观察区 / 重点观察区
 * Coloring (压力红系, tokens.css):
 *   tier-none  → --muted (灰, 无信号)
 *   tier-enter → --orange-deep (橙, 初步信号)
 *   tier-key   → --red (红, 深度压力/强信号)
 */
export type TierClass = "tier-none" | "tier-enter" | "tier-key";

export function tierClass(label: string | undefined | null): TierClass {
  if (!label) return "tier-none";
  if (label.startsWith("重点")) return "tier-key";
  if (label.startsWith("进入")) return "tier-enter";
  return "tier-none";
}
