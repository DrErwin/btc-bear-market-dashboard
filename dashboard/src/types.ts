export type Role = "核心" | "辅助";
export type CategoryStatus = "未确认" | "部分确认" | "充分确认";
export type Consistency = "弱" | "中等" | "强";
export type Stage =
  | "尚未进入熊底观察期"
  | "熊市下行期"
  | "深度压力期"
  | "筑底证据积累期"
  | "熊底证据充分期"
  | "数据不足";

export interface Threshold {
  value: number;
  direction: "below" | "above";
  label: string;
  meaning: string;
}

export interface Metric {
  id: string;
  label: string;
  category: string;
  role: Role;
  unit: string;
  description: string;
  formula: string;
  source: string;
  method: string;
  caveat: string;
  current_value: number;
  display_value: string;
  current_date: string;
  tier_label: string;
  tier_meaning: string;
  thresholds: Threshold[];
}

export interface Category {
  id: string;
  short: string;
  name: string;
}

export interface Snapshot {
  snapshot_date: string;
  price: {
    current_value: number;
    display_value: string;
    unit: string;
    current_date: string;
  };
  categories: Category[];
  metrics: Metric[];
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export type MetricLineAxis = "indicator" | "price";

export interface MetricLine {
  id: string;
  label: string;
  axis: MetricLineAxis;
  points: SeriesPoint[];
}

export interface MetricSeries {
  points: SeriesPoint[];
  thresholds: Threshold[];
  /** Every visible validation-panel curve, including the primary line. */
  lines?: MetricLine[];
}

export interface SeriesData {
  price: SeriesPoint[];
  metrics: Record<string, MetricSeries>;
}

/** Requirement 3 bars: HODLer capitulation + >=155d spent share. */
export type BarQuality = "ok" | "missing" | "undetermined";

export interface BarPoint {
  date: string;
  value: number;
  quality: BarQuality;
}

export interface BarSeries {
  id: string;
  label: string;
  unit: string;
  description: string;
  source: string;
  method: string;
  caveat: string;
  points: BarPoint[];
}

/** Historical bear-bottom markers (vertical dashed lines on the main chart). */
export interface BottomMark {
  date: string;
  label: string;
}

export interface CategoryAssessment {
  id: string;
  status: CategoryStatus;
  note: string;
}

export interface Analysis {
  analysis_date: string;
  stage: Stage;
  consistency: Consistency;
  summary: string;
  compact: {
    support: { title: string; text: string };
    obstacle: { title: string; text: string };
    next: { title: string; text: string };
  };
  categories: CategoryAssessment[];
  detailed: {
    supporting: string;
    contrary: string;
    next_stage: string;
  };
}

export interface StatusData {
  today_available: boolean;
  last_success_date: string | null;
  reason: string | null;
}

/**
 * Requirement 1: a single complete packet. The page reads exactly one of these
 * (the current success, or a fallback fixture via ?fixture=); snapshot, series,
 * bars, analysis and status never update independently.
 */
export interface Packet {
  schema_version: string;
  run_id: string;
  generated_at: string;
  config_version: string;
  data_date: string;
  analysis_date: string | null;
  input_summary: {
    category_count: number;
    metric_count: number;
    price: { date: string; value: number };
    source: Record<string, unknown>;
  };
  snapshot: Snapshot;
  series: SeriesData;
  bars: Record<string, BarSeries>;
  bottoms: BottomMark[];
  analysis: Analysis | null;
  fallback: Analysis | null;
  status: StatusData;
}

export interface DashboardData {
  snapshot: Snapshot;
  series: SeriesData;
  bars: Record<string, BarSeries>;
  bottoms: BottomMark[];
  analysis: Analysis | null;
  status: StatusData;
  fallback: Analysis | null;
  fixture: string;
  runId: string | null;
  dataDate: string | null;
}
