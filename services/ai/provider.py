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

from . import validator
from .contract import (
    ALLOWED_STAGES,
    CATEGORY_IDS,
    CATEGORY_STATUS_VALUES,
    CONSISTENCY_VALUES,
)
from .input_builder import build_ai_input


DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-5.2"


_SYSTEM_PROMPT = (
    "你是 BTC 周期证据看板的日度分析器。根据给定的指标快照，把当前市场归纳为一个阶段并解释证据。"
    "你只能基于已提供的指标事实做归纳，绝不预测价格、不给出任何买卖/入场/仓位/杠杆建议、不输出任何概率或置信度数字。"
    "输出必须是单个 JSON 对象，字段使用简体中文，遵循下面给定的固定词汇表与结构。"
)


def _user_prompt(
    ai_input: dict,
    data_date: str,
    validation_feedback: str | None = None,
) -> str:
    correction = ""
    if validation_feedback:
        correction = (
            "\n上一份输出未通过校验，请重新生成完整 JSON。"
            f"校验原因：{validation_feedback}。不要解释错误，只输出修正后的完整对象。\n"
        )
    return (
        f"分析日期 analysis_date = {data_date}。\n"
        f"阶段只能从这些里选一个 stage：{list(ALLOWED_STAGES)}。\n"
        f"一致性只能从这些里选 consistency：{list(CONSISTENCY_VALUES)}。\n"
        f"必须为这六个类别各给出 status（只能从 {list(CATEGORY_STATUS_VALUES)} 中选）：{list(CATEGORY_IDS)}。\n\n"
        "证据判定必须严格遵守 thresholds：direction=below 时 current_value 小于阈值才算触发；"
        "direction=above 时 current_value 大于阈值才算触发。\n"
        "只有触发阈值的指标才能列入支持证据；未触发的指标只能列入阻碍、反面证据或待确认条件，"
        "不能因为数值看起来偏高、偏低、为正或为负就自行改变阈值方向。\n"
        "核心或辅助是指标角色，不是类别角色；不要把类别称为核心类别或辅助类别，也不要把包含核心指标的类别概括为辅助类别。\n\n"
        "描述阈值档位时必须先看该指标实际提供了几个触发阈值："
        "只有一个触发阈值的指标，应说它已触发唯一阈值或尚未触发唯一阈值，"
        "不得说它未触发更深档位，也不得把它和多档指标合并描述为都未触发更深档位。\n\n"
        "即使是否定句或风险提示，也不要复述任何禁止词；只描述证据、阶段和待确认条件。\n"
        f"{correction}\n"
        "输出 JSON 结构（不要输出任何 JSON 以外的文字）：\n"
        "{\n"
        '  "analysis_date": "<上面给的分析日期>",\n'
        '  "stage": "<阶段>",\n'
        '  "consistency": "<一致性>",\n'
        '  "summary": "<一段基于证据的归纳，不预测价格>",\n'
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
        '    "supporting": "<支持证据的详细说明>",\n'
        '    "contrary": "<反面或未完成证据的详细说明>",\n'
        '    "next_stage": "<下一阶段确认条件的详细说明>"\n'
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
        "reasoning_effort": "max",
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
    with urlopen(request, timeout=180) as response:
        payload = json.loads(response.read())
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("AI 返回不是 JSON 对象")
    return parsed


def _mock_analysis(data_date: str) -> dict:
    """A fixed, validator-compliant analysis for offline / --mock-ai runs."""
    return {
        "analysis_date": data_date,
        "stage": "筑底证据积累期",
        "consistency": "中等",
        "summary": "多类证据向底部结构收敛，但尚未形成完整一致性。",
        "compact": {
            "support": {"title": "估值 + 矿工压力", "text": "核心估值与矿工压力类别已进入观察区。"},
            "obstacle": {"title": "持有者行为仍在积累", "text": "持有者类别证据仍需更多独立确认。"},
            "next": {"title": "核心类别继续收敛", "text": "等待更多核心类别同步确认。"},
        },
        "categories": [
            {"id": "valuation", "status": "充分确认", "note": "核心估值进入深度观察。"},
            {"id": "supply", "status": "部分确认", "note": "供应盈亏结构偏向压力。"},
            {"id": "capital", "status": "部分确认", "note": "已实现资本仍偏弱。"},
            {"id": "holders", "status": "充分确认", "note": "持有者投降证据增强。"},
            {"id": "miners", "status": "部分确认", "note": "矿工压力进入观察区。"},
            {"id": "anchors", "status": "部分确认", "note": "长期成本锚开始接近。"},
        ],
        "detailed": {
            "supporting": "估值与矿工压力类别提供核心支持证据，多个核心维度进入观察区。",
            "contrary": "持有者投降信号与长期成本锚类别仍未充分聚合。",
            "next_stage": "需要核心类别与支持证据形成更完整的一致性组合。",
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
    if mock:
        analysis = _mock_analysis(data_date)
        try:
            validator.validate_analysis(analysis)
        except validator.InvalidAnalysisError as exc:
            return None, f"mock 分析契约校验失败: {exc.errors[:3]}"
        return analysis, None

    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        return None, "未配置 AI_API_KEY，跳过 AI 分析（回退上一份成功结果）"

    base_url = os.environ.get("AI_BASE_URL", "").strip() or DEFAULT_BASE_URL
    model = os.environ.get("AI_MODEL", "").strip() or DEFAULT_MODEL

    try:
        ai_input = build_ai_input(snapshot)
    except (OSError, KeyError, ValueError) as exc:
        return None, f"AI 调用失败: {type(exc).__name__}: {str(exc)[:120]}"

    validation_feedback: str | None = None
    for attempt in range(2):
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
            return None, f"AI 调用失败: {type(exc).__name__}: {str(exc)[:120]}"

        try:
            validator.validate_analysis(raw)
        except validator.InvalidAnalysisError as exc:
            if attempt == 0:
                validation_feedback = "；".join(exc.errors[:3])
                continue
            return None, f"AI 输出契约校验失败: {exc.errors[:3]}"

        return raw, None

    return None, "AI 输出契约校验失败: 重试后仍不可用"
