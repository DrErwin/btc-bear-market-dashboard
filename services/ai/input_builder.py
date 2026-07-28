"""Build the small, offline-safe request sent to an AI provider."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .contract import (
    ALLOWED_STAGES,
    CATEGORY_IDS,
    CATEGORY_STATUS_DEFINITIONS,
    CONSISTENCY_DEFINITIONS,
    CONSISTENCY_VALUES,
    MARKET_STAGES,
    STAGE_DEFINITIONS,
    CATEGORY_STATUS_VALUES,
    DATA_INSUFFICIENT_STAGE,
)
from services.evidence.compiler import compile_evidence


_REQUIRED_METRIC_KEYS = (
    "id",
    "label",
    "description",
    "category",
    "role",
    "current_value",
    "thresholds",
)
_REQUIRED_THRESHOLD_KEYS = ("value", "direction", "label", "meaning")


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


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"snapshot 字段 {field} 必须是非空文本")
    return value


def _number(value: object, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"snapshot 字段 {field} 必须是数值")
    return value


def _category_definitions(snapshot: Mapping[str, Any]) -> list[dict[str, str]]:
    raw_categories = snapshot.get("categories")
    if not isinstance(raw_categories, Sequence) or isinstance(raw_categories, (str, bytes)):
        raise ValueError("snapshot.categories 必须是类别列表")

    definitions: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw_category in enumerate(raw_categories):
        if not isinstance(raw_category, Mapping):
            raise ValueError(f"snapshot.categories[{index}] 必须是对象")
        category_id = _text(raw_category.get("id"), f"categories[{index}].id")
        category_name = _text(raw_category.get("name"), f"categories[{index}].name")
        if category_id not in CATEGORY_IDS:
            raise ValueError(f"未知类别: {category_id}")
        if category_id in seen:
            raise ValueError(f"重复类别: {category_id}")
        seen.add(category_id)
        definitions.append({"category": category_id, "definition": category_name})

    if seen != set(CATEGORY_IDS):
        raise ValueError("snapshot 必须包含六个固定类别")
    return definitions


def _metric_inputs(snapshot: Mapping[str, Any]) -> list[dict[str, object]]:
    raw_metrics = snapshot.get("metrics")
    if not isinstance(raw_metrics, Sequence) or isinstance(raw_metrics, (str, bytes)):
        raise ValueError("snapshot.metrics 必须是指标列表")
    if len(raw_metrics) != 16:
        raise ValueError("snapshot 必须包含 16 个指标")

    result: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, raw_metric in enumerate(raw_metrics):
        if not isinstance(raw_metric, Mapping):
            raise ValueError(f"snapshot.metrics[{index}] 必须是对象")
        missing = [key for key in _REQUIRED_METRIC_KEYS if key not in raw_metric]
        if missing:
            raise ValueError(f"指标 {index} 缺少字段: {', '.join(missing)}")

        metric_id = _text(raw_metric["id"], f"metrics[{index}].id")
        if metric_id in seen_ids:
            raise ValueError(f"重复指标: {metric_id}")
        seen_ids.add(metric_id)
        category = _text(raw_metric["category"], f"metrics[{index}].category")
        if category not in CATEGORY_IDS:
            raise ValueError(f"指标 {metric_id} 使用未知类别: {category}")
        role = _text(raw_metric["role"], f"metrics[{index}].role")
        if role not in {"核心", "核心锚", "核心复核", "强辅助", "辅助"}:
            raise ValueError(f"指标 {metric_id} 使用未知角色: {role}")

        raw_thresholds = raw_metric["thresholds"]
        if not isinstance(raw_thresholds, Sequence) or isinstance(raw_thresholds, (str, bytes)):
            raise ValueError(f"指标 {metric_id} 的 thresholds 必须是列表")
        thresholds: list[dict[str, object]] = []
        for threshold_index, raw_threshold in enumerate(raw_thresholds):
            if not isinstance(raw_threshold, Mapping):
                raise ValueError(f"指标 {metric_id} 的阈值 {threshold_index} 必须是对象")
            threshold_role = raw_threshold.get("role", "trigger")
            if threshold_role not in {"trigger", "neutral"}:
                raise ValueError(
                    f"指标 {metric_id} 的阈值 {threshold_index} 使用未知 role: "
                    f"{threshold_role}"
                )
            if threshold_role == "neutral":
                continue
            missing_threshold = [
                key for key in _REQUIRED_THRESHOLD_KEYS if key not in raw_threshold
            ]
            if missing_threshold:
                raise ValueError(
                    f"指标 {metric_id} 的阈值缺少字段: {', '.join(missing_threshold)}"
                )
            thresholds.append(
                {
                    "value": _number(
                        raw_threshold["value"],
                        f"metrics[{index}].thresholds[{threshold_index}].value",
                    ),
                    "direction": _text(
                        raw_threshold["direction"],
                        f"metrics[{index}].thresholds[{threshold_index}].direction",
                    ),
                    "label": _text(
                        raw_threshold["label"],
                        f"metrics[{index}].thresholds[{threshold_index}].label",
                    ),
                    "meaning": _text(
                        raw_threshold["meaning"],
                        f"metrics[{index}].thresholds[{threshold_index}].meaning",
                    ),
                }
            )

        result.append(
            {
                "id": metric_id,
                "name": _text(raw_metric["label"], f"metrics[{index}].label"),
                "meaning": _text(raw_metric["description"], f"metrics[{index}].description"),
                "category": category,
                "role": role,
                "current_value": _number(
                    raw_metric["current_value"], f"metrics[{index}].current_value"
                ),
                "thresholds": thresholds,
            }
        )
    return result


def build_ai_input(snapshot: str | Path | Mapping[str, Any]) -> dict[str, object]:
    """Return only the fields allowed at the AI input boundary.

    The function deliberately selects fields from the snapshot instead of
    copying it. That keeps chart series, dates, source metadata, and any future
    external context out of the provider request by construction.
    """

    loaded = _load_snapshot(snapshot)
    return {
        "market_stage_definitions": [
            {"stage": stage, "definition": STAGE_DEFINITIONS[stage]}
            for stage in ALLOWED_STAGES
        ],
        "category_status_definitions": [
            {"status": status, "definition": CATEGORY_STATUS_DEFINITIONS[status]}
            for status in CATEGORY_STATUS_VALUES
        ],
        "consistency_definitions": [
            {"consistency": consistency, "definition": CONSISTENCY_DEFINITIONS[consistency]}
            for consistency in CONSISTENCY_VALUES
        ],
        "category_definitions": _category_definitions(loaded),
        "metrics": _metric_inputs(loaded),
    }


def build_evidence_input(
    snapshot: str | Path | Mapping[str, Any],
    *,
    evidence_brief: Mapping[str, Any] | None = None,
    analysis_date: str | None = None,
) -> dict[str, object]:
    """Build the v0.3.0 AI boundary from a deterministic evidence brief.

    The old ``build_ai_input`` function remains available for v0.2 fixtures and
    compatibility tests.  The live provider uses this function: it receives
    relationships, eligibility, and stage limits rather than a sixteen-item
    definition dump.  Metric states are retained only for traceability (value,
    date, trigger status, and reason); formulas, source metadata, chart history
    and price are intentionally absent.
    """

    loaded = _load_snapshot(snapshot)
    brief = dict(evidence_brief or compile_evidence(loaded, analysis_date=analysis_date))
    allowed = brief.get("allowed_stages")
    if not isinstance(allowed, list) or not allowed:
        raise ValueError("证据简报缺少 allowed_stages")

    metric_states = brief.get("metric_states")
    if not isinstance(metric_states, list):
        raise ValueError("证据简报缺少 metric_states")
    # Do not pass display-only/pending values as if they were evidence.  Their
    # status and reason stay in data_quality so the AI can explain limitations.
    eligible_states = [
        {
            "id": state.get("id"),
            "name": state.get("label"),
            "role": state.get("role"),
            "status": state.get("status"),
            "judgment_eligible": state.get("judgment_eligible"),
            "triggered": state.get("triggered"),
            "current_value": state.get("current_value"),
            "metric_date": state.get("metric_date"),
        }
        for state in metric_states
        if isinstance(state, Mapping) and state.get("judgment_eligible") is True
    ]
    excluded_states = [
        {
            "id": state.get("id"),
            "name": state.get("label"),
            "status": state.get("status"),
            "reason": state.get("reason"),
            "metric_date": state.get("metric_date"),
        }
        for state in metric_states
        if isinstance(state, Mapping) and state.get("judgment_eligible") is not True
    ]

    return {
        "input_version": "0.3.0",
        "analysis_date": brief.get("analysis_date"),
        "allowed_stages": [
            {"stage": stage, "definition": STAGE_DEFINITIONS[stage]}
            for stage in allowed
            if stage in STAGE_DEFINITIONS
        ],
        "core_dimensions": brief.get("core_dimensions", {}),
        "strong_auxiliary_themes": brief.get("strong_auxiliary_themes", []),
        "auxiliary_themes": brief.get("auxiliary_themes", []),
        "contrary_or_incomplete": brief.get("contrary_or_incomplete", []),
        "next_stage_conditions": brief.get("next_stage_conditions", []),
        "data_quality": {
            "stage_ready": brief.get("data_quality", {}).get("stage_ready"),
            "common_anchor_date": brief.get("data_quality", {}).get("common_anchor_date"),
            "critical_missing": brief.get("data_quality", {}).get("critical_missing", []),
            "excluded_metrics": excluded_states,
        },
        "metric_states": eligible_states,
    }


build_input = build_ai_input
