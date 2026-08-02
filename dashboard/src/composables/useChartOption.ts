import { computed, type Ref } from "vue";
import {
  chartLineColor,
  getChartLineDisplayLabel,
  getRenderableChartLines,
  isChartLineVisible,
  type ChartVisibility,
} from "../chartLineControls";
import type { BarSeries, BottomMark, Metric, MetricLine, MetricSeries, SeriesData } from "../types";
import { useI18n } from "../i18n";

export type { ChartVisibility } from "../chartLineControls";

export interface ZoomRange {
  start: number; // 0..100 (percent)
  end: number; // 0..100 (percent)
}

const BAR_METRIC_IDS = ["hodler", "spent155"];
const BAR_SERIES_KEYS = {
  hodler: "hodler_npc_30d",
  spent155: "spent_value_ge155d_share",
} as const;
const BAR_HEIGHT_FRACTION = 0.4;
const PRICE_LINE_WIDTH = 1.35;
const PRIMARY_INDICATOR_LINE_WIDTH = 1.2;
const SECONDARY_INDICATOR_LINE_WIDTH = 1;
const REFERENCE_LINE_WIDTH = 0.8;

/**
 * Shared-chart option.
 *
 * - One shared grid contains BTC price, the indicator, threshold/bottom
 *   markLines, and (for a holder-capitulation metric) its one matching bar
 *   series. Bars use a compressed right-side value axis so they sit in the
 *   lower portion of the same plot instead of becoming a second panel.
 * - BTC price y-axis toggles linear/log via ``logPrice``.
 * - One dataZoom drives every x-axis; the inside zoom pans on drag (not on
 *   move) so a plain mouse move shows a crosshair instead of panning.
 * - axisPointer is a crosshair so hovering shows both the vertical (date) and
 *   horizontal (indicator value) readouts.
 * - Grid bottom + slider bottom leave room for the x-axis labels (v0.2.1).
 * - v0.2.2: no native ECharts legend — the custom HTML legend in SharedChart is
 *   the single legend AND the curve toggle. ``visibility`` drives each series'
 *   opacity; threshold / bear-bottom markLine groups are included only while
 *   their toggle is on, so they can be shown/hidden independently of the
 *   indicator curve. The indicator y-axis always covers the threshold values so
 *   threshold lines never fall outside the auto-fit range.
 */
