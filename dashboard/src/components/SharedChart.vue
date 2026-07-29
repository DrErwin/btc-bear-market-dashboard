<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  DataZoomComponent,
  GridComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import { BarChart, LineChart } from "echarts/charts";
import VChart from "vue-echarts";
import {
  chartLineColor,
  chartLineVisibilityKey,
  getChartLineDisplayLabel,
  getDedicatedChartLineToggleGroups,
  getRenderableChartLines,
  hasDedicatedChartLineControls,
  isChartLineGroupVisible,
  isChartLineVisible,
  toggleChartLineGroup,
  type ChartVisibility,
  type ResolvedChartLineToggleGroup,
} from "../chartLineControls";
import type { BarSeries, BottomMark, Metric, MetricLine, SeriesData } from "../types";
import { useChartOption, type ZoomRange } from "../composables/useChartOption";
import { tierClass } from "../utils/tier";

use([
  CanvasRenderer,
  GridComponent,
  MarkLineComponent,
  TooltipComponent,
  DataZoomComponent,
  LineChart,
  BarChart,
]);

const props = defineProps<{
  metric: Metric;
  series: SeriesData;
  bars: Record<string, BarSeries>;
  bottoms: BottomMark[];
}>();

const metricRef = computed(() => props.metric);
const seriesRef = computed(() => props.series);
const barsRef = computed(() => props.bars);
const bottomsRef = computed(() => props.bottoms);
const zoom = ref<ZoomRange>({ start: 0, end: 100 });
const logPrice = ref(false);
const CHART_HEIGHT_STORAGE_KEY = "btc-dashboard.chart-height.v1";
const DEFAULT_CHART_HEIGHT = 420;
const MIN_CHART_HEIGHT = 320;
const MAX_CHART_HEIGHT = 760;
const CHART_HEIGHT_STEP = 24;

function clampChartHeight(value: number) {
  return Math.max(MIN_CHART_HEIGHT, Math.min(MAX_CHART_HEIGHT, Math.round(value)));
}

function readChartHeight() {
  if (typeof window === "undefined") return DEFAULT_CHART_HEIGHT;
  try {
    const raw = window.localStorage.getItem(CHART_HEIGHT_STORAGE_KEY);
    if (raw === null) return DEFAULT_CHART_HEIGHT;
    const stored = Number(raw);
    if (!Number.isFinite(stored) || stored < MIN_CHART_HEIGHT || stored > MAX_CHART_HEIGHT) {
      return DEFAULT_CHART_HEIGHT;
    }
    return clampChartHeight(stored);
  } catch {
    return DEFAULT_CHART_HEIGHT;
  }
}

const chartHeight = ref(readChartHeight());
const fullscreenActive = ref(false);

function persistChartHeight() {
  try {
    window.localStorage.setItem(CHART_HEIGHT_STORAGE_KEY, String(chartHeight.value));
  } catch {
    // Private browsing or a blocked storage policy should not stop resizing.
  }
}

function setChartHeight(value: number) {
  chartHeight.value = clampChartHeight(value);
  persistChartHeight();
}

const chartWrapStyle = computed(() => ({
  height: fullscreenActive.value
    ? "clamp(320px, calc(100vh - 290px), 760px)"
    : `${chartHeight.value}px`,
}));

// Single legend is also the curve toggle (v0.2.2 #3): each flag drives one
// series' opacity, and for thresholds / bear-bottoms whether the markLine group
// is included at all. State persists across metric switches.
const visibility = ref<ChartVisibility>({
  price: true,
  indicator: true,
  thresholds: true,
  bottoms: true,
  hodler: true,
  spent: true,
  lines: {},
});
const option = useChartOption(metricRef, seriesRef, barsRef, zoom, bottomsRef, logPrice, visibility);

const sourceChartLines = computed<MetricLine[]>(() => {
  const metricSeries = props.series.metrics[props.metric.id];
  return metricSeries?.lines?.length
    ? metricSeries.lines
    : [{ id: "primary", label: props.metric.label, axis: "indicator", points: metricSeries?.points ?? [] }];
});
const chartLines = computed(() => getRenderableChartLines(props.metric.id, sourceChartLines.value));
const extraChartLines = computed(() => chartLines.value.filter((line) => line.id !== "primary"));
const hasThresholds = computed(() => (props.series.metrics[props.metric.id]?.thresholds.length ?? 0) > 0);
const hasDedicatedLineControls = computed(() => hasDedicatedChartLineControls(props.metric.id));
const dedicatedLineToggleGroups = computed(() => getDedicatedChartLineToggleGroups(props.metric.id, chartLines.value));
const showDefaultIndicatorToggle = computed(() => !hasDedicatedLineControls.value
  && chartLines.value.some((line) => line.id === "primary" && line.axis === "indicator"));
