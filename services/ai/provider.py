"""AI provider and deterministic v0.4 mock judgement."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import semantic_validator, validator
from .contract import BOTTOMING_STATES, CATEGORY_IDS, CATEGORY_STATUS_VALUES, PRESSURE_STATES
from .input_builder import build_evidence_input
from services.evidence.compiler import compile_evidence
from services.evidence.context import state_change_facts


DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-5.2"

_SYSTEM_PROMPT = (
    "你是 BTC 周期证据看板的日度分析器。你会收到固定的压力轴和筑底过程轴词汇，以及当前事实、阈值方向、数据质量、相关证据家族、有限时间线和前三个自然日上下文。"
    "请分别选择压力状态和筑底状态，不能合并成一个总阶段，也不能计算分数或多数票。"
    "请用普通读者能理解的市场语言解释支持、反面、缺失、修复和下一步观察重点。"
    "只能使用输入事实，不预测价格，不给出交易动作，不输出概率或后台规则术语。只返回一个 JSON 对象。"
)


def _user_prompt(ai_input: dict, data_date: str, validation_feedback: str | None = None) -> str:
    correction = ""
    if validation_feedback:
        correction = f"\n上一份输出未通过校验，请重写完整 JSON。校验原因：{validation_feedback}。\n"
    return (
        f"分析日期：{data_date}。\n"
        f"压力状态只能从：{list(PRESSURE_STATES)} 中选择。\n"
        f"筑底状态只能从：{list(BOTTOMING_STATES)} 中选择。\n"
        f"六个分类状态只能从：{list(CATEGORY_STATUS_VALUES)} 中选择；不能改写、缩写或使用近义词。\n"
        "支持证据只能引用已触发指标：metric_states 中 support_eligible 为 true，也就是 judgment_eligible 为 true、status 为 current 且 tier.id 不是 none。\n"
        "如果支持文字引用具体阈值或档位，对应 thresholds 项的 triggered 为 true；不能把 triggered 为 false 的阈值方向、档位名称或含义写成当前事实。\n"
        "support_eligible 为 false 的指标只能写入 detailed.contrary_or_gaps 或 detailed.next_evidence，并明确说明未触发、缺失或过期。\n"
        "只有当两条轴都不是数据不足时，才填写一致性（弱、中等、强）；两条轴都数据不足时填写 null。\n"
        "机器提供的是事实边界，不是答案：不要寻找允许范围，不要把相关家族的多张卡片当成多票，不要把前三天变成投票或晋级规则。\n"
        "压力解释说明当前压力深度；筑底解释说明熊底过程形成到哪一步。需要明确哪些事实支持、哪些相反或缺失、时间线如何变化、修复是否持续、接下来观察什么。\n"
        "六个 detailed 部分必须全部填写：pressure_reason、bottoming_reason、evidence_timeline、contrary_or_gaps、repair_exit、next_evidence。\n"
        "不要逐项复述指标卡片；不要引入新闻、宏观消息、价格预测或任何交易建议。\n"
        f"{correction}\n"
        "JSON 结构：\n"
        "{\n"
        f'  "analysis_date": "{data_date}",\n'
        '  "pressure_state": "压力状态",\n'
        '  "bottoming_state": "筑底状态",\n'
        '  "consistency": "弱/中等/强 或 null",\n'
        '  "summary": "一句综合结论",\n'
        '  "compact": {"pressure": {"title": "压力", "text": "..."}, "bottoming": {"title": "筑底过程", "text": "..."}, "change": {"title": "近三日变化", "text": "..."}},\n'
        '  "categories": [{"id": "valuation", "status": "未确认/部分确认/充分确认 三选一", "note": "..."}],\n'
        '  "detailed": {"pressure_reason": "...", "bottoming_reason": "...", "evidence_timeline": "...", "contrary_or_gaps": "...", "repair_exit": "...", "next_evidence": "..."},\n'
        '  "state_changes": {"pressure": {"changed": false, "from": null, "to": "...", "reason": "...", "compared_date": null}, "bottoming": {"changed": false, "from": null, "to": "...", "reason": "...", "compared_date": null}}\n'
        "}\n\n"
        "输入事实：\n"
        f"{json.dumps(ai_input, ensure_ascii=False)}"
    )


def _chat(ai_input: dict, data_date: str, api_key: str, base_url: str, model: str, validation_feedback: str | None = None) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(ai_input, data_date, validation_feedback)},
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "max_tokens": 5000,
        "temperature": 0.2,
    }).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=300) as response:
        payload = json.loads(response.read())
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("AI 返回不是 JSON 对象")
    return parsed


def _tier_rank(value: object) -> int:
    return {"none": 0, "observation": 1, "deep_pressure": 2, "extreme_pressure": 3}.get(str(value), 0)


def _facts(ai_input: Mapping[str, object]) -> tuple[list[Mapping[str, object]], dict[str, Mapping[str, object]]]:
    raw = ai_input.get("metric_states")
    metrics = [item for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []
    return metrics, {str(item.get("id")): item for item in metrics}


def _mock_states(ai_input: Mapping[str, object]) -> tuple[str, str, str | None]:
    # 这里只生成可重复的离线验收夹具；真实 provider 不调用这段计数逻辑，
    # 而是依据同一份事实输入和固定词汇做定性综合。
    metrics, _ = _facts(ai_input)
    readiness = ai_input.get("axis_readiness")
    readiness = readiness if isinstance(readiness, Mapping) else {}
    pressure_ready = bool(isinstance(readiness.get("pressure"), Mapping) and readiness["pressure"].get("ready"))
    bottoming_ready = bool(isinstance(readiness.get("bottoming"), Mapping) and readiness["bottoming"].get("ready"))
    if not pressure_ready:
        pressure = "数据不足"
    else:
        anchors = [item for item in metrics if item.get("responsibility") == "pressure_anchor" and item.get("judgment_eligible")]
        ranks = [_tier_rank((item.get("tier") or {}).get("id")) for item in anchors if isinstance(item.get("tier"), Mapping)]
        triggered_families = {str(item.get("correlation_family")) for item in metrics if item.get("judgment_eligible") and item.get("tier", {}).get("id") not in {None, "none"}}
        if len([rank for rank in ranks if rank >= 2]) >= 2 and len(triggered_families) >= 3:
            pressure = "极端压力" if all(rank >= 3 for rank in ranks) else "深度压力"
        elif any(rank >= 2 for rank in ranks) or any(rank == 1 for rank in ranks):
            pressure = "深度压力" if any(rank >= 2 for rank in ranks) and len(triggered_families) >= 2 else "进入观察"
        else:
            pressure = "压力尚未明显"
    if not bottoming_ready:
        bottoming = "数据不足"
    else:
        bottoming_metrics = [
            item for item in metrics
            if item.get("judgment_eligible") and item.get("responsibility") in {"capitulation_clue", "exhaustion_clue", "repair_signal", "bottoming_context", "capitulation_context"}
        ]
        families = {str(item.get("correlation_family")) for item in bottoming_metrics if (item.get("tier") or {}).get("id") not in {None, "none"}}
        repairs = [item for item in bottoming_metrics if item.get("responsibility") == "repair_signal" and (item.get("tier") or {}).get("id") not in {None, "none"}]
        if len(repairs) >= 2 and pressure in {"压力尚未明显", "进入观察"}:
            bottoming = "已离开底部窗口"
        elif len(repairs) >= 1:
            bottoming = "市场修复中"
        elif len(families) >= 3:
            bottoming = "筑底证据较完整"
        elif len(families) >= 2:
            bottoming = "筑底证据聚合"
        elif len(families) == 1:
            bottoming = "筑底线索出现"
        else:
            bottoming = "未见筑底结构"
    triggered_families = {
        str(item.get("correlation_family"))
        for item in metrics
        if item.get("judgment_eligible") and (item.get("tier") or {}).get("id") not in {None, "none"}
    }
    if pressure == "数据不足" and bottoming == "数据不足":
        consistency = None
    elif len(triggered_families) >= 3:
        consistency = "强"
    elif len(triggered_families) >= 2:
        consistency = "中等"
    else:
        consistency = "弱"
    return pressure, bottoming, consistency


def _theme_phrase(family: str) -> str:
    return {
        "valuation": "估值与成本压力",
        "miner_pressure": "矿工收入压力",
        "supply_loss": "供应盈亏范围",
        "realized_loss": "链上亏损花费",
        "seller_exhaustion": "卖方力量变化",
        "short_term_cost": "短期持有者承接",
        "realized_capital": "已实现资本变化",
        "holder_behavior": "持有者行为",
        "long_term_anchor": "长期成本背景",
    }.get(family, "市场证据")


def _mock_analysis(data_date: str, evidence_brief: Mapping[str, object], ai_input: Mapping[str, object]) -> dict[str, object]:
    pressure, bottoming, consistency = _mock_states(ai_input)
    metrics, _ = _facts(ai_input)
    families = [
        _theme_phrase(str(item.get("correlation_family")))
        for item in metrics
        if item.get("judgment_eligible") and (item.get("tier") or {}).get("id") not in {None, "none"}
    ]
    unique_families = list(dict.fromkeys(families))
    support = "、".join(unique_families[:3]) or "当前可用证据还没有形成明显方向。"
    pressure_reason = f"当前压力轴为“{pressure}”，主要因为{support}。" if pressure != "数据不足" else "压力轴所需的关键数据没有同时满足新鲜度或覆盖条件。"
    bottoming_reason = f"当前筑底过程为“{bottoming}”，可见事实包括{support}。" if bottoming != "数据不足" else "筑底轴所需的承接、耗竭或时间线事实暂时不完整。"
    gaps = "仍有部分证据没有触发或暂时不可用，不能把缺口解释成反向证据。"
    timeline_text = "时间线显示不同证据并非同一天出现，当前判断反映的是过程中的组合变化。"
    repair_text = "目前没有足够事实证明修复已经稳定离开底部窗口。" if bottoming not in {"市场修复中", "已离开底部窗口"} else "修复相关事实正在持续，需要继续观察是否保持。"
    next_text = "继续观察独立证据家族是否持续、反向变化是否出现，以及缺失数据是否恢复。"
    previous = ai_input.get("previous_three_days")
    context = previous if isinstance(previous, list) else []
    current_stub = {"pressure_state": pressure, "bottoming_state": bottoming}
    changes = state_change_facts(context, current_stub)
    changed_reasons = [
        f"{axis}轴：{item['reason']}"
        for axis, item in changes.items()
        if item.get("changed")
    ]
    change_text = "；".join(changed_reasons) if changed_reasons else "前三个自然日只作为连续性背景，今天仍由最新事实判断。"
    category_triggered = {str(item.get("category")) for item in metrics if item.get("judgment_eligible") and (item.get("tier") or {}).get("id") not in {None, "none"}}
    categories = [
        {"id": category, "status": "部分确认" if category in category_triggered else "未确认", "note": "当前有相关事实" if category in category_triggered else "当前没有足够的可用支持事实"}
        for category in CATEGORY_IDS
    ]
    return {
        "analysis_date": data_date,
        "pressure_state": pressure,
        "bottoming_state": bottoming,
        "consistency": consistency,
        "summary": f"市场压力为“{pressure}”，筑底过程为“{bottoming}”。{change_text}",
        "compact": {
            "pressure": {"title": "压力深度", "text": pressure_reason},
            "bottoming": {"title": "熊底过程", "text": bottoming_reason},
            "change": {"title": "近三日变化", "text": change_text},
        },
        "categories": categories,
        "detailed": {
            "pressure_reason": pressure_reason,
            "bottoming_reason": bottoming_reason,
            "evidence_timeline": timeline_text,
            "contrary_or_gaps": gaps,
            "repair_exit": repair_text,
            "next_evidence": next_text,
        },
        "state_changes": changes,
    }


def data_insufficient_analysis(data_date: str, evidence_brief: Mapping[str, object]) -> dict[str, object]:
    """Create a deterministic result when one or both axes lack data."""

    readiness = evidence_brief.get("axis_readiness")
    readiness = readiness if isinstance(readiness, Mapping) else {}
    pressure_ready = bool(isinstance(readiness.get("pressure"), Mapping) and readiness["pressure"].get("ready"))
    bottoming_ready = bool(isinstance(readiness.get("bottoming"), Mapping) and readiness["bottoming"].get("ready"))
    pressure = "压力尚未明显" if pressure_ready else "数据不足"
    bottoming = "未见筑底结构" if bottoming_ready else "数据不足"
    missing = []
    for axis in ("pressure", "bottoming"):
        item = readiness.get(axis)
        if isinstance(item, Mapping) and not item.get("ready"):
            missing.extend(str(value) for value in item.get("missing_metric_ids", []))
    reason = "、".join(dict.fromkeys(missing)) or "部分轴所需数据"
    consistency = None if pressure == bottoming == "数据不足" else "弱"
    context = [{"date": "", "status": "missing", "pressure_state": None, "bottoming_state": None, "consistency": None, "reason": ""}]
    changes = state_change_facts(context, {"pressure_state": pressure, "bottoming_state": bottoming})
    return {
        "analysis_date": data_date,
        "pressure_state": pressure,
        "bottoming_state": bottoming,
        "consistency": consistency,
        "summary": f"当前压力状态为“{pressure}”，筑底状态为“{bottoming}”。{reason}暂时不可用于对应轴的判断。",
        "compact": {
            "pressure": {"title": "压力轴数据", "text": "压力轴数据可用。" if pressure_ready else f"压力轴缺少：{reason}。"},
            "bottoming": {"title": "筑底轴数据", "text": "筑底轴数据可用。" if bottoming_ready else f"筑底轴缺少：{reason}。"},
            "change": {"title": "近三日变化", "text": "数据恢复前不把缺失日补成判断。"},
        },
        "categories": [{"id": category, "status": "未确认", "note": "数据不足时不作类别确认"} for category in CATEGORY_IDS],
        "detailed": {
            "pressure_reason": "压力轴只根据当前可用事实说明压力深度。",
            "bottoming_reason": "筑底轴只根据当前可用的筑底相关事实说明过程。",
            "evidence_timeline": "缺失日期和缺失指标保持为空，不用其他日期猜测。",
            "contrary_or_gaps": f"缺少：{reason}。缺失数据不作为反向证据。",
            "repair_exit": "数据恢复后重新观察修复和离开窗口的证据。",
            "next_evidence": "继续观察缺失指标是否恢复，以及对应时间线是否完整。",
        },
        "state_changes": changes,
    }


def call_ai(
    snapshot: dict,
    *,
    data_date: str,
    mock: bool = False,
    evidence_brief: Mapping[str, object] | None = None,
    previous_three_days: list[Mapping[str, Any]] | None = None,
) -> tuple[dict | None, str | None]:
    """Return a validated v0.4 analysis or a failure reason."""

    try:
        brief = evidence_brief or compile_evidence(snapshot, analysis_date=data_date, previous_three_days=previous_three_days)
        ai_input = build_evidence_input(snapshot, evidence_brief=brief, analysis_date=data_date, previous_three_days=previous_three_days)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return None, f"证据整理失败: {type(exc).__name__}: {str(exc)[:120]}"

    readiness = brief.get("axis_readiness")
    readiness = readiness if isinstance(readiness, Mapping) else {}
    both_unready = all(isinstance(readiness.get(axis), Mapping) and not readiness[axis].get("ready") for axis in ("pressure", "bottoming"))
    if mock:
        analysis = data_insufficient_analysis(data_date, brief) if both_unready else _mock_analysis(data_date, brief, ai_input)
        try:
            validator.validate_analysis(analysis)
            semantic_validator.validate_analysis_semantics(analysis, ai_input)
        except validator.InvalidAnalysisError as exc:
            return None, f"mock 分析契约校验失败: {exc.errors[:3]}"
        return analysis, None

    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        return None, "未配置 AI_API_KEY，跳过 AI 分析（回退上一份成功结果）"
    base_url = os.environ.get("AI_BASE_URL", "").strip() or DEFAULT_BASE_URL
    model = os.environ.get("AI_MODEL", "").strip() or DEFAULT_MODEL
    feedback: str | None = None
    last_error: str | None = None
    for attempt in range(3):
        try:
            raw = _chat(ai_input, data_date, api_key, base_url, model, feedback)
            raw.setdefault("analysis_date", data_date)
            validator.validate_analysis(raw)
            semantic_validator.validate_analysis_semantics(raw, ai_input)
            return raw, None
        except validator.InvalidAnalysisError as exc:
            last_error = f"AI 输出校验失败: {exc.errors[:3]}"
            feedback = "；".join(exc.errors[:3])
            if attempt == 2:
                return None, last_error
        except (HTTPError, URLError, TimeoutError, ConnectionError, OSError, KeyError, ValueError) as exc:
            last_error = f"AI 调用失败: {type(exc).__name__}: {str(exc)[:120]}"
            if attempt == 2:
                return None, last_error
    return None, last_error or "AI 输出不可用"


__all__ = ["call_ai", "data_insufficient_analysis"]