export function useChartOption(
  metric: Ref<Metric>,
  series: Ref<SeriesData>,
  bars: Ref<Record<string, BarSeries>>,
  zoom: Ref<ZoomRange>,
  bottoms: Ref<BottomMark[]>,
  logPrice: Ref<boolean>,
  visibility: Ref<ChartVisibility>,
) {
  const { locale, t } = useI18n();
  return computed(() => {
    const pricePoints = series.value.price;
    const dates = pricePoints.map((point) => point.date);
    const n = dates.length;

    const metricSeries: MetricSeries = series.value.metrics[metric.value.id] ?? {
      points: [],
      thresholds: metric.value.thresholds,
    };
    const sourceMetricLines: MetricLine[] = metricSeries.lines?.length
      ? metricSeries.lines
      : [{ id: "primary", label: metric.value.label, axis: "indicator", points: metricSeries.points }];
    const metricLines = getRenderableChartLines(metric.value.id, sourceMetricLines);
    const hasPrimaryLine = metricLines.some((line) => line.id === "primary");
    const lineValuesById = new Map(
      metricLines.map((line) => {
        const valuesByDate = new Map(line.points.map((point) => [point.date, point.value]));
        return [line.id, dates.map((date) => valuesByDate.get(date) ?? null)] as const;
      }),
    );
    const vis = visibility.value;

    // Each holder-capitulation metric owns one bar series: HODLer shows only
    // HODLer NPC, while >=155d shows only spent-value share.
    const showHodlerBar = metric.value.id === "hodler";
    const showSpentBar = metric.value.id === "spent155";
    const isBarMetric = BAR_METRIC_IDS.includes(metric.value.id);
    const hodlerBar = showHodlerBar ? bars.value[BAR_SERIES_KEYS.hodler] : undefined;
    const spentBar = showSpentBar ? bars.value[BAR_SERIES_KEYS.spent155] : undefined;
    const hodlerByDate = new Map((hodlerBar?.points ?? []).map((p) => [p.date, p.value]));
    const spentByDate = new Map((spentBar?.points ?? []).map((p) => [p.date, p.value]));
    const hodlerValues = showHodlerBar ? dates.map((d) => (hodlerByDate.has(d) ? hodlerByDate.get(d)! : null)) : [];
    const spentValues = showSpentBar ? dates.map((d) => (spentByDate.has(d) ? spentByDate.get(d)! : null)) : [];

    // Visible slice for y-axis auto-fit.
    const startIdx = Math.max(0, Math.floor((zoom.value.start / 100) * n));
    const endIdx = Math.min(n, Math.ceil((zoom.value.end / 100) * n));
    const lineValues = (axis: MetricLine["axis"]) => metricLines
      .filter((line) => line.axis === axis)
      .flatMap((line) => (lineValuesById.get(line.id) ?? []).slice(startIdx, endIdx));
    const priceValues = [
      ...pricePoints.slice(startIdx, endIdx).map((point) => point.value),
      ...lineValues("price").filter((value): value is number => value !== null && Number.isFinite(value) && value > 0),
    ];
    const priceBounds = bounds(priceValues);
    const thresholdValues = metricSeries.thresholds.map((threshold) => threshold.value);
    // Mirror the indicator-validation dashboard: fit the visible indicator
    // range to its robust 2%–98% values, while always keeping every configured
    // threshold visible. This lets normal movement remain readable when an
    // old outlier would otherwise flatten the line.
    const indBounds = adaptiveIndicatorBounds(lineValues("indicator"), thresholdValues);
    const thresholdAnchorLine = metricLines.find((line) => line.axis === "indicator");
    const hodlerBounds = showHodlerBar
      ? compressedBarBounds(hodlerValues.slice(startIdx, endIdx), thresholdValues)
      : { min: 0, max: 1 };
    const spentBounds = showSpentBar
      ? compressedBarBounds(spentValues.slice(startIdx, endIdx), thresholdValues)
      : { min: 0, max: 1 };

    // Horizontal threshold lines + vertical bear-bottom lines, merged on the indicator series.
    const thresholdLines = metricSeries.thresholds.map((threshold) => ({
      yAxis: threshold.value,
      name: threshold.label,
      lineStyle: { color: "#de8a57", type: "dashed" as const, width: REFERENCE_LINE_WIDTH },
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
      lineStyle: { color: "#5a7a86", type: "dashed" as const, width: REFERENCE_LINE_WIDTH },
      label: {
        show: true,
        formatter: bottom.label,
        color: "#9fb4b8",
        fontSize: 10,
        backgroundColor: "#101719",
        padding: [3, 5],
      },
    }));

    // One plot area keeps the active bar series inside the main chart. Its
    // right-side axis uses an expanded range so bars occupy the lower band
    // without becoming an unreadable sliver.
    const grids = [{ left: 58, right: 68, top: 32, bottom: 72 }];

    const categoryAxis = (gridIndex: number, boundaryGap: boolean) => ({
      type: "category" as const,
      boundaryGap,
      data: dates,
      gridIndex,
      axisLine: { lineStyle: { color: "#526260" } },
      axisLabel: { color: "#8fa19e", fontSize: 10 },
    });
    const xAxes = [categoryAxis(0, false)];

    const priceAxis = logPrice.value
      ? {
          type: "log" as const,
          name: `${t("btcPrice")} (${t("logarithmic")})`,
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
          name: t("btcPrice"),
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
        show: !isBarMetric,
        min: indBounds.min,
        max: indBounds.max,
        nameTextStyle: { color: "#c98a5d", fontSize: 10 },
        axisLabel: { color: "#c98a5d", fontSize: 10 },
        splitLine: { show: false },
      },
    ];
    const activeBarBounds = showHodlerBar ? hodlerBounds : spentBounds;
    const activeBarSeries = showHodlerBar ? hodlerBar : spentBar;
    const activeBarColor = showHodlerBar ? "#c98a5d" : "#7fa6c0";
    const yAxes = isBarMetric
      ? [
          ...yAxesBase,
          {
            type: "value" as const,
            position: "right" as const,
            name: activeBarSeries?.unit ?? (locale.value === "en" ? "Share %" : "占比 %"),
            gridIndex: 0,
            min: activeBarBounds.min,
            max: activeBarBounds.max,
            nameTextStyle: { color: activeBarColor, fontSize: 10 },
            axisLabel: { color: activeBarColor, fontSize: 10 },
            axisLine: { show: true, lineStyle: { color: activeBarColor } },
            splitLine: { show: false },
          },
        ]
      : yAxesBase;

    // Bear-bottom markers belong to the price context, so the vertical dashed
    // lines remain available even when a bar metric omits its own line.
    const seriesArr: any[] = [
      {
        name: t("btcPrice"),
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        showSymbol: false,
        smooth: true,
        data: pricePoints.map((p) => p.value),
        lineStyle: { width: PRICE_LINE_WIDTH, color: "#9bc0b8", opacity: vis.price ? 1 : 0 },
        areaStyle: { color: "rgba(155, 192, 184, 0.08)", opacity: vis.price ? 1 : 0 },
        markLine: {
          symbol: ["none", "none"],
          silent: true,
          data: vis.bottoms ? bottomLines : [],
        },
      },
    ];
    if (!isBarMetric) {
      metricLines.forEach((line, index) => {
        const values = lineValuesById.get(line.id) ?? dates.map(() => null);
        const indicatorLine = line.axis === "indicator";
        const lineVisible = isChartLineVisible(metric.value.id, line, vis);
        const color = chartLineColor(line, index, hasPrimaryLine);
        seriesArr.push({
          name: getChartLineDisplayLabel(metric.value, line),
          type: "line",
          xAxisIndex: 0,
          yAxisIndex: indicatorLine ? 1 : 0,
          showSymbol: false,
          smooth: true,
          connectNulls: false,
          data: values,
          lineStyle: {
            width: line.id === "primary" ? PRIMARY_INDICATOR_LINE_WIDTH : SECONDARY_INDICATOR_LINE_WIDTH,
            color,
            type: "solid",
            opacity: lineVisible ? 1 : 0,
          },
          itemStyle: { color },
          // Thresholds belong to the indicator axis and are drawn once on the
          // primary line, so extra curves do not duplicate the labels.
          markLine: {
            symbol: ["none", "none"],
            silent: true,
            data: indicatorLine && line.id === thresholdAnchorLine?.id && vis.thresholds ? thresholdLines : [],
          },
        });
      });
      // STH-MVRV intentionally hides its indicator curve but keeps its
      // indicator-axis reference line. This invisible anchor owns only that
      // markLine, so it cannot appear in the tooltip or chart legend.
      if (!thresholdAnchorLine && metricSeries.thresholds.length) {
        seriesArr.push({
          name: "__threshold_anchor",
          type: "line",
          xAxisIndex: 0,
          yAxisIndex: 1,
          data: dates.map(() => null),
          showSymbol: false,
          silent: true,
          tooltip: { show: false },
          lineStyle: { opacity: 0 },
          itemStyle: { opacity: 0 },
          markLine: {
            symbol: ["none", "none"],
            silent: true,
            data: vis.thresholds ? thresholdLines : [],
          },
        });
      }
    }
    if (showHodlerBar) {
      seriesArr.push({
        name: hodlerBar?.label ?? "HODLer NPC",
        type: "bar",
        xAxisIndex: 0,
        yAxisIndex: 2,
        data: hodlerValues,
        barWidth: "72%",
        barGap: "-100%",
        barCategoryGap: "40%",
        z: 1,
        itemStyle: { color: "#c98a5d", opacity: vis.hodler ? 0.45 : 0 },
        markLine: {
          symbol: ["none", "none"],
          silent: true,
          data: vis.thresholds ? thresholdLines : [],
        },
      });
    }
    if (showSpentBar) {
      seriesArr.push({
        name: spentBar?.label ?? "≥155d 花费占比",
        type: "bar",
        xAxisIndex: 0,
        yAxisIndex: 2,
        data: spentValues,
        barWidth: "42%",
        barGap: "-100%",
        barCategoryGap: "40%",
        z: 2,
        itemStyle: { color: "#7fa6c0", opacity: vis.spent ? 0.6 : 0 },
        markLine: {
          symbol: ["none", "none"],
          silent: true,
          data: vis.thresholds ? thresholdLines : [],
        },
      });
    }

    const xAxisIndices = [0];

    return {
      animation: false,
      color: ["#9bc0b8", "#e2a06e", "#c98a5d", "#7fa6c0"],
      grid: grids,
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
          // Drag-pan is handled manually in SharedChart (moveOnMouseDrag is
          // unreliable alongside a tooltip axisPointer); keep wheel zoom here.
          moveOnMouseDrag: false,
          moveOnMouseMove: false,
          zoomOnMouseWheel: true,
        },
      ],
      series: seriesArr,
    };
  });
}

