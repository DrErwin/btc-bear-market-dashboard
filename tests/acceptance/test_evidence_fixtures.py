"""Phase 0 fixed evidence scenarios.

The scenarios are deliberately offline JSON.  They are inputs for later
freshness, evidence-compilation, and stage-guardrail tests; this test only
checks that every scenario is complete and uses the v0.3.0 catalogue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.evidence.catalog import (  # noqa: E402
    INDICATOR_ROLE_REGISTRY,
    canonical_id_for_snapshot_id,
)


FIXTURE_PATH = ROOT / "tests" / "fixtures" / "evidence" / "v0.3.0-scenarios.json"
EXPECTED_SCENARIO_IDS = {
    "both_core_none",
    "valuation_watch_only",
    "miner_watch_only",
    "both_core_watch",
    "valuation_deep_miner_watch",
    "both_deep_aviv_unconfirmed",
    "both_deep_aviv_deep",
    "strong_auxiliary_pressure",
    "stale_core_anchor",
    "stale_auxiliary",
}
VALID_JUDGMENT_STATUSES = {
    "current",
    "display_only",
    "validation_pending",
    "missing",
}
VALID_THRESHOLD_STATES = {"none", "watch", "deep", "strong", "neutral", "unknown"}
VALID_ALLOWED_STAGES = {
    "尚未进入熊底观察期",
    "熊市下行期",
    "深度压力期",
    "筑底证据积累期",
    "熊底证据充分期",
    "数据不足",
}


@pytest.fixture(scope="module")
def scenarios() -> list[dict]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "0.3.0"
    templates = payload["metric_templates"]
    materialised: list[dict] = []
    for raw_scenario in payload["scenarios"]:
        metrics = {
            metric_id: dict(template)
            for metric_id, template in templates.items()
        }
        for metric_id, override in raw_scenario.get("metric_overrides", {}).items():
            metrics[metric_id].update(override)
        materialised.append(
            {
                **raw_scenario,
                "analysis_date": payload["analysis_date"],
                "snapshot_date": payload["analysis_date"],
                "metrics": metrics,
            }
        )
    return materialised


def test_fixture_catalogue_contains_the_ten_confirmed_scenarios(scenarios: list[dict]) -> None:
    assert {scenario["id"] for scenario in scenarios} == EXPECTED_SCENARIO_IDS
    assert len(scenarios) == 10


def test_each_scenario_has_sixteen_complete_metric_facts(scenarios: list[dict]) -> None:
    canonical_ids = {
        entry["canonical_id"] for entry in INDICATOR_ROLE_REGISTRY.values()
    }
    for scenario in scenarios:
        assert scenario["analysis_date"] == "2026-07-28"
        assert scenario["snapshot_date"] == "2026-07-28"
        assert scenario["metrics"].keys() == canonical_ids
        assert scenario["expected_allowed_stages"]
        assert set(scenario["expected_allowed_stages"]).issubset(VALID_ALLOWED_STAGES)
        assert isinstance(scenario["ai_call"], bool)

        for snapshot_id, metric in scenario["metrics"].items():
            assert canonical_id_for_snapshot_id(snapshot_id) == snapshot_id
            assert metric["metric_date"]
            assert metric["judgment_status"] in VALID_JUDGMENT_STATUSES
            assert metric["threshold_state"] in VALID_THRESHOLD_STATES
            assert isinstance(metric["eligible_for_judgment"], bool)


def test_fixed_status_exclusions_are_present_in_every_scenario(scenarios: list[dict]) -> None:
    for scenario in scenarios:
        metrics = scenario["metrics"]
        assert metrics["hodler_npc_30d"]["judgment_status"] == "display_only"
        assert metrics["spent_value_ge155d_share"]["judgment_status"] == "display_only"
        assert metrics["cvdd_proximity"]["judgment_status"] == "validation_pending"
        assert all(
            not metrics[metric_id]["eligible_for_judgment"]
            for metric_id in (
                "hodler_npc_30d",
                "spent_value_ge155d_share",
                "cvdd_proximity",
            )
        )


def test_core_stale_fixture_blocks_ai_but_auxiliary_stale_fixture_does_not(
    scenarios: list[dict],
) -> None:
    by_id = {scenario["id"]: scenario for scenario in scenarios}
    assert by_id["stale_core_anchor"]["ai_call"] is False
    assert by_id["stale_core_anchor"]["expected_allowed_stages"] == ["数据不足"]
    assert by_id["stale_auxiliary"]["ai_call"] is True
    assert by_id["stale_auxiliary"]["expected_allowed_stages"] == ["熊市下行期"]


def test_strong_auxiliary_fixture_is_separate_from_core_stage_fixture(
    scenarios: list[dict],
) -> None:
    by_id = {scenario["id"]: scenario for scenario in scenarios}
    pressure = by_id["strong_auxiliary_pressure"]
    assert pressure["expected_allowed_stages"] == ["熊市下行期", "深度压力期"]
    assert pressure["strong_auxiliary_themes"]
    assert set(pressure["strong_auxiliary_themes"]).isdisjoint(
        by_id["both_core_watch"]["strong_auxiliary_themes"]
    )
