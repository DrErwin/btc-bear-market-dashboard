from __future__ import annotations

import pytest

from services.ai.provider import call_ai
from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


@pytest.mark.parametrize("stale,axis,expected", [
    ({"mvrv"}, "pressure", False),
    ({"puell"}, "pressure", False),
    ({"asopr"}, "bottoming", False),
])
def test_axis_readiness_is_independent(stale: set[str], axis: str, expected: bool) -> None:
    brief = compile_evidence(make_snapshot(stale_ids=stale))
    assert brief["axis_readiness"][axis]["ready"] is expected
    other = "bottoming" if axis == "pressure" else "pressure"
    assert brief["axis_readiness"][other]["ready"] is True


def test_one_extreme_anchor_does_not_become_machine_overall_state() -> None:
    snapshot = make_snapshot(mvrv=0.7, puell=1.1)
    brief = compile_evidence(snapshot)
    assert "pressure_state" not in brief
    analysis, reason = call_ai(snapshot, data_date=snapshot["snapshot_date"], mock=True, evidence_brief=brief)
    assert reason is None
    assert analysis["pressure_state"] in {"进入观察", "深度压力"}


def test_aviv_stays_in_same_valuation_family_as_mvrv() -> None:
    brief = compile_evidence(make_snapshot(mvrv=0.7, aviv=0.5))
    family = next(item for item in brief["evidence_families"] if item["correlation_family"] == "valuation")
    assert set(family["metric_ids"]) >= {"mvrv", "aviv"}
