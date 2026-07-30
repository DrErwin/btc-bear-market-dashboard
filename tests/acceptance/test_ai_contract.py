from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from services.ai import provider
from services.ai.contract import CATEGORY_STATUS_VALUES
from services.ai.validator import InvalidAnalysisError, validate_analysis


ROOT = Path(__file__).resolve().parents[2]


def load_analysis() -> dict:
    packet = json.loads((ROOT / "dashboard" / "public" / "data" / "packet.json").read_text(encoding="utf-8"))
    return copy.deepcopy(packet["analysis"] or packet["fallback"])


def test_current_offline_analysis_matches_v04_contract() -> None:
    normalized = validate_analysis(load_analysis())
    assert normalized["pressure_state"] in {"压力尚未明显", "进入观察", "深度压力", "极端压力", "数据不足"}
    assert normalized["bottoming_state"] in {"未见筑底结构", "筑底线索出现", "筑底证据聚合", "筑底证据较完整", "市场修复中", "已离开底部窗口", "数据不足"}
    assert "stage" not in normalized
    assert set(normalized["detailed"]) == {
        "pressure_reason",
        "bottoming_reason",
        "evidence_timeline",
        "contrary_or_gaps",
        "repair_exit",
        "next_evidence",
    }


@pytest.mark.parametrize("field,value", [("pressure_state", "未知压力"), ("bottoming_state", "未知筑底")])
def test_rejects_unknown_axis_state(field: str, value: str) -> None:
    payload = load_analysis()
    payload[field] = value
    with pytest.raises(InvalidAnalysisError):
        validate_analysis(payload)


def test_both_axes_insufficient_require_empty_consistency() -> None:
    payload = load_analysis()
    payload["pressure_state"] = "数据不足"
    payload["bottoming_state"] = "数据不足"
    payload["consistency"] = "弱"
    with pytest.raises(InvalidAnalysisError, match="consistency"):
        validate_analysis(payload)


@pytest.mark.parametrize("detail_field", [
    "pressure_reason",
    "bottoming_reason",
    "evidence_timeline",
    "contrary_or_gaps",
    "repair_exit",
    "next_evidence",
])
def test_rejects_missing_required_detail(detail_field: str) -> None:
    payload = load_analysis()
    del payload["detailed"][detail_field]
    with pytest.raises(InvalidAnalysisError, match=detail_field):
        validate_analysis(payload)


@pytest.mark.parametrize("text", ["建议买入", "应该卖出", "当前概率为 80%", "把它当作独立投票"])
def test_rejects_public_action_or_rule_language(text: str) -> None:
    payload = load_analysis()
    payload["summary"] = text
    with pytest.raises(InvalidAnalysisError):
        validate_analysis(payload)


def test_allows_observational_loss_selling_language() -> None:
    payload = load_analysis()
    payload["detailed"]["contrary_or_gaps"] = "链上亏损卖出仍然存在，但这里只描述市场现象。"
    validate_analysis(payload)


def test_rejects_old_single_stage_shape() -> None:
    payload = load_analysis()
    payload["stage"] = "熊市下行期"
    with pytest.raises(InvalidAnalysisError, match="stage"):
        validate_analysis(payload)


def test_requires_per_axis_state_changes() -> None:
    payload = load_analysis()
    del payload["state_changes"]
    with pytest.raises(InvalidAnalysisError, match="state_changes"):
        validate_analysis(payload)


@pytest.mark.parametrize("validation_feedback", [None, "categories[1] 使用未知状态: 修复中"])
def test_daily_prompt_lists_every_allowed_category_status(validation_feedback: str | None) -> None:
    prompt = provider._user_prompt({}, "2026-07-30", validation_feedback)
    assert "分类状态只能从" in prompt
    assert all(status in prompt for status in CATEGORY_STATUS_VALUES)
