"""Per-axis data readiness for the v0.4 evidence brief."""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from .catalog import (
    INDICATOR_ROLE_REGISTRY,
    canonical_id_for_snapshot_id,
    correlation_family_for,
    role_for,
)


CURRENT = "current"
DISPLAY_ONLY = "display_only"
VALIDATION_PENDING = "validation_pending"
MISSING = "missing"
DEFAULT_MAX_STALE_DAYS = 2

# These are coverage requirements, not state rules.  A ready axis is still
# judged by the AI from all supplied facts; the machine never turns this list
# into a state or score.
AXIS_REQUIRED_METRICS: dict[str, tuple[str, ...]] = {
    "pressure": ("mvrv", "puell_multiple"),
    "bottoming": (
        "asopr",
        "seller_exhaustion",
        "sth_mvrv_price",
        "realized_cap_relative_npc_30d",
    ),
}


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _initial_status(canonical_id: str) -> tuple[str, str | None]:
    if canonical_id == "cvdd_proximity":
        return VALIDATION_PENDING, "CVDD 距离阈值仍在验证，暂不参与当前判断"
    return CURRENT, None


def evaluate_snapshot_quality(
    snapshot: dict[str, Any],
    *,
    analysis_date: str | date | None = None,
    max_stale_days: int = DEFAULT_MAX_STALE_DAYS,
) -> dict[str, Any]:
    """Evaluate every visible metric and readiness of each state axis."""

    analysis_day = _parse_date(analysis_date) or _parse_date(snapshot.get("snapshot_date"))
    if analysis_day is None:
        raise ValueError("snapshot 缺少有效 analysis_date/snapshot_date")
    if max_stale_days < 0:
        raise ValueError("max_stale_days 不能为负数")
    raw_metrics = snapshot.get("metrics")
    if not isinstance(raw_metrics, list):
        raise ValueError("snapshot.metrics 必须是列表")

    metrics: list[dict[str, Any]] = []
    by_canonical: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_metrics):
        if not isinstance(raw, dict):
            raise ValueError(f"snapshot.metrics[{index}] 必须是对象")
        metric_id = raw.get("id")
        if not isinstance(metric_id, str) or not metric_id:
            raise ValueError(f"snapshot.metrics[{index}].id 必须是非空字符串")
        canonical_id = canonical_id_for_snapshot_id(metric_id)
        metric_date = _parse_date(raw.get("current_date") or raw.get("metric_date"))
        value = _number(raw.get("current_value"))
        age_days = None if metric_date is None else (analysis_day - metric_date).days
        reason: str | None = None
        status = MISSING
        if value is None:
            reason = "当前值缺失或不是有限数值"
        elif metric_date is None:
            reason = "指标日期缺失或无法解析"
        elif age_days < 0:
            reason = "指标日期晚于分析日期，不能用于当前判断"
        elif age_days > max_stale_days:
            status = DISPLAY_ONLY
            reason = f"数据已过期 {age_days} 天，超过 {max_stale_days} 天新鲜度上限"
        else:
            status, reason = _initial_status(canonical_id)
        item = {
            "id": metric_id,
            "canonical_id": canonical_id,
            "label": str(raw.get("label") or metric_id),
            "category": str(raw.get("category") or ""),
            "role": role_for(canonical_id),
            "responsibility": str(INDICATOR_ROLE_REGISTRY[canonical_id].get("primary_responsibility") or "context"),
            "axis_relevance": list(INDICATOR_ROLE_REGISTRY[canonical_id].get("axis_relevance") or ()),
            "correlation_family": correlation_family_for(canonical_id),
            "status": status,
            "judgment_eligible": status == CURRENT,
            "metric_date": metric_date.isoformat() if metric_date else None,
            "days_stale": age_days,
            "current_value": value,
            "reason": reason,
            "tier_id": raw.get("tier_id") or "none",
            "tier_label": raw.get("tier_label") or "未进入观察区",
            "tier_meaning": raw.get("tier_meaning") or "当前值未触及该指标的观察阈值。",
        }
        metrics.append(item)
        by_canonical[canonical_id] = item

    axis_readiness: dict[str, dict[str, Any]] = {}
    for axis, required in AXIS_REQUIRED_METRICS.items():
        missing: list[str] = []
        for canonical_id in required:
            item = by_canonical.get(canonical_id)
            if not item or not item["judgment_eligible"]:
                missing.append(canonical_id)
        families = sorted({str(by_canonical[item]["correlation_family"]) for item in required if item in by_canonical and by_canonical[item]["judgment_eligible"]})
        axis_readiness[axis] = {
            "ready": not missing,
            "required_metric_ids": list(required),
            "missing_metric_ids": missing,
            "missing_reasons": [
                str(by_canonical.get(item, {}).get("reason") or "指标缺失或不可用")
                for item in missing
            ],
            "available_families": families,
            "family_coverage": len(families),
            "timeline_complete": True,
        }

    pressure_dates = [by_canonical[item]["metric_date"] for item in AXIS_REQUIRED_METRICS["pressure"] if item in by_canonical and by_canonical[item]["judgment_eligible"]]
    return {
        "analysis_date": analysis_day.isoformat(),
        "max_stale_days": max_stale_days,
        "axis_readiness": axis_readiness,
        "metrics": metrics,
        "common_anchor_date": min(pressure_dates) if len(pressure_dates) == len(AXIS_REQUIRED_METRICS["pressure"]) else None,
        # Compatibility information is nested under migration metadata and is
        # never exposed as an AI state range.
        "migration": {"old_single_stage_supported": False},
    }


__all__ = [
    "CURRENT",
    "DISPLAY_ONLY",
    "VALIDATION_PENDING",
    "MISSING",
    "DEFAULT_MAX_STALE_DAYS",
    "AXIS_REQUIRED_METRICS",
    "evaluate_snapshot_quality",
]
