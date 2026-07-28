"""Validate that AI prose uses the supplied threshold evidence consistently."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .validator import InvalidAnalysisError


def _triggered(metric: Mapping[str, Any]) -> bool:
    if isinstance(metric.get("triggered"), bool):
        return metric["triggered"]
    threshold_results = [
        threshold.get("triggered")
        for threshold in metric.get("thresholds", [])
        if isinstance(threshold, Mapping)
        and isinstance(threshold.get("triggered"), bool)
    ]
    if threshold_results:
        return any(threshold_results)
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


def _input_metrics(ai_input: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], bool]:
    """Return metric states and whether the input is the v0.3 evidence boundary."""

    raw = ai_input.get("metric_states")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, Mapping)], True
    raw = ai_input.get("metrics")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, Mapping)], False
    return [], False


def validate_analysis_semantics(
    analysis: Mapping[str, Any],
    ai_input: Mapping[str, Any],
) -> None:
    """Reject prose that contradicts trigger state or fixed metric meaning."""

    metrics, is_evidence_input = _input_metrics(ai_input)
    if not metrics:
        raise InvalidAnalysisError("AI 语义校验缺少 metrics 输入")

    errors: list[str] = []
    support = "\n".join(_support_texts(analysis)).casefold()
    triggered_by_category: dict[str, bool] = {}

    for metric in metrics:
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
            if is_evidence_input and category not in triggered_by_category:
                # v0.3 categories remain a display summary; the two core
                # dimensions are guarded separately by allowed_stages.
                continue
            has_trigger = triggered_by_category.get(category, False)
            if not has_trigger and status != "未确认":
                errors.append(
                    f"{category} 没有触发指标，状态必须为未确认"
                )
            if has_trigger and status == "未确认":
                errors.append(
                    f"{category} 已有触发指标，状态不能为未确认"
                )

    strong_themes = ai_input.get("strong_auxiliary_themes")
    if isinstance(strong_themes, list) and strong_themes:
        pressure = _as_text(analysis.get("pressure_summary"))
        if not pressure:
            errors.append("存在强辅助证据时必须说明阶段内部压力")

    if is_evidence_input and analysis.get("stage") != "数据不足":
        summary = _as_text(analysis.get("summary"))
        compact = analysis.get("compact")
        if isinstance(compact, Mapping):
            summary += " " + _as_text(compact.get("support"))
        summary += " " + _as_text(analysis.get("pressure_summary"))
        signal_terms = (
            r"估值|成本|矿工|收入压力|供应|亏损|投降|卖方|耗竭|恢复|承接|持有者|资本"
        )
        if len(re.findall(signal_terms, summary)) < 2:
            errors.append("首屏解释必须综合至少两个证据维度")

        visible_metric_names = 0
        for metric in metrics:
            if any(pattern.search(summary) for pattern in _metric_patterns(metric)):
                visible_metric_names += 1
        if visible_metric_names > 4:
            errors.append("首屏解释最多提及四个代表性指标")
        if re.search(r"(?:\$|\d+\.\d+\s*%?|\b\d+\.\d+\b|Market\s*Cap\s*/|Realized\s*Cap\s*/|公式=)", summary, re.IGNORECASE):
            errors.append("首屏解释不应复述公式或卡片数值")
        if re.search(r"新闻|宏观|美联储|ETF|外部消息|政策声明", summary, re.IGNORECASE):
            errors.append("解释只能使用证据简报，不得引入外部信息")

    if errors:
        raise InvalidAnalysisError(errors)
