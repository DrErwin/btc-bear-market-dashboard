from __future__ import annotations

import copy

from services.ai.input_builder import build_evidence_input
from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def test_input_boundary_contains_dual_axis_facts_and_no_old_range() -> None:
    snapshot = make_snapshot(aux_values={"rul-z": 2.7, "asopr": 0.9, "seller": 0.04})
    brief = compile_evidence(snapshot)
    request = build_evidence_input(snapshot, evidence_brief=brief)
    assert request["contract_version"] == "0.4.0"
    assert set(request["axis_readiness"]) == {"pressure", "bottoming"}
    assert "allowed_stages" not in request
    assert "market_stage_definitions" not in request
    assert len(request["metric_states"]) == 16
    assert request["previous_three_days"] and len(request["previous_three_days"]) == 3


def test_input_has_actual_values_directions_and_stable_tier_ids() -> None:
    request = build_evidence_input(make_snapshot(mvrv=0.7, puell=0.4))
    mvrv = next(item for item in request["metric_states"] if item["id"] == "mvrv")
    assert mvrv["value"] == 0.7
    assert {item["direction"] for item in mvrv["thresholds"]} == {"below"}
    assert mvrv["tier"]["id"] == "deep_pressure"


def test_input_does_not_copy_history_or_private_action_provenance() -> None:
    snapshot = make_snapshot()
    snapshot["metrics"][0]["history"] = [{"date": "2026-07-01", "value": 0.5}]
    snapshot["metrics"][0]["private_action"] = "internal calibration"
    request = build_evidence_input(copy.deepcopy(snapshot))
    encoded = str(request)
    assert "2026-07-01" in encoded  # bounded timeline events are allowed
    assert "private_action" not in encoded
