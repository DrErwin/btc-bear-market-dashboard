"""Build the bounded v0.4 request sent to the AI provider."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .contract import (
    BOTTOMING_STATES,
    CATEGORY_IDS,
    CONSISTENCY_VALUES,
    PRESSURE_STATES,
    STATE_DEFINITIONS,
)
from services.evidence.compiler import compile_evidence


def _load_snapshot(snapshot: str | Path | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(snapshot, Mapping):
        return snapshot
    path = Path(snapshot)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 snapshot JSON: {path}") from exc
    if not isinstance(value, Mapping):
        raise ValueError("snapshot 必须是 JSON 对象")
    return value


def _threshold_summary(status: str, tier_id: str, tier_label: str, thresholds: list[dict[str, Any]]) -> str:
    if status != "current":
        return "当前不把该指标作为有效判断证据。"
    if tier_id == "none":
        return "当前未触发该指标的校准阈值。"
    triggered = [item for item in thresholds if item.get("triggered") is True]
    if not triggered:
        return f"当前档位为{tier_label}。"
    highest = triggered[-1]
    symbol = "低于" if highest.get("direction") == "below" else "高于"
    return f"当前已触发{highest.get('label')}（{symbol} {highest.get('value')}）。"


def _metric_inputs(snapshot: Mapping[str, Any], brief: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_metrics = snapshot.get("metrics")
    states = brief.get("metric_states")
    if not isinstance(raw_metrics, list) or not isinstance(states, list):
        raise ValueError("证据简报缺少完整指标状态")
    raw_by_id = {
        str(item.get("id")): item
        for item in raw_metrics
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }
    result: list[dict[str, Any]] = []
    for state in states:
        if not isinstance(state, Mapping):
            continue
        metric_id = str(state.get("id") or "")
        raw = raw_by_id.get(metric_id, {})
        thresholds = [
            {
                "value": threshold.get("value"),
                "direction": threshold.get("direction"),
                "tier_id": threshold.get("tier_id") or "observation",
                "label": threshold.get("label"),
                "meaning": threshold.get("meaning"),
                "triggered": threshold.get("triggered"),
            }
            for threshold in state.get("thresholds", [])
            if isinstance(threshold, Mapping)
        ]
        result.append({
            "id": metric_id,
            "name": str(state.get("label") or raw.get("label") or metric_id),
            "category": str(state.get("category") or raw.get("category") or ""),
            "role": state.get("role"),
            "responsibility": state.get("responsibility"),
            "axis_relevance": list(state.get("axis_relevance") or []),
            "correlation_family": state.get("correlation_family"),
            "value": state.get("current_value") if state.get("status") == "current" else None,
            "date": state.get("metric_date"),
            "status": state.get("status"),
            "judgment_eligible": bool(state.get("judgment_eligible")),
            "days_stale": state.get("days_stale"),
            "unavailable_reason": state.get("reason"),
            "tier": {
                "id": state.get("tier_id") or "none",
                "label": state.get("tier_label") or "未进入观察区",
                "meaning": state.get("tier_meaning") or "当前值未触及该指标的观察阈值。",
            },
            "thresholds": thresholds,
            "threshold_summary": _threshold_summary(
                str(state.get("status") or "missing"),
                str(state.get("tier_id") or "none"),
                str(state.get("tier_label") or "未进入观察区"),
                thresholds,
            ),
        })
    return result


def build_evidence_input(
    snapshot: str | Path | Mapping[str, Any],
    *,
    evidence_brief: Mapping[str, Any] | None = None,
    analysis_date: str | None = None,
    previous_three_days: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return facts and boundaries allowed at the AI input seam.

    Chart series, price, source metadata, private calibration actions, and
    unrestricted historical curves are excluded by construction.
    """

    loaded = _load_snapshot(snapshot)
    brief = evidence_brief or compile_evidence(loaded, analysis_date=analysis_date)
    metrics = _metric_inputs(loaded, brief)
    context = previous_three_days or brief.get("previous_three_days") or []
    return {
        "contract_version": "0.4.0",
        "analysis_date": str(brief.get("analysis_date") or analysis_date or loaded.get("snapshot_date") or ""),
        "state_definitions": {
            "pressure": [{"state": state, "definition": STATE_DEFINITIONS["pressure"][state]} for state in PRESSURE_STATES],
            "bottoming": [{"state": state, "definition": STATE_DEFINITIONS["bottoming"][state]} for state in BOTTOMING_STATES],
            "consistency": [{"value": value, "definition": {"弱": "证据方向分散", "中等": "部分独立维度一致", "强": "多个独立维度一致"}[value]} for value in CONSISTENCY_VALUES],
        },
        "axis_readiness": brief.get("axis_readiness", {}),
        "category_ids": list(CATEGORY_IDS),
        "metric_states": metrics,
        "evidence_families": brief.get("evidence_families", []),
        "timeline": brief.get("timeline", {"metrics": [], "config": {}}),
        "contrary_or_gaps": brief.get("contrary_or_gaps", []),
        "previous_three_days": context,
        "instructions": {
            "choose_independently": True,
            "do_not_count_correlated_metrics_as_separate_votes": True,
            "do_not_output_machine_rule_terms": True,
            "do_not_give_trading_advice": True,
        },
    }


def build_ai_input(snapshot: str | Path | Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Compatibility name for callers migrating from v0.3."""

    return build_evidence_input(snapshot, **kwargs)


__all__ = ["build_evidence_input", "build_ai_input"]