function compressedBarBounds(values: (number | null)[], thresholds: number[] = []): { min: number; max: number } {
  const base = bounds([...values, ...thresholds]);
  const min = Math.min(0, base.min);
  const max = Math.max(0, base.max);
  const span = Math.max(max - min, 1);
  return { min, max: min + span / BAR_HEIGHT_FRACTION };
}

function adaptiveIndicatorBounds(
  values: (number | null)[],
  thresholdValues: number[],
): { min: number; max: number } {
  const sortedValues = values
    .filter((value): value is number => value !== null && Number.isFinite(value))
    .sort((left, right) => left - right);
  const finiteThresholds = thresholdValues.filter((value) => Number.isFinite(value));

  if (!sortedValues.length) return bounds(finiteThresholds);

  const quantile = (items: number[], probability: number): number => {
    const index = Math.min(
      items.length - 1,
      Math.max(0, Math.round((items.length - 1) * probability)),
    );
    return items[index];
  };

  let minimum = quantile(sortedValues, 0.02);
  let maximum = quantile(sortedValues, 0.98);
  for (const value of finiteThresholds) {
    minimum = Math.min(minimum, value);
    maximum = Math.max(maximum, value);
  }

  const span = maximum - minimum || Math.max(Math.abs(maximum), 1) * 0.1;
  return { min: minimum - span * 0.08, max: maximum + span * 0.08 };
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
