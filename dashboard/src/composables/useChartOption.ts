import { computed, type Ref } from "vue";
import type { Metric, MetricSeries, SeriesData } from "../types";

export function useChartOption(
  metric: Ref<Metric>,
  series: Ref<SeriesData>,
) {
  return computed(() => {
    const metricSeries: MetricSeries = series.value.metrics[metric.value.id] ?? {
      points: [],
      thresholds: metric.value.thresholds,
    };
    const dates = series.value.price.map((point) => point.date);
    const indicatorByDate = new Map(
      metricSeries.points.map((point) => [point.date, point.value]),
    );
    const indicatorValues = dates.map((date) => indicatorByDate.get(date) ?? null);
    const thresholdLines = metricSeries.thresholds.map((threshold) => ({
      yAxis: threshold.value,
      name: threshold.label,
      lineStyle: {
        color: "#de8a57",
        type: "dashed" as const,
        width: 1,
      },
      label: {
        show: true,
        formatter: threshold.label,
        color: "#de8a57",
        fontSize: 10,
        backgroundColor: "#101719",
        padding: [3, 5],
      },
    }));

    return {
      animation: false,
      color: ["#9bc0b8", "#e2a06e"],
      grid: { left: 58, right: 68, top: 38, bottom: 42 },
      legend: {
        top: 0,
        left: 0,
        itemWidth: 16,
        itemHeight: 3,
        textStyle: { color: "#d6e0dc", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1d2a2b",
        borderColor: "#526260",
        textStyle: { color: "#f2f3ed" },
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: dates,
        axisLine: { lineStyle: { color: "#526260" } },
        axisLabel: { color: "#8fa19e", fontSize: 10 },
      },
      yAxis: [
        {
          type: "value",
          name: "BTC 价格",
          nameTextStyle: { color: "#8fa19e", fontSize: 10 },
          axisLabel: { color: "#8fa19e", fontSize: 10 },
          splitLine: { lineStyle: { color: "#29383a" } },
        },
        {
          type: "value",
          name: metric.value.unit,
          nameTextStyle: { color: "#c98a5d", fontSize: 10 },
          axisLabel: { color: "#c98a5d", fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      dataZoom: [{ type: "inside" }],
      series: [
        {
          name: "BTC 价格",
          type: "line",
          yAxisIndex: 0,
          showSymbol: false,
          smooth: true,
          data: series.value.price.map((point) => point.value),
          lineStyle: { width: 2, color: "#9bc0b8" },
          areaStyle: { color: "rgba(155, 192, 184, 0.08)" },
        },
        {
          name: metric.value.label,
          type: "line",
          yAxisIndex: 1,
          showSymbol: false,
          smooth: true,
          connectNulls: true,
          data: indicatorValues,
          lineStyle: { width: 2, color: "#e2a06e" },
          markLine: {
            symbol: ["none", "none"],
            silent: true,
            data: thresholdLines,
          },
        },
      ],
    };
  });
}
