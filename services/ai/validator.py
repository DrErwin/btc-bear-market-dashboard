"""Offline validation for the structured AI analysis response."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .contract import (
    ALLOWED_STAGES,
    CATEGORY_IDS,
    CATEGORY_STATUS_VALUES,
    CONSISTENCY_VALUES,
    DATA_INSUFFICIENT_STAGE,
)


class InvalidAnalysisError(ValueError):
    """Raised when an AI response cannot be published."""

    def __init__(self, errors: str | list[str]) -> None:
        self.errors = [errors] if isinstance(errors, str) else errors
        super().__init__("AI 分析契约校验失败: " + "；".join(self.errors))


_RAW_TOP_LEVEL_KEYS = {
    "analysis_date",
    "stage",
    "consistency",
    "summary",
    "core_support",
    "main_obstacle",
    "next_stage_condition",
    "categories",
    "supporting_evidence",
    "contrary_evidence",
    "next_stage_confirmation",
    "pressure_summary",
    "supporting",
    "contrary",
    "next_stage",
    "compact",
    "detailed",
}
_COMPACT_KEYS = {"support", "obstacle", "next"}
_DETAILED_KEYS = {
    "supporting",
    "contrary",
    "next_stage",
    "supporting_evidence",
    "contrary_evidence",
    "next_stage_confirmation",
    "pressure",
}
_CATEGORY_KEYS = {"id", "category", "status", "note"}

_FORBIDDEN_KEY_PARTS = (
    "buy",
    "sell",
    "entry_price",
    "entryprice",
    "position",
    "leverage",
    "probability",
    "confidence_pct",
    "probability_pct",
    "bottom_probability",
    "买",
    "卖",
    "入场",
    "仓位",
    "杠杆",
    "概率",
)
FORBIDDEN_OUTPUT_TERMS = (
    "买入",
    "卖出",
    "买卖",
    "做多",
    "做空",
    "抄底",
    "入场",
    "入场价",
    "入场价格",
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
    "confidence_pct",
    "position",
    "position size",
    "entry price",
)
_FORBIDDEN_TEXT_RE = re.compile(
    r"买入|卖出|买卖|做多|做空|抄底|入场(?:价|价格)?|仓位|持仓|杠杆|概率|"
    r"\b(?:buy|sell|long|short|leverage|probability|confidence_pct|position(?:\s+size)?|entry\s+price)\b",
    re.IGNORECASE,
)
_NUMERIC_PROBABILITY_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s*%?\s*(?:的\s*)?(?:概率|probability|confidence)|"
    r"(?:概率|probability|confidence)\s*(?:为|是|约为|:|：|=)?\s*\d+(?:\.\d+)?\s*%?)",
    re.IGNORECASE,
)


def _scan_forbidden(value: object, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).casefold()
            if any(part in key_text for part in _FORBIDDEN_KEY_PARTS):
                errors.append(f"{path}.{key} 是禁止字段")
            _scan_forbidden(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden(child, f"{path}[{index}]", errors)
    elif isinstance(value, str):
        matches = [
            match.group(0)
            for pattern in (_FORBIDDEN_TEXT_RE, _NUMERIC_PROBABILITY_RE)
            if (match := pattern.search(value))
        ]
        if matches:
            terms = "、".join(dict.fromkeys(matches))
            errors.append(f"{path} 含有禁止措辞：{terms}")


def _check_container_keys(payload: Mapping[str, Any], errors: list[str]) -> None:
    unknown_top = set(payload) - _RAW_TOP_LEVEL_KEYS
    errors.extend(f"未知顶层字段: {key}" for key in sorted(unknown_top))

    compact = payload.get("compact")
    if compact is not None and isinstance(compact, Mapping):
        errors.extend(
            f"未知 compact 字段: {key}"
            for key in sorted(set(compact) - _COMPACT_KEYS)
        )
    detailed = payload.get("detailed")
    if detailed is not None and isinstance(detailed, Mapping):
        errors.extend(
            f"未知 detailed 字段: {key}"
            for key in sorted(set(detailed) - _DETAILED_KEYS)
        )
    categories = payload.get("categories")
    if isinstance(categories, list):
        for index, category in enumerate(categories):
            if isinstance(category, Mapping):
                errors.extend(
                    f"categories[{index}] 含未知字段: {key}"
                    for key in sorted(set(category) - _CATEGORY_KEYS)
                )


def _text_value(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        text = value.get("text")
        return isinstance(text, str) and bool(text.strip())
    return False


def _normalise_analysis(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map the checked dashboard fixture shape to the strict output shape."""

    normalized: dict[str, Any] = {}
    for key in (
        "analysis_date",
        "stage",
        "consistency",
        "summary",
        "core_support",
        "main_obstacle",
        "next_stage_condition",
        "supporting_evidence",
        "contrary_evidence",
        "next_stage_confirmation",
        "pressure_summary",
    ):
        if key in payload:
            normalized[key] = payload[key]

    compact = payload.get("compact")
    if isinstance(compact, Mapping):
        for target, source in (
            ("core_support", "support"),
            ("main_obstacle", "obstacle"),
            ("next_stage_condition", "next"),
        ):
            if target not in normalized and source in compact:
                normalized[target] = compact[source]

    detailed = payload.get("detailed")
    if isinstance(detailed, Mapping):
        for target, source in (
            ("supporting_evidence", ("supporting_evidence", "supporting")),
            ("contrary_evidence", ("contrary_evidence", "contrary")),
            (
                "next_stage_confirmation",
                ("next_stage_confirmation", "next_stage"),
            ),
        ):
            if target not in normalized:
                for candidate in source:
                    if candidate in detailed:
                        normalized[target] = detailed[candidate]
                        break
        if "pressure_summary" not in normalized:
            for candidate in ("pressure_summary", "pressure"):
                if candidate in detailed:
                    normalized["pressure_summary"] = detailed[candidate]
                    break

    for target, aliases in (
        ("supporting_evidence", ("supporting",)),
        ("contrary_evidence", ("contrary",)),
        ("next_stage_confirmation", ("next_stage",)),
    ):
        if target not in normalized:
            for alias in aliases:
                if alias in payload:
                    normalized[target] = payload[alias]
                    break

    raw_categories = payload.get("categories")
    if isinstance(raw_categories, list):
        normalized_categories: list[Any] = []
        for item in raw_categories:
            if isinstance(item, Mapping):
                normalized_categories.append(
                    {
                        "category": item.get("category", item.get("id")),
                        "status": item.get("status"),
                    }
                )
            else:
                normalized_categories.append(item)
        normalized["categories"] = normalized_categories
    elif "categories" in payload:
        normalized["categories"] = raw_categories

    return normalized


