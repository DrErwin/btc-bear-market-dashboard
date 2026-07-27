import type {
  Analysis,
  DashboardData,
  SeriesData,
  Snapshot,
  StatusData,
} from "../types";

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`无法读取本地数据：${path}`);
  }
  return (await response.json()) as T;
}

function hasAnalysis(value: unknown): value is Analysis {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<Analysis>;
  return Boolean(
    candidate.analysis_date &&
      candidate.stage &&
      candidate.consistency &&
      candidate.summary &&
      candidate.compact &&
      candidate.categories &&
      candidate.detailed,
  );
}

export async function loadDashboardData(): Promise<DashboardData> {
  const params = new URLSearchParams(window.location.search);
  const fixture = params.get("fixture") || "success";
  const statusFile =
    fixture === "failure"
      ? "/data/status-failure.json"
      : fixture === "no-fallback"
        ? "/data/status-no-fallback.json"
        : "/data/status.json";

  const [snapshot, series, currentCandidate, status] = await Promise.all([
    loadJson<Snapshot>("/data/snapshot.json"),
    loadJson<SeriesData>("/data/series.json"),
    loadJson<Analysis>("/data/analysis-current.json"),
    loadJson<StatusData>(statusFile),
  ]);

  let fallback: Analysis | null = null;
  if (fixture !== "no-fallback") {
    try {
      const fallbackCandidate = await loadJson<Analysis>(
        "/data/analysis-fallback.json",
      );
      fallback = hasAnalysis(fallbackCandidate) ? fallbackCandidate : null;
    } catch {
      fallback = null;
    }
  }

  const analysis = status.today_available && hasAnalysis(currentCandidate)
    ? currentCandidate
    : null;

  return { snapshot, series, analysis, status, fallback, fixture };
}
