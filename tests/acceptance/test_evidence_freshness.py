from __future__ import annotations

from services.evidence.quality import (
    DISPLAY_ONLY,
    MISSING,
    VALIDATION_PENDING,
    evaluate_snapshot_quality,
)
from tests.acceptance.evidence_test_utils import clone_snapshot, make_snapshot


def test_stale_hodler_and_spent155_are_display_only_and_cvdd_is_pending() -> None:
    report = evaluate_snapshot_quality(
        make_snapshot(stale_ids={"hodler", "spent155"}),
        analysis_date="2026-07-28",
    )
    by_id = {item["id"]: item for item in report["metrics"]}

    assert by_id["hodler"]["status"] == DISPLAY_ONLY
    assert by_id["spent155"]["status"] == DISPLAY_ONLY
    assert by_id["cvdd"]["status"] == VALIDATION_PENDING
    assert by_id["hodler"]["judgment_eligible"] is False
    assert report["stage_ready"] is True


def test_stale_auxiliary_does_not_move_the_common_anchor_date() -> None:
    report = evaluate_snapshot_quality(
        make_snapshot(stale_ids={"psip"}),
        analysis_date="2026-07-28",
    )
    by_id = {item["id"]: item for item in report["metrics"]}
    assert by_id["psip"]["status"] == DISPLAY_ONLY
    assert report["common_anchor_date"] == "2026-07-28"
    assert report["stage_ready"] is True


def test_stale_critical_anchor_is_data_insufficient_not_untriggered() -> None:
    report = evaluate_snapshot_quality(
        make_snapshot(stale_ids={"mvrv"}),
        analysis_date="2026-07-28",
    )
    assert report["stage_ready"] is False
    assert report["critical_missing"] == ["mvrv"]
    assert next(item for item in report["metrics"] if item["id"] == "mvrv")["status"] == DISPLAY_ONLY


def test_non_numeric_value_is_missing() -> None:
    snapshot = clone_snapshot(make_snapshot())
    snapshot["metrics"][0]["current_value"] = None
    report = evaluate_snapshot_quality(snapshot, analysis_date="2026-07-28")
    assert report["stage_ready"] is False
    assert report["critical_missing"] == ["mvrv"]
    assert next(item for item in report["metrics"] if item["id"] == "mvrv")["status"] == MISSING
