from __future__ import annotations

from copy import deepcopy


METRICS = [
    ("mvrv", "MVRV"),
    ("aviv", "AVIV"),
    ("sth-mvrv", "STH-MVRV"),
    ("psip", "PSIP"),
    ("sipl", "SIPL"),
    ("rup", "RUP"),
    ("rul-z", "RUL z-score"),
    ("rc-npc", "RC-NPC"),
    ("asopr", "aSOPR"),
    ("hodler", "HODLer NPC"),
    ("spent155", ">=155d spent value"),
    ("seller", "Seller Exhaustion"),
    ("puell", "Puell Multiple"),
    ("thermo", "Thermocap z-score"),
    ("cvdd", "CVDD proximity"),
    ("reserve", "Reserve Risk z-score"),
]


def _thresholds(metric_id: str) -> list[dict[str, object]]:
    if metric_id == "mvrv":
        return [
            {"value": 1.0, "direction": "below", "label": "成本平衡线", "meaning": "进入估值压力"},
            {"value": 0.8, "direction": "below", "label": "深度低估线", "meaning": "进入深度估值压力"},
        ]
    if metric_id == "aviv":
        return [
            {"value": 0.65, "direction": "below", "label": "低估观察线", "meaning": "估值复核"},
            {"value": 0.55, "direction": "below", "label": "深度低估参考", "meaning": "深度复核"},
        ]
    if metric_id == "puell":
        return [
            {"value": 1.0, "direction": "below", "label": "低收入区上界", "meaning": "矿工压力"},
            {"value": 0.5, "direction": "below", "label": "历史深压参考", "meaning": "深度矿工压力"},
        ]
    if metric_id in {"rul-z", "cvdd"}:
        return [{"value": 2.0 if metric_id == "rul-z" else 0.5, "direction": "above", "label": "观察线", "meaning": "辅助压力"}]
    if metric_id in {"asopr", "seller", "psip", "sipl", "rup", "sth-mvrv"}:
        return [{"value": 1.0 if metric_id in {"asopr", "sth-mvrv"} else 50.0, "direction": "below", "label": "观察线", "meaning": "辅助压力"}]
    return [{"value": 0.0, "direction": "above", "label": "观察线", "meaning": "辅助信号"}]


def make_snapshot(
    *,
    mvrv: float = 1.1,
    puell: float = 1.1,
    aviv: float = 0.8,
    analysis_date: str = "2026-07-28",
    stale_ids: set[str] | None = None,
    aux_values: dict[str, float] | None = None,
) -> dict:
    stale_ids = stale_ids or set()
    aux_values = aux_values or {}
    values = {metric_id: 1.0 for metric_id, _ in METRICS}
    values.update({"mvrv": mvrv, "puell": puell, "aviv": aviv})
    values.update(aux_values)
    metrics = []
    for metric_id, label in METRICS:
        metrics.append(
            {
                "id": metric_id,
                "label": label,
                "category": "valuation",
                "role": "辅助",
                "unit": "比率",
                "description": f"{label} 的说明",
                "current_value": values[metric_id],
                "current_date": "2023-01-12" if metric_id in stale_ids else analysis_date,
                "thresholds": _thresholds(metric_id),
            }
        )
    return {
        "snapshot_date": analysis_date,
        "categories": [
            {"id": category, "short": category, "name": category}
            for category in ("valuation", "supply", "capital", "holders", "miners", "anchors")
        ],
        "metrics": metrics,
    }


def clone_snapshot(snapshot: dict) -> dict:
    return deepcopy(snapshot)
