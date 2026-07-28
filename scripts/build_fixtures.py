"""Build the two fixed acceptance fixtures from the current success packet.

The success packet (``dashboard/public/data/packet.json``) is regenerated daily
by ``run_daily`` with real data + real AI. The failure / no-fallback fixtures
are *fixed* acceptance snapshots: they are committed once and never overwritten
by the daily run, so Playwright acceptance has stable dates and stages to
assert against.

Run after ``run_daily --mock-ai`` has produced the success packet:

    python services/run_daily.py --mock-ai
    python scripts/build_fixtures.py
"""

from __future__ import annotations

import copy
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.data import packet  # noqa: E402


DATA_DIR = ROOT / "dashboard" / "public" / "data"

# The fallback shown when today's AI is unavailable. Stage and wording match the
# v0.1.0 acceptance expectation (深度压力期, anchored on the previous day).
FALLBACK_ANALYSIS = {
    "stage": "深度压力期",
    "consistency": "中等",
    "summary": "整体估值和矿工收入都已明显承压，市场处于深度压力期；不过，持有者行为与长期成本位置还没有形成足够一致的变化。",
    "pressure_summary": "整体估值和矿工收入同时承压，说明此前市场压力较重。",
    "compact": {
        "support": {"title": "当前市场状态", "text": "整体估值和矿工收入都已进入明显压力区。"},
        "obstacle": {"title": "还没有进入更深阶段", "text": "持有者行为与长期成本位置仍需更多当前数据支持。"},
        "next": {"title": "接下来观察", "text": "观察持有者行为与长期成本位置是否出现一致变化。"},
    },
    "categories": [
        {"id": "valuation", "status": "充分确认", "note": "整体估值进入深度压力。"},
        {"id": "supply", "status": "部分确认", "note": "供应盈亏结构偏向压力。"},
        {"id": "capital", "status": "部分确认", "note": "已实现资本仍偏弱。"},
        {"id": "holders", "status": "未确认", "note": "持有者投降证据尚不充分。"},
        {"id": "miners", "status": "充分确认", "note": "矿工压力已进入深度区。"},
        {"id": "anchors", "status": "未确认", "note": "长期成本位置尚未接近历史压力区。"},
    ],
    "detailed": {
        "supporting": "整体估值和矿工收入同步进入压力区，说明市场压力已经明显加深。",
        "contrary": "持有者行为与长期成本位置尚未形成一致变化。",
        "next_stage": "继续观察持有者行为与长期成本位置是否同步变化。",
    },
}

LEGACY_FILES = (
    "snapshot.json",
    "series.json",
    "analysis-current.json",
    "analysis-fallback.json",
    "status.json",
    "status-failure.json",
    "status-no-fallback.json",
)


def main() -> int:
    success = packet.load_packet(DATA_DIR / "packet.json")
    if not success:
        print("先运行 `python services/run_daily.py --mock-ai` 生成成功包")
        return 1

    data_date = success["data_date"]
    previous_date = (date.fromisoformat(data_date) - timedelta(days=1)).isoformat()

    # --- failure: today unavailable, fallback to previous success ---
    failure = copy.deepcopy(success)
    failure["run_id"] = success["run_id"] + "--fixture-failure"
    failure["analysis"] = None
    failure["analysis_date"] = previous_date
    fallback = copy.deepcopy(FALLBACK_ANALYSIS)
    fallback["analysis_date"] = previous_date
    failure["fallback"] = fallback
    failure["status"] = {
        "today_available": False,
        "last_success_date": previous_date,
        "reason": "今日 AI 分析不可用（验收回退场景）",
    }
    packet.validate_packet(failure)
    packet.write_packet_atomic(failure, DATA_DIR / "packet-failure.json")
    print(f"wrote packet-failure.json (fallback stage=深度压力期, date={previous_date})")

    # --- no-fallback: today unavailable, no previous success ---
    no_fallback = copy.deepcopy(success)
    no_fallback["run_id"] = success["run_id"] + "--fixture-no-fallback"
    no_fallback["analysis"] = None
    no_fallback["analysis_date"] = None
    no_fallback["fallback"] = None
    no_fallback["status"] = {
        "today_available": False,
        "last_success_date": None,
        "reason": "今日 AI 分析不可用，且没有上一份成功结果",
    }
    packet.validate_packet(no_fallback)
    packet.write_packet_atomic(no_fallback, DATA_DIR / "packet-no-fallback.json")
    print("wrote packet-no-fallback.json (no fallback)")

    # --- remove the v0.1.0 scattered files (page now reads one packet) ---
    removed = []
    for name in LEGACY_FILES:
        legacy = DATA_DIR / name
        if legacy.exists():
            legacy.unlink()
            removed.append(name)
    if removed:
        print(f"removed legacy scattered files: {', '.join(removed)}")

    print("\nfixtures ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
