"""Daily AI analysis provider — constrained input, validated output.

Flow: ``input_builder`` whitelists what leaves the system -> an OpenAI-compatible
chat call (GLM by default, any compatible endpoint via env) -> ``validator``
rejects anything with trading/probability language or a wrong vocabulary word.

Every failure mode returns ``(None, reason)`` so ``run_daily`` keeps the previous
success packet (requirement 1 整包回退). A real key is never required for local
development: set ``--mock-ai`` to run the full chain with a fixed compliant
analysis.

Environment:
* ``AI_API_KEY``  — bearer token; absent => skip AI (fallback).
* ``AI_BASE_URL`` — OpenAI-compatible root (default GLM open platform).
* ``AI_MODEL``    — model id (default glm-5.2).
"""

from __future__ import annotations

import json
import os
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import semantic_validator, validator
from .contract import (
    ALLOWED_STAGES,
    CATEGORY_IDS,
    CATEGORY_STATUS_VALUES,
    CONSISTENCY_VALUES,
)
from .input_builder import build_evidence_input
from services.evidence.compiler import compile_evidence


DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-5.2"


_SYSTEM_PROMPT = (
    "你是 BTC 周期证据看板的日度分析器。机器已经把指标整理成核心维度和辅助证据主题。"
    "你的任务是综合这些证据关系，在机器给出的相邻阶段范围内选择一个阶段并解释为什么。"
    "先说证据合在一起说明什么，再提少量代表性指标；不要逐项复述指标定义或卡片数字。"
    "你只能基于已提供的证据简报做归纳，绝不预测价格、不给出任何买卖/入场/仓位/杠杆建议、不输出任何概率或置信度数字。"
    "输出必须是单个 JSON 对象，字段使用简体中文，遵循下面给定的固定词汇表与结构。"
)


def _user_prompt(
    ai_input: dict,
    data_date: str,
    validation_feedback: str | None = None,
) -> str:
    forbidden_terms = "、".join(validator.FORBIDDEN_OUTPUT_TERMS)
    correction = ""
    if validation_feedback:
        correction = (
            "\n上一份输出未通过校验，请重新生成完整 JSON。"
            f"校验原因：{validation_feedback}。不要解释错误，只输出修正后的完整对象。\n"
        )
    return (
        f"分析日期 analysis_date = {data_date}。\n"
        f"阶段只能从机器允许范围中选一个 stage：{[item.get('stage') for item in ai_input.get('allowed_stages', [])]}。\n"
        f"一致性只能从这些里选 consistency：{list(CONSISTENCY_VALUES)}。\n"
        f"必须为这六个类别各给出 status（只能从 {list(CATEGORY_STATUS_VALUES)} 中选）：{list(CATEGORY_IDS)}。\n\n"
        "机器已经标出哪些证据可用、哪些主题较强；不要把被排除指标当成当前支持或反面证据。\n"
        "只有触发阈值的指标才能列入支持证据；未触发的指标只能列入阻碍、反面证据或待确认条件。\n"
        "compact.support 与 detailed.supporting 中不得出现任何未触发指标的名称或数值。\n"
        "核心或辅助是指标角色，不是类别角色；不要把类别称为核心类别或辅助类别。\n"
        "只有一个触发阈值的指标，应说它已触发唯一阈值或尚未触发唯一阈值，不得说它未触发更深档位。\n"
        "MVRV 与 AVIV 属于同一个估值维度，不能写成两张估值票；Puell 是独立的矿工压力维度。\n"
        "辅助主题不能扩大 allowed_stages；它们只能帮助你解释当前阶段内部的压力、投降、恢复或矛盾。\n"
        "当 strong_auxiliary_themes 非空时，pressure_summary 必须明确说明当前阶段内部的压力程度。\n\n"
        "即使是否定句或风险提示，也不要复述任何禁止词；只描述证据、阶段和待确认条件。\n"
        "描述阈值档位时不得把单阈值指标说成还缺少更深档位。\n"
        f"禁止词表（输入里出现也不能照抄）：{forbidden_terms}。\n"
        "提及相关指标时，改用“链上花费”“供应变化”“阶段确认”等中性说法。\n"
        "Reserve Risk 的数值进入周期低位，含义是长期持有信念进入周期高位，绝不能写成持有信念低位。\n"
        "HODLer 的零阈值不要改名为“积累/链上花费分界”，请称为“长期供应净变化零线”。\n"
        f"{correction}\n"
        "输出 JSON 结构（不要输出任何 JSON 以外的文字）：\n"
        "{\n"
        '  "analysis_date": "<上面给的分析日期>",\n'
        '  "stage": "<阶段>",\n'
        '  "consistency": "<一致性>",\n'
        '  "summary": "<先综合至少两个证据维度，再用少量代表性证据说明，不预测价格>",\n'
        '  "pressure_summary": "<若有强辅助主题，说明当前阶段内部压力；否则为空字符串>",\n'
        '  "compact": {\n'
        '    "support": {"title": "<短标题>", "text": "<支持证据要点>"},\n'
        '    "obstacle": {"title": "<短标题>", "text": "<未完成或反面证据>"},\n'
        '    "next": {"title": "<短标题>", "text": "<进入下一阶段需要的确认>"}\n'
        "  },\n"
        '  "categories": [\n'
        '    {"id": "<类别id>", "status": "<状态>", "note": "<一句话说明，可为空>"}\n'
        "    // 共 6 个，覆盖全部类别\n"
        "  ],\n"
        '  "detailed": {\n'
        '    "supporting": "<核心依据与辅助主题如何共同支持当前阶段>",\n'
        '    "contrary": "<反面或未完成证据的详细说明>",\n'
        '    "next_stage": "<下一阶段确认条件的详细说明>",\n'
        '    "pressure": "<阶段内部压力的展开说明，可为空>"\n'
        "  }\n"
        "}\n\n"
        "指标快照输入（只读，作为归纳依据）：\n"
        f"{json.dumps(ai_input, ensure_ascii=False)}"
    )


