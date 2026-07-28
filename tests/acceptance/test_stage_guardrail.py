from __future__ import annotations

from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def test_auxiliary_pressure_cannot_expand_core_stage_range() -> None:
    baseline = compile_evidence(make_snapshot(mvrv=0.9, puell=1.1))
    pressure = compile_evidence(
        make_snapshot(
            mvrv=0.9,
            puell=1.1,
            aux_values={"rul-z": 2.8, "asopr": 0.8, "seller": 0.03},
        )
    )
    assert pressure["allowed_stages"] == baseline["allowed_stages"] == ["熊市下行期"]
    assert pressure["strong_auxiliary_themes"]


def test_data_insufficient_is_a_separate_system_state() -> None:
    brief = compile_evidence(make_snapshot(stale_ids={"puell"}))
    assert brief["allowed_stages"] == ["数据不足"]
    assert brief["next_stage_conditions"]
    assert brief["data_quality"]["stage_ready"] is False
