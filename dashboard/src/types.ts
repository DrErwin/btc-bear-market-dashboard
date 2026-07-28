/**
 * A metric's fixed evidence role. The two short values are kept so that
 * v0.2 packets can still be read while the evidence registry migrates.
 */
export type Role =
  | "核心锚"
  | "核心复核"
  | "强辅助"
  | "辅助"
  | "核心"
  | "supporting"
  | "core";

/** Whether this metric may enter the current evidence brief. */
export type MetricAvailabilityStatus =
  | "current"
  | "display_only"
  | "validation_pending"
  | "missing"
  | "当前可用"
  | "仅供展示"
  | "待验证"
  | "缺失";
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
  role?: "trigger" | "neutral";
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
  /** v0.3 evidence/data-quality fields. Optional for v0.2 fixture compatibility. */
  availability_status?: MetricAvailabilityStatus | string | null;
  judgment_eligible?: boolean | null;
  days_stale?: number | null;
  availability_reason?: string | null;
  /** Evidence-brief aliases accepted during packet assembly migration. */
  status?: MetricAvailabilityStatus | string | null;
  reason?: string | null;
  metric_date?: string | null;
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

export interface EvidenceBrief {
  brief_version?: string;
  analysis_date?: string;
  allowed_stages: string[];
  core_dimensions: Record<string, unknown>;
  strong_auxiliary_themes: Array<Record<string, unknown>>;
  auxiliary_themes?: Array<Record<string, unknown>>;
  contrary_or_incomplete?: Array<Record<string, unknown>>;
  next_stage_conditions?: string[];
  data_quality: {
    stage_ready?: boolean;
    critical_missing?: string[];
    common_anchor_date?: string | null;
    [key: string]: unknown;
  };
  metric_states?: Array<Record<string, unknown>>;
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
  /** A short ordinary-reader explanation of strong auxiliary pressure, if any. */
  pressure_summary?: string | null;
  compact: {
    support: { title: string; text: string };
    obstacle: { title: string; text: string };
    next: { title: string; text: string };
  };
  categories: CategoryAssessment[];
  detailed: {
    /** Legacy v0.2 name for the core evidence section. */
    supporting?: string;
    /** Preferred v0.3 name for the core evidence section. */
    core_evidence?: string;
    core?: string;
    /** Strong auxiliary evidence explained without moving the stage ceiling. */
    pressure?: string;
    contrary?: string;
    next_stage?: string;
    /** v0.3 data-quality limits; aliases keep early fixtures readable. */
    data_limit?: string;
    data_limits?: string;
    data_quality?: string;
    limitations?: string;
  };
}

export interface StatusData {
  today_available: boolean;
  last_success_date: string | null;
  reason: string | null;
  data_insufficient?: boolean;
  data_quality?: Record<string, unknown>;
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
  evidence_brief?: EvidenceBrief;
  series: SeriesData;
  bars: Record<string, BarSeries>;
  bottoms: BottomMark[];
  analysis: Analysis | null;
  fallback: Analysis | null;
  status: StatusData;
}

export interface DashboardData {
  snapshot: Snapshot;
  evidenceBrief?: EvidenceBrief;
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
