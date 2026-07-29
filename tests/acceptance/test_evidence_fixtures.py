from __future__ import annotations

from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def test_fixed_success_fixture_covers_both_axis_readiness_results() -> None:
    brief = compile_evidence(make_snapshot(mvrv=0.7, puell=0.4, aviv=0.5, aux_values={"asopr": 0.9, "seller": 0.04}))
    assert brief["brief_version"] == "0.4.0"
    assert len(brief["metric_states"]) == 16
    assert brief["axis_readiness"]["pressure"]["ready"] is True
    assert brief["axis_readiness"]["bottoming"]["ready"] is True


def test_fixed_partial_fixtures_keep_the_other_axis_available() -> None:
    pressure_missing = compile_evidence(make_snapshot(stale_ids={"mvrv"}))
    bottoming_missing = compile_evidence(make_snapshot(stale_ids={"asopr"}))
    assert pressure_missing["axis_readiness"]["pressure"]["ready"] is False
    assert pressure_missing["axis_readiness"]["bottoming"]["ready"] is True
    assert bottoming_missing["axis_readiness"]["pressure"]["ready"] is True
    assert bottoming_missing["axis_readiness"]["bottoming"]["ready"] is False


def test_missing_timeline_marks_only_the_affected_axis_unready() -> None:
    brief = compile_evidence(make_snapshot(histories={"asopr": []}))
    assert brief["axis_readiness"]["bottoming"]["timeline_complete"] is False
    assert brief["axis_readiness"]["bottoming"]["ready"] is False
    assert brief["axis_readiness"]["pressure"]["ready"] is True