def _chat(
    ai_input: dict,
    data_date: str,
    api_key: str,
    base_url: str,
    model: str,
    validation_feedback: str | None = None,
) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _user_prompt(
                    ai_input,
                    data_date,
                    validation_feedback,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "temperature": 0.2,
    }).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=300) as response:
        payload = json.loads(response.read())
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("AI 返回不是 JSON 对象")
    return parsed


def _mock_analysis(data_date: str, evidence_brief: dict | None = None) -> dict:
    """A fixed, validator-compliant analysis for offline / --mock-ai runs."""
    brief = evidence_brief or {}
    allowed = brief.get("allowed_stages") or ["熊市下行期"]
    strong = brief.get("strong_auxiliary_themes") or []
    # 机器层已经给出允许的阶段范围。没有强辅助证据时，离线示例取较保守的一端；
    # 只有在辅助证据确实形成一致压力时，才展示范围内更高的一档。
    stage = allowed[-1] if strong and len(allowed) > 1 else allowed[0]
    strong_labels = [str(item.get("label")) for item in strong if item.get("label")]
    pressure = (
        f"{'、'.join(strong_labels)}等辅助证据同时偏强，"
        "说明当前阶段内部的压力较重，但它们不会越过核心阶段上限。"
        if strong
        else "当前辅助证据没有形成额外的强压力主题。"
    )
    dimensions = brief.get("core_dimensions", {})
    valuation_state = dimensions.get("valuation", {}).get("state")
    miners_state = dimensions.get("miners", {}).get("state")
    status_for_state = {"none": "未确认", "watch": "部分确认", "deep": "充分确认"}
    valuation_status = status_for_state.get(valuation_state, "未确认")
    miners_status = status_for_state.get(miners_state, "未确认")
    return {
        "analysis_date": data_date,
        "stage": stage,
        "consistency": "中等" if len(allowed) > 1 else "弱",
        "summary": "估值与矿工压力共同决定当前阶段范围，辅助证据用于补充压力和未完成条件。",
        "pressure_summary": pressure,
        "compact": {
            "support": {"title": "估值 + 矿工压力", "text": "估值和矿工收入两个独立维度共同限定了当前阶段范围。"},
            "obstacle": {"title": "持有者行为仍在积累", "text": "持有者类别证据仍需更多独立确认。"},
            "next": {"title": "下一阶段条件", "text": "等待简报列出的核心条件进一步满足。"},
        },
        "categories": [
            {"id": "valuation", "status": valuation_status, "note": "MVRV 形成估值维度状态。"},
            {"id": "supply", "status": "部分确认", "note": "供应盈亏结构偏向压力。"},
            {"id": "capital", "status": "部分确认", "note": "已实现资本仍偏弱。"},
            {"id": "holders", "status": "充分确认", "note": "持有者投降证据增强。"},
            {"id": "miners", "status": miners_status, "note": "Puell 形成矿工压力维度状态。"},
            {"id": "anchors", "status": "部分确认", "note": "长期成本锚开始接近。"},
        ],
        "detailed": {
            "supporting": "估值与矿工压力是两个独立核心维度；辅助主题只用于补充当前阶段内部的压力强度。",
            "contrary": "持有者投降信号与长期成本锚类别仍未充分聚合。",
            "next_stage": "需要核心类别与支持证据形成更完整的一致性组合。",
            "pressure": pressure,
        },
    }


