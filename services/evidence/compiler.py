"""Compile the v0.4 factual evidence brief for the AI boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from services.ai.contract import (
    BOTTOMING_STATES,
    CATEGORY_IDS,
    CONSISTENCY_VALUES,
    PRESSURE_STATES,
    STATE_DEFINITIONS,
)

from .catalog import (
    INDICATOR_ROLE_REGISTRY,
    THEME_REGISTRY,
    canonical_id_for_snapshot_id,
    correlation_family_for,
    role_for,
    theme_for,
)
from .context import build_previous_three_day_context
from .quality import AXIS_REQUIRED_METRICS, CURRENT, DEFAULT_MAX_STALE_DAYS, evaluate_snapshot_quality
from .timeline import (
    LOOKBACK_CONFIG,
    build_family_timeline,
    build_timeline_summary,
    classify_tier,
)


def _raw_by_id(snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item.get("id")): item
        for item in snapshot.get("metrics", [])
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }


def _metric_thresholds(raw: Mapping[str, Any], state: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    current_value = state.get("current_value")
    raw_thresholds = raw.get("thresholds")
    if not isinstance(raw_thresholds, list):
        raw_thresholds = []
    classified = classify_tier(current_value, [item for item in raw_thresholds if isinstance(item, Mapping)], raw.get("direction"))
    result: list[dict[str, Any]] = []
    for index, threshold in enumerate(raw_thresholds):
        if not isinstance(threshold, Mapping) or threshold.get("role", "trigger") == "neutral":
            continue
        threshold_value = threshold.get("value")
        direction = threshold.get("direction")
        triggered = (
            isinstance(current_value, (int, float))
            and not isinstance(current_value, bool)
            and isinstance(threshold_value, (int, float))
            and not isinstance(threshold_value, bool)
            and ((direction == "below" and current_value < threshold_value) or (direction == "above" and current_value > threshold_value))
            if state.get("status") == CURRENT
            else None
        )
        tier_id = threshold.get("tier_id") or (classified.get("tier_id") if classified.get("threshold_index") == index else "observation")
        result.append({
            "value": threshold_value,
            "direction": direction,
            "label": str(threshold.get("label") or "观察区"),
            "meaning": str(threshold.get("meaning") or ""),
            "tier_id": str(tier_id),
            "triggered": triggered,
        })
    return {"tier": classified, "thresholds": result}, classified


def _metric_index(snapshot: Mapping[str, Any], quality: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_by_id = _raw_by_id(snapshot)
    result: list[dict[str, Any]] = []
    for state in quality.get("metrics", []):
        if not isinstance(state, Mapping):
            continue
        metric_id = str(state.get("id") or "")
        raw = raw_by_id.get(metric_id, {})
        threshold_data, classified = _metric_thresholds(raw, state)
        item = {
            **dict(state),
            "thresholds": threshold_data["thresholds"],
            "triggered": bool(classified.get("triggered")) if state.get("status") == CURRENT else None,
            "tier_id": str(classified.get("tier_id") or state.get("tier_id") or "none") if state.get("status") == CURRENT else "none",
            "tier_label": str(classified.get("tier_label") or state.get("tier_label") or "未进入观察区") if state.get("status") == CURRENT else "不可判断",
            "tier_meaning": str(classified.get("tier_meaning") or state.get("tier_meaning") or "当前值未触及该指标的观察阈值。"),
            "theme_id": theme_for(str(state.get("canonical_id") or metric_id)),
            "correlation_family": correlation_family_for(str(state.get("canonical_id") or metric_id)),
            "responsibility": str(INDICATOR_ROLE_REGISTRY[str(state.get("canonical_id") or metric_id)].get("primary_responsibility") or "context"),
            "axis_relevance": list(INDICATOR_ROLE_REGISTRY[str(state.get("canonical_id") or metric_id)].get("axis_relevance") or ()),
        }
        result.append(item)
    return result


def _theme_items(metric_index: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for metric in metric_index:
        family = str(metric.get("correlation_family") or "unknown")
        grouped.setdefault(family, []).append(metric)
    items: list[dict[str, Any]] = []
    for family, metrics in sorted(grouped.items()):
        eligible = [metric for metric in metrics if metric.get("judgment_eligible")]
        triggered = [metric for metric in eligible if metric.get("triggered")]
        items.append({
            "correlation_family": family,
            "theme_id": str(metrics[0].get("theme_id") or family),
            "label": str(THEME_REGISTRY.get(str(metrics[0].get("theme_id")), {}).get("label") or family),
            "description": str(THEME_REGISTRY.get(str(metrics[0].get("theme_id")), {}).get("description") or "相关事实归为同一证据家族。"),
            "metric_ids": [str(metric.get("id")) for metric in metrics],
            "triggered_metric_ids": [str(metric.get("id")) for metric in triggered],
            "eligible_metric_ids": [str(metric.get("id")) for metric in eligible],
            "has_current_support": bool(triggered),
            "axis_relevance": sorted({axis for metric in metrics for axis in metric.get("axis_relevance", [])}),
        })
    return items


def _contrary_or_gaps(metric_index: list[Mapping[str, Any]], readiness: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for axis, axis_state in readiness.items():
        if not isinstance(axis_state, Mapping):
            continue
        for metric_id, reason in zip(axis_state.get("missing_metric_ids", []), axis_state.get("missing_reasons", [])):
            result.append({
                "kind": "data_gap",
                "axis": axis,
                "metric_ids": [metric_id],
                "detail": f"{metric_id} 当前不可用：{reason}；不能当作没有压力或没有筑底。",
            })
    for metric in metric_index:
        if metric.get("status") != CURRENT:
            result.append({
                "kind": "data_limit",
                "axis": list(metric.get("axis_relevance") or []),
                "metric_ids": [metric.get("id")],
                "detail": f"{metric.get('label') or metric.get('id')}：{metric.get('reason') or '当前不参与判断'}。",
            })
    for metric in metric_index:
        if metric.get("status") == CURRENT and not metric.get("triggered") and metric.get("responsibility") in {"pressure_anchor", "pressure_confirmation", "repair_signal", "exhaustion_clue"}:
            result.append({
                "kind": "contrary_or_untriggered",
                "axis": list(metric.get("axis_relevance") or []),
                "metric_ids": [metric.get("id")],
                "detail": f"{metric.get('label') or metric.get('id')} 当前没有触发自己的校准阈值，不能当作支持事实。",
            })
    return result


def compile_evidence(
    snapshot: dict[str, Any],
    *,
    analysis_date: str | None = None,
    histories: Mapping[str, object] | None = None,
    previous_records: list[Mapping[str, Any]] | None = None,
    previous_three_days: list[Mapping[str, Any]] | None = None,
    lookback_days: int = int(LOOKBACK_CONFIG["selected_days"]),
    max_stale_days: int = DEFAULT_MAX_STALE_DAYS,
) -> dict[str, Any]:
    """Return the deterministic v0.4 evidence brief."""

    quality = evaluate_snapshot_quality(snapshot, analysis_date=analysis_date, max_stale_days=max_stale_days)
    metric_index = _metric_index(snapshot, quality)
    timelines = build_timeline_summary(
        snapshot,
        histories=histories,
        analysis_date=quality["analysis_date"],
        lookback_days=lookback_days,
        max_stale_days=max_stale_days,
    )
    families = build_family_timeline(metric_index, timelines["metrics"])
    readiness = quality["axis_readiness"]
    timeline_by_id = {
        str(item.get("metric_id")): item
        for item in timelines["metrics"]
        if isinstance(item, Mapping)
    }
    state_by_canonical = {
        str(item.get("canonical_id")): item
        for item in metric_index
        if isinstance(item, Mapping)
    }
    for axis, required_ids in AXIS_REQUIRED_METRICS.items():
        axis_state = readiness[axis]
        incomplete = []
        for canonical_id in required_ids:
            state = state_by_canonical.get(canonical_id)
            timeline = timeline_by_id.get(str(state.get("id"))) if state else None
            if not timeline or timeline.get("timeline_complete") is not True:
                incomplete.append(canonical_id)
        axis_state["timeline_complete"] = not incomplete
        for canonical_id in incomplete:
            if canonical_id not in axis_state["missing_metric_ids"]:
                axis_state["missing_metric_ids"].append(canonical_id)
                axis_state["missing_reasons"].append("该指标缺少可用的时间线覆盖")
        if incomplete:
            axis_state["ready"] = False
    context = previous_three_days or build_previous_three_day_context(quality["analysis_date"], previous_records or [])
    themes = _theme_items(metric_index)
    metric_states = [
        {
            "id": item["id"],
            "canonical_id": item["canonical_id"],
            "label": item["label"],
            "category": item.get("category"),
            "role": item["role"],
            "responsibility": item["responsibility"],
            "axis_relevance": item["axis_relevance"],
            "correlation_family": item["correlation_family"],
            "status": item["status"],
            "judgment_eligible": item["judgment_eligible"],
            "metric_date": item["metric_date"],
            "days_stale": item["days_stale"],
            "current_value": item["current_value"],
            "reason": item["reason"],
            "tier_id": item["tier_id"],
            "tier_label": item["tier_label"],
            "tier_meaning": item["tier_meaning"],
            "triggered": item["triggered"],
            "thresholds": item["thresholds"],
        }
        for item in metric_index
    ]
    pressure_facts = [item for item in metric_states if item.get("judgment_eligible") and "pressure" in item.get("axis_relevance", [])]
    bottoming_facts = [item for item in metric_states if item.get("judgment_eligible") and "bottoming" in item.get("axis_relevance", [])]
    return {
        "brief_version": "0.4.0",
        "analysis_date": quality["analysis_date"],
        "state_vocabularies": {
            "pressure": [{"state": state, "definition": STATE_DEFINITIONS["pressure"][state]} for state in PRESSURE_STATES],
            "bottoming": [{"state": state, "definition": STATE_DEFINITIONS["bottoming"][state]} for state in BOTTOMING_STATES],
            "consistency": [{"value": value, "definition": {"弱": "证据方向分散", "中等": "部分独立维度一致", "强": "多个独立维度一致"}[value]} for value in CONSISTENCY_VALUES],
        },
        "axis_readiness": readiness,
        "metric_states": metric_states,
        "pressure_facts": pressure_facts,
        "bottoming_facts": bottoming_facts,
        "evidence_families": families,
        "themes": themes,
        "contrary_or_gaps": _contrary_or_gaps(metric_index, readiness),
        "timeline": timelines,
        "previous_three_days": context,
        "lookback_config": timelines["config"],
        "category_ids": list(CATEGORY_IDS),
        "data_quality": quality,
    }


__all__ = ["compile_evidence"]
