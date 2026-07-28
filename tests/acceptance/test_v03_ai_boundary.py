from __future__ import annotations

import copy
import json

import pytest

from services.ai import semantic_validator, validator
from services.ai.input_builder import build_evidence_input
from services.ai.provider import call_ai
from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def test_v03_ai_input_is_an_evidence_brief_not_a_definition_dump() -> None:
    snapshot = make_snapshot(
        stale_ids={"hodler", "spent155"},
        aux_values={"rul-z": 2.7, "asopr": 0.9, "seller": 0.05},
    )
    brief = compile_evidence(snapshot)
    request = build_evidence_input(snapshot, evidence_brief=brief)

    assert request["input_version"] == "0.3.0"
    assert request["allowed_stages"]
    assert request["core_dimensions"]["valuation"]["vote"] == "valuation"
    assert request["strong_auxiliary_themes"]
    assert len(request["metric_states"]) == 16
    by_id = {state["id"]: state for state in request["metric_states"]}
    assert set(by_id["asopr"]) == {
        "id",
        "name",
        "importance",
        "value",
        "date",
        "status",
        "thresholds",
        "threshold_summary",
        "evidence_use",
    }
    assert by_id["asopr"]["importance"].startswith("强辅助")
    assert by_id["asopr"]["value"] == 0.9
    assert by_id["asopr"]["date"] == "2026-07-28"
    assert by_id["asopr"]["status"] == "当前可用，可参与判断"
    assert by_id["asopr"]["thresholds"] == [
        {
            "rule": "< 1.0",
            "name": "观察线",
            "meaning": "辅助压力",
            "triggered": True,
        }
    ]
    assert "观察线" in by_id["asopr"]["threshold_summary"]
    assert by_id["asopr"]["evidence_use"]

    assert by_id["hodler"]["status"] == "仅供展示，不参与判断"
    assert all(
        threshold["triggered"] is None
        for threshold in by_id["hodler"]["thresholds"]
    )
    assert "不进行阈值判断" in by_id["hodler"]["threshold_summary"]

    assert by_id["cvdd"]["status"] == "待验证，不参与判断"
    assert all(
        threshold["triggered"] is None
        for threshold in by_id["cvdd"]["thresholds"]
    )
    keys = {key.casefold() for key in _walk_keys(request)}
    assert {"series", "formula", "source", "method", "caveat", "price"}.isdisjoint(keys)


def test_validator_can_enforce_machine_stage_range_and_pressure_summary() -> None:
    payload = {
        "stage": "筑底证据积累期",
        "consistency": "中等",
        "summary": "估值与矿工压力共同限定当前阶段，辅助证据说明压力较重。",
        "pressure_summary": "辅助压力较重，但没有越过核心上限。",
        "core_support": "估值与矿工压力形成共同支持。",
        "main_obstacle": "AVIV 尚未深度复核。",
        "next_stage_condition": "等待 AVIV 深度复核。",
        "categories": [{"category": category, "status": "未确认"} for category in ("valuation", "supply", "capital", "holders", "miners", "anchors")],
        "supporting_evidence": "核心维度共同支持当前范围。",
        "contrary_evidence": "仍有未完成复核。",
        "next_stage_confirmation": "满足下一阶段条件后再上移。",
    }
    with pytest.raises(validator.InvalidAnalysisError, match="超出机器允许范围"):
        validator.validate_analysis(payload, allowed_stages=["熊市下行期"], require_pressure_summary=True)
    normalized = validator.validate_analysis(
        {**payload, "stage": "熊市下行期"},
        allowed_stages=["熊市下行期"],
        require_pressure_summary=True,
    )
    assert normalized["pressure_summary"]


def test_semantic_validator_requires_pressure_summary_for_strong_auxiliary() -> None:
    snapshot = make_snapshot(aux_values={"rul-z": 2.7, "asopr": 0.9, "seller": 0.05})
    brief = compile_evidence(snapshot)
    request = build_evidence_input(snapshot, evidence_brief=brief)
    payload = {
        "stage": brief["allowed_stages"][0],
        "consistency": "中等",
        "summary": "估值和矿工压力共同限定当前范围。",
        "pressure_summary": "",
        "core_support": "核心维度限定了范围。",
        "main_obstacle": "仍有未完成条件。",
        "next_stage_condition": "等待核心条件。",
        "categories": [{"category": category, "status": "未确认"} for category in ("valuation", "supply", "capital", "holders", "miners", "anchors")],
        "supporting_evidence": "核心证据共同支持当前范围。",
        "contrary_evidence": "辅助证据虽强但不能抬高阶段。",
        "next_stage_confirmation": "等待下一阶段条件。",
    }
    with pytest.raises(validator.InvalidAnalysisError, match="阶段内部压力"):
        semantic_validator.validate_analysis_semantics(payload, request)


def test_mock_provider_selects_only_from_compiled_range() -> None:
    snapshot = make_snapshot(mvrv=0.7, puell=0.4, aviv=0.5, aux_values={"rul-z": 2.7, "asopr": 0.9, "seller": 0.05})
    brief = compile_evidence(snapshot)
    analysis, reason = call_ai(snapshot, data_date="2026-07-28", mock=True)
    assert reason is None
    assert analysis is not None
    assert analysis["stage"] in brief["allowed_stages"]
    assert analysis["pressure_summary"]
    visible_text = json.dumps(analysis, ensure_ascii=False)
    assert "链上亏损卖出增多" in visible_text
    for internal_term in validator.INTERNAL_OUTPUT_TERMS:
        assert internal_term not in visible_text