function lineVisibilityKey(line: MetricLine) {
  return chartLineVisibilityKey(props.metric.id, line.id);
}
function isLineVisible(line: MetricLine) {
  return isChartLineVisible(props.metric.id, line, visibility.value);
}
function toggleLine(line: MetricLine) {
  const key = lineVisibilityKey(line);
  visibility.value.lines[key] = !isLineVisible(line);
}
function isLineGroupVisible(group: ResolvedChartLineToggleGroup) {
  return isChartLineGroupVisible(props.metric.id, group.lines, visibility.value);
}
function toggleLineGroup(group: ResolvedChartLineToggleGroup) {
  toggleChartLineGroup(props.metric.id, group.lines, visibility.value);
}
function lineColor(line: MetricLine | undefined) {
  if (!line) return "#e2a06e";
  return chartLineColor(
    line,
    chartLines.value.findIndex((candidate) => candidate.id === line.id),
    chartLines.value.some((candidate) => candidate.id === "primary"),
  );
}
function lineDisplayLabel(line: MetricLine) {
  return getChartLineDisplayLabel(props.metric, line);
}

// Each bar metric owns one series: HODLer and >=155d are separate views.
const showHodlerBar = computed(() => props.metric.id === "hodler");
const showSpentBar = computed(() => props.metric.id === "spent155");
const isBarMetric = computed(() => showHodlerBar.value || showSpentBar.value);
const chartAriaLabel = computed(() => {
  if (showHodlerBar.value) return "BTC 价格、HODLer 柱状图、历史熊底共享图表";
  if (showSpentBar.value) return "BTC 价格、≥155d 柱状图、历史熊底共享图表";
  const metricSeries = props.series.metrics[props.metric.id];
  const references = metricSeries?.thresholds.map((threshold) => threshold.label).join("、") || "无";
  const lines = chartLines.value.map((line) => lineDisplayLabel(line)).join("、");
  const thresholdPhrase = hasThresholds.value ? "与阈值线" : "";
  return `BTC 价格、${props.metric.label}${thresholdPhrase}、历史熊底共享图表；参考线：${references}；曲线：${lines}`;
});

interface RangeOption {
  id: string;
  label: string;
  days: number | null;
}
const RANGES: RangeOption[] = [
  { id: "6m", label: "6 月", days: 182 },
  { id: "1y", label: "1 年", days: 365 },
  { id: "2y", label: "2 年", days: 730 },
  { id: "4y", label: "4 年", days: 1460 },
  { id: "all", label: "全量", days: null },
];
const activeRange = ref<string>("all");

const dates = computed(() => props.series.price.map((point) => point.date));
const rangeLabel = computed(() => {
  const arr = dates.value;
  if (!arr.length) return "";
  const n = arr.length;
  const startIdx = Math.max(0, Math.min(n - 1, Math.floor((zoom.value.start / 100) * n)));
  const endIdx = Math.max(0, Math.min(n - 1, Math.ceil((zoom.value.end / 100) * n) - 1));
  return `${arr[startIdx]} ~ ${arr[endIdx]}`;
});

function applyRange(option: RangeOption) {
  activeRange.value = option.id;
  const n = dates.value.length;
  if (option.days === null || option.days >= n) {
    zoom.value = { start: 0, end: 100 };
    return;
  }
  const startIdx = Math.max(0, n - option.days);
  zoom.value = { start: (startIdx / n) * 100, end: 100 };
}

function onZoom(event: { start?: number; end?: number; batch?: Array<{ start?: number; end?: number }> }) {
  const batch = event.batch?.[0];
  const start = batch?.start ?? event.start;
  const end = batch?.end ?? event.end;
  if (start === undefined || end === undefined) return;
  zoom.value = { start, end };
  const matched = RANGES.find((range) => {
    if (range.days === null) return start <= 0.5 && end >= 99.5;
    const n = dates.value.length;
    const expected = (Math.max(0, n - range.days) / n) * 100;
    return Math.abs(start - expected) < 0.6 && end >= 99.5;
  });
  activeRange.value = matched?.id ?? "custom";
}

