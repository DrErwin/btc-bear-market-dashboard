"""Compile raw metric cards into the constrained v0.3.0 evidence brief."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .catalog import THEME_REGISTRY, canonical_id_for_snapshot_id, role_for, theme_for
from .quality import (
    CURRENT,
    DEFAULT_MAX_STALE_DAYS,
    evaluate_snapshot_quality,
)


STAGE_0 = "尚未进入熊底观察期"
STAGE_1 = "熊市下行期"
STAGE_2 = "深度压力期"
STAGE_3 = "筑底证据积累期"
STAGE_4 = "熊底证据充分期"
DATA_INSUFFICIENT = "数据不足"

_CORE_METRICS = ("mvrv", "puell_multiple")


def _state_from_thresholds(metric: Mapping[str, Any]) -> str:
    """Classify a metric from the same thresholds exposed in its snapshot."""
    value = metric.get("current_value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "missing"
    state = "none"
    for threshold in metric.get("thresholds", []):
        if not isinstance(threshold, Mapping) or threshold.get("role", "trigger") == "neutral":
            continue
        target = threshold.get("value")
        direction = threshold.get("direction")
        if not isinstance(target, (int, float)) or isinstance(target, bool):
            continue
        crossed = (
            (direction == "below" and value < target)
            or (direction == "above" and value > target)
        )
        if not crossed:
            continue
        label = str(threshold.get("label") or "")
        if "深度" in label or "深部" in label or "极端" in label:
            return "deep"
        state = "watch"
    return state


def _state_label(state: str) -> str:
    return {
        "none": "未触发",
        "watch": "观察",
        "deep": "深度压力",
        "missing": "不可判断",
    }[state]


def _threshold_triggered(metric: Mapping[str, Any]) -> bool:
    value = metric.get("current_value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    for threshold in metric.get("thresholds", []):
        if not isinstance(threshold, Mapping) or threshold.get("role", "trigger") == "neutral":
            continue
        target = threshold.get("value")
        direction = threshold.get("direction")
        if not isinstance(target, (int, float)):
            continue
        if direction == "below" and value < target:
            return True
        if direction == "above" and value > target:
            return True
    return False


def _metric_index(snapshot: Mapping[str, Any], quality: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw_by_id = {
        raw.get("id"): raw
        for raw in snapshot.get("metrics", [])
        if isinstance(raw, Mapping) and isinstance(raw.get("id"), str)
    }
    result: dict[str, dict[str, Any]] = {}
    for item in quality["metrics"]:
        raw = raw_by_id.get(item["id"], {})
        copy = dict(item)
        copy["triggered"] = item["status"] == CURRENT and _threshold_triggered(raw)
        copy["thresholds"] = [
            {
                "value": threshold.get("value"),
                "direction": threshold.get("direction"),
                "label": threshold.get("label"),
                "meaning": threshold.get("meaning"),
            }
            for threshold in raw.get("thresholds", [])
            if isinstance(threshold, Mapping) and threshold.get("role", "trigger") != "neutral"
        ]
        result[item["canonical_id"]] = copy
    return result


def _core_dimension(
    metric: Mapping[str, Any] | None,
    *,
    dimension: str,
) -> dict[str, Any]:
    if not metric or metric.get("status") != CURRENT or not isinstance(metric.get("current_value"), (int, float)):
        return {
            "dimension": dimension,
            "state": "missing",
            "label": _state_label("missing"),
            "metric_id": metric.get("id") if metric else None,
            "metric_date": metric.get("metric_date") if metric else None,
            "current_value": metric.get("current_value") if metric else None,
            "judgment_eligible": False,
        }
    state = _state_from_thresholds(metric)
    return {
        "dimension": dimension,
        "state": state,
        "label": _state_label(state),
        "metric_id": metric["id"],
        "metric_date": metric["metric_date"],
        "current_value": metric["current_value"],
        "judgment_eligible": True,
    }


def _allowed_stages(valuation: str, miners: str, aviv: str) -> list[str]:
    if valuation == "missing" or miners == "missing":
        return [DATA_INSUFFICIENT]
    if valuation == "none" and miners == "none":
        return [STAGE_0]
    if {valuation, miners} == {"none", "watch"}:
        return [STAGE_1]
    if valuation == "none" or miners == "none":
        return [STAGE_1, STAGE_2]
    if valuation == "deep" and miners == "deep":
        if aviv == "deep":
            return [STAGE_3, STAGE_4]
        return [STAGE_2, STAGE_3]
    if "deep" in {valuation, miners}:
        return [STAGE_2, STAGE_3]
    return [STAGE_1, STAGE_2]


def _next_condition(allowed: list[str]) -> str:
    if allowed == [DATA_INSUFFICIENT]:
        return "先补齐 MVRV 与 Puell 的当前有效数据，才能继续判断阶段。"
    highest = allowed[-1]
    return {
        STAGE_0: "MVRV 或 Puell 进入观察区，才会进入熊市下行期。",
        STAGE_1: "MVRV 与 Puell 同时进入观察区，或其中一项进入深度压力，才会扩大到深度压力期。",
        STAGE_2: "估值与矿工压力都触发，且至少一项进入深度压力，才会积累筑底证据。",
        STAGE_3: "MVRV、Puell 都进入深度压力，并获得 AVIV 的深度复核，才可能进入熊底证据充分期。",
        STAGE_4: "当前核心阶段上限已到；辅助证据仍需保持一致，不能由单项指标单独改变阶段。",
    }.get(highest, "继续补充当前有效的核心证据。")


def _theme_items(metric_index: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for canonical_id, metric in metric_index.items():
        if canonical_id in _CORE_METRICS or metric.get("status") != CURRENT:
            continue
        theme_id = theme_for(canonical_id)
        grouped.setdefault(theme_id, []).append(metric)

    items: list[dict[str, Any]] = []
    for theme_id, metrics in grouped.items():
        triggered = [metric for metric in metrics if metric.get("triggered")]
        if not triggered:
            continue
        labels = [str(metric.get("label") or metric.get("id")) for metric in triggered]
        strong = any(metric.get("role") == "strong_auxiliary" for metric in triggered)
        items.append({
            "theme_id": theme_id,
            "label": str(THEME_REGISTRY.get(theme_id, {}).get("label") or theme_id),
            "strength": "strong" if strong else "supporting",
            "metric_ids": [metric["id"] for metric in triggered],
            "metric_labels": labels,
            "signal": "；".join(labels),
        })
    items.sort(key=lambda item: (item["strength"] != "strong", -len(item["metric_ids"]), item["theme_id"]))
    return items


def _contrary(
    core_dimensions: Mapping[str, Mapping[str, Any]],
    metric_index: Mapping[str, Mapping[str, Any]],
    allowed: list[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for dimension in ("valuation", "miners"):
        item = core_dimensions[dimension]
        if item["state"] in {"none", "missing"}:
            result.append({
                "kind": "core_incomplete",
                "label": f"{dimension} 核心维度未形成压力",
                "detail": f"{item['metric_id'] or dimension} 当前为{item['label']}，不能把辅助压力当作核心确认。",
                "metric_ids": [item["metric_id"]] if item.get("metric_id") else [],
            })
    # 缺失或过期的指标不能被误读成“没有压力”。明确列为数据限制，
    # 让解释层知道它们暂时不参与判断，也不能充当反面证据。
    for canonical_id, metric in metric_index.items():
        if metric.get("status") == CURRENT:
            continue
        metric_id = metric.get("id")
        if not metric_id:
            continue
        result.append({
            "kind": "data_limit",
            "label": metric.get("label", canonical_id),
            "detail": f"{metric.get('reason') or '当前不参与判断。'}；不作为反面证据。",
            "metric_ids": [metric_id],
        })
    if allowed != [DATA_INSUFFICIENT]:
        result.append({
            "kind": "stage_limit",
            "label": "阶段上限",
            "detail": f"机器允许的阶段范围为：{' / '.join(allowed)}。辅助主题不能扩大这个范围。",
            "metric_ids": [],
        })
    return result


def compile_evidence(
    snapshot: dict[str, Any],
    *,
    analysis_date: str | None = None,
    max_stale_days: int = DEFAULT_MAX_STALE_DAYS,
) -> dict[str, Any]:
    """Return the deterministic, JSON-ready v0.3.0 evidence brief."""

    quality = evaluate_snapshot_quality(
        snapshot,
        analysis_date=analysis_date,
        max_stale_days=max_stale_days,
    )
    metric_index = _metric_index(snapshot, quality)
    valuation = _core_dimension(metric_index.get("mvrv"), dimension="valuation")
    miners = _core_dimension(metric_index.get("puell_multiple"), dimension="miners")
    aviv_metric = metric_index.get("aviv")
    aviv_state = "missing"
    if aviv_metric and aviv_metric.get("status") == CURRENT and isinstance(aviv_metric.get("current_value"), (int, float)):
        aviv_state = _state_from_thresholds(aviv_metric)

    allowed = _allowed_stages(valuation["state"], miners["state"], aviv_state)
    themes = _theme_items(metric_index)
    strong = [item for item in themes if item["strength"] == "strong"][:3]
    ordinary = [item for item in themes if item not in strong][:3]

    core_dimensions = {
        "valuation": {
            **valuation,
            "vote": "valuation",
            "confirmation": {
                "metric_id": aviv_metric.get("id") if aviv_metric else None,
                "state": aviv_state,
                "label": _state_label(aviv_state),
                "metric_date": aviv_metric.get("metric_date") if aviv_metric else None,
                "judgment_eligible": bool(aviv_metric and aviv_metric.get("status") == CURRENT),
            },
        },
        "miners": {**miners, "vote": "miners"},
    }
    serialised_metrics = []
    for metric in metric_index.values():
        serialised_metrics.append({
            "id": metric["id"],
            "canonical_id": metric["canonical_id"],
            "label": metric["label"],
            "role": metric["role"],
            "status": metric["status"],
            "judgment_eligible": metric["judgment_eligible"],
            "triggered": metric["triggered"],
            "metric_date": metric["metric_date"],
            "days_stale": metric["days_stale"],
            "current_value": metric["current_value"],
            "reason": metric["reason"],
        })

    return {
        "brief_version": "0.3.0",
        "analysis_date": quality["analysis_date"],
        "allowed_stages": allowed,
        "core_dimensions": core_dimensions,
        "strong_auxiliary_themes": strong,
        "auxiliary_themes": ordinary,
        "contrary_or_incomplete": _contrary(core_dimensions, metric_index, allowed),
        "next_stage_conditions": [_next_condition(allowed)],
        "data_quality": quality,
        "metric_states": serialised_metrics,
    }


__all__ = ["compile_evidence"]
