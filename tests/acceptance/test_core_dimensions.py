from __future__ import annotations

import pytest

from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


@pytest.mark.parametrize(
    ("mvrv", "puell", "aviv", "expected"),
    [
        (1.1, 1.1, 0.8, ["尚未进入熊底观察期"]),
        (0.9, 1.1, 0.8, ["熊市下行期"]),
        (1.1, 0.55, 0.8, ["熊市下行期"]),
        (0.9, 0.55, 0.8, ["熊市下行期", "深度压力期"]),
        (0.7, 1.1, 0.8, ["熊市下行期", "深度压力期"]),
        (0.7, 0.55, 0.8, ["深度压力期", "筑底证据积累期"]),
        (0.7, 0.4, 0.6, ["深度压力期", "筑底证据积累期"]),
        (0.7, 0.4, 0.5, ["筑底证据积累期", "熊底证据充分期"]),
    ],
)
def test_core_dimensions_generate_the_stage_guardrail(mvrv, puell, aviv, expected) -> None:
    brief = compile_evidence(make_snapshot(mvrv=mvrv, puell=puell, aviv=aviv))
    assert brief["allowed_stages"] == expected
    assert brief["core_dimensions"]["valuation"]["vote"] == "valuation"
    assert brief["core_dimensions"]["miners"]["vote"] == "miners"


def test_aviv_is_confirmation_not_a_second_valuation_vote() -> None:
    brief = compile_evidence(make_snapshot(mvrv=1.1, puell=1.1, aviv=0.5))
    assert brief["allowed_stages"] == ["尚未进入熊底观察期"]
    assert brief["core_dimensions"]["valuation"]["state"] == "none"
    assert brief["core_dimensions"]["valuation"]["confirmation"]["state"] == "deep"
