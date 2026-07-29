from __future__ import annotations

from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def test_related_supply_metrics_share_one_correlation_family() -> None:
    brief = compile_evidence(make_snapshot(aux_values={"psip": 0.4, "sipl": 0.4, "rup": 0.4, "rul-z": 2.7}))
    family = next(item for item in brief["evidence_families"] if item["correlation_family"] == "supply_loss")
    assert set(family["metric_ids"]) >= {"psip", "sipl", "rup", "rul-z"}
    assert family["correlation_family"] == "supply_loss"
    assert "independent_count" not in family


def test_stale_metrics_are_visible_but_cvdd_is_current_support() -> None:
    brief = compile_evidence(make_snapshot(stale_ids={"hodler", "spent155"}))
    by_id = {item["id"]: item for item in brief["metric_states"]}
    assert by_id["hodler"]["status"] == "display_only"
    assert by_id["spent155"]["judgment_eligible"] is False
    assert by_id["cvdd"]["status"] == "current"
    assert by_id["cvdd"]["judgment_eligible"] is True
    assert by_id["hodler"]["triggered"] is None


def test_data_gap_is_not_written_as_no_pressure() -> None:
    brief = compile_evidence(make_snapshot(stale_ids={"mvrv"}))
    assert brief["axis_readiness"]["pressure"]["ready"] is False
    assert any(item["kind"] == "data_gap" for item in brief["contrary_or_gaps"])
    assert any("不能当作没有压力" in item["detail"] for item in brief["contrary_or_gaps"])