def _validate_categories(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("categories 必须是六类列表")
        return
    if len(value) != len(CATEGORY_IDS):
        errors.append("categories 必须恰好包含六类")

    seen: list[object] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            errors.append(f"categories[{index}] 必须是对象")
            continue
        category = item.get("category")
        status = item.get("status")
        if category not in CATEGORY_IDS:
            errors.append(f"categories[{index}] 使用未知类别: {category}")
        elif category in seen:
            errors.append(f"categories 出现重复类别: {category}")
        else:
            seen.append(category)
        if status not in CATEGORY_STATUS_VALUES:
            errors.append(f"categories[{index}] 使用未知状态: {status}")

    if set(seen) != set(CATEGORY_IDS):
        errors.append("categories 未覆盖全部六个固定类别")


def validate_analysis(
    payload: Mapping[str, Any],
    *,
    allowed_stages: list[str] | tuple[str, ...] | None = None,
    require_pressure_summary: bool = False,
) -> dict[str, Any]:
    """Validate and return a canonical analysis, or raise ``InvalidAnalysisError``."""

    errors: list[str] = []
    if not isinstance(payload, Mapping):
        raise InvalidAnalysisError("AI 输出必须是 JSON 对象")

    _scan_forbidden(payload, "$", errors)
    _check_container_keys(payload, errors)
    normalized = _normalise_analysis(payload)

    required = (
        "stage",
        "summary",
        "core_support",
        "main_obstacle",
        "next_stage_condition",
        "categories",
        "supporting_evidence",
        "contrary_evidence",
        "next_stage_confirmation",
    )
    for field in required:
        if field not in normalized:
            errors.append(f"缺少必填字段: {field}")

    stage = normalized.get("stage")
    if stage not in ALLOWED_STAGES:
        errors.append(f"未知 stage: {stage}")
    if allowed_stages is not None and stage not in allowed_stages:
        errors.append(f"stage 超出机器允许范围: {stage}；允许范围={list(allowed_stages)}")

    consistency = normalized.get("consistency")
    if stage != DATA_INSUFFICIENT_STAGE and "consistency" not in normalized:
        errors.append("缺少必填字段: consistency")
    elif consistency is not None and consistency not in CONSISTENCY_VALUES:
        errors.append(f"未知 consistency: {consistency}")

    if "summary" in normalized and not _text_value(normalized["summary"]):
        errors.append("summary 必须是非空文本")
    for field in (
        "core_support",
        "main_obstacle",
        "next_stage_condition",
    ):
        if field in normalized and not _text_value(normalized[field]):
            errors.append(f"{field} 必须是非空文本或含 text 的摘要对象")
    for field in (
        "supporting_evidence",
        "contrary_evidence",
        "next_stage_confirmation",
    ):
        if field in normalized and not _text_value(normalized[field]):
            errors.append(f"{field} 必须是非空文本")
    if require_pressure_summary and not _text_value(normalized.get("pressure_summary")):
        errors.append("存在强辅助证据时必须填写 pressure_summary")

    if "categories" in normalized:
        _validate_categories(normalized["categories"], errors)

    if errors:
        raise InvalidAnalysisError(errors)
    return normalized


validate = validate_analysis
