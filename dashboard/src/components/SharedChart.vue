<script setup lang="ts">
import { computed, ref } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import { BarChart, LineChart } from "echarts/charts";
import VChart from "vue-echarts";
import type { BarSeries, BottomMark, Metric, SeriesData } from "../types";
import { useChartOption, type ZoomRange } from "../composables/useChartOption";
import { tierClass } from "../utils/tier";

use([
  CanvasRenderer,
  GridComponent,
  LegendComponent,
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
const option = useChartOption(metricRef, seriesRef, barsRef, zoom, bottomsRef, logPrice);

// Bars only when the active metric IS one of the two capitulation metrics.
const isBarMetric = computed(() => ["hodler", "spent155"].includes(props.metric.id));

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

const hodlerBar = computed(() => props.bars["hodler"] ?? null);
const spentBar = computed(() => props.bars["spent155"] ?? null);

function fullscreen() {
  const root = document.querySelector<HTMLElement>(".chart-card");
  if (root?.requestFullscreen) void root.requestFullscreen();
}
</script>

<template>
  <section class="chart-card" aria-labelledby="chart-title">
    <div class="chart-head">
      <div>
        <span class="eyebrow">共享图表 / 独立于 AI 输入</span>
        <h3 id="chart-title">{{ metric.label }}</h3>
        <p class="chart-subtitle">
          BTC 价格 + {{ metric.label }} + 配置阈值 + 历史熊底虚线<template v-if="isBarMetric"> + 持有者卖出柱状图</template>
        </p>
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

    <div class="chart-legend" aria-label="图例">
      <span><i class="legend-line price"></i>BTC 价格</span>
      <span><i class="legend-line indicator"></i>{{ metric.label }}</span>
      <span><i class="legend-line threshold"></i>阈值线</span>
      <span><i class="legend-line bottom"></i>历史熊底</span>
      <template v-if="isBarMetric">
        <span><i class="legend-swatch hodler"></i>{{ hodlerBar?.label ?? "HODLer NPC" }}</span>
        <span><i class="legend-swatch spent"></i>{{ spentBar?.label ?? "≥155d 花费占比" }}</span>
      </template>
    </div>

    <VChart
      class="shared-chart"
      :option="option"
      autoresize
      :aria-label="`BTC 价格、${metric.label}、阈值线、历史熊底与持有者卖出柱状图共享图表`"
      @datazoom="onZoom"
    />

    <div class="chart-facts">
      <div><span>当前值</span><strong>{{ metric.display_value }}</strong></div>
      <div><span>当前档位</span><strong :class="tierClass(metric.tier_label)">{{ metric.tier_label }}</strong></div>
      <div><span>证据角色</span><strong :class="metric.role === '核心' ? 'is-core' : 'is-supporting'">{{ metric.role }}</strong></div>
    </div>

    <div v-if="isBarMetric && (hodlerBar || spentBar)" class="bars-meta" aria-label="柱状图口径说明">
      <article v-if="hodlerBar">
        <span class="bars-tag">柱状系列</span>
        <strong>{{ hodlerBar.label }}</strong>
        <p class="bars-caveat">{{ hodlerBar.description }} 来源：{{ hodlerBar.source }}。{{ hodlerBar.caveat }} 缺失日期不补齐；非低估期与零分母记为不可判定。</p>
      </article>
      <article v-if="spentBar">
        <span class="bars-tag">柱状系列</span>
        <strong>{{ spentBar.label }}</strong>
        <p class="bars-caveat">{{ spentBar.description }} 来源：{{ spentBar.source }}。{{ spentBar.caveat }} 缺失日期不补齐；非低估期与零分母记为不可判定。</p>
      </article>
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
.bars-meta {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #29383a;
}
.bars-meta article {
  background: #131c1d;
  border: 1px solid #243233;
  border-radius: 8px;
  padding: 8px 10px;
}
.bars-tag {
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6f8280;
  display: block;
  margin-bottom: 2px;
}
.bars-meta strong {
  color: #d6e0dc;
  font-size: 13px;
}
.bars-caveat {
  margin: 4px 0 0;
  font-size: 11px;
  line-height: 1.5;
  color: #93a3a0;
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
