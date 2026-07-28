from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from services.ai.contract import CATEGORY_IDS
from services.ai.validator import InvalidAnalysisError, validate_analysis


ROOT = Path(__file__).resolve().parents[2]
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"


def load_analysis() -> dict:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    return packet["analysis"] or packet["fallback"]


def load_packet() -> dict:
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def assert_rejected(payload: dict) -> None:
    with pytest.raises(InvalidAnalysisError):
        validate_analysis(payload)


def plain_language_analysis() -> dict:
    return {
        "analysis_date": "2026-07-28",
        "stage": "熊市下行期",
        "consistency": "中等",
        "summary": (
            "矿工收入已经开始承压，链上亏损卖出增多，"
            "说明市场内部压力不轻。"
        ),
        "pressure_summary": "亏损卖出和卖方力量减弱同时出现，当前压力偏重。",
        "compact": {
            "support": {
                "title": "当前市场状态",
                "text": "矿工收入承压，供应利润空间也在收窄。",
            },
            "obstacle": {
                "title": "还没有进入更深阶段",
                "text": "整体估值还没有进入更深的压力区。",
            },
            "next": {
                "title": "接下来观察",
                "text": "观察整体估值是否继续下降，以及矿工压力是否进一步加深。",
            },
        },
        "categories": [
            {"id": category, "status": "部分确认", "note": "相关市场现象已经出现。"}
            for category in CATEGORY_IDS
        ],
        "detailed": {
            "supporting": "矿工收入、亏损卖出和供应利润共同显示市场正在承压。",
            "contrary": "整体估值尚未进入过去深熊阶段常见的位置。",
            "next_stage": "继续观察整体估值与矿工收入压力是否进一步加深。",
            "pressure": "亏损卖出和卖方力量减弱同时出现，当前压力偏重。",
        },
    }


def test_current_offline_analysis_matches_the_ai_contract() -> None:
    normalized = validate_analysis(load_analysis())

    assert normalized["stage"]
    assert normalized["consistency"]
    assert {item["category"] for item in normalized["categories"]} == set(CATEGORY_IDS)
    assert normalized["supporting_evidence"]
    assert normalized["contrary_evidence"]
    assert normalized["next_stage_confirmation"]


def test_visible_analysis_never_fully_confirms_an_untriggered_category() -> None:
    """A category label must not contradict every visible metric card."""
    packet = load_packet()
    visible_analysis = packet["analysis"] or packet["fallback"]
    analysis_by_category = {
        item["id"]: item["status"]
        for item in visible_analysis["categories"]
    }

    for category in packet["snapshot"]["categories"]:
        metrics = [
            metric
            for metric in packet["snapshot"]["metrics"]
            if metric["category"] == category["id"]
        ]
        all_untriggered = all(
            metric["tier_label"] == "未进入观察区" for metric in metrics
        )
        if all_untriggered:
            assert analysis_by_category[category["id"]] != "充分确认", (
                f"{category['name']} 的所有指标均未进入观察区，"
                "但页面分类被标为充分确认"
            )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("stage", "未知阶段"),
        ("consistency", "未知一致性"),
    ],
)
def test_rejects_unknown_stage_or_consistency(field: str, value: str) -> None:
    payload = load_analysis()
    payload[field] = value
    assert_rejected(payload)


def test_rejects_unknown_category_status() -> None:
    payload = load_analysis()
    payload["categories"][0]["status"] = "未知状态"
    assert_rejected(payload)


def test_rejects_incomplete_or_duplicate_six_category_assessment() -> None:
    payload = load_analysis()
    payload["categories"] = payload["categories"][:-1]
    assert_rejected(payload)

    payload = load_analysis()
    payload["categories"][0]["id"] = payload["categories"][1]["id"]
    assert_rejected(payload)


@pytest.mark.parametrize("detail_field", ["supporting", "contrary", "next_stage"])
def test_rejects_missing_required_detail(detail_field: str) -> None:
    payload = load_analysis()
    del payload["detailed"][detail_field]
    assert_rejected(payload)


@pytest.mark.parametrize(
    "forbidden_text",
    [
        "熊底概率为 78%",
        "建议买入并提高仓位",
        "建议卖出",
        "卖出 BTC",
        "逢高卖出 BTC",
        "使用 3 倍杠杆",
    ],
)
def test_rejects_numeric_probability_and_trading_advice(forbidden_text: str) -> None:
    payload = load_analysis()
    payload["detailed"]["supporting"] = forbidden_text
    assert_rejected(payload)


def test_forbidden_word_feedback_names_the_exact_term() -> None:
    payload = load_analysis()
    payload["detailed"]["supporting"] = "建议买入"

    with pytest.raises(InvalidAnalysisError) as exc_info:
        validate_analysis(payload)

    assert any("买入" in error for error in exc_info.value.errors)


@pytest.mark.parametrize(
    "internal_term",
    [
        "核心锚",
        "强辅助",
        "阶段上限",
        "抬高阶段",
        "替代核心",
        "allowed_stages",
        "triggered",
        "evidence_use",
        "机器规定",
        "系统不允许",
    ],
)
def test_rejects_internal_rule_language_from_user_visible_text(
    internal_term: str,
) -> None:
    payload = plain_language_analysis()
    payload["summary"] = f"当前结论依据{internal_term}。"

    with pytest.raises(InvalidAnalysisError) as exc_info:
        validate_analysis(payload)

    assert any(internal_term in error for error in exc_info.value.errors)


def test_allows_observational_loss_selling_language() -> None:
    normalized = validate_analysis(plain_language_analysis())

    assert "链上亏损卖出增多" in normalized["summary"]


def test_rejects_forbidden_advice_field_even_when_nested() -> None:
    payload = load_analysis()
    payload["detailed"]["extra"] = {"position": "50%"}
    assert_rejected(payload)
