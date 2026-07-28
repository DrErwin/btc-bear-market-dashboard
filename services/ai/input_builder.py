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
from services.evidence.catalog import canonical_id_for_snapshot_id
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

_IMPORTANCE_BY_ROLE = {
    "core_anchor": "核心锚，决定所属判断维度和阶段范围；不能单独证明最低点。",
    "core_confirmation": "核心复核，用于复核估值压力；不能单独改变市场阶段。",
    "strong_auxiliary": "强辅助，用于说明当前阶段内部的压力强度；不能单独改变市场阶段。",
    "auxiliary": "辅助，用于补充相关市场现象；不能单独改变市场阶段。",
}

_EVIDENCE_USE_BY_CANONICAL_ID = {
    "mvrv": "用于判断全市场估值压力；不能单独证明最低点。",
    "aviv": "用于复核 MVRV 的估值判断；不能作为第二个独立估值信号。",
    "sth_mvrv_price": "用于观察短期持有者成本位置和市场承接；只补充当前阶段。",
    "psip": "用于观察盈利供应是否明显收缩；与 SIPL 属于同一组供应盈亏现象。",
    "sipl": "用于补充供应盈亏结构；与 PSIP 属于同一组现象，不能重复计算。",
    "relative_unrealized_profit": "用于说明市场利润空间是否收窄；不能单独说明全面投降。",
    "relative_unrealized_loss_zscore_4y": "用于说明未实现亏损在周期中的严重程度；只增强压力解释。",
    "realized_cap_relative_npc_30d": "用于观察链上资本是扩张还是收缩；不能单独决定市场阶段。",
    "asopr": "用于说明链上是否出现亏损卖出压力；不能单独决定市场阶段。",
    "hodler_npc_30d": "用于说明长期持有者供应变化；当前旧数据不能代表今天。",
    "spent_value_ge155d_share": "用于说明老币花费活动；当前旧数据不能代表今天。",
    "seller_exhaustion": "用于说明卖方力量是否接近耗竭；不能单独决定市场阶段。",
    "puell_multiple": "用于判断矿工收入压力；不能单独证明最低点。",
    "thermocap_multiple_zscore": "用于补充矿工成本和长期成本背景；不能单独决定市场阶段。",
    "cvdd_proximity": "用于补充价格与长期成本基础的距离；当前规则仍在验证。",
    "reserve_risk_zscore": "用于说明长期持有信念的周期背景；不能单独决定市场阶段。",
}

_STATUS_TEXT = {
    "current": "当前可用，可参与判断",
    "display_only": "仅供展示，不参与判断",
    "validation_pending": "待验证，不参与判断",
    "missing": "缺失，不参与判断",
}


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


def _threshold_triggered(
    value: object,
    direction: object,
    target: object,
) -> bool:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or isinstance(target, bool)
        or not isinstance(target, (int, float))
    ):
        return False
    if direction == "below":
        return value < target
    if direction == "above":
        return value > target
    return False


def _threshold_rule(direction: object, target: object) -> str:
    symbol = {"below": "<", "above": ">"}.get(direction)
    if symbol is None or isinstance(target, bool) or not isinstance(target, (int, float)):
        raise ValueError("判断阈值必须包含有效 direction 和 value")
    return f"{symbol} {target}"


def _threshold_summary(
    *,
    status: str,
    reason: object,
    thresholds: list[dict[str, object]],
) -> str:
    if status == "display_only":
        if isinstance(reason, str) and "过期" in reason:
            return "数据已过期，本次不进行阈值判断，旧值不作为当前证据。"
        return "该指标仅供展示，本次不进行阈值判断。"
    if status == "validation_pending":
        return "判断规则仍在验证，本次不进行阈值判断。"
    if status == "missing":
        return "数据缺失，本次不进行阈值判断。"

    triggered = [
        threshold for threshold in thresholds if threshold.get("triggered") is True
    ]
    if not triggered:
        return "当前未触发任何判断阈值。"
    highest = triggered[-1]
    meaning = str(highest["meaning"]).rstrip("。")
    return f"当前已触发{highest['name']}，{meaning}。"


