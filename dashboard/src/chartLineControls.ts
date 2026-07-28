import type { Metric, MetricLine } from "./types";

/** State shared by the HTML legend controls and the ECharts series. */
export interface ChartVisibility {
  price: boolean;
  indicator: boolean;
  thresholds: boolean;
  bottoms: boolean;
  hodler: boolean;
  spent: boolean;
  lines: Record<string, boolean>;
}

export interface ResolvedChartLineToggleGroup {
  id: string;
  label: string;
  lines: MetricLine[];
}

interface ChartLineToggleGroupDefinition {
  id: string;
  label: string;
  lineIds: string[];
}

/** Keep legend swatches aligned with the colours assigned in useChartOption. */
export const PRIMARY_CHART_LINE_COLOR = "#e2a06e";
export const SECONDARY_CHART_LINE_COLORS = ["#d65d52", "#4e9b73", "#5d8fcb"];

const DEDICATED_LINE_TOGGLE_GROUPS: Record<string, ChartLineToggleGroupDefinition[]> = {
  sipl: [
    { id: "sipl", label: "SIPL", lineIds: ["primary", "loss_share"] },
    { id: "sipl-gap", label: "SIPL 差值", lineIds: ["profit_loss_gap"] },
  ],
  asopr: [
    { id: "asopr", label: "aSOPR", lineIds: ["primary"] },
    { id: "asopr-3d", label: "3日滞后均值（趋势辅助）", lineIds: ["sma_3d"] },
    { id: "asopr-7d", label: "7日滞后均值（趋势辅助）", lineIds: ["sma_7d"] },
  ],
};

export function chartLineVisibilityKey(metricId: string, lineId: string) {
  return `${metricId}:${lineId}`;
}

/** The source remains in the packet, but this dashboard deliberately omits it. */
export function isHiddenChartLine(metricId: string, lineId: string) {
  return metricId === "sth-mvrv" && lineId === "primary";
}

export function getRenderableChartLines(metricId: string, lines: MetricLine[]) {
  return lines.filter((line) => !isHiddenChartLine(metricId, line.id));
}

export function hasDedicatedChartLineControls(metricId: string) {
  return metricId in DEDICATED_LINE_TOGGLE_GROUPS;
}

export function getDedicatedChartLineToggleGroups(metricId: string, lines: MetricLine[]): ResolvedChartLineToggleGroup[] {
  const linesById = new Map(lines.map((line) => [line.id, line]));
  return (DEDICATED_LINE_TOGGLE_GROUPS[metricId] ?? [])
    .map((group) => ({
      id: group.id,
      label: group.label,
      lines: group.lineIds
        .map((lineId) => linesById.get(lineId))
        .filter((line): line is MetricLine => line !== undefined),
    }))
    .filter((group) => group.lines.length > 0);
}

export function isChartLineVisible(metricId: string, line: MetricLine, visibility: ChartVisibility) {
  if (isHiddenChartLine(metricId, line.id)) return false;
  if (visibility.lines[chartLineVisibilityKey(metricId, line.id)] === false) return false;
  if (hasDedicatedChartLineControls(metricId)) return true;
  return line.axis === "indicator" ? visibility.indicator : visibility.price;
}

export function isChartLineGroupVisible(metricId: string, lines: MetricLine[], visibility: ChartVisibility) {
  return lines.every((line) => isChartLineVisible(metricId, line, visibility));
}

export function toggleChartLineGroup(metricId: string, lines: MetricLine[], visibility: ChartVisibility) {
  const nextVisible = !isChartLineGroupVisible(metricId, lines, visibility);
  for (const line of lines) {
    visibility.lines[chartLineVisibilityKey(metricId, line.id)] = nextVisible;
  }
}

/** Raw source labels stay intact; only the dashboard-facing Reserve Risk title changes. */
export function getChartLineDisplayLabel(metric: Metric, line: MetricLine) {
  return metric.id === "reserve" && line.id === "primary" ? metric.label : line.label;
}

export function chartLineColor(line: MetricLine, index: number, hasPrimaryLine: boolean) {
  if (line.id === "primary") return PRIMARY_CHART_LINE_COLOR;
  // Secondary validation lines use only red, green and blue. If a metric has
  // no visible primary (STH-MVRV), its first price ladder begins with red.
  const secondaryIndex = Math.max(0, index - (hasPrimaryLine ? 1 : 0));
  return SECONDARY_CHART_LINE_COLORS[secondaryIndex % SECONDARY_CHART_LINE_COLORS.length];
}
