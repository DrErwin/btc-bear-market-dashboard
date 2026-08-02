"""Factual semantic checks for the v0.4 dual-axis analysis."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .validator import InvalidAnalysisError


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return str(value.get("text") or "")
    return ""


def _alias_pattern(alias: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in re.split(r"[\s._/·\-]+", alias.casefold()) if part]
    separator = r"[\s._/·\-]*"
    return re.compile(rf"(?<![a-z0-9]){separator.join(parts)}(?![a-z0-9])", re.IGNORECASE)


def _support_text(analysis: Mapping[str, Any]) -> str:
    chunks = [_text(analysis.get("summary"))]
    compact = analysis.get("compact")
    if isinstance(compact, Mapping):
        for key in ("pressure", "bottoming", "change"):
            chunks.append(_text(compact.get(key)))
    detailed = analysis.get("detailed")
    if isinstance(detailed, Mapping):
        for key in ("pressure_reason", "bottoming_reason", "evidence_timeline", "repair_exit"):
            chunks.append(_text(detailed.get(key)))
    return "\n".join(chunk for chunk in chunks if chunk)


def _input_metrics(ai_input: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = ai_input.get("metric_states")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise InvalidAnalysisError("AI 语义校验缺少 metric_states 输入")
    return [item for item in raw if isinstance(item, Mapping)]


def _triggered(metric: Mapping[str, Any]) -> bool:
    tier = metric.get("tier")
    if isinstance(tier, Mapping) and tier.get("id") not in {None, "none"}:
        return bool(metric.get("judgment_eligible"))
    return bool(metric.get("triggered"))


def _check_threshold_labels(name: str, text: str, metric: Mapping[str, Any], errors: list[str]) -> None:
    # Direction-word scanning is paused because whole-text matching cannot
    # distinguish a factual claim from a negated phrase such as "并未高于".
    for threshold in metric.get("thresholds", []):
        if not isinstance(threshold, Mapping):
            continue
        label = str(threshold.get("label") or "")
        if label and label in text and threshold.get("triggered") is not True:
            errors.append(f"支持文字引用了未触发档位 {name}/{label}")


def _check_dates(text: str, ai_input: Mapping[str, Any], errors: list[str]) -> None:
    mentioned = set(re.findall(r"20\d{2}-\d{2}-\d{2}", text))
    if not mentioned:
        return
    allowed: set[str] = {str(ai_input.get("analysis_date"))}
    for metric in _input_metrics(ai_input):
        if metric.get("date"):
            allowed.add(str(metric.get("date")))
    timeline = ai_input.get("timeline")
    if isinstance(timeline, Mapping):
        for item in timeline.get("metrics", []):
            if not isinstance(item, Mapping):
                continue
            if item.get("data_date"):
                allowed.add(str(item.get("data_date")))
            for event in item.get("events", []):
                if isinstance(event, Mapping) and event.get("date"):
                    allowed.add(str(event.get("date")))
    context = ai_input.get("previous_three_days")
    if isinstance(context, Sequence):
        for item in context:
            if isinstance(item, Mapping) and item.get("date"):
                allowed.add(str(item.get("date")))
    for value in sorted(mentioned - allowed):
        errors.append(f"文字包含输入事实不存在的日期: {value}")


def _check_state_changes(analysis: Mapping[str, Any], ai_input: Mapping[str, Any], errors: list[str]) -> None:
    changes = analysis.get("state_changes")
    if not isinstance(changes, Mapping):
        return
    context = ai_input.get("previous_three_days")
    prior_by_axis: dict[str, Mapping[str, Any] | None] = {}
    if isinstance(context, Sequence):
        items = list(context)
        for axis in ("pressure", "bottoming"):
            key = f"{axis}_state"
            prior_by_axis[axis] = next(
                (
                    item
                    for item in reversed(items)
                    if isinstance(item, Mapping)
                    and item.get("status") in {"current", "fallback"}
                    and item.get(key)
                ),
                None,
            )
    for axis in ("pressure", "bottoming"):
        change = changes.get(axis)
        if not isinstance(change, Mapping):
            continue
        current = analysis.get(f"{axis}_state")
        prior = prior_by_axis.get(axis)
        previous = prior.get(f"{axis}_state") if prior else None
        expected_changed = bool(previous and current and previous != current)
        if bool(change.get("changed")) != expected_changed:
            errors.append(f"state_changes.{axis} 与前三天最近可用状态不一致")
        if change.get("to") not in {None, current}:
            errors.append(f"state_changes.{axis}.to 与当前状态不一致")


def _check_axis_readiness(analysis: Mapping[str, Any], ai_input: Mapping[str, Any], errors: list[str]) -> None:
    readiness = ai_input.get("axis_readiness")
    if not isinstance(readiness, Mapping):
        return
    for axis in ("pressure", "bottoming"):
        item = readiness.get(axis)
        if isinstance(item, Mapping) and item.get("ready") is False and analysis.get(f"{axis}_state") != "数据不足":
            errors.append(f"{axis} 轴数据未就绪时必须选择数据不足")


def validate_analysis_semantics(analysis: Mapping[str, Any], ai_input: Mapping[str, Any]) -> None:
    metrics = _input_metrics(ai_input)
    support = _support_text(analysis)
    errors: list[str] = []
    family_mentions: dict[str, list[str]] = {}
    for metric in metrics:
        name = str(metric.get("name") or metric.get("id") or "")
        aliases = [str(metric.get("id") or ""), name]
        mentioned = any(_alias_pattern(alias).search(support) for alias in aliases if alias)
        if mentioned:
            family = str(metric.get("correlation_family") or "")
            family_mentions.setdefault(family, []).append(name)
            if not metric.get("judgment_eligible") or metric.get("status") != "current":
                start = max(0, next((match.start() for alias in aliases if alias and (match := _alias_pattern(alias).search(support))), 0) - 35)
                context = support[start:start + 90]
                if not re.search(r"缺少|不可用|过期|不参与|不能|数据不足|缺口", context):
                    errors.append(f"支持文字引用了不可用或过期指标 {name}")
            elif not _triggered(metric):
                errors.append(f"支持文字引用了未触发指标 {name}")
            _check_threshold_labels(name, support, metric, errors)
    for family, names in family_mentions.items():
        if family and len(names) > 1 and re.search(r"独立|分别证明|多个独立|各自证明|票", support):
            errors.append(f"相关性家族 {family} 被文字当成多个独立证据")

    _check_dates(support, ai_input, errors)
    _check_state_changes(analysis, ai_input, errors)
    _check_axis_readiness(analysis, ai_input, errors)
    if analysis.get("pressure_state") != "数据不足" and analysis.get("bottoming_state") != "数据不足":
        if len(re.findall(r"估值|成本|矿工|供应|亏损|投降|卖方|耗竭|承接|修复|持有者|资本", support)) < 2:
            errors.append("双轴解释必须综合至少两个证据维度")
    if len([metric for metric in metrics if any(_alias_pattern(str(metric.get(key) or "")).search(support) for key in ("id", "name") if metric.get(key))]) > 6:
        errors.append("首屏与详细解释不应逐项复述过多指标")
    if re.search(r"新闻|宏观|美联储|ETF|外部消息|政策声明", support, re.IGNORECASE):
        errors.append("解释只能使用输入证据，不得引入外部信息")
    if errors:
        raise InvalidAnalysisError(errors)


__all__ = ["validate_analysis_semantics"]