const hodlerBar = computed(() => showHodlerBar.value ? (props.bars["hodler_npc_30d"] ?? null) : null);
const spentBar = computed(() => showSpentBar.value ? (props.bars["spent_value_ge155d_share"] ?? null) : null);

const hasVisibleBars = computed(() => {
  if (!isBarMetric.value) return true;
  const datesInView = new Set(dates.value.slice(
    Math.max(0, Math.floor((zoom.value.start / 100) * dates.value.length)),
    Math.min(dates.value.length, Math.ceil((zoom.value.end / 100) * dates.value.length)),
  ));
  return [hodlerBar.value, spentBar.value].some((bar) =>
    bar?.points.some((point) => datesInView.has(point.date) && Number.isFinite(point.value)),
  );
});

function fullscreen() {
  const root = chartCardRef.value;
  if (root?.requestFullscreen) void root.requestFullscreen();
}

function onFullscreenChange() {
  fullscreenActive.value = document.fullscreenElement === chartCardRef.value;
}

const chartCardRef = ref<HTMLElement | null>(null);
const resizing = ref(false);
let resizeStartClientY = 0;
let resizeStartHeight = DEFAULT_CHART_HEIGHT;

function onResizeStart(event: PointerEvent) {
  if (event.button !== 0 && event.pointerType === "mouse") return;
  resizeStartClientY = event.clientY;
  resizeStartHeight = chartHeight.value;
  resizing.value = true;
  event.preventDefault();
  event.stopPropagation();
  window.addEventListener("pointermove", onResizeMove);
  window.addEventListener("pointerup", onResizeEnd);
  window.addEventListener("pointercancel", onResizeEnd);
}

function onResizeMove(event: PointerEvent) {
  if (!resizing.value) return;
  setChartHeight(resizeStartHeight + (event.clientY - resizeStartClientY));
}

function onResizeEnd() {
  if (!resizing.value) return;
  resizing.value = false;
  window.removeEventListener("pointermove", onResizeMove);
  window.removeEventListener("pointerup", onResizeEnd);
  window.removeEventListener("pointercancel", onResizeEnd);
}

function onResizeKeydown(event: KeyboardEvent) {
  if (event.key === "ArrowUp") {
    event.preventDefault();
    setChartHeight(chartHeight.value - CHART_HEIGHT_STEP);
  } else if (event.key === "ArrowDown") {
    event.preventDefault();
    setChartHeight(chartHeight.value + CHART_HEIGHT_STEP);
  } else if (event.key === "Home") {
    event.preventDefault();
    setChartHeight(MIN_CHART_HEIGHT);
  } else if (event.key === "End") {
    event.preventDefault();
    setChartHeight(MAX_CHART_HEIGHT);
  }
}

// v0.2.2 #2: in-chart drag-to-pan. ECharts `inside` dataZoom.moveOnMouseDrag is
// unreliable alongside a tooltip axisPointer (browser-reproed: wheel zoom works,
// drag pan does not). So pan manually — a left-drag on the plot area shifts the
// visible window by rewriting zoom.value, which the slider + inside zoom both
// follow. The bottom slider/axis zone is skipped so ECharts still owns it.
const chartWrapRef = ref<HTMLElement | null>(null);
const dragging = ref(false);
let dragStartClientX = 0;
let dragStartZoom: ZoomRange = { start: 0, end: 100 };
let dragWidth = 0;

function onDragStart(event: MouseEvent) {
  const el = chartWrapRef.value;
  if (!el || event.button !== 0) return;
  const rect = el.getBoundingClientRect();
  // Skip the bottom slider / axis-label zone — let ECharts handle drags there.
  if (event.clientY - rect.top > rect.height - 60) return;
  dragWidth = rect.width;
  if (dragWidth <= 0) return;
  dragStartClientX = event.clientX;
  dragStartZoom = { ...zoom.value };
  dragging.value = true;
  window.addEventListener("mousemove", onDragMove);
  window.addEventListener("mouseup", onDragEnd);
  event.preventDefault();
}

