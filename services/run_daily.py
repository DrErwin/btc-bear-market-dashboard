"""Daily dashboard update — the requirement-4 main chain.

    fetch -> freshness check -> derive -> AI -> validate -> assemble packet
        -> archive previous -> atomic publish -> append audit log

Failure handling (requirement 1 整包回退):
* Data-source / freshness failure  -> do NOT publish; the previous complete
  packet stays. Logged as ``skipped``.
* AI failure (no key / call error / non-compliant output) -> still publish a
  complete packet whose analysis falls back to the last success and whose
  status flags ``today_available=false``. Logged as ``published-fallback``.
* Full success -> ``published-fresh``.

The AI key is read from the environment and never written into the packet, the
run log, or stdout. Run from the repo root:

    python services/run_daily.py [--mock-ai] [--max-stale-days N]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ai import provider  # noqa: E402
from services.data import fetch, metrics, packet  # noqa: E402
from services.evidence.compiler import compile_evidence  # noqa: E402


DEFAULT_PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"
DEFAULT_LOG_PATH = ROOT / "artifacts" / "run-log.jsonl"
DEFAULT_ARCHIVE_DIR = ROOT / "artifacts" / "packet-archive"
MAX_STALE_DAYS_DEFAULT = 2
KEEP_HISTORY_DEFAULT = 7


def _append_log(log_path: Path, record: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _archive_previous(packet_path: Path, archive_dir: Path, keep: int) -> None:
    previous = packet.load_packet(packet_path)
    if not previous:
        return
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / f"{previous['data_date']}.json"
    shutil.copyfile(packet_path, archive_file)
    archives = sorted(archive_dir.glob("*.json"), reverse=True)
    for stale_archive in archives[keep:]:
        stale_archive.unlink(missing_ok=True)


def run(
    *,
    mock_ai: bool,
    packet_path: Path,
    log_path: Path,
    archive_dir: Path,
    max_stale_days: int,
    keep_history: int,
) -> int:
    generated_at_dt = datetime.now(timezone.utc)
    generated_at = generated_at_dt.isoformat()
    run_id = generated_at_dt.strftime("%Y%m%dT%H%M%SZ")
    today = generated_at_dt.date()

    def log_skipped(reason: str) -> int:
        _append_log(log_path, {
            "run_id": run_id,
            "generated_at": generated_at,
            "config_version": packet.CONFIG_VERSION,
            "outcome": "skipped",
            "data_date": None,
            "analysis_stage": None,
            "reason": reason,
        })
        print(f"[run_daily] SKIPPED run_id={run_id}: {reason}")
        return 0

    # 1. Fetch public base series.
    try:
        raw, bitview_meta = fetch.fetch_bitview()
        obm_total, obm_long, obm_meta = fetch.fetch_obm_spent()
    except Exception as exc:  # noqa: BLE001 — any fetch error -> retain previous
        return log_skipped(f"数据源抓取失败: {type(exc).__name__}: {str(exc)[:150]}")

    # 2. Derive + freshness (date-consistency) check.
    computed = metrics.compute_indicators(
        raw, obm_total, obm_long, {"bitview": bitview_meta, "obm": obm_meta}
    )
    data_date = computed.data_date
    stale_days = (today - data_date).days
    if stale_days > max_stale_days:
        return log_skipped(f"数据日期 {data_date} 过期（>{max_stale_days} 天），疑似数据源延迟")

    # 3. AI analysis (None + reason on any failure -> fallback).
    snapshot = packet.build_snapshot(computed)
    evidence_brief = compile_evidence(snapshot, analysis_date=data_date.isoformat())
    if evidence_brief["data_quality"]["stage_ready"]:
        analysis, ai_reason = provider.call_ai(
            snapshot, data_date=data_date.isoformat(), mock=mock_ai
        )
        data_insufficient = False
    else:
        analysis = provider.data_insufficient_analysis(
            data_date.isoformat(), evidence_brief
        )
        ai_reason = "数据不足：关键锚不可用，不调用 AI"
        data_insufficient = True

    # 4. Resolve analysis + fallback against the previous success.
    previous = packet.load_packet(packet_path)
    prev_analysis = previous.get("analysis") if previous else None
    prev_fallback = previous.get("fallback") if previous else None
    prev_last_success = previous["status"]["last_success_date"] if previous else None
    carry_forward = prev_analysis or prev_fallback

    if data_insufficient:
        today_available = True
        new_analysis = analysis
        new_fallback = carry_forward
        last_success_date = prev_last_success
        reason = ai_reason
        outcome = "published-data-insufficient"
        analysis_stage = analysis.get("stage")
    elif analysis is not None:
        today_available = True
        new_analysis = analysis
        new_fallback = carry_forward
        last_success_date = data_date.isoformat()
        reason = None
        outcome = "published-fresh"
        analysis_stage = analysis.get("stage")
    else:
        today_available = False
        new_analysis = None
        new_fallback = carry_forward
        last_success_date = prev_last_success
        reason = ai_reason or "AI 分析不可用"
        outcome = "published-fallback"
        analysis_stage = new_fallback.get("stage") if new_fallback else None

    # 5. Assemble + validate + atomic publish.
    pkt = packet.build_packet(
        computed,
        analysis=new_analysis,
        fallback=new_fallback,
        today_available=today_available,
        last_success_date=last_success_date,
        reason=reason,
        run_id=run_id,
        generated_at=generated_at,
    )

    if previous:
        _archive_previous(packet_path, archive_dir, keep_history)
    packet.write_packet_atomic(pkt, packet_path)

    _append_log(log_path, {
        "run_id": run_id,
        "generated_at": generated_at,
        "config_version": packet.CONFIG_VERSION,
        "outcome": outcome,
        "data_date": data_date.isoformat(),
        "analysis_date": pkt["analysis_date"],
        "analysis_stage": analysis_stage,
        "today_available": today_available,
        "reason": reason,
    })
    print(
        f"[run_daily] {outcome} run_id={run_id} data_date={data_date} "
        f"stage={analysis_stage} today_available={today_available}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily BTC bear-bottom dashboard update")
    parser.add_argument("--mock-ai", action="store_true", help="use a fixed compliant analysis instead of a real AI call")
    parser.add_argument("--packet-path", type=Path, default=DEFAULT_PACKET_PATH)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--max-stale-days", type=int, default=MAX_STALE_DAYS_DEFAULT)
    parser.add_argument("--keep-history", type=int, default=KEEP_HISTORY_DEFAULT)
    args = parser.parse_args()
    return run(
        mock_ai=args.mock_ai,
        packet_path=args.packet_path,
        log_path=args.log_path,
        archive_dir=args.archive_dir,
        max_stale_days=args.max_stale_days,
        keep_history=args.keep_history,
    )


if __name__ == "__main__":
    raise SystemExit(main())
