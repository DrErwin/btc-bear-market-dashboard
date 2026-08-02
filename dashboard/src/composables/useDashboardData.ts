import type { DashboardData, Packet } from "../types";

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`无法读取本地数据：${path}`);
  }
  return (await response.json()) as T;
}

/**
 * Requirement 1: the page reads exactly ONE packet entry point. The fixture
 * switch only chooses which complete packet to load — it never assembles parts
 * from independently-updated files. The packet itself carries analysis/fallback
 * and a status block, so the caller does not decide availability here.
 */
export async function loadDashboardData(): Promise<DashboardData> {
  const params = new URLSearchParams(window.location.search);
  const fixture = params.get("fixture") || "success";
  const packetPath =
    fixture === "failure"
      ? "/data/packet-failure.json"
      : fixture === "no-fallback"
        ? "/data/packet-no-fallback.json"
        : "/data/packet.json";

  const packet = await loadJson<Packet>(packetPath);

  return {
    snapshot: packet.snapshot,
    evidenceBrief: packet.evidence_brief,
    series: packet.series,
    bars: packet.bars ?? {},
    bottoms: packet.bottoms ?? [],
    analysis: packet.analysis,
    fallback: packet.fallback,
    analysisEn: packet.analysis_en ?? null,
    fallbackEn: packet.fallback_en ?? null,
    status: packet.status,
    fixture,
    runId: packet.run_id ?? null,
    dataDate: packet.data_date ?? null,
  };
}
