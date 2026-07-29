"""Stable v0.4 indicator roles, eligibility, and evidence families.

The dashboard has one visible catalogue of sixteen indicators, but a visible
card is not automatically a vote in either market-state axis.  This module
is the small, dependency-free registry shared by the data-quality gate,
evidence compiler, AI input builder, and frontend adapters.

``canonical_id`` is the identifier used by the computation pipeline.  The
``display_id`` is the identifier used by the public packet/series layer.  Both
forms are accepted by the lookup functions and both forms are keys in
``INDICATOR_ROLE_REGISTRY``.  Registry entries are plain dictionaries on
purpose: they can be serialised to the review evidence JSON without a custom
encoder.
"""

from __future__ import annotations

from typing import Final


# Stable internal vocabulary.  Chinese labels live alongside these tokens so
# that UI text does not become an API contract.
ROLE_VALUES: Final[tuple[str, ...]] = (
    "core_anchor",
    "core_confirmation",
    "strong_auxiliary",
    "auxiliary",
)

JUDGMENT_STATUS_VALUES: Final[tuple[str, ...]] = (
    "current",
    "display_only",
    "validation_pending",
    "missing",
)

ROLE_LABELS: Final[dict[str, str]] = {
    "core_anchor": "核心锚",
    "core_confirmation": "核心复核",
    "strong_auxiliary": "强辅助",
    "auxiliary": "辅助",
}

JUDGMENT_STATUS_LABELS: Final[dict[str, str]] = {
    "current": "当前可用",
    "display_only": "仅供展示",
    "validation_pending": "待验证",
    "missing": "缺失",
}


# Canonical catalogue order follows services.data.metrics.INDICATOR_CATALOG.
# ``theme_id`` values are deliberately stable English ids; their Chinese
# labels are presentation copy and can evolve without changing the compiler.
_INDICATOR_DEFINITIONS: Final[tuple[dict[str, object], ...]] = (
    {
        "canonical_id": "mvrv",
        "display_id": "mvrv",
        "label": "MVRV",
        "role": "core_anchor",
        "judgment_status": "current",
        "theme_id": "valuation",
    },
    {
        "canonical_id": "aviv",
        "display_id": "aviv",
        "label": "AVIV",
        "role": "core_confirmation",
        "judgment_status": "current",
        "theme_id": "valuation",
    },
    {
        "canonical_id": "sth_mvrv_price",
        "display_id": "sth-mvrv",
        "label": "STH-MVRV 战术价位",
        "role": "auxiliary",
        "judgment_status": "current",
        "theme_id": "recovery_absorption",
    },
    {
        "canonical_id": "psip",
        "display_id": "psip",
        "label": "PSIP",
        "role": "auxiliary",
        "judgment_status": "current",
        "theme_id": "supply_loss",
    },
    {
        "canonical_id": "sipl",
        "display_id": "sipl",
        "label": "SIPL",
        "role": "auxiliary",
        "judgment_status": "current",
        "theme_id": "supply_loss",
    },
    {
        "canonical_id": "relative_unrealized_profit",
        "display_id": "rup",
        "label": "Relative Unrealized Profit",
        "role": "auxiliary",
        "judgment_status": "current",
        "theme_id": "supply_loss",
    },
    {
        "canonical_id": "relative_unrealized_loss_zscore_4y",
        "display_id": "rul-z",
        "label": "RUL · 4年 z-score",
        "role": "strong_auxiliary",
        "judgment_status": "current",
        "theme_id": "supply_loss",
    },
    {
        "canonical_id": "realized_cap_relative_npc_30d",
        "display_id": "rc-npc",
        "label": "Realized Cap Relative NPC · 30d",
        "role": "auxiliary",
        "judgment_status": "current",
        "theme_id": "recovery_absorption",
    },
    {
        "canonical_id": "asopr",
        "display_id": "asopr",
        "label": "aSOPR",
        "role": "strong_auxiliary",
        "judgment_status": "current",
        "theme_id": "realized_loss",
    },
    {
        "canonical_id": "hodler_npc_30d",
        "display_id": "hodler",
        "label": "HODLer NPC · 30d",
        "role": "auxiliary",
        "judgment_status": "display_only",
        "theme_id": "holder_behavior",
    },
    {
        "canonical_id": "spent_value_ge155d_share",
        "display_id": "spent155",
        "label": "≥155d 花费价值占比",
        "role": "auxiliary",
        "judgment_status": "display_only",
        "theme_id": "holder_behavior",
    },
    {
        "canonical_id": "seller_exhaustion",
        "display_id": "seller",
        "label": "Seller Exhaustion Constant",
        "role": "strong_auxiliary",
        "judgment_status": "current",
        "theme_id": "seller_exhaustion",
    },
    {
        "canonical_id": "puell_multiple",
        "display_id": "puell",
        "label": "Puell Multiple",
        "role": "core_anchor",
        "judgment_status": "current",
        "theme_id": "miner_pressure",
    },
    {
        "canonical_id": "thermocap_multiple_zscore",
        "display_id": "thermo",
        "label": "Thermocap Multiple · 周期 z",
        "role": "auxiliary",
        "judgment_status": "current",
        "theme_id": "miner_pressure",
    },
    {
        "canonical_id": "cvdd_proximity",
        "display_id": "cvdd",
        "label": "CVDD 接近程度",
        "role": "strong_auxiliary",
        "judgment_status": "current",
        "theme_id": "long_term_anchor",
    },
    {
        "canonical_id": "reserve_risk_zscore",
        "display_id": "reserve",
        "label": "Reserve Risk · 周期",
        "role": "auxiliary",
        "judgment_status": "current",
        "theme_id": "long_term_anchor",
    },
)


