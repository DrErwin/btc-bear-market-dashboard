"""Structural and product-safety validation for v0.4 AI output."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .contract import (
    BOTTOMING_STATES,
    CATEGORY_IDS,
    CATEGORY_STATUS_VALUES,
    CONSISTENCY_VALUES,
    DETAIL_SECTION_IDS,
    PRESSURE_STATES,
)


class InvalidAnalysisError(ValueError):
    """Raised when an AI response cannot be published."""

    def __init__(self, errors: str | list[str]) -> None:
        self.errors = [errors] if isinstance(errors, str) else errors
        super().__init__("AI 分析契约校验失败: " + "；".join(self.errors))


_TOP_LEVEL_KEYS = {
    "analysis_date",
    "pressure_state",
    "bottoming_state",
    "consistency",
    "summary",
    "compact",
    "categories",
    "detailed",
    "state_changes",
}
_COMPACT_KEYS = {"pressure", "bottoming", "change"}
_DETAILED_KEYS = set(DETAIL_SECTION_IDS)
_CATEGORY_KEYS = {"id", "category", "status", "note"}
_CHANGE_KEYS = {"changed", "from", "to", "reason", "compared_date"}

FORBIDDEN_OUTPUT_TERMS = (
    "买入",
    "建议卖出",
    "应该卖出",
    "可以卖出",
    "买卖",
    "做多",
    "做空",
    "抄底",
    "入场",
    "入场价",
    "仓位",
    "持仓",
    "杠杆",
    "概率",
    "buy",
    "sell",
    "long",
    "short",
    "leverage",
    "probability",
    "confidence",
    "position size",
    "entry price",
)
INTERNAL_OUTPUT_TERMS = (
    "核心锚",
    "核心复核",
    "强辅助",
    "辅助票",
    "允许阶段",
    "阶段上限",
    "allowed_stages",
    "triggered",
    "evidence_use",
    "机器规定",
    "系统不允许",
    "独立投票",
    "投票数",
    "评分",
    "加权总分",
)

_ADVICE_RE = re.compile(
    r"买入|买卖|做多|做空|抄底|入场(?:价|价格)?|仓位|持仓|杠杆|概率|"
    r"(?:建议|应该|可以|适合|考虑|立即|现在|逢高|逢低|止损|止盈).{0,10}(?:卖出|买入|增持|减持)|"
    r"\b(?:buy|sell|long|short|leverage|probability|confidence|position(?:\s+size)?|entry\s+price)\b",
    re.IGNORECASE,
)
_INTERNAL_RE = re.compile("|".join(re.escape(term) for term in INTERNAL_OUTPUT_TERMS), re.IGNORECASE)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _scan_forbidden(value: object, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).casefold()
            if any(part in key_text for part in ("probability", "confidence", "position", "leverage", "entry_price", "allowed_stage", "stage")):
                errors.append(f"{path}.{key} 是禁止字段")
            _scan_forbidden(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden(child, f"{path}[{index}]", errors)
    elif isinstance(value, str):
        if (match := _ADVICE_RE.search(value)):
            errors.append(f"{path} 含有交易或预测建议措辞：{match.group(0)}")
        if (match := _INTERNAL_RE.search(value)):
            errors.append(f"{path} 含有后台规则术语：{match.group(0)}")


def _check_container_keys(payload: Mapping[str, Any], errors: list[str]) -> None:
    errors.extend(f"未知顶层字段: {key}" for key in sorted(set(payload) - _TOP_LEVEL_KEYS))
    compact = payload.get("compact")
    if isinstance(compact, Mapping):
        errors.extend(f"未知 compact 字段: {key}" for key in sorted(set(compact) - _COMPACT_KEYS))
    detailed = payload.get("detailed")
    if isinstance(detailed, Mapping):
        errors.extend(f"未知 detailed 字段: {key}" for key in sorted(set(detailed) - _DETAILED_KEYS))
    changes = payload.get("state_changes")
    if isinstance(changes, Mapping):
        for axis, change in changes.items():
            if axis not in {"pressure", "bottoming"} or not isinstance(change, Mapping):
                errors.append(f"state_changes.{axis} 结构无效")
            elif set(change) - _CHANGE_KEYS:
                errors.extend(f"state_changes.{axis} 含未知字段: {key}" for key in sorted(set(change) - _CHANGE_KEYS))
    categories = payload.get("categories")
    if isinstance(categories, list):
        for index, item in enumerate(categories):
            if isinstance(item, Mapping):
                errors.extend(f"categories[{index}] 含未知字段: {key}" for key in sorted(set(item) - _CATEGORY_KEYS))


def _validate_categories(value: object, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) != len(CATEGORY_IDS):
        errors.append("categories 必须恰好包含六类")
        return
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            errors.append(f"categories[{index}] 必须是对象")
            continue
        category = item.get("id", item.get("category"))
        status = item.get("status")
        if category not in CATEGORY_IDS:
            errors.append(f"categories[{index}] 使用未知类别: {category}")
        elif category in seen:
            errors.append(f"categories 出现重复类别: {category}")
        else:
            seen.add(str(category))
        if status not in CATEGORY_STATUS_VALUES:
            errors.append(f"categories[{index}] 使用未知状态: {status}")
        if "note" in item and not _text(item.get("note")):
            errors.append(f"categories[{index}].note 必须是非空文本")
    if seen != set(CATEGORY_IDS):
        errors.append("categories 未覆盖全部六个固定类别")


def validate_analysis(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a v0.4 analysis."""

    errors: list[str] = []
    if not isinstance(payload, Mapping):
        raise InvalidAnalysisError("AI 输出必须是 JSON 对象")
    _scan_forbidden(payload, "$", errors)
    _check_container_keys(payload, errors)
    for field in (
        "analysis_date",
        "summary",
        "pressure_state",
        "bottoming_state",
        "compact",
        "detailed",
        "categories",
        "state_changes",
    ):
        if field not in payload:
            errors.append(f"缺少必填字段: {field}")
    if payload.get("pressure_state") not in PRESSURE_STATES:
        errors.append(f"未知 pressure_state: {payload.get('pressure_state')}")
    if payload.get("bottoming_state") not in BOTTOMING_STATES:
        errors.append(f"未知 bottoming_state: {payload.get('bottoming_state')}")
    pressure_insufficient = payload.get("pressure_state") == "数据不足"
    bottoming_insufficient = payload.get("bottoming_state") == "数据不足"
    consistency = payload.get("consistency")
    if pressure_insufficient and bottoming_insufficient:
        if consistency is not None:
            errors.append("两条轴都数据不足时 consistency 必须为空")
    elif consistency not in CONSISTENCY_VALUES:
        errors.append(f"未知或缺少 consistency: {consistency}")
    if not _text(payload.get("analysis_date")):
        errors.append("analysis_date 必须是非空文本")
    if not _text(payload.get("summary")):
        errors.append("summary 必须是非空文本")

    compact = payload.get("compact")
    if not isinstance(compact, Mapping):
        errors.append("compact 必须是对象")
    else:
        for key in _COMPACT_KEYS:
            item = compact.get(key)
            if not isinstance(item, Mapping) or not _text(item.get("title")) or not _text(item.get("text")):
                errors.append(f"compact.{key} 必须包含 title 与 text")

    detailed = payload.get("detailed")
    if not isinstance(detailed, Mapping):
        errors.append("detailed 必须是对象")
    else:
        for section in DETAIL_SECTION_IDS:
            if not _text(detailed.get(section)):
                errors.append(f"detailed 缺少必填部分: {section}")
    _validate_categories(payload.get("categories"), errors)

    changes = payload.get("state_changes")
    if not isinstance(changes, Mapping):
        errors.append("state_changes 必须是对象")
    else:
        for axis in ("pressure", "bottoming"):
            change = changes.get(axis)
            if not isinstance(change, Mapping):
                errors.append(f"state_changes.{axis} 必须是对象")
            elif not isinstance(change.get("changed"), bool) or not _text(change.get("reason")):
                errors.append(f"state_changes.{axis} 必须包含 changed 与 reason")

    if errors:
        raise InvalidAnalysisError(errors)
    return dict(payload)


validate = validate_analysis


__all__ = ["InvalidAnalysisError", "validate_analysis", "validate", "FORBIDDEN_OUTPUT_TERMS", "INTERNAL_OUTPUT_TERMS"]
