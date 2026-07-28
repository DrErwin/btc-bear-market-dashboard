<script setup lang="ts">
import type { Metric } from "../types";
import { tierClass } from "../utils/tier";

const props = defineProps<{
  metrics: Metric[];
  activeMetricId: string;
}>();

const emit = defineEmits<{
  select: [metricId: string];
}>();

function moveFocus(event: KeyboardEvent, index: number) {
  if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
  event.preventDefault();
  const nextIndex = event.key === 'ArrowDown'
    ? (index + 1) % props.metrics.length
    : (index - 1 + props.metrics.length) % props.metrics.length;
  document.getElementById(`metric-${props.metrics[nextIndex].id}`)?.focus();
}
</script>

<template>
  <div class="metric-list" aria-label="当前分类指标列表">
    <button
      v-for="(metric, index) in metrics"
      :id="`metric-${metric.id}`"
      :key="metric.id"
      type="button"
      class="metric-card"
      :class="{ 'is-active': activeMetricId === metric.id }"
      :aria-pressed="activeMetricId === metric.id"
      @click="emit('select', metric.id)"
      @keydown="moveFocus($event, index)"
    >
      <span class="metric-role" :class="metric.role === '核心' ? 'is-core' : 'is-supporting'">{{ metric.role }}</span>
      <span class="metric-main">
        <strong>{{ metric.label }}</strong>
        <small>{{ metric.current_date }} · {{ metric.unit }}</small>
      </span>
      <span class="metric-value">{{ metric.display_value }}</span>
      <span class="metric-tier" :class="tierClass(metric.tier_label)">{{ metric.tier_label }}</span>
    </button>
  </div>
</template>
