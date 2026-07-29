from __future__ import annotations

from services.evidence.quality import DISPLAY_ONLY, VALIDATION_PENDING, evaluate_snapshot_quality
from tests.acceptance.evidence_test_utils import clone_snapshot, make_snapshot


def test_stale_and_pending_statuses_are_distinct() -> None:
    report = evaluate_snapshot_quality(make_snapshot(stale_ids={"hodler", "spent155"}), analysis_date="2026-07-28")
    by_id = {item["id"]: item for item in report["metrics"]}
    assert by_id["hodler"]["status"] == DISPLAY_ONLY
    assert by_id["spent155"]["status"] == DISPLAY_ONLY
    assert by_id["cvdd"]["status"] == VALIDATION_PENDING
    assert report["axis_readiness"]["pressure"]["ready"] is True


def test_stale_pressure_anchor_only_blocks_pressure_axis() -> None:
    report = evaluate_snapshot_quality(make_snapshot(stale_ids={"mvrv"}), analysis_date="2026-07-28")
    assert report["axis_readiness"]["pressure"]["ready"] is False
    assert report["axis_readiness"]["bottoming"]["ready"] is True


def test_non_numeric_value_is_missing_for_its_axis() -> None:
    snapshot = clone_snapshot(make_snapshot())
    snapshot["metrics"][0]["current_value"] = None
    report = evaluate_snapshot_quality(snapshot, analysis_date="2026-07-28")
    assert report["axis_readiness"]["pressure"]["ready"] is False
