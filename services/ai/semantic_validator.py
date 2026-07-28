"""Validate that AI prose uses the supplied threshold evidence consistently."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from .validator import InvalidAnalysisError


def _triggered(metric: Mapping[str, Any]) -> bool:
    value = metric.get("current_value")
    if not isinstance(value, (int, float)):
        return False
    for threshold in metric.get("thresholds", []):
        threshold_value = threshold.get("value")
        direction = threshold.get("direction")
        if not isinstance(threshold_value, (int, float)):
            continue
        if direction == "below" and value < threshold_value:
            return True
        if direction == "above" and value > threshold_value:
            return True
    return False


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        text = value.get("text")
        return text if isinstance(text, str) else ""
    return ""


def _support_texts(analysis: Mapping[str, Any]) -> list[str]:
    texts = [
        _as_text(analysis.get("core_support")),
        _as_text(analysis.get("supporting_evidence")),
        _as_text(analysis.get("supporting")),
    ]
    compact = analysis.get("compact")
    if isinstance(compact, Mapping):
        texts.append(_as_text(compact.get("support")))
    detailed = analysis.get("detailed")
    if isinstance(detailed, Mapping):
        texts.extend(
            (
                _as_text(detailed.get("supporting")),
                _as_text(detailed.get("supporting_evidence")),
            )
        )
    return [text for text in texts if text]


def _all_text(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from _all_text(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_text(child)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    parts = [
        re.escape(part)
        for part in re.split(r"[\s._/·\-]+", alias.casefold())
        if part
    ]
    body = r"[\s._/·\-]*".join(parts)
    return re.compile(
        rf"(?<![a-z0-9]){body}(?![a-z0-9])",
        re.IGNORECASE,
    )


def _metric_patterns(metric: Mapping[str, Any]) -> list[re.Pattern[str]]:
    aliases = {
        str(metric.get("id", "")).strip(),
        str(metric.get("name", "")).strip(),
    }
    return [_alias_pattern(alias) for alias in aliases if alias]


def validate_analysis_semantics(
    analysis: Mapping[str, Any],
    ai_input: Mapping[str, Any],
) -> None:
    """Reject prose that contradicts trigger state or fixed metric meaning."""

    metrics = ai_input.get("metrics")
    if not isinstance(metrics, list):
        raise InvalidAnalysisError("AI 语义校验缺少 metrics 输入")

    errors: list[str] = []
    support = "\n".join(_support_texts(analysis)).casefold()
    triggered_by_category: dict[str, bool] = {}

    for metric in metrics:
        if not isinstance(metric, Mapping):
            continue
        category = str(metric.get("category", ""))
        is_triggered = _triggered(metric)
        triggered_by_category[category] = (
            triggered_by_category.get(category, False) or is_triggered
        )
        if is_triggered:
            continue
        if any(pattern.search(support) for pattern in _metric_patterns(metric)):
            errors.append(
                f"支持证据引用了未触发指标 {metric.get('id')}"
            )

    categories = analysis.get("categories")
    if isinstance(categories, list):
        for item in categories:
            if not isinstance(item, Mapping):
                continue
            category = str(item.get("category", item.get("id", "")))
            status = item.get("status")
            has_trigger = triggered_by_category.get(category, False)
            if not has_trigger and status != "未确认":
                errors.append(
                    f"{category} 没有触发指标，状态必须为未确认"
                )
            if has_trigger and status == "未确认":
                errors.append(
                    f"{category} 已有触发指标，状态不能为未确认"
                )

    combined = "\n".join(_all_text(analysis))
    if re.search(r"(?:长期)?持有信念.{0,12}(?:周期)?低位", combined):
        errors.append(
            "Reserve Risk 含义写反：长期持有信念应为周期高位"
        )
    if "积累/链上花费分界" in combined:
        errors.append(
            "HODLer 零线不得改名为积累/链上花费分界，"
            "请使用长期供应净变化零线"
        )

    if errors:
        raise InvalidAnalysisError(errors)
