"""The v0.4 dual-axis AI contract.

The machine sends facts and fixed vocabularies.  The model chooses one state
on each axis and explains the choice.  There is deliberately no combined
stage, score, or machine-generated ``allowed_stages`` range in this contract.
"""

from __future__ import annotations

from typing import Final


PRESSURE_STATES: Final[tuple[str, ...]] = (
    "压力尚未明显",
    "进入观察",
    "深度压力",
    "极端压力",
    "数据不足",
)

BOTTOMING_STATES: Final[tuple[str, ...]] = (
    "未见筑底结构",
    "筑底线索出现",
    "筑底证据聚合",
    "筑底证据较完整",
    "市场修复中",
    "已离开底部窗口",
    "数据不足",
)

AXIS_IDS: Final[tuple[str, ...]] = ("pressure", "bottoming")
CONSISTENCY_VALUES: Final[tuple[str, ...]] = ("弱", "中等", "强")
CATEGORY_IDS: Final[tuple[str, ...]] = (
    "valuation",
    "supply",
    "capital",
    "holders",
    "miners",
    "anchors",
)
CATEGORY_STATUS_VALUES: Final[tuple[str, ...]] = ("未确认", "部分确认", "充分确认")
DETAIL_SECTION_IDS: Final[tuple[str, ...]] = (
    "pressure_reason",
    "bottoming_reason",
    "evidence_timeline",
    "contrary_or_gaps",
    "repair_exit",
    "next_evidence",
)

STATE_DEFINITIONS: Final[dict[str, dict[str, str]]] = {
    "pressure": {
        "压力尚未明显": "当前可用事实还没有形成明显的广泛压力。",
        "进入观察": "已经出现需要持续观察的压力现象，但深度尚未广泛聚合。",
        "深度压力": "多个相互独立的市场压力维度已经明显加深。",
        "极端压力": "多个独立维度同时处在历史校准的极端压力附近。",
        "数据不足": "当前数据覆盖、新鲜度或时间线不足以判断压力深度。",
    },
    "bottoming": {
        "未见筑底结构": "当前没有足够的筑底、耗竭或承接结构事实。",
        "筑底线索出现": "已经出现少量筑底相关线索，但结构仍不完整。",
        "筑底证据聚合": "来自不同职责的筑底线索正在陆续聚合。",
        "筑底证据较完整": "压力、耗竭、承接和时间线共同形成较完整结构。",
        "市场修复中": "底部窗口内的修复和承接事实持续出现。",
        "已离开底部窗口": "修复持续且主要底部压力事实已明显离开底部窗口。",
        "数据不足": "当前数据覆盖、新鲜度或时间线不足以判断筑底过程。",
    },
}

CONSISTENCY_DEFINITIONS: Final[dict[str, str]] = {
    "弱": "证据方向分散，支持、反面和缺失事实之间仍有明显空白。",
    "中等": "部分独立维度方向一致，但仍有重要反面或缺失事实。",
    "强": "多个独立维度和时间线方向较为一致，反面证据有限。",
}

# Kept as import-only aliases for old scripts.  v0.4 never serialises these
# names and no runtime decision is allowed to depend on them.
MARKET_STAGES: Final[tuple[str, ...]] = ()
ALLOWED_STAGES: Final[tuple[str, ...]] = ()
DATA_INSUFFICIENT_STAGE: Final[str] = "数据不足"
STAGE_DEFINITIONS: Final[dict[str, str]] = {}
CATEGORY_STATUS_DEFINITIONS: Final[dict[str, str]] = {
    "未确认": "当前没有达到可确认的证据条件。",
    "部分确认": "出现方向性证据，但仍缺少完整确认。",
    "充分确认": "当前类别的事实较为完整。",
}


def _text_schema() -> dict[str, object]:
    return {"type": "string", "minLength": 1}


ANALYSIS_SCHEMA: Final[dict[str, object]] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "analysis_date",
        "pressure_state",
        "bottoming_state",
        "summary",
        "compact",
        "detailed",
    ],
    "properties": {
        "analysis_date": _text_schema(),
        "pressure_state": {"enum": list(PRESSURE_STATES)},
        "bottoming_state": {"enum": list(BOTTOMING_STATES)},
        "consistency": {"enum": list(CONSISTENCY_VALUES)},
        "summary": _text_schema(),
        "compact": {"type": "object"},
        "detailed": {"type": "object"},
    },
    "additionalProperties": False,
}


__all__ = [
    "PRESSURE_STATES",
    "BOTTOMING_STATES",
    "AXIS_IDS",
    "CONSISTENCY_VALUES",
    "CATEGORY_IDS",
    "CATEGORY_STATUS_VALUES",
    "DETAIL_SECTION_IDS",
    "STATE_DEFINITIONS",
    "CONSISTENCY_DEFINITIONS",
    "ANALYSIS_SCHEMA",
    "MARKET_STAGES",
    "ALLOWED_STAGES",
    "DATA_INSUFFICIENT_STAGE",
    "STAGE_DEFINITIONS",
    "CATEGORY_STATUS_DEFINITIONS",
]
