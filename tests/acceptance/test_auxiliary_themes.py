from __future__ import annotations

from services.evidence.compiler import compile_evidence
from tests.acceptance.evidence_test_utils import make_snapshot


def test_related_supply_metrics_are_one_theme_not_two_votes() -> None:
    brief = compile_evidence(
        make_snapshot(
            aux_values={"psip": 40.0, "sipl": 40.0},
        )
    )
    supply_themes = [
        theme for theme in brief["auxiliary_themes"] + brief["strong_auxiliary_themes"]
        if any(metric_id in {"psip", "sipl"} for metric_id in theme["metric_ids"])
    ]
    assert len(supply_themes) == 1
    assert {"psip", "sipl"}.issubset(set(supply_themes[0]["metric_ids"]))


def test_strong_auxiliary_evidence_is_kept_for_explanation() -> None:
    brief = compile_evidence(
        make_snapshot(
            aux_values={"rul-z": 2.6, "asopr": 0.9, "seller": 0.05, "cvdd": 0.8},
        )
    )
    assert len(brief["strong_auxiliary_themes"]) >= 2
    assert all(theme["strength"] == "strong" for theme in brief["strong_auxiliary_themes"])
    assert all("cvdd" not in theme["metric_ids"] for theme in brief["strong_auxiliary_themes"])


def test_display_only_and_pending_metrics_never_enter_theme_conclusions() -> None:
    brief = compile_evidence(
        make_snapshot(
            stale_ids={"hodler", "spent155"},
            aux_values={"cvdd": 0.8},
        )
    )
    all_themes = brief["auxiliary_themes"] + brief["strong_auxiliary_themes"]
    all_metric_ids = {metric_id for theme in all_themes for metric_id in theme["metric_ids"]}
    assert "hodler" not in all_metric_ids
    assert "spent155" not in all_metric_ids
    assert "cvdd" not in all_metric_ids


def test_stale_auxiliary_metric_is_a_data_limit_not_contrary_evidence() -> None:
    brief = compile_evidence(make_snapshot(stale_ids={"psip"}))
    limits = [item for item in brief["contrary_or_incomplete"] if item["kind"] == "data_limit"]
    psip_limits = [item for item in limits if "psip" in item["metric_ids"]]
    assert psip_limits
    assert "不作为反面证据" in psip_limits[0]["detail"]
