"""The fixed vocabulary and public shape of a daily AI analysis."""

from __future__ import annotations

from typing import Final


MARKET_STAGES: Final[tuple[str, ...]] = (
    "尚未进入熊底观察期",
    "熊市下行期",
    "深度压力期",
    "筑底证据积累期",
    "熊底证据充分期",
)
DATA_INSUFFICIENT_STAGE: Final[str] = "数据不足"
ALLOWED_STAGES: Final[tuple[str, ...]] = MARKET_STAGES + (DATA_INSUFFICIENT_STAGE,)

CATEGORY_IDS: Final[tuple[str, ...]] = (
    "valuation",
    "supply",
    "capital",
    "holders",
    "miners",
    "anchors",
)
CATEGORY_STATUS_VALUES: Final[tuple[str, ...]] = ("未确认", "部分确认", "充分确认")
CONSISTENCY_VALUES: Final[tuple[str, ...]] = ("弱", "中等", "强")

STAGE_DEFINITIONS: Final[dict[str, str]] = {
    "尚未进入熊底观察期": "当前快照还没有进入项目定义的熊底证据观察范围。",
    "熊市下行期": "当前快照显示下行压力，但熊底证据仍未充分聚合。",
    "深度压力期": "多个压力类别已经明显，但仍需要更多独立类别确认。",
    "筑底证据积累期": "部分核心类别已经确认，证据正在向更完整的底部结构收敛。",
    "熊底证据充分期": "核心类别与支持证据形成较完整的一致性组合。",
    "数据不足": "当前输入不足以做出可靠的市场阶段判断。",
}

CATEGORY_STATUS_DEFINITIONS: Final[dict[str, str]] = {
    "未确认": "该类别当前没有达到可确认的证据条件。",
    "部分确认": "该类别出现方向性证据，但仍缺少完整确认。",
    "充分确认": "该类别的当前快照满足项目设定的充分确认条件。",
}

CONSISTENCY_DEFINITIONS: Final[dict[str, str]] = {
    "弱": "不同类别之间的证据方向不够一致。",
    "中等": "部分类别方向一致，但仍有重要未确认或反面证据。",
    "强": "多个独立类别的证据方向较为一致。",
}


def _text_schema() -> dict[str, object]:
    return {
        "oneOf": [
            {"type": "string", "minLength": 1},
            {
                "type": "object",
                "required": ["text"],
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "text": {"type": "string", "minLength": 1},
                },
                "additionalProperties": False,
            },
        ]
    }


# This schema is exported for callers that use jsonschema. The validator below
# deliberately uses only the Python standard library so offline acceptance does
# not depend on an optional package.
ANALYSIS_SCHEMA: Final[dict[str, object]] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "stage",
        "summary",
        "core_support",
        "main_obstacle",
        "next_stage_condition",
        "categories",
        "supporting_evidence",
        "contrary_evidence",
        "next_stage_confirmation",
    ],
    "properties": {
        "analysis_date": {"type": "string", "minLength": 1},
        "stage": {"enum": list(ALLOWED_STAGES)},
        "consistency": {"enum": list(CONSISTENCY_VALUES)},
        "summary": {"type": "string", "minLength": 1},
        "core_support": _text_schema(),
        "main_obstacle": _text_schema(),
        "next_stage_condition": _text_schema(),
        "categories": {
            "type": "array",
            "minItems": len(CATEGORY_IDS),
            "maxItems": len(CATEGORY_IDS),
            "items": {
                "type": "object",
                "required": ["category", "status"],
                "properties": {
                    "category": {"enum": list(CATEGORY_IDS)},
                    "status": {"enum": list(CATEGORY_STATUS_VALUES)},
                },
                "additionalProperties": False,
            },
        },
        "supporting_evidence": {"type": "string", "minLength": 1},
        "contrary_evidence": {"type": "string", "minLength": 1},
        "next_stage_confirmation": {"type": "string", "minLength": 1},
    },
    "additionalProperties": False,
}
OUTPUT_SCHEMA: Final[dict[str, object]] = ANALYSIS_SCHEMA

