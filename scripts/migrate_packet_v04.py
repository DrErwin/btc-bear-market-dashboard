"""Regenerate local packet fixtures at the v0.4 contract boundary.

This migration only reshapes the checked-in fixture and preserves its numeric
values, threshold directions, order, chart series, and source facts.  It does
not recalculate indicators or alter the user's manual calibration thresholds.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ai import provider  # noqa: E402
from services.data.packet import validate_packet  # noqa: E402
from services.data.packet_display import stable_tier_id_for_display  # noqa: E402
from services.evidence.compiler import compile_evidence  # noqa: E402
from services.evidence.timeline import classify_tier  # noqa: E402

SUCCESS = ROOT / "dashboard" / "public" / "data" / "packet.json"
FAILURE = ROOT / "dashboard" / "public" / "data" / "packet-failure.json"
NO_FALLBACK = ROOT / "dashboard" / "public" / "data" / "packet-no-fallback.json"


def _public_label(label: object) -> str:
    """Remove historical action wording from the public fixture only."""

    return str(label or "").replace("定投", "观察")


def _stable_threshold(threshold: dict, index: int) -> dict:
    item = dict(threshold)
    item["label"] = _public_label(item.get("label"))
    item["tier_id"] = stable_tier_id_for_display(str(threshold.get("metric_id") or ""), index) if threshold.get("metric_id") else item.get("tier_id")
    if not item.get("tier_id"):
        raise ValueError("迁移阈值缺少 metric_id，无法确定稳定档位")
    item.pop("metric_id", None)
    return item


def _upgrade_snapshot(packet: dict) -> tuple[dict, dict[str, list[dict[str, object]]]]:
    snapshot = copy.deepcopy(packet["snapshot"])
    series = packet.get("series", {}).get("metrics", {})
    histories: dict[str, list[dict[str, object]]] = {}
    for metric in snapshot.get("metrics", []):
        metric_id = str(metric.get("id"))
        metric["thresholds"] = [
            _stable_threshold({**threshold, "metric_id": metric_id}, index)
            for index, threshold in enumerate(metric.get("thresholds", []))
        ]
        classified = classify_tier(metric.get("current_value"), metric["thresholds"])
        metric["tier_id"] = classified["tier_id"]
        metric["tier_label"] = classified["tier_label"]
        metric["tier_meaning"] = classified["tier_meaning"]
        chart = series.get(metric_id, {})
        histories[metric_id] = chart.get("points", []) if isinstance(chart, dict) else []
        if isinstance(chart, dict):
            chart["thresholds"] = [
                _stable_threshold({**threshold, "metric_id": metric_id}, index)
                for index, threshold in enumerate(chart.get("thresholds", []))
            ]
    return snapshot, histories


def _make_success(old: dict) -> dict:
    snapshot, histories = _upgrade_snapshot(old)
    data_date = str(old["data_date"])
    brief = compile_evidence(snapshot, analysis_date=data_date, histories=histories, previous_three_days=[])
    analysis, reason = provider.call_ai(snapshot, data_date=data_date, mock=True, evidence_brief=brief, previous_three_days=[])
    if analysis is None:
        raise RuntimeError(reason or "mock analysis failed")
    result = copy.deepcopy(old)
    result.update({
        "schema_version": "0.4.0",
        "config_version": "0.4.0",
        "snapshot": snapshot,
        "evidence_brief": brief,
        "analysis": analysis,
        "fallback": None,
        "analysis_date": data_date,
        "status": {
            "today_available": True,
            "last_success_date": data_date,
            "reason": None,
            "data_insufficient": any(not item.get("ready") for item in brief["axis_readiness"].values()),
            "axis_readiness": brief["axis_readiness"],
            "data_quality": brief["data_quality"],
        },
    })
    validate_packet(result)
    return result


def _write(path: Path, packet: dict) -> None:
    path.write_text(json.dumps(packet, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    old = json.loads(SUCCESS.read_text(encoding="utf-8"))
    success = _make_success(old)
    _write(SUCCESS, success)

    failure = copy.deepcopy(success)
    failure["run_id"] = "20260729T000000Z-failure"
    failure["analysis"] = None
    failure["fallback"] = copy.deepcopy(success["analysis"])
    failure["analysis_date"] = success["analysis_date"]
    failure["status"] = {**success["status"], "today_available": False, "reason": "AI 输出不可用，展示最近一次完整 v0.4 结果。"}
    validate_packet(failure)
    _write(FAILURE, failure)

    no_fallback = copy.deepcopy(failure)
    no_fallback["run_id"] = "20260729T000000Z-no-fallback"
    no_fallback["fallback"] = None
    no_fallback["analysis_date"] = None
    no_fallback["status"] = {**no_fallback["status"], "last_success_date": None}
    validate_packet(no_fallback)
    _write(NO_FALLBACK, no_fallback)


if __name__ == "__main__":
    main()
