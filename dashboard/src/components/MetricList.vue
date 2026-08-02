<script setup lang="ts">
import type { Metric } from "../types";
import { tierClass } from "../utils/tier";
import { useI18n } from "../i18n";

const props = defineProps<{
  metrics: Metric[];
  activeMetricId: string;
}>();

const emit = defineEmits<{
  select: [metricId: string];
}>();
const { t, metric: metricCopy, role, state } = useI18n();

type AvailabilityKey = "current" | "display_only" | "validation_pending" | "missing";

const ROLE_BY_ID: Record<string, "核心锚" | "核心复核" | "强辅助" | "辅助"> = {
  mvrv: "核心锚",
  puell: "核心锚",
  aviv: "核心复核",
  "rul-z": "强辅助",
  asopr: "强辅助",
  seller: "强辅助",
  cvdd: "强辅助",
};

function roleLabel(metric: Metric) {
  if (metric.role === "核心锚" || metric.role === "核心复核" || metric.role === "强辅助") {
    return metric.role;
  }
  // Legacy packets only had “核心 / 辅助”. Resolve both old labels from the
  // v0.3 registry so old fixtures get the same user-facing vocabulary.
  return ROLE_BY_ID[metric.id] ?? "辅助";
}

function roleClass(metric: Metric) {
  const role = roleLabel(metric);
  if (role === "核心锚") return "role-core-anchor";
  if (role === "核心复核") return "role-core-confirmation";
  if (role === "强辅助") return "role-strong-supporting";
  return "role-supporting";
}

function availabilityState(metric: Metric): AvailabilityKey {
  const raw = String(metric.availability_status ?? metric.status ?? "").trim().toLowerCase();
  const normalized = raw.replace(/[\s-]+/g, "_");

  if (metric.judgment_eligible === false) {
    if (["missing", "缺失", "unavailable"].includes(normalized)) return "missing";
    const reason = String(metric.availability_reason ?? metric.reason ?? "").toLowerCase();
    return /验证|pending|校验/.test(reason) || normalized === "validation_pending"
      ? "validation_pending"
      : "display_only";
  }

  if (["current", "available", "fresh", "当前可用"].includes(normalized)) return "current";
  if (["display_only", "display", "仅供展示", "仅供显示"].includes(normalized)) return "display_only";
  if (["validation_pending", "pending", "待验证", "验证中"].includes(normalized)) return "validation_pending";
  if (["missing", "缺失", "unavailable"].includes(normalized)) return "missing";

  // The first v0.3 migration deliberately keeps these two old fixture series
  // visible while preventing them from looking like current evidence.
  const metricDate = metric.current_date || metric.metric_date || "";
  if (["hodler", "spent155"].includes(metric.id) && metricDate <= "2023-01-12") {
    return "display_only";
  }
  return "current";
}

function availabilityLabel(metric: Metric) {
  return {
    current: t("current"),
    display_only: t("displayOnly"),
    validation_pending: t("validation"),
    missing: t("missing"),
  }[availabilityState(metric)];
}

function availabilityNote(metric: Metric) {
  const state = availabilityState(metric);
  // “仅供展示” already communicates the boundary. Do not repeat a stale
  // day-count warning for the two historical holder series.
  if (state === "display_only" && typeof metric.days_stale === "number" && metric.days_stale > 0) return "";
  if (state === "current" && metric.judgment_eligible !== false) return "";
  const parts: string[] = [];
  if (typeof metric.days_stale === "number" && metric.days_stale > 0) {
    parts.push(t("expired", { days: metric.days_stale }));
  }
  const reason = metric.availability_reason ?? metric.reason;
  if (reason?.trim()) {
    parts.push(reason.trim());
  }
  if (state !== "current") parts.push(t("notPart"));
  return Array.from(new Set(parts)).join(" · ");
}

function moveFocus(event: KeyboardEvent, index: number) {
  if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
  if (props.metrics.length === 0) return;
  event.preventDefault();
  const nextIndex = event.key === 'ArrowDown'
    ? (index + 1) % props.metrics.length
    : (index - 1 + props.metrics.length) % props.metrics.length;
  document.getElementById(`metric-${props.metrics[nextIndex].id}`)?.focus();
}
</script>

<template>
  <div class="metric-list" aria-label="Metric list for the selected category">
    <button
      v-for="(metric, index) in metrics"
      :id="`metric-${metric.id}`"
      :key="metric.id"
      type="button"
      class="metric-card"
      :class="{ 'is-active': activeMetricId === metric.id }"
      :aria-pressed="activeMetricId === metric.id"
      :aria-label="`${metricCopy(metric).label} · ${role(roleLabel(metric))} · ${availabilityLabel(metric)} · ${state(metric.tier_label)}`"
      @click="emit('select', metric.id)"
      @keydown="moveFocus($event, index)"
    >
      <span class="metric-role" :class="roleClass(metric)">{{ role(roleLabel(metric)) }}</span>
      <span class="metric-main">
        <strong>{{ metricCopy(metric).label }}</strong>
        <small>{{ metric.current_date || metric.metric_date || t("unknownDate") }} · {{ metric.unit }}</small>
      </span>
      <span class="metric-value">{{ metric.display_value }}</span>
      <span class="metric-tier" :class="tierClass(metric.tier_id, metric.tier_label)">{{ state(metric.tier_label) }}</span>
      <span class="metric-availability" :class="`availability-${availabilityState(metric)}`">{{ availabilityLabel(metric) }}</span>
      <small v-if="availabilityNote(metric)" class="metric-availability-note">{{ availabilityNote(metric) }}</small>
    </button>
  </div>
</template>
