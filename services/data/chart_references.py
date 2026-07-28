"""Chart-only reference lines exported from the indicator validation panel.

The validation export is intentionally kept out of the AI snapshot boundary:
these values control the visual reference lines, while the existing snapshot
thresholds continue to drive the published observation state and AI input.
Source export: btc-indicator-config-2026-07-28.json
SHA-256: CAD0028AF77A30065A42D0C47181DEB8256434DC2410C4B2128391D4477EBC98
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
            {"value": 1.0, "label": "成本平衡线"},
            {"value": 0.8, "label": "深度低估观察线"},
        ],
        "direction": "below",
    },
    "aviv": {
        "references": [
            {"value": 0.55, "label": "低估观察线"},
            {"value": 0.5, "label": "深度低估参考"},
        ],
        "direction": "below",
    },
    "sth_mvrv_price": {
        "references": [{"value": 0.6370026843, "label": "1.5·MAD（无前视）"}],
        "direction": "below",
    },
    "psip": {
        "references": [{"value": 0.5, "label": "盈亏供应平衡"}],
        "direction": "below",
    },
    "sipl": {
        "references": [{"value": -0.1, "label": "两线理论交错参考"}],
        "direction": "below",
    },
    "relative_unrealized_profit": {
        "references": [{"value": 0.37, "label": "深低值观察线"}],
        "direction": "below",
    },
    "relative_unrealized_loss_zscore_4y": {
        "references": [
            {"value": 2.0, "label": "高于均值2σ（投降区）"},
            {"value": 2.5, "label": "高于均值2.5σ（深度投降）"},
        ],
        "direction": "above",
    },
    "realized_cap_relative_npc_30d": {
        "references": [{"value": -0.04, "label": "资本扩张/收缩分界"}],
        "direction": "above",
    },
    "asopr": {
        "references": [{"value": 0.9, "label": "投降"}],
        "direction": "below",
    },
    "hodler_npc_30d": {
        "references": [{"value": 0.0, "label": "净积累/净释放分界"}],
        "direction": "above",
    },
    "spent_value_ge155d_share": {
        "references": [{"value": 0.02448369429, "label": "全样本90%分位（探索）"}],
        "direction": "above",
    },
    "seller_exhaustion": {
        "references": [{"value": 0.03544264742, "label": "全样本10%分位（探索）"}],
        "direction": "below",
    },
    "puell_multiple": {
        "references": [
            {"value": 0.7, "label": "低收入区上界"},
            {"value": 0.5, "label": "历史深压参考"},
        ],
        "direction": "below",
    },
    "thermocap_multiple_zscore": {
        "references": [
            {"value": -0.6147138165, "label": "z·过去周期10%分位（先触发）"},
            {"value": -0.8703706199, "label": "z·过去周期5%分位（深部）"},
            {"value": 0.0, "label": "自身4年均值（中性）"},
        ],
        "direction": "below",
    },
    "cvdd_proximity": {
        "references": [{"value": 2.5, "label": "高于CVDD 50%"}],
        "direction": "above",
    },
    "reserve_risk_zscore": {
        "references": [
            {"value": -1.320779819, "label": "z·过去周期10%分位"},
            {"value": -1.892782115, "label": "z·过去周期5%分位"},
        ],
        "direction": "below",
    },
}

def references_for(canonical_id: str) -> ChartReferenceConfig | None:
    """Return chart references for a canonical metric, if it is configured."""

    return CHART_REFERENCES.get(canonical_id)