# Themes are groups of related facts, not independent votes.  The registry
# contains canonical ids only; callers can use theme_for() for aliases.
THEME_REGISTRY: Final[dict[str, dict[str, object]]] = {
    "valuation": {
        "theme_id": "valuation",
        "label": "估值维度",
        "description": "MVRV 与 AVIV 共同观察全市场估值压力；AVIV 只做复核。",
        "indicator_ids": ("mvrv", "aviv"),
        "role": "core",
    },
    "supply_loss": {
        "theme_id": "supply_loss",
        "label": "供应亏损范围",
        "description": "把供应盈利/亏损与未实现亏损深度合并成一组证据。",
        "indicator_ids": (
            "psip",
            "sipl",
            "relative_unrealized_profit",
            "relative_unrealized_loss_zscore_4y",
        ),
        "role": "auxiliary",
    },
    "realized_loss": {
        "theme_id": "realized_loss",
        "label": "已实现亏损与投降",
        "description": "观察链上花费者是否正在亏损卖出。",
        "indicator_ids": ("asopr",),
        "role": "auxiliary",
    },
    "seller_exhaustion": {
        "theme_id": "seller_exhaustion",
        "label": "卖方耗竭",
        "description": "观察卖方压力是否接近耗竭区。",
        "indicator_ids": ("seller_exhaustion",),
        "role": "auxiliary",
    },
    "recovery_absorption": {
        "theme_id": "recovery_absorption",
        "label": "恢复与承接",
        "description": "观察短期持有者成本和已实现资本是否出现恢复。",
        "indicator_ids": ("sth_mvrv_price", "realized_cap_relative_npc_30d"),
        "role": "auxiliary",
    },
    "holder_behavior": {
        "theme_id": "holder_behavior",
        "label": "持有者行为",
        "description": "观察长期持有者相关供应变化和老币花费背景。",
        "indicator_ids": ("hodler_npc_30d", "spent_value_ge155d_share"),
        "role": "auxiliary",
    },
    "miner_pressure": {
        "theme_id": "miner_pressure",
        "label": "矿工压力",
        "description": "Puell 是矿工压力核心锚，Thermocap 提供背景补充。",
        "indicator_ids": ("puell_multiple", "thermocap_multiple_zscore"),
        "role": "core",
    },
    "long_term_anchor": {
        "theme_id": "long_term_anchor",
        "label": "长期成本与持币信念",
        "description": "观察 CVDD 成本锚和 Reserve Risk 长期信念背景。",
        "indicator_ids": ("cvdd_proximity", "reserve_risk_zscore"),
        "role": "auxiliary",
    },
}


# v0.4 facts for the AI boundary.  They describe what a metric is useful for;
# they do not tell the model which axis state to select.  One metric has one
# primary responsibility and one correlation family, so related cards cannot
# silently become several independent votes.
_RESPONSIBILITY_BY_ID: Final[dict[str, dict[str, object]]] = {
    "mvrv": {"primary_responsibility": "pressure_anchor", "axis_relevance": ("pressure", "bottoming"), "correlation_family": "valuation"},
    "aviv": {"primary_responsibility": "pressure_confirmation", "axis_relevance": ("pressure", "bottoming"), "correlation_family": "valuation"},
    "sth_mvrv_price": {"primary_responsibility": "repair_signal", "axis_relevance": ("bottoming",), "correlation_family": "short_term_cost"},
    "psip": {"primary_responsibility": "pressure_context", "axis_relevance": ("pressure", "bottoming"), "correlation_family": "supply_loss"},
    "sipl": {"primary_responsibility": "pressure_context", "axis_relevance": ("pressure",), "correlation_family": "supply_loss"},
    "relative_unrealized_profit": {"primary_responsibility": "pressure_context", "axis_relevance": ("pressure", "bottoming"), "correlation_family": "supply_loss"},
    "relative_unrealized_loss_zscore_4y": {"primary_responsibility": "pressure_severity", "axis_relevance": ("pressure", "bottoming"), "correlation_family": "supply_loss"},
    "realized_cap_relative_npc_30d": {"primary_responsibility": "repair_signal", "axis_relevance": ("bottoming",), "correlation_family": "realized_capital"},
    "asopr": {"primary_responsibility": "capitulation_clue", "axis_relevance": ("pressure", "bottoming"), "correlation_family": "realized_loss"},
    "hodler_npc_30d": {"primary_responsibility": "capitulation_context", "axis_relevance": ("bottoming",), "correlation_family": "holder_behavior"},
    "spent_value_ge155d_share": {"primary_responsibility": "capitulation_context", "axis_relevance": ("bottoming",), "correlation_family": "holder_behavior"},
    "seller_exhaustion": {"primary_responsibility": "exhaustion_clue", "axis_relevance": ("bottoming",), "correlation_family": "seller_exhaustion"},
    "puell_multiple": {"primary_responsibility": "pressure_anchor", "axis_relevance": ("pressure", "bottoming"), "correlation_family": "miner_pressure"},
    "thermocap_multiple_zscore": {"primary_responsibility": "pressure_context", "axis_relevance": ("pressure",), "correlation_family": "miner_pressure"},
    "cvdd_proximity": {"primary_responsibility": "bottoming_context", "axis_relevance": ("bottoming",), "correlation_family": "long_term_anchor"},
    "reserve_risk_zscore": {"primary_responsibility": "bottoming_context", "axis_relevance": ("bottoming",), "correlation_family": "long_term_anchor"},
}