function onDragMove(event: MouseEvent) {
  if (!dragging.value) return;
  const span = dragStartZoom.end - dragStartZoom.start;
  if (span >= 100) return; // whole range visible — nowhere to pan
  const dx = event.clientX - dragStartClientX;
  // Drag right (dx>0) "grabs" the chart, revealing older data → window shifts
  // toward the start (lower start/end).
  const shift = (dx / dragWidth) * span;
  const start = Math.max(0, Math.min(100 - span, dragStartZoom.start - shift));
  zoom.value = { start, end: start + span };
  activeRange.value = "custom";
}

function onDragEnd() {
  if (!dragging.value) return;
  dragging.value = false;
  window.removeEventListener("mousemove", onDragMove);
  window.removeEventListener("mouseup", onDragEnd);
}

onMounted(() => {
  document.addEventListener("fullscreenchange", onFullscreenChange);
});

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onDragMove);
  window.removeEventListener("mouseup", onDragEnd);
  window.removeEventListener("pointermove", onResizeMove);
  window.removeEventListener("pointerup", onResizeEnd);
  window.removeEventListener("pointercancel", onResizeEnd);
  document.removeEventListener("fullscreenchange", onFullscreenChange);
});
</script>

<template>
  <section ref="chartCardRef" class="chart-card" aria-labelledby="chart-title">
    <div class="chart-head">
      <div>
        <h3 id="chart-title">{{ metric.label }}</h3>
      </div>
      <button class="chart-expand" type="button" aria-label="放大共享图表" @click="fullscreen">放大 <span aria-hidden="true">↗</span></button>
    </div>

    <div class="chart-toolbar" role="group" aria-label="时间范围与坐标">
      <span class="range-label" aria-live="polite">{{ rangeLabel || "无可用日期" }}</span>
      <div class="range-buttons">
        <button
          v-for="range in RANGES"
          :key="range.id"
          type="button"
          class="range-btn"
          :class="{ 'is-active': activeRange === range.id }"
          :aria-pressed="activeRange === range.id"
          @click="applyRange(range)"
        >
          {{ range.label }}
        </button>
        <span class="toolbar-sep" aria-hidden="true"></span>
        <button type="button" class="range-btn" :class="{ 'is-active': !logPrice }" :aria-pressed="!logPrice" @click="logPrice = false">线性</button>
        <button type="button" class="range-btn" :class="{ 'is-active': logPrice }" :aria-pressed="logPrice" @click="logPrice = true">对数</button>
      </div>
    </div>

    <div class="chart-legend" role="group" aria-label="图例与曲线开关">
      <button type="button" class="legend-toggle" :class="{ 'is-off': !visibility.price }" :aria-pressed="visibility.price" @click="visibility.price = !visibility.price"><i class="legend-line price"></i>BTC 价格</button>
      <template v-if="!isBarMetric">
        <template v-if="hasDedicatedLineControls">
          <button
            v-for="group in dedicatedLineToggleGroups"
            :key="group.id"
            type="button"
            class="legend-toggle legend-line-toggle"
            :class="{ 'is-off': !isLineGroupVisible(group) }"
            :aria-pressed="isLineGroupVisible(group)"
            :data-line-control="group.id"
            @click="toggleLineGroup(group)"
          >
            <i class="legend-line extra" :style="{ backgroundColor: lineColor(group.lines[0]) }"></i>{{ group.label }}
          </button>
        </template>
        <template v-else>
          <button v-if="showDefaultIndicatorToggle" type="button" class="legend-toggle" :class="{ 'is-off': !visibility.indicator }" :aria-pressed="visibility.indicator" @click="visibility.indicator = !visibility.indicator"><i class="legend-line indicator"></i>{{ metric.label }}</button>
          <button
            v-for="line in extraChartLines"
            :key="line.id"
            type="button"
            class="legend-toggle legend-line-toggle"
            :class="{ 'is-off': !isLineVisible(line) }"
            :aria-pressed="isLineVisible(line)"
            @click="toggleLine(line)"
          >
            <i class="legend-line extra" :style="{ backgroundColor: lineColor(line) }"></i>{{ lineDisplayLabel(line) }}
          </button>
        </template>
        <button v-if="hasThresholds" type="button" class="legend-toggle" :class="{ 'is-off': !visibility.thresholds }" :aria-pressed="visibility.thresholds" @click="visibility.thresholds = !visibility.thresholds"><i class="legend-line threshold"></i>阈值线</button>
      </template>
      <button type="button" class="legend-toggle" :class="{ 'is-off': !visibility.bottoms }" :aria-pressed="visibility.bottoms" @click="visibility.bottoms = !visibility.bottoms"><i class="legend-line bottom"></i>历史熊底</button>
      <template v-if="isBarMetric">
        <button v-if="showHodlerBar" type="button" class="legend-toggle" :class="{ 'is-off': !visibility.hodler }" :aria-pressed="visibility.hodler" @click="visibility.hodler = !visibility.hodler"><i class="legend-swatch hodler"></i>{{ hodlerBar?.label ?? "HODLer NPC" }}</button>
        <button v-if="showSpentBar" type="button" class="legend-toggle" :class="{ 'is-off': !visibility.spent }" :aria-pressed="visibility.spent" @click="visibility.spent = !visibility.spent"><i class="legend-swatch spent"></i>{{ spentBar?.label ?? "≥155d 花费占比" }}</button>
      </template>
    </div>

    <p v-if="isBarMetric && !hasVisibleBars" class="bars-empty-note" role="status">
      当前时间范围暂无柱状数据，可切换到全量查看
    </p>

    <div
      ref="chartWrapRef"
      class="shared-chart-wrap"
      :class="{ 'is-dragging': dragging }"
      :style="chartWrapStyle"
      @mousedown="onDragStart"
    >
      <VChart
        class="shared-chart"
        :option="option"
        autoresize
        :aria-label="chartAriaLabel"
        @datazoom="onZoom"
      />
    </div>

    <div
      class="chart-resize-handle"
      role="separator"
      aria-orientation="horizontal"
      aria-label="调整图表高度"
      :aria-valuemin="MIN_CHART_HEIGHT"
      :aria-valuemax="MAX_CHART_HEIGHT"
      :aria-valuenow="chartHeight"
      tabindex="0"
      @pointerdown="onResizeStart"
      @keydown="onResizeKeydown"
    >
      <span aria-hidden="true"></span>
    </div>

    <div class="chart-facts">
      <div><span>当前值</span><strong>{{ metric.display_value }}</strong></div>
      <div><span>当前档位</span><strong :class="tierClass(metric.tier_id, metric.tier_label)">{{ metric.tier_label }}</strong></div>
      <div><span>证据角色</span><strong :class="metric.role === '核心锚' || metric.role === '核心复核' ? 'is-core' : 'is-supporting'">{{ metric.role }}</strong></div>
    </div>

  </section>
