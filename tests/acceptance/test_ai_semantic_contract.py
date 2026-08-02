from __future__ import annotations

import copy

import pytest

from services.ai import semantic_validator, validator
from services.ai.input_builder import build_evidence_input
from services.ai.provider import call_ai
from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def _current_context(snapshot: dict | None = None) -> tuple[dict, dict]:
    snapshot = snapshot or make_snapshot(mvrv=0.7, puell=0.4, aux_values={"asopr": 0.9, "seller": 0.04, "rc-npc": -0.1})
    brief = compile_evidence(snapshot)
    analysis, reason = call_ai(snapshot, data_date=snapshot["snapshot_date"], mock=True, evidence_brief=brief)
    assert reason is None and analysis is not None
    ai_input = build_evidence_input(snapshot, evidence_brief=brief)
    validator.validate_analysis(analysis)
    return copy.deepcopy(analysis), ai_input


def test_mock_analysis_passes_factual_semantic_validation() -> None:
    analysis, ai_input = _current_context()
    semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_untriggered_metric_in_support() -> None:
    analysis, ai_input = _current_context(make_snapshot(mvrv=1.1, puell=1.1))
    analysis["detailed"]["pressure_reason"] += " MVRV 已进入深度压力。"
    with pytest.raises(validator.InvalidAnalysisError, match="未触发"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_allows_threshold_direction_keywords() -> None:
    analysis, ai_input = _current_context()
    analysis["detailed"]["pressure_reason"] += " MVRV 并未高于或升入高位区，当前仍在低位。"
    semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_stale_metric_as_current_support() -> None:
    snapshot = make_snapshot(mvrv=0.7, puell=0.4, stale_ids={"rul-z"})
    analysis, ai_input = _current_context(snapshot)
    analysis["detailed"]["pressure_reason"] += " RUL z-score 显示当前压力已经极端。"
    with pytest.raises(validator.InvalidAnalysisError, match="不可用或过期"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_correlated_metrics_as_independent_votes() -> None:
    analysis, ai_input = _current_context()
    analysis["detailed"]["pressure_reason"] += " PSIP 和 SIPL 分别证明了两个独立压力。"
    with pytest.raises(validator.InvalidAnalysisError, match="相关性家族"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_invented_date() -> None:
    analysis, ai_input = _current_context()
    analysis["detailed"]["evidence_timeline"] += " 2020-01-01 已经持续。"
    with pytest.raises(validator.InvalidAnalysisError, match="日期"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_false_state_change() -> None:
    analysis, ai_input = _current_context()
    ai_input["previous_three_days"] = [{
        "date": "2026-07-27",
        "status": "current",
        "pressure_state": analysis["pressure_state"],
        "bottoming_state": analysis["bottoming_state"],
        "consistency": analysis["consistency"],
    }]
    analysis["state_changes"]["pressure"]["changed"] = True
    with pytest.raises(validator.InvalidAnalysisError, match="前三天"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_forces_unready_axis_to_data_insufficient() -> None:
    snapshot = make_snapshot(stale_ids={"asopr"})
    brief = compile_evidence(snapshot)
    analysis, reason = call_ai(snapshot, data_date=snapshot["snapshot_date"], mock=True, evidence_brief=brief)
    assert reason is None and analysis is not None
    ai_input = build_evidence_input(snapshot, evidence_brief=brief)
    analysis["bottoming_state"] = "已离开底部窗口"
    with pytest.raises(validator.InvalidAnalysisError, match="bottoming"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)