def _entry(definition: dict[str, object]) -> dict[str, object]:
    role = str(definition["role"])
    status = str(definition["judgment_status"])
    theme_id = str(definition["theme_id"])
    responsibility = _RESPONSIBILITY_BY_ID.get(str(definition["canonical_id"]), {})
    return {
        **definition,
        **responsibility,
        "role_label": ROLE_LABELS[role],
        "status_label": JUDGMENT_STATUS_LABELS[status],
        # Both spellings are retained to keep downstream adapters explicit.
        "theme": theme_id,
        "eligible_for_judgment": status == "current",
    }


# Keep one entry object for a canonical id and its display alias.  This makes
# alias resolution deterministic while avoiding two subtly different copies
# of the role/eligibility facts.
_CANONICAL_ENTRIES: dict[str, dict[str, object]] = {
    str(item["canonical_id"]): _entry(item) for item in _INDICATOR_DEFINITIONS
}
INDICATOR_ROLE_REGISTRY: dict[str, dict[str, object]] = {}
for _canonical_id, _role_entry in _CANONICAL_ENTRIES.items():
    INDICATOR_ROLE_REGISTRY[_canonical_id] = _role_entry
    INDICATOR_ROLE_REGISTRY[str(_role_entry["display_id"])] = _role_entry


def canonical_id_for_snapshot_id(metric_id: str) -> str:
    """Resolve a canonical or packet display id to the canonical id.

    ``KeyError`` is intentional for an unknown id: silently accepting an
    unknown metric would make a later data-quality gate look like a missing
    value and could hide a catalogue drift.
    """

    if not isinstance(metric_id, str) or not metric_id:
        raise KeyError(metric_id)
    try:
        return str(INDICATOR_ROLE_REGISTRY[metric_id]["canonical_id"])
    except KeyError as exc:
        raise KeyError(f"未知指标 ID: {metric_id}") from exc


def role_for(metric_id: str) -> str:
    """Return the stable role token for a canonical/display metric id."""

    canonical_id = canonical_id_for_snapshot_id(metric_id)
    return str(INDICATOR_ROLE_REGISTRY[canonical_id]["role"])


def theme_for(metric_id: str) -> str:
    """Return the evidence-theme id for a canonical/display metric id."""

    canonical_id = canonical_id_for_snapshot_id(metric_id)
    return str(INDICATOR_ROLE_REGISTRY[canonical_id]["theme_id"])


def responsibility_for(metric_id: str) -> str:
    canonical_id = canonical_id_for_snapshot_id(metric_id)
    return str(INDICATOR_ROLE_REGISTRY[canonical_id]["primary_responsibility"])


def correlation_family_for(metric_id: str) -> str:
    canonical_id = canonical_id_for_snapshot_id(metric_id)
    return str(INDICATOR_ROLE_REGISTRY[canonical_id]["correlation_family"])


CANONICAL_INDICATOR_IDS: Final[tuple[str, ...]] = tuple(_CANONICAL_ENTRIES)
DISPLAY_INDICATOR_IDS: Final[tuple[str, ...]] = tuple(
    str(item["display_id"]) for item in _INDICATOR_DEFINITIONS
)


__all__ = [
    "ROLE_VALUES",
    "JUDGMENT_STATUS_VALUES",
    "ROLE_LABELS",
    "JUDGMENT_STATUS_LABELS",
    "THEME_REGISTRY",
    "INDICATOR_ROLE_REGISTRY",
    "CANONICAL_INDICATOR_IDS",
    "DISPLAY_INDICATOR_IDS",
    "canonical_id_for_snapshot_id",
    "role_for",
    "theme_for",
    "responsibility_for",
    "correlation_family_for",
]
