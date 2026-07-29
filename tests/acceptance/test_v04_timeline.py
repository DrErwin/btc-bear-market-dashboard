from __future__ import annotations

from services.data.packet import _compute_tier
from services.evidence.context import build_previous_three_day_context
from services.evidence.timeline import build_metric_timeline, classify_tier, validate_lookback_candidates


def _metric(value: float, *, date: str = "2026-07-28", direction: str = "below", tier_id: str = "observation") -> dict:
    return {
        "id": "demo",
        "current_value": value,
        "current_date": date,
        "judgment_eligible": True,
        "status": "current",
        "thresholds": [
            {"value": 1.0, "direction": direction, "label": "编辑文字 A", "meaning": "A", "tier_id": tier_id},
            {"value": 0.8 if direction == "below" else 1.2, "direction": direction, "label": "编辑文字 B", "meaning": "B", "tier_id": "deep_pressure"},
        ],
    }


def test_timeline_records_entry_duration_recurrence_and_weakening() -> None:
    metric = _metric(0.7)
    history = [
        {"date": "2026-07-20", "value": 1.1},
        {"date": "2026-07-21", "value": 0.9},
        {"date": "2026-07-22", "value": 0.7},
        {"date": "2026-07-23", "value": 1.1},
        {"date": "2026-07-24", "value": 0.7},
    ]
    timeline = build_metric_timeline(metric, history=history, analysis_date="2026-07-28")
    assert timeline["current_tier_id"] == "deep_pressure"
    assert timeline["recurrence_count"] == 2
    assert timeline["first_entry_date"] == "2026-07-24"
    assert timeline["duration_days"] == 1
    assert any(event["kind"] == "exit" for event in timeline["events"])


def test_timeline_records_weakening_when_pressure_moves_to_a_shallower_tier() -> None:
    metric = _metric(0.9)
    history = [
        {"date": "2026-07-20", "value": 0.7},
        {"date": "2026-07-21", "value": 0.9},
    ]
    timeline = build_metric_timeline(metric, history=history, analysis_date="2026-07-28")
    assert timeline["current_tier_id"] == "observation"
    assert any(event["kind"] == "weakening" for event in timeline["events"])


def test_above_direction_is_preserved_in_timeline() -> None:
    metric = _metric(1.3, direction="above")
    assert classify_tier(1.3, metric["thresholds"], "above")["tier_id"] == "deep_pressure"


def test_expired_metric_has_no_current_tier() -> None:
    metric = _metric(0.7, date="2023-01-12")
    metric["status"] = "display_only"
    metric["judgment_eligible"] = False
    timeline = build_metric_timeline(metric, analysis_date="2026-07-28")
    assert timeline["current_tier_id"] == "none"
    assert timeline["duration_days"] is None


def test_stale_metric_has_no_current_tier_even_without_quality_metadata() -> None:
    metric = _metric(0.7, date="2026-07-20")
    timeline = build_metric_timeline(metric, analysis_date="2026-07-28", max_stale_days=2)
    assert timeline["current_tier_id"] == "none"
    assert timeline["duration_days"] is None


def test_label_only_change_does_not_change_stable_tier() -> None:
    thresholds = [
        {"value": 1.0, "direction": "below", "label": "任意文案", "meaning": "A", "tier_id": "observation"},
        {"value": 0.8, "direction": "below", "label": "另一种文案", "meaning": "B", "tier_id": "deep_pressure"},
    ]
    before = classify_tier(0.7, thresholds, "below")
    thresholds[0]["label"] = "新的显示名称"
    thresholds[1]["label"] = "新的深层名称"
    after = classify_tier(0.7, thresholds, "below")
    assert before["tier_id"] == after["tier_id"] == "deep_pressure"
    assert _compute_tier("below", [1.0, 0.8], thresholds, 0.7)[2] == "deep_pressure"


def test_three_natural_days_keep_missing_and_incompatible_records_explicit() -> None:
    records = [
        {"data_date": "2026-07-27", "status": {"today_available": True}, "analysis": {"pressure_state": "进入观察", "bottoming_state": "筑底线索出现", "consistency": "弱", "analysis_date": "2026-07-27"}},
        {"data_date": "2026-07-26", "status": {"today_available": True}, "analysis": {"stage": "熊市下行期"}},
    ]
    context = build_previous_three_day_context("2026-07-28", records)
    assert [item["date"] for item in context] == ["2026-07-25", "2026-07-26", "2026-07-27"]
    assert context[0]["status"] == "missing"
    assert context[1]["status"] == "incompatible"
    assert context[2]["status"] == "current"


def test_lookback_validation_produces_a_reviewable_report() -> None:
    report = validate_lookback_candidates({"mvrv": [{"date": "2026-01-01", "value": 1.0}]}, analysis_date="2026-07-28")
    assert report["status"] == "review_required"
    assert report["candidates"]
    assert {"series_without_coverage", "expired_only_series"} <= set(report["candidates"][0])
