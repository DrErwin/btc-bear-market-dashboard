import { computed, type Ref } from "vue";
import type { BarSeries, BottomMark, Metric, MetricSeries, SeriesData } from "../types";

export interface ZoomRange {
  start: number; // 0..100 (percent)
  end: number; // 0..100 (percent)
}

const BAR_METRIC_IDS = ["hodler", "spent155"];

/**
 * Shared-chart option.
 *
 * - Main line grid (BTC price + indicator + threshold markLines + bear-bottom
 *   vertical dashed markLines). Bars grid (HODLer capitulation + >=155d spent
 *   share) is added ONLY when the active metric IS one of those two bar
 *   metrics (v0.2.1: by id, not by category — so Seller Exhaustion no longer
 *   triggers bars).
 * - BTC price y-axis toggles linear/log via ``logPrice``.
 * - One dataZoom drives every x-axis; the inside zoom pans on drag (not on
 *   move) so a plain mouse move shows a crosshair instead of panning.
 * - axisPointer is a crosshair so hovering shows both the vertical (date) and
 *   horizontal (indicator value) readouts.
 * - Grid bottom + slider bottom leave room for the x-axis labels (v0.2.1).
 */
export function useChartOption(
  metric: Ref<Metric>,
  series: Ref<SeriesData>,
  bars: Ref<Record<string, BarSeries>>,
  zoom: Ref<ZoomRange>,
  bottoms: Ref<BottomMark[]>,
  logPrice: Ref<boolean>,
) {
  return computed(() => {
    const pricePoints = series.value.price;
    const dates = pricePoints.map((point) => point.date);
    const n = dates.length;

    const metricSeries: MetricSeries = series.value.metrics[metric.value.id] ?? {
      points: [],
      thresholds: metric.value.thresholds,
    };
    const indicatorByDate = new Map(metricSeries.points.map((point) => [point.date, point.value]));
    const indicatorValues = dates.map((date) => indicatorByDate.get(date) ?? null);

    // Bars render only for the two holder-capitulation metrics themselves.
    const isBarMetric = BAR_METRIC_IDS.includes(metric.value.id);
    const hodlerBar = isBarMetric ? bars.value["hodler"] : undefined;
    const spentBar = isBarMetric ? bars.value["spent155"] : undefined;
    const hodlerByDate = new Map((hodlerBar?.points ?? []).map((p) => [p.date, p.value]));
    const spentByDate = new Map((spentBar?.points ?? []).map((p) => [p.date, p.value]));
    const hodlerValues = isBarMetric ? dates.map((d) => (hodlerByDate.has(d) ? hodlerByDate.get(d)! : null)) : [];
    const spentValues = isBarMetric ? dates.map((d) => (spentByDate.has(d) ? spentByDate.get(d)! : null)) : [];

    // Visible slice for y-axis auto-fit.
    const startIdx = Math.max(0, Math.floor((zoom.value.start / 100) * n));
    const endIdx = Math.min(n, Math.ceil((zoom.value.end / 100) * n));
    const priceBounds = bounds(pricePoints.slice(startIdx, endIdx).map((p) => p.value));
    const indBounds = bounds(indicatorValues.slice(startIdx, endIdx));
    const hodlerBounds = isBarMetric ? bounds(hodlerValues.slice(startIdx, endIdx)) : { min: 0, max: 1 };
    const spentBounds = isBarMetric ? bounds(spentValues.slice(startIdx, endIdx)) : { min: 0, max: 1 };

    // Horizontal threshold lines + vertical bear-bottom lines, merged on the indicator series.
    const thresholdLines = metricSeries.thresholds.map((threshold) => ({
      yAxis: threshold.value,
      name: threshold.label,
      lineStyle: { color: "#de8a57", type: "dashed" as const, width: 1 },
      label: {
        show: true,
        formatter: threshold.label,
        color: "#de8a57",
        fontSize: 10,
        backgroundColor: "#101719",
        padding: [3, 5],
      },
    }));
    const bottomLines = bottoms.value.map((bottom) => ({
      xAxis: bottom.date,
      name: bottom.label,
      lineStyle: { color: "#5a7a86", type: "dashed" as const, width: 1 },
      label: {
        show: true,
        formatter: bottom.label,
        color: "#9fb4b8",
        fontSize: 10,
        backgroundColor: "#101719",
        padding: [3, 5],
      },
    }));

    const legendData: string[] = ["BTC 价格", metric.value.label];
    if (isBarMetric) {
      if (hodlerBar) legendData.push(hodlerBar.label);
      if (spentBar) legendData.push(spentBar.label);
    }

    // grid bottom 72 reserves room for x-axis labels above the slider.
    const grids = isBarMetric
      ? [
          { left: 58, right: 68, top: 32, bottom: "48%" },
          { left: 58, right: 68, top: "62%", bottom: 72 },
        ]
      : [{ left: 58, right: 68, top: 32, bottom: 72 }];

    const categoryAxis = (gridIndex: number, boundaryGap: boolean) => ({
      type: "category" as const,
      boundaryGap,
      data: dates,
      gridIndex,
      axisLine: { lineStyle: { color: "#526260" } },
      axisLabel: { color: "#8fa19e", fontSize: 10 },
    });
    const xAxes = isBarMetric ? [categoryAxis(0, false), categoryAxis(1, true)] : [categoryAxis(0, false)];

    const priceAxis = logPrice.value
      ? {
          type: "log" as const,
          name: "BTC 价格（对数）",
          gridIndex: 0,
          nameTextStyle: { color: "#8fa19e", fontSize: 10 },
          axisLabel: {
            color: "#8fa19e",
            fontSize: 10,
            formatter: (v: number) => (v >= 1000 ? `$${Math.round(v).toLocaleString()}` : String(v)),
          },
          splitLine: { lineStyle: { color: "#29383a" } },
        }
      : {
          type: "value" as const,
          name: "BTC 价格",
          gridIndex: 0,
          min: priceBounds.min,
          max: priceBounds.max,
          nameTextStyle: { color: "#8fa19e", fontSize: 10 },
          axisLabel: {
            color: "#8fa19e",
            fontSize: 10,
            formatter: (v: number) => (v >= 1000 ? `$${Math.round(v).toLocaleString()}` : String(v)),
          },
          splitLine: { lineStyle: { color: "#29383a" } },
        };
    const yAxesBase = [
      priceAxis,
      {
        type: "value" as const,
        name: metric.value.unit,
        gridIndex: 0,
        min: indBounds.min,
        max: indBounds.max,
        nameTextStyle: { color: "#c98a5d", fontSize: 10 },
        axisLabel: { color: "#c98a5d", fontSize: 10 },
        splitLine: { show: false },
      },
    ];
    const yAxes = isBarMetric
      ? [
          ...yAxesBase,
          {
            type: "value" as const,
            name: "占供应 %",
            gridIndex: 1,
            min: hodlerBounds.min,
            max: hodlerBounds.max,
            nameTextStyle: { color: "#c98a5d", fontSize: 10 },
            axisLabel: { color: "#c98a5d", fontSize: 10 },
            splitLine: { lineStyle: { color: "#29383a" } },
          },
          {
            type: "value" as const,
            name: "占比 %",
            gridIndex: 1,
            min: spentBounds.min,
            max: spentBounds.max,
            nameTextStyle: { color: "#7fa6c0", fontSize: 10 },
            axisLabel: { color: "#7fa6c0", fontSize: 10 },
            splitLine: { show: false },
          },
        ]
      : yAxesBase;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const seriesArr: any[] = [
      {
        name: "BTC 价格",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        showSymbol: false,
        smooth: true,
        data: pricePoints.map((p) => p.value),
        lineStyle: { width: 2, color: "#9bc0b8" },
        areaStyle: { color: "rgba(155, 192, 184, 0.08)" },
      },
      {
        name: metric.value.label,
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 1,
        showSymbol: false,
        smooth: true,
        connectNulls: true,
        data: indicatorValues,
        lineStyle: { width: 2, color: "#e2a06e" },
        markLine: { symbol: ["none", "none"], silent: true, data: [...thresholdLines, ...bottomLines] },
      },
    ];
    if (isBarMetric) {
      seriesArr.push({
        name: hodlerBar?.label ?? "HODLer NPC",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 2,
        data: hodlerValues,
        itemStyle: { color: "#c98a5d" },
      });
      seriesArr.push({
        name: spentBar?.label ?? "≥155d 花费占比",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 3,
        data: spentValues,
        itemStyle: { color: "#7fa6c0" },
      });
    }

    const xAxisIndices = isBarMetric ? [0, 1] : [0];

    return {
      animation: false,
      color: ["#9bc0b8", "#e2a06e", "#c98a5d", "#7fa6c0"],
      grid: grids,
      legend: {
        top: 0,
        left: 0,
        itemWidth: 16,
        itemHeight: 3,
        textStyle: { color: "#d6e0dc", fontSize: 11 },
        data: legendData,
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1d2a2b",
        borderColor: "#526260",
        textStyle: { color: "#f2f3ed" },
        axisPointer: {
          type: "cross",
          lineStyle: { color: "#7fa6c0", type: "dashed" },
          crossStyle: { color: "#7fa6c0", type: "dashed" },
          label: { backgroundColor: "#2c3a39" },
        },
      },
      axisPointer: { link: [{ xAxisIndex: "all" }], label: { backgroundColor: "#2c3a39" } },
      xAxis: xAxes,
      yAxis: yAxes,
      dataZoom: [
        {
          type: "slider",
          xAxisIndex: xAxisIndices,
          start: zoom.value.start,
          end: zoom.value.end,
          bottom: 24,
          height: 20,
          dataBackground: { lineStyle: { color: "#3a5052" }, areaStyle: { color: "#233335" } },
          textStyle: { color: "#8fa19e", fontSize: 10 },
        },
        {
          type: "inside",
          xAxisIndex: xAxisIndices,
          moveOnMouseDrag: true,
          moveOnMouseMove: false,
          zoomOnMouseWheel: true,
        },
      ],
      series: seriesArr,
    };
  });
}

function bounds(values: (number | null)[]): { min: number; max: number } {
  const finite = values.filter((v): v is number => v !== null && Number.isFinite(v));
  if (finite.length === 0) return { min: 0, max: 1 };
  let min = Infinity;
  let max = -Infinity;
  for (const v of finite) {
    if (v < min) min = v;
    if (v > max) max = v;
  }
  if (min === max) return { min: min - 1, max: max + 1 };
  const pad = (max - min) * 0.08;
  return { min: min - pad, max: max + pad };
}
