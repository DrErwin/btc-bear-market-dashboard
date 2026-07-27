<script setup lang="ts">
import { computed, ref } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, DataZoomComponent } from "echarts/components";
import { LineChart } from "echarts/charts";
import VChart from "vue-echarts";
import type { Metric, SeriesData } from "../types";
import { useChartOption } from "../composables/useChartOption";

use([CanvasRenderer, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, DataZoomComponent, LineChart]);

const props = defineProps<{
  metric: Metric;
  series: SeriesData;
}>();

const chartRef = ref<InstanceType<typeof VChart> | null>(null);
const metricRef = computed(() => props.metric);
const seriesRef = computed(() => props.series);
const option = useChartOption(metricRef, seriesRef);

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
        <p class="chart-subtitle">BTC 价格 + {{ metric.label }} + 配置阈值</p>
      </div>
      <button class="chart-expand" type="button" aria-label="放大共享图表" @click="fullscreen">放大 <span aria-hidden="true">↗</span></button>
    </div>
    <div class="chart-legend" aria-label="图例">
      <span><i class="legend-line price"></i>BTC 价格</span>
      <span><i class="legend-line indicator"></i>{{ metric.label }}</span>
      <span><i class="legend-line threshold"></i>阈值线</span>
    </div>
    <VChart
      ref="chartRef"
      class="shared-chart"
      :option="option"
      autoresize
      :aria-label="`BTC 价格、${metric.label} 和阈值线共享图表`"
    />
    <div class="chart-facts">
      <div><span>当前值</span><strong>{{ metric.display_value }}</strong></div>
      <div><span>当前档位</span><strong>{{ metric.tier_label }}</strong></div>
      <div><span>证据角色</span><strong>{{ metric.role }}</strong></div>
    </div>
  </section>
</template>
