from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from services.ai import provider, semantic_validator, validator
from services.ai.input_builder import build_ai_input
from tests.acceptance.analysis_fixture import build_valid_analysis


ROOT = Path(__file__).resolve().parents[2]
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"


def _current_context() -> tuple[dict, dict]:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    analysis = build_valid_analysis(packet)
    validator.validate_analysis(analysis)
    return analysis, build_ai_input(packet["snapshot"])


def test_semantic_validator_accepts_trigger_aligned_evidence() -> None:
    analysis, ai_input = _current_context()

    semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_untriggered_metric_in_support() -> None:
    analysis, ai_input = _current_context()
    analysis["detailed"]["supporting"] += (
        " RC-NPC 30d 为负，已实现资本仍在收缩。"
    )

    with pytest.raises(validator.InvalidAnalysisError, match="rc-npc"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_confirmation_without_any_trigger() -> None:
    analysis, ai_input = _current_context()
    analysis["categories"][0]["status"] = "充分确认"

    with pytest.raises(validator.InvalidAnalysisError, match="valuation"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_reversed_reserve_risk_meaning() -> None:
    analysis, ai_input = _current_context()
    analysis["summary"] = "长期持有信念进入周期低位区。"

    with pytest.raises(validator.InvalidAnalysisError, match="持有信念"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_semantic_validator_rejects_invented_hodler_zero_line_name() -> None:
    analysis, ai_input = _current_context()
    analysis["compact"]["obstacle"]["text"] = (
        "HODLer NPC 尚未触发积累/链上花费分界。"
    )

    with pytest.raises(validator.InvalidAnalysisError, match="长期供应净变化零线"):
        semantic_validator.validate_analysis_semantics(analysis, ai_input)


def test_real_provider_rewrites_semantically_invalid_output_once(
    monkeypatch,
) -> None:
    valid, _ = _current_context()
    invalid = copy.deepcopy(valid)
    invalid["detailed"]["supporting"] += " RC-NPC 30d 仍在收缩。"
    responses = [invalid, valid]
    feedback: list[str | None] = []

    def fake_chat(
        ai_input,
        data_date,
        api_key,
        base_url,
        model,
        validation_feedback=None,
    ):
        feedback.append(validation_feedback)
        return responses.pop(0)

    monkeypatch.setenv("AI_API_KEY", "test-only-key")
    monkeypatch.setattr(provider, "_chat", fake_chat)

    analysis, reason = provider.call_ai(
        json.loads(PACKET_PATH.read_text(encoding="utf-8"))["snapshot"],
        data_date=valid["analysis_date"],
        mock=False,
    )

    assert reason is None
    assert analysis == valid
    assert len(feedback) == 2
    assert feedback[0] is None
    assert feedback[1] is not None
    assert "rc-npc" in feedback[1]
