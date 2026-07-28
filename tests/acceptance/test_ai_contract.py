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
    return packet["analysis"]


def load_packet() -> dict:
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def assert_rejected(payload: dict) -> None:
    with pytest.raises(InvalidAnalysisError):
        validate_analysis(payload)


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
    analysis_by_category = {
        item["id"]: item["status"]
        for item in packet["analysis"]["categories"]
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
        "使用 3 倍杠杆",
    ],
)
def test_rejects_numeric_probability_and_trading_advice(forbidden_text: str) -> None:
    payload = load_analysis()
    payload["detailed"]["supporting"] = forbidden_text
    assert_rejected(payload)


def test_rejects_forbidden_advice_field_even_when_nested() -> None:
    payload = load_analysis()
    payload["detailed"]["extra"] = {"position": "50%"}
    assert_rejected(payload)
