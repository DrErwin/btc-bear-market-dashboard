from __future__ import annotations

from services.evidence.catalog import (
    CANONICAL_INDICATOR_IDS,
    INDICATOR_ROLE_REGISTRY,
    correlation_family_for,
    responsibility_for,
)


def test_all_sixteen_indicators_have_one_primary_responsibility_and_family() -> None:
    assert len(CANONICAL_INDICATOR_IDS) == 16
    for metric_id in CANONICAL_INDICATOR_IDS:
        entry = INDICATOR_ROLE_REGISTRY[metric_id]
        assert entry["primary_responsibility"]
        assert entry["correlation_family"]
        assert entry["axis_relevance"]
        assert responsibility_for(metric_id) == entry["primary_responsibility"]
        assert correlation_family_for(metric_id) == entry["correlation_family"]


def test_alias_and_canonical_id_resolve_to_same_role_facts() -> None:
    assert correlation_family_for("mvrv") == correlation_family_for("mvrv")
    assert responsibility_for("puell") == responsibility_for("puell_multiple")