def data_insufficient_analysis(data_date: str, evidence_brief: dict) -> dict:
    """Create a deterministic system-state result without calling an AI."""

    missing = evidence_brief.get("data_quality", {}).get("critical_missing", [])
    detail = "、".join(str(item) for item in missing) or "关键指标"
    reason = f"{detail} 当前不可用，暂时不能形成阶段判断。"
    return {
        "analysis_date": data_date,
        "stage": "数据不足",
        "consistency": "弱",
        "summary": "当前关键数据不完整，页面只说明数据状态，不把缺失数据当作未触发证据。",
        "pressure_summary": "",
        "compact": {
            "support": {"title": "数据状态", "text": reason},
            "obstacle": {"title": "暂不能判断", "text": "MVRV 与 Puell 必须同时有当前有效数据。"},
            "next": {"title": "恢复判断条件", "text": "补齐关键锚的当前数据后，系统才会重新生成阶段解释。"},
        },
        "categories": [
            {"id": category, "status": "未确认", "note": "数据不足，不把缺失解释为未触发。"}
            for category in CATEGORY_IDS
        ],
        "detailed": {
            "supporting": reason,
            "contrary": "当前没有足够的关键锚数据，辅助指标也不会替代核心判断。",
            "next_stage": "关键锚恢复当前有效后，重新检查估值和矿工压力两个独立维度。",
            "pressure": "",
        },
    }


def call_ai(
    snapshot: dict,
    *,
    data_date: str,
    mock: bool = False,
) -> tuple[dict | None, str | None]:
    """Return (analysis, reason).

    ``analysis`` is a validated dashboard-format dict on success, or ``None``
    with a human-readable ``reason`` when AI is unavailable / non-compliant so
    the caller falls back to the previous success packet.
    """
    # The empty-input mock is kept for the contract unit tests and local
    # smoke checks; a real daily run always supplies all sixteen cards.
    if mock and not isinstance(snapshot.get("metrics"), list):
        legacy = _mock_analysis(data_date, {"allowed_stages": ["筑底证据积累期"]})
        try:
            validator.validate_analysis(legacy)
        except validator.InvalidAnalysisError as exc:
            return None, f"mock 分析契约校验失败: {exc.errors[:3]}"
        return legacy, None

    try:
        evidence_brief = compile_evidence(snapshot, analysis_date=data_date)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return None, f"证据整理失败: {type(exc).__name__}: {str(exc)[:120]}"

    if not evidence_brief["data_quality"]["stage_ready"]:
        missing = ", ".join(evidence_brief["data_quality"].get("critical_missing", []))
        return None, f"数据不足：关键锚不可用（{missing or '未知原因'}），不调用 AI"

    ai_input = build_evidence_input(
        snapshot,
        evidence_brief=evidence_brief,
        analysis_date=data_date,
    )
    allowed_stages = evidence_brief["allowed_stages"]
    require_pressure = bool(evidence_brief.get("strong_auxiliary_themes"))

    if mock:
        analysis = _mock_analysis(data_date, evidence_brief)
        try:
            validator.validate_analysis(
                analysis,
                allowed_stages=allowed_stages,
                require_pressure_summary=require_pressure,
            )
            semantic_validator.validate_analysis_semantics(analysis, ai_input)
        except validator.InvalidAnalysisError as exc:
            return None, f"mock 分析契约校验失败: {exc.errors[:3]}"
        return analysis, None

    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        return None, "未配置 AI_API_KEY，跳过 AI 分析（回退上一份成功结果）"

    base_url = os.environ.get("AI_BASE_URL", "").strip() or DEFAULT_BASE_URL
    model = os.environ.get("AI_MODEL", "").strip() or DEFAULT_MODEL

    validation_feedback: str | None = None
    last_call_error: str | None = None
    for attempt in range(3):
        try:
            raw = _chat(
                ai_input,
                data_date,
                api_key,
                base_url,
                model,
                validation_feedback,
            )
        except (
            HTTPError,
            URLError,
            TimeoutError,
            ConnectionError,
            OSError,
            KeyError,
            ValueError,
        ) as exc:
            last_call_error = (
                f"AI 调用失败: {type(exc).__name__}: {str(exc)[:120]}"
            )
            if attempt < 2:
                continue
            return None, last_call_error

        try:
            raw.setdefault("analysis_date", data_date)
            validator.validate_analysis(
                raw,
                allowed_stages=allowed_stages,
                require_pressure_summary=require_pressure,
            )
            semantic_validator.validate_analysis_semantics(raw, ai_input)
        except validator.InvalidAnalysisError as exc:
            if attempt < 2:
                validation_feedback = "；".join(exc.errors[:3])
                continue
            return None, f"AI 输出契约校验失败: {exc.errors[:3]}"

        return raw, None

    return None, last_call_error or "AI 输出契约校验失败: 重试后仍不可用"
