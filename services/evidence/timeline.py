"""Bounded, factual evidence timelines for v0.4.

The timeline records when a metric crossed its own calibrated thresholds.  It
never turns those events into a market-state score; the AI receives the events
and makes the qualitative two-axis judgement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any


LOOKBACK_CONFIG: dict[str, Any] = {
    "version": "v0.4.0-lookback-1",
    "selected_days": 730,
    "candidate_days": [365, 730, 1095],
    "validation_status": "validated_local_fixture",
    "validation_report": "specs/v0.4.0/lookback-validation.json",
}


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _threshold_tier(threshold: Mapping[str, Any], index: int) -> str:
    tier_id = threshold.get("tier_id")
    if tier_id in {"observation", "deep_pressure", "extreme_pressure"}:
        return tier_id
    return "none"


def _tier_rank(tier_id: str) -> int:
    return {
        "none": 0,
        "observation": 1,
        "deep_pressure": 2,
        "extreme_pressure": 3,
    }.get(tier_id, 0)


def classify_tier(value: object, thresholds: Sequence[Mapping[str, Any]], direction: str | None = None) -> dict[str, Any]:
    """Classify one value using stable threshold ids and supplied direction."""

    current = _number(value)
    selected: Mapping[str, Any] | None = None
    selected_id = "none"
    selected_index = -1
    for index, threshold in enumerate(thresholds):
        if threshold.get("role", "trigger") == "neutral":
            continue
        target = _number(threshold.get("value"))
        rule_direction = str(threshold.get("direction") or direction or "")
        if current is None or target is None:
            continue
        crossed = (rule_direction == "below" and current < target) or (
            rule_direction == "above" and current > target
        )
        if not crossed:
            continue
        tier_id = _threshold_tier(threshold, index)
        if tier_id == "none":
            continue
        if _tier_rank(tier_id) >= _tier_rank(selected_id):
            selected = threshold
            selected_id = tier_id
            selected_index = index
    return {
        "tier_id": selected_id,
        "tier_label": str(selected.get("label") or "未进入观察区") if selected else "未进入观察区",
        "tier_meaning": str(selected.get("meaning") or "当前值未触及该指标的观察阈值。") if selected else "当前值未触及该指标的观察阈值。",
        "threshold_index": selected_index,
        "triggered": selected is not None,
    }


def _normalise_history(metric: Mapping[str, Any], history: object) -> list[tuple[date, float]]:
    values: list[tuple[date, float]] = []
    raw = history if history is not None else metric.get("history")
    if isinstance(raw, Mapping):
        iterator = raw.items()
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        iterator = (
            (item.get("date"), item.get("value"))
            for item in raw
            if isinstance(item, Mapping)
        )
    else:
        iterator = ()
    for raw_day, raw_value in iterator:
        day = _parse_date(raw_day)
        value = _number(raw_value)
        if day is not None and value is not None:
            values.append((day, value))
    return sorted(dict(values).items())


def build_metric_timeline(
    metric: Mapping[str, Any],
    *,
    history: object = None,
    analysis_date: str | date | None = None,
    lookback_days: int = 730,
    max_stale_days: int = 2,
) -> dict[str, Any]:
    """Return a bounded timeline summary for one metric."""

    analysis_day = _parse_date(analysis_date) or _parse_date(metric.get("current_date"))
    if analysis_day is None:
        raise ValueError("时间线缺少有效分析日期")
    thresholds = metric.get("thresholds")
    if not isinstance(thresholds, Sequence) or isinstance(thresholds, (str, bytes)):
        thresholds = []
    direction = str(metric.get("direction") or next((item.get("direction") for item in thresholds if isinstance(item, Mapping)), ""))
    history_supplied = history is not None or "history" in metric
    points = _normalise_history(metric, history)
    current_date = _parse_date(metric.get("current_date")) or (points[-1][0] if points else None)
    cutoff = analysis_day - timedelta(days=max(0, lookback_days))
    points = [(day, value) for day, value in points if cutoff <= day <= analysis_day]
    window_history_points = len(points)
    if not points and current_date is not None:
        current_value = _number(metric.get("current_value"))
        if current_value is not None:
            points = [(current_date, current_value)]

    classified = [
        (day, value, classify_tier(value, thresholds, direction))
        for day, value in points
    ]
    events: list[dict[str, Any]] = []
    previous = "none"
    for day, value, state in classified:
        current = str(state["tier_id"])
        if current != previous:
            if current != "none" and previous == "none":
                kind = "entry"
            elif current == "none" and previous != "none":
                kind = "exit"
            elif current != "none" and _tier_rank(current) > _tier_rank(previous):
                kind = "strengthening"
            elif current != "none" and _tier_rank(current) < _tier_rank(previous):
                kind = "weakening"
            else:
                kind = "reversal"
            events.append({"date": day.isoformat(), "kind": kind, "from": previous, "to": current})
        previous = current
    current_state = classified[-1][2] if classified else classify_tier(metric.get("current_value"), thresholds, direction)
    current_tier = str(current_state["tier_id"])
    latest_change = events[-1] if events else None
    duration = None
    current_episode_start: date | None = None
    if classified and current_tier != "none":
        latest_index = len(classified) - 1
        if classified and classified[-1][2]["tier_id"] == "none":
            latest_index = next((index for index in range(len(classified) - 1, -1, -1) if classified[index][2]["tier_id"] != "none"), -1)
        first_index = latest_index
        while first_index > 0 and classified[first_index - 1][2]["tier_id"] != "none":
            first_index -= 1
        if first_index >= 0 and latest_index >= first_index:
            current_episode_start = classified[first_index][0]
            duration = (classified[latest_index][0] - classified[first_index][0]).days + 1
    recurrence = sum(1 for event in events if event["kind"] == "entry")
    metric_date = _parse_date(metric.get("current_date"))
    freshness_days = None if metric_date is None else (analysis_day - metric_date).days
    unavailable_reason = metric.get("availability_reason") or metric.get("reason")
    expired = (
        freshness_days is None
        or freshness_days < 0
        or freshness_days > max_stale_days
    )
    if (
        expired
        or metric.get("judgment_eligible") is False
        or metric.get("status") in {"display_only", "validation_pending", "missing"}
    ):
        current_tier = "none"
        duration = None
        current_episode_start = None

    return {
        "metric_id": str(metric.get("id") or ""),
        "current_tier_id": current_tier,
        "current_tier_label": current_state.get("tier_label", "未进入观察区") if current_tier != "none" else "未进入观察区",
        "first_entry_date": current_episode_start.isoformat() if current_episode_start else None,
        "latest_change": latest_change,
        "duration_days": duration,
        "recurrence_count": recurrence,
        "recent_direction": (
            latest_change["kind"]
            if latest_change and latest_change["kind"] in {"entry", "exit", "strengthening", "weakening", "reversal"}
            else "unchanged"
        ),
        "data_date": metric_date.isoformat() if metric_date else None,
        "freshness_days": freshness_days,
        "history_points": len(points),
        "timeline_complete": bool(metric.get("timeline_complete", True)) and (
            not history_supplied or window_history_points > 0
        ) and not expired,
        "events": events[-12:],
        "unavailable_reason": unavailable_reason,
    }


def build_timeline_summary(
    snapshot: Mapping[str, Any],
    *,
    histories: Mapping[str, object] | None = None,
    analysis_date: str | date | None = None,
    lookback_days: int = 730,
    max_stale_days: int = 2,
) -> dict[str, Any]:
    metrics = snapshot.get("metrics")
    if not isinstance(metrics, Sequence) or isinstance(metrics, (str, bytes)):
        raise ValueError("snapshot.metrics 必须是列表")
    summaries: list[dict[str, Any]] = []
    histories = histories or {}
    for metric in metrics:
        if not isinstance(metric, Mapping):
            continue
        metric_id = str(metric.get("id") or "")
        summaries.append(
            build_metric_timeline(
                metric,
                history=histories.get(metric_id),
                analysis_date=analysis_date,
                lookback_days=lookback_days,
                max_stale_days=max_stale_days,
            )
        )
    return {
        "config": {**LOOKBACK_CONFIG, "selected_days": lookback_days},
        "metrics": summaries,
    }


def build_family_timeline(
    metric_states: Sequence[Mapping[str, Any]],
    metric_timelines: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    timeline_by_id = {str(item.get("metric_id")): item for item in metric_timelines}
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for state in metric_states:
        family = str(state.get("correlation_family") or "unknown")
        grouped.setdefault(family, []).append(state)
    result: list[dict[str, Any]] = []
    for family, states in sorted(grouped.items()):
        timelines = [timeline_by_id.get(str(state.get("id")), {}) for state in states]
        result.append({
            "correlation_family": family,
            "label": family,
            "metric_ids": [str(state.get("id")) for state in states],
            "eligible_metric_ids": [str(state.get("id")) for state in states if state.get("judgment_eligible")],
            "triggered_metric_ids": [
                str(state.get("id")) for state in states if state.get("judgment_eligible") and state.get("triggered")
            ],
            "current_tiers": [timeline.get("current_tier_id", "none") for timeline in timelines],
            "recent_events": [
                {"metric_id": timeline.get("metric_id"), "event": timeline.get("latest_change")}
                for timeline in timelines if timeline.get("latest_change")
            ][-8:],
        })
    return result


def validate_lookback_candidates(
    histories: Mapping[str, object],
    *,
    analysis_date: str | date,
    candidate_days: Sequence[int] = (365, 730, 1095),
    selected_days: int = 730,
) -> dict[str, Any]:
    """Produce an auditable comparison before a lookback is activated.

    This is intentionally a coverage report, not a state rule.  A release can
    record the report alongside the selected range and review it separately.
    """

    analysis_day = _parse_date(analysis_date)
    if analysis_day is None:
        raise ValueError("analysis_date 无效")
    results: list[dict[str, Any]] = []
    for days in candidate_days:
        cutoff = analysis_day - timedelta(days=int(days))
        coverage = 0
        expired_only = 0
        spans: list[int] = []
        for raw in histories.values():
            points = _normalise_history({}, raw)
            in_window = [(day, value) for day, value in points if cutoff <= day <= analysis_day]
            if in_window:
                coverage += 1
                spans.append((in_window[-1][0] - in_window[0][0]).days + 1)
            elif points:
                expired_only += 1
        results.append({
            "days": int(days),
            "series_with_coverage": coverage,
            "series_without_coverage": len(histories) - coverage,
            "expired_only_series": expired_only,
            "series_count": len(histories),
            "shortest_covered_span_days": min(spans) if spans else None,
            "longest_covered_span_days": max(spans) if spans else None,
        })
    selected = next((item for item in results if item["days"] == selected_days), None)
    if selected is None:
        selected = max((item for item in results if item["series_with_coverage"]), key=lambda item: item["days"], default=None)
    return {
        "config_version": LOOKBACK_CONFIG["version"],
        "candidates": results,
        "selected_days": selected["days"] if selected else None,
        "status": "review_required",
    }


__all__ = [
    "LOOKBACK_CONFIG",
    "classify_tier",
    "build_metric_timeline",
    "build_timeline_summary",
    "build_family_timeline",
    "validate_lookback_candidates",
]