def _metric_evidence_inputs(
    snapshot: Mapping[str, Any],
    brief: Mapping[str, Any],
) -> list[dict[str, object]]:
    raw_metrics = snapshot.get("metrics")
    metric_states = brief.get("metric_states")
    if not isinstance(raw_metrics, list) or not isinstance(metric_states, list):
        raise ValueError("证据简报缺少完整指标状态")

    state_by_id = {
        state.get("id"): state
        for state in metric_states
        if isinstance(state, Mapping) and isinstance(state.get("id"), str)
    }
    result: list[dict[str, object]] = []
    for index, raw_metric in enumerate(raw_metrics):
        if not isinstance(raw_metric, Mapping):
            raise ValueError(f"snapshot.metrics[{index}] 必须是对象")
        metric_id = _text(raw_metric.get("id"), f"metrics[{index}].id")
        state = state_by_id.get(metric_id)
        if not isinstance(state, Mapping):
            raise ValueError(f"证据简报缺少指标状态: {metric_id}")

        role = str(state.get("role"))
        status = str(state.get("status"))
        if role not in _IMPORTANCE_BY_ROLE:
            raise ValueError(f"指标 {metric_id} 使用未知证据角色: {role}")
        if status not in _STATUS_TEXT:
            raise ValueError(f"指标 {metric_id} 使用未知数据状态: {status}")

        current_value = (
            None if status == "missing" else state.get("current_value")
        )
        threshold_inputs: list[dict[str, object]] = []
        raw_thresholds = raw_metric.get("thresholds")
        if not isinstance(raw_thresholds, list):
            raise ValueError(f"指标 {metric_id} 的 thresholds 必须是列表")
        for threshold_index, raw_threshold in enumerate(raw_thresholds):
            if not isinstance(raw_threshold, Mapping):
                raise ValueError(
                    f"指标 {metric_id} 的阈值 {threshold_index} 必须是对象"
                )
            if raw_threshold.get("role", "trigger") == "neutral":
                continue
            direction = raw_threshold.get("direction")
            target = raw_threshold.get("value")
            threshold_inputs.append(
                {
                    "rule": _threshold_rule(direction, target),
                    "name": _text(
                        raw_threshold.get("label"),
                        f"metrics[{index}].thresholds[{threshold_index}].label",
                    ),
                    "meaning": _text(
                        raw_threshold.get("meaning"),
                        f"metrics[{index}].thresholds[{threshold_index}].meaning",
                    ),
                    "triggered": (
                        _threshold_triggered(current_value, direction, target)
                        if status == "current"
                        else None
                    ),
                }
            )

        canonical_id = canonical_id_for_snapshot_id(metric_id)
        result.append(
            {
                "id": metric_id,
                "name": _text(raw_metric.get("label"), f"metrics[{index}].label"),
                "importance": _IMPORTANCE_BY_ROLE[role],
                "value": current_value,
                "date": state.get("metric_date"),
                "status": _STATUS_TEXT[status],
                "thresholds": threshold_inputs,
                "threshold_summary": _threshold_summary(
                    status=status,
                    reason=state.get("reason"),
                    thresholds=threshold_inputs,
                ),
                "evidence_use": _EVIDENCE_USE_BY_CANONICAL_ID[canonical_id],
            }
        )
    return result


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
    evidence relationships plus one compact evidence-use record for each
    indicator.  Current indicators carry machine-evaluated threshold results;
    display-only, pending, and missing indicators carry ``None`` results so the
    model can explain data limits without treating them as current evidence.
    Formulas, source metadata, chart history, and price are intentionally absent.
    """

    loaded = _load_snapshot(snapshot)
    brief = dict(evidence_brief or compile_evidence(loaded, analysis_date=analysis_date))
    allowed = brief.get("allowed_stages")
    if not isinstance(allowed, list) or not allowed:
        raise ValueError("证据简报缺少 allowed_stages")

    metric_states = brief.get("metric_states")
    if not isinstance(metric_states, list):
        raise ValueError("证据简报缺少 metric_states")
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
        "metric_states": _metric_evidence_inputs(loaded, brief),
    }


build_input = build_ai_input