</template>

<style scoped>
.chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin: 10px 0 6px;
}
.shared-chart-wrap {
  cursor: grab;
  user-select: none;
  min-height: 320px;
}
.shared-chart-wrap.is-dragging {
  cursor: grabbing;
}
.chart-resize-handle {
  display: grid;
  place-items: center;
  height: 18px;
  margin: 0 -6px -4px;
  cursor: ns-resize;
  touch-action: none;
  outline: none;
}
.chart-resize-handle span {
  width: 48px;
  height: 4px;
  border-radius: 999px;
  background: #526260;
  transition: background 0.15s, width 0.15s;
}
.chart-resize-handle:hover span,
.chart-resize-handle:focus-visible span {
  width: 64px;
  background: #de8a57;
}
.bars-empty-note {
  margin: 8px 0 0;
  color: #c98a5d;
  font-size: 11px;
}
.range-label {
  font-size: 12px;
  color: #8fa19e;
  font-variant-numeric: tabular-nums;
}
.range-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.range-btn {
  background: #16201f;
  color: #c5d1cd;
  border: 1px solid #2c3a39;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.range-btn:hover {
  border-color: #4a605c;
}
.range-btn.is-active {
  background: #2c3a39;
  border-color: #de8a57;
  color: #f2f3ed;
}
.toolbar-sep {
  display: inline-block;
  width: 1px;
  height: 16px;
  background: #2c3a39;
  margin: 0 4px;
}
.legend-swatch {
  display: inline-block;
  width: 12px;
  height: 8px;
  border-radius: 2px;
  margin-right: 4px;
  vertical-align: middle;
}
.legend-swatch.hodler {
  background: #c98a5d;
}
.legend-swatch.spent {
  background: #7fa6c0;
}
.legend-line.bottom {
  background: #5a7a86;
}
</style>
