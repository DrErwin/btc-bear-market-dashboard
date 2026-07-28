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


def assert_rejected(payload: dict) -> None:
    with pytest.raises(InvalidAnalysisError):
        validate_analysis(payload)


def test_current_offline_analysis_matches_the_ai_contract() -> None:
    normalized = validate_analysis(load_analysis())

    assert normalized["stage"] == "筑底证据积累期"
    assert normalized["consistency"] == "中等"
    assert {item["category"] for item in normalized["categories"]} == set(CATEGORY_IDS)
    assert normalized["supporting_evidence"]
    assert normalized["contrary_evidence"]
    assert normalized["next_stage_confirmation"]


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

