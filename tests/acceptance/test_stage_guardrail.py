from __future__ import annotations

from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def test_brief_contains_facts_but_no_machine_stage_range_or_score() -> None:
    brief = compile_evidence(make_snapshot(mvrv=0.7, puell=0.4))
    assert "allowed_stages" not in brief
    assert "pressure_state" not in brief
    assert "bottoming_state" not in brief
    assert "score" not in brief
