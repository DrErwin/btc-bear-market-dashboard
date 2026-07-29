"""Shared non-STH thresholds exported from the indicator validation panel.

These values drive both chart reference lines and snapshot status calculation,
so the visible chart and published evidence use the same threshold contract.
STH-MVRV is the sole exception: it has no horizontal chart references and its
three status thresholds are recalculated from the latest history on every run.
Source export: specs/v0.2.4/btc-indicator-config-2026-07-28.json
SHA-256: 435BB97DF65A69F1C50E084AB3C18A048D2AED57699B1E2945BDC1B72C2AFF81
"""

from __future__ import annotations

from typing import TypedDict


class ChartReference(TypedDict):
    value: float
    label: str


class ChartReferenceConfig(TypedDict):
    references: list[ChartReference]
    direction: str


CHART_REFERENCES: dict[str, ChartReferenceConfig] = {
    "mvrv": {
        "references": [
            {"value": 1.0, "label": "观察区"},
            {"value": 0.8, "label": "深度压力区"},
        ],
        "direction": "below",
    },
    "aviv": {
        "references": [{"value": 0.55, "label": "深度压力区"}],
        "direction": "below",
    },
    "sth_mvrv_price": {
        "references": [],
        "direction": "below",
    },
    "psip": {
        "references": [
            {"value": 0.5, "label": "观察区"},
            {"value": 0.45, "label": "极端压力区"},
        ],
        "direction": "below",
    },
    "sipl": {
        "references": [{"value": -0.05, "label": "深度压力区"}],
        "direction": "below",
    },
    "relative_unrealized_profit": {
        "references": [{"value": 0.35, "label": "深度压力区"}],
        "direction": "below",
    },
    "relative_unrealized_loss_zscore_4y": {
        "references": [
            {"value": 2.0, "label": "观察区"},
            {"value": 2.5, "label": "深度压力区"},
        ],
        "direction": "above",
    },
    "realized_cap_relative_npc_30d": {
        "references": [{"value": -0.04, "label": "深度压力区"}],
        "direction": "below",
    },
    "asopr": {
        "references": [
            {"value": 0.9, "label": "深度压力区"},
            {"value": 0.95, "label": "观察区"},
        ],
        "direction": "below",
    },
    "hodler_npc_30d": {
        "references": [{"value": 0.0, "label": "深度压力区"}],
        "direction": "below",
    },
    "spent_value_ge155d_share": {
        "references": [{"value": 0.03, "label": "90%分位观察区"}],
        "direction": "above",
    },
    "seller_exhaustion": {
        "references": [{"value": 0.05, "label": "10%分位观察区"}],
        "direction": "below",
    },
    "puell_multiple": {
        "references": [
            {"value": 0.6, "label": "观察区"},
            {"value": 0.5, "label": "深度压力区"},
        ],
        "direction": "below",
    },
    "thermocap_multiple_zscore": {
        "references": [
            {"value": -0.6147138165, "label": "10%分位定投区"},
            {"value": -0.8703706199, "label": "5%分位深度压力区"},
        ],
        "direction": "below",
    },
    "cvdd_proximity": {
        "references": [{"value": 5.0, "label": "极端压力区"}],
        "direction": "above",
    },
    "reserve_risk_zscore": {
        "references": [
            {"value": -1.320779819, "label": "10%分位观察区"},
            {"value": -1.892782115, "label": "5%分位深度压力区"},
        ],
        "direction": "below",
    },
}

def references_for(canonical_id: str) -> ChartReferenceConfig | None:
    """Return chart references for a canonical metric, if it is configured."""

    return CHART_REFERENCES.get(canonical_id)
