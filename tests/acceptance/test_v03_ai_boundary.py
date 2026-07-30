from __future__ import annotations

from services.ai.input_builder import build_evidence_input
from services.ai.provider import call_ai
from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def test_v04_boundary_replaces_old_single_stage_boundary() -> None:
    snapshot = make_snapshot(aux_values={"rul-z": 2.7, "asopr": 0.9, "seller": 0.05})
    brief = compile_evidence(snapshot)
    request = build_evidence_input(snapshot, evidence_brief=brief)
    assert request["contract_version"] == "0.4.0"
    assert "allowed_stages" not in request
    assert "pressure_state" not in brief
    assert "bottoming_state" not in brief
    assert request["instructions"]["support_only_triggered_metrics"] is True
    assert request["instructions"]["untriggered_metrics_only_as_gaps"] is True


def test_missing_metric_is_explicit_and_not_zero() -> None:
    snapshot = make_snapshot()
    next(metric for metric in snapshot["metrics"] if metric["id"] == "mvrv")["current_value"] = None
    brief = compile_evidence(snapshot)
    request = build_evidence_input(snapshot, evidence_brief=brief)
    mvrv = next(metric for metric in request["metric_states"] if metric["id"] == "mvrv")
    assert mvrv["value"] is None
    assert mvrv["status"] == "missing"
    assert brief["axis_readiness"]["pressure"]["ready"] is False


def test_untriggered_metric_is_explicitly_ineligible_for_support_text() -> None:
    snapshot = make_snapshot(mvrv=1.2)
    brief = compile_evidence(snapshot)
    request = build_evidence_input(snapshot, evidence_brief=brief)
    mvrv = next(metric for metric in request["metric_states"] if metric["id"] == "mvrv")
    assert mvrv["tier"]["id"] == "none"
    assert mvrv["support_eligible"] is False


def test_mock_judgement_selects_both_axes_from_fixed_vocabularies() -> None:
    snapshot = make_snapshot(mvrv=0.7, puell=0.4, aviv=0.5)
    analysis, reason = call_ai(snapshot, data_date=snapshot["snapshot_date"], mock=True)
    assert reason is None
    assert analysis["pressure_state"] in {"压力尚未明显", "进入观察", "深度压力", "极端压力", "数据不足"}
    assert analysis["bottoming_state"] in {"未见筑底结构", "筑底线索出现", "筑底证据聚合", "筑底证据较完整", "市场修复中", "已离开底部窗口", "数据不足"}
