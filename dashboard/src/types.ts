export type Role = "核心锚" | "核心复核" | "强辅助" | "辅助";

export type MetricAvailabilityStatus =
  | "current"
  | "display_only"
  | "validation_pending"
  | "missing";

export type CategoryStatus = "未确认" | "部分确认" | "充分确认";
export type Consistency = "弱" | "中等" | "强";
export type PressureState = "压力尚未明显" | "进入观察" | "深度压力" | "极端压力" | "数据不足";
export type BottomingState =
  | "未见筑底结构"
  | "筑底线索出现"
  | "筑底证据聚合"
  | "筑底证据较完整"
  | "市场修复中"
  | "已离开底部窗口"
  | "数据不足";
export type StableTierId = "none" | "observation" | "deep_pressure" | "extreme_pressure";

export interface Threshold {
  value: number;
  direction: "below" | "above";
  label: string;
  meaning: string;
  tier_id?: StableTierId;
  role?: "trigger" | "neutral";
  triggered?: boolean | null;
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
  tier_id: StableTierId;
  tier_label: string;
  tier_meaning: string;
  thresholds: Threshold[];
  canonical_id?: string;
  responsibility?: string;
  axis_relevance?: string[];
  correlation_family?: string;
  availability_status?: MetricAvailabilityStatus | null;
  availability_label?: string | null;
  judgment_eligible?: boolean | null;
  days_stale?: number | null;
  availability_reason?: string | null;
  status?: MetricAvailabilityStatus | null;
  reason?: string | null;
  metric_date?: string | null;
}

export interface Category {
  id: string;
  short: string;
  name: string;
}

export interface EvidenceBrief {
  brief_version: string;
  analysis_date: string;
  state_vocabularies?: Record<string, unknown>;
  axis_readiness: Record<"pressure" | "bottoming", AxisReadiness>;
  metric_states: Array<Record<string, unknown>>;
  evidence_families?: Array<Record<string, unknown>>;
  themes?: Array<Record<string, unknown>>;
  contrary_or_gaps?: Array<Record<string, unknown>>;
  timeline?: Record<string, unknown>;
  previous_three_days?: PreviousDayContext[];
  lookback_config?: Record<string, unknown>;
  data_quality?: Record<string, unknown>;
}

export interface AxisReadiness {
  ready: boolean;
  required_metric_ids?: string[];
  missing_metric_ids?: string[];
  missing_reasons?: string[];
  family_coverage?: number;
  timeline_complete?: boolean;
  [key: string]: unknown;
}

export interface PreviousDayContext {
  date: string;
  status: "current" | "fallback" | "missing" | "incompatible";
  analysis_date?: string | null;
  pressure_state?: PressureState | null;
  bottoming_state?: BottomingState | null;
  consistency?: Consistency | null;
  reason?: string | null;
}

export interface CategoryAssessment {
  id: string;
  status: CategoryStatus;
  note: string;
}

export interface StateChange {
  changed: boolean;
  from: string | null;
  to: string | null;
  reason: string;
  compared_date?: string | null;
}

export interface Analysis {
  analysis_date: string;
  pressure_state: PressureState;
  bottoming_state: BottomingState;
  consistency: Consistency | null;
  summary: string;
  compact: {
    pressure: { title: string; text: string };
    bottoming: { title: string; text: string };
    change: { title: string; text: string };
  };
  categories: CategoryAssessment[];
  detailed: {
    pressure_reason: string;
    bottoming_reason: string;
    evidence_timeline: string;
    contrary_or_gaps: string;
    repair_exit: string;
    next_evidence: string;
  };
  state_changes?: {
    pressure: StateChange;
    bottoming: StateChange;
  };
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
  lines?: MetricLine[];
}

export interface SeriesData {
  price: SeriesPoint[];
  metrics: Record<string, MetricSeries>;
}

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

export interface BottomMark {
  date: string;
  label: string;
}

export interface StatusData {
  today_available: boolean;
  last_success_date: string | null;
  reason: string | null;
  data_insufficient?: boolean;
  axis_readiness?: Record<"pressure" | "bottoming", AxisReadiness>;
  data_quality?: Record<string, unknown>;
}

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
  snapshot: {
    snapshot_date: string;
    price: {
      current_value: number;
      display_value: string;
      unit: string;
      current_date: string;
    };
    categories: Category[];
    metrics: Metric[];
  };
  evidence_brief: EvidenceBrief;
  series: SeriesData;
  bars: Record<string, BarSeries>;
  bottoms: BottomMark[];
  analysis: Analysis | null;
  fallback: Analysis | null;
  status: StatusData;
}

export interface DashboardData {
  snapshot: Packet["snapshot"];
  evidenceBrief: EvidenceBrief;
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
