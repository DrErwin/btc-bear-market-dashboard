"""Data-quality gate for the v0.3.0 evidence brief.

The gate deliberately treats missing, stale, and indeterminate values as
different from an untriggered indicator.  That distinction prevents an old
series (or a zero denominator) from silently becoming evidence that a phase
has not started.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from .catalog import canonical_id_for_snapshot_id, role_for


CURRENT = "current"
DISPLAY_ONLY = "display_only"
VALIDATION_PENDING = "validation_pending"
MISSING = "missing"

DEFAULT_MAX_STALE_DAYS = 2
CRITICAL_ANCHORS = ("mvrv", "puell_multiple")


def _parse_date(value: object) -> date | None:
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


def _initial_status(canonical_id: str, metric: dict[str, Any]) -> tuple[str, str | None]:
    """Return a non-date status for a valid metric value.

    CVDD has a known concept but its current distance rule is still being
    validated.  It is therefore visible but not allowed into the AI brief.
    """

    if canonical_id == "cvdd_proximity":
        return VALIDATION_PENDING, "CVDD 距离阈值仍在验证，暂不参与阶段判断"
    return CURRENT, None


def evaluate_snapshot_quality(
    snapshot: dict[str, Any],
    *,
    analysis_date: str | date | None = None,
    max_stale_days: int = DEFAULT_MAX_STALE_DAYS,
) -> dict[str, Any]:
    """Evaluate every visible metric and identify whether the stage is ready.

    The return value is JSON-ready so it can be persisted in the complete
    packet and used as an auditable input to the evidence compiler.
    """

    if isinstance(analysis_date, date):
        analysis_day = analysis_date
    elif isinstance(analysis_date, str):
        analysis_day = _parse_date(analysis_date)
    else:
        analysis_day = _parse_date(snapshot.get("snapshot_date"))
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
        metric_date = _parse_date(raw.get("current_date"))
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
            status, reason = _initial_status(canonical_id, raw)

        judgment_eligible = status == CURRENT
        item = {
            "id": metric_id,
            "canonical_id": canonical_id,
            "label": str(raw.get("label") or metric_id),
            "role": role_for(canonical_id),
            "status": status,
            "judgment_eligible": judgment_eligible,
            "metric_date": metric_date.isoformat() if metric_date else None,
            "days_stale": age_days,
            "current_value": value,
            "reason": reason,
        }
        metrics.append(item)
        by_canonical[canonical_id] = item

    anchor_dates = [
        by_canonical[anchor]["metric_date"]
        for anchor in CRITICAL_ANCHORS
        if anchor in by_canonical and by_canonical[anchor]["judgment_eligible"]
    ]
    common_anchor_date = min(anchor_dates) if len(anchor_dates) == len(CRITICAL_ANCHORS) else None
    critical_missing = [
        anchor
        for anchor in CRITICAL_ANCHORS
        if anchor not in by_canonical or not by_canonical[anchor]["judgment_eligible"]
    ]

    return {
        "analysis_date": analysis_day.isoformat(),
        "max_stale_days": max_stale_days,
        "common_anchor_date": common_anchor_date,
        "stage_ready": not critical_missing,
        "critical_missing": critical_missing,
        "metrics": metrics,
    }


__all__ = [
    "CURRENT",
    "DISPLAY_ONLY",
    "VALIDATION_PENDING",
    "MISSING",
    "DEFAULT_MAX_STALE_DAYS",
    "CRITICAL_ANCHORS",
    "evaluate_snapshot_quality",
]
