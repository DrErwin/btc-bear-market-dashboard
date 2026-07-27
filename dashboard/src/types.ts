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

export interface MetricSeries {
  points: SeriesPoint[];
  thresholds: Threshold[];
}

export interface SeriesData {
  price: SeriesPoint[];
  metrics: Record<string, MetricSeries>;
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

export interface DashboardData {
  snapshot: Snapshot;
  series: SeriesData;
  analysis: Analysis | null;
  status: StatusData;
  fallback: Analysis | null;
  fixture: string;
}
