"""Phase 0 contract tests for the v0.3.0 evidence catalogue.

These tests exercise the public catalogue seam.  They intentionally do not
inspect the implementation of the catalogue; the registry itself is the
source of truth that later data-quality and evidence-compilation phases will
consume.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ROLE_EXPORT_PATH = ROOT / "tests" / "fixtures" / "evidence" / "v0.3.0-role-registry.json"

from services.evidence.catalog import (  # noqa: E402
    INDICATOR_ROLE_REGISTRY,
    ROLE_VALUES,
    THEME_REGISTRY,
    canonical_id_for_snapshot_id,
    role_for,
    theme_for,
)


CANONICAL_IDS = {
    "mvrv",
    "aviv",
    "sth_mvrv_price",
    "psip",
    "sipl",
    "relative_unrealized_profit",
    "relative_unrealized_loss_zscore_4y",
    "realized_cap_relative_npc_30d",
    "asopr",
    "hodler_npc_30d",
    "spent_value_ge155d_share",
    "seller_exhaustion",
    "puell_multiple",
    "thermocap_multiple_zscore",
    "cvdd_proximity",
    "reserve_risk_zscore",
}


def test_registry_has_exactly_sixteen_canonical_indicators() -> None:
    registered_canonical = {
        entry["canonical_id"] for entry in INDICATOR_ROLE_REGISTRY.values()
    }
    assert registered_canonical == CANONICAL_IDS
    assert len(registered_canonical) == 16


def test_roles_have_the_confirmed_v03_distribution() -> None:
    by_role = {
        role: {
            entry["canonical_id"]
            for entry in INDICATOR_ROLE_REGISTRY.values()
            if entry["role"] == role
        }
        for role in ROLE_VALUES
    }

    assert set(ROLE_VALUES) == {
        "core_anchor",
        "core_confirmation",
        "strong_auxiliary",
        "auxiliary",
    }
    assert by_role["core_anchor"] == {"mvrv", "puell_multiple"}
    assert by_role["core_confirmation"] == {"aviv"}
    assert by_role["strong_auxiliary"] == {
        "relative_unrealized_loss_zscore_4y",
        "asopr",
        "seller_exhaustion",
        "cvdd_proximity",
    }
    assert len(by_role["auxiliary"]) == 9


def test_judgment_eligibility_is_separate_from_role() -> None:
    hodler = INDICATOR_ROLE_REGISTRY["hodler_npc_30d"]
    spent = INDICATOR_ROLE_REGISTRY["spent_value_ge155d_share"]
    cvdd = INDICATOR_ROLE_REGISTRY["cvdd_proximity"]

    assert hodler["judgment_status"] == "display_only"
    assert spent["judgment_status"] == "display_only"
    assert cvdd["judgment_status"] == "validation_pending"
    assert not hodler["eligible_for_judgment"]
    assert not spent["eligible_for_judgment"]
    assert not cvdd["eligible_for_judgment"]

    for metric_id, entry in INDICATOR_ROLE_REGISTRY.items():
        if entry["canonical_id"] not in {
            "hodler_npc_30d",
            "spent_value_ge155d_share",
            "cvdd_proximity",
        }:
            assert entry["judgment_status"] == "current", metric_id
            assert entry["eligible_for_judgment"] is True, metric_id


def test_canonical_and_display_ids_resolve_to_one_entry() -> None:
    assert canonical_id_for_snapshot_id("mvrv") == "mvrv"
    assert canonical_id_for_snapshot_id("sth-mvrv") == "sth_mvrv_price"
    assert canonical_id_for_snapshot_id("rul-z") == "relative_unrealized_loss_zscore_4y"
    assert canonical_id_for_snapshot_id("spent155") == "spent_value_ge155d_share"
    assert canonical_id_for_snapshot_id("hodler") == "hodler_npc_30d"

    for metric_id in CANONICAL_IDS:
        assert canonical_id_for_snapshot_id(metric_id) == metric_id

    with pytest.raises(KeyError):
        canonical_id_for_snapshot_id("not-a-dashboard-indicator")


def test_core_valuation_uses_one_theme_for_mvrv_and_aviv() -> None:
    assert role_for("mvrv") == "core_anchor"
    assert role_for("aviv") == "core_confirmation"
    assert theme_for("mvrv") == theme_for("aviv")
    valuation = THEME_REGISTRY[theme_for("mvrv")]
    assert set(valuation["indicator_ids"]) == {"mvrv", "aviv"}


def test_theme_registry_covers_each_canonical_indicator_once() -> None:
    themed_ids = [
        metric_id
        for theme in THEME_REGISTRY.values()
        for metric_id in theme["indicator_ids"]
    ]
    assert set(themed_ids) == CANONICAL_IDS
    assert len(themed_ids) == len(set(themed_ids)) == 16


def test_exported_role_evidence_matches_the_runtime_registry() -> None:
    payload = json.loads(ROLE_EXPORT_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "0.3.0"
    exported = {item["canonical_id"]: item for item in payload["indicators"]}
    assert set(exported) == CANONICAL_IDS
    for canonical_id, item in exported.items():
        runtime = INDICATOR_ROLE_REGISTRY[canonical_id]
        for field in ("display_id", "role", "judgment_status", "theme_id", "eligible_for_judgment"):
            assert item[field] == runtime[field], (canonical_id, field)
