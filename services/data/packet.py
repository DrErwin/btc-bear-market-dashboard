"""The single dashboard data packet: assembly, contract, atomic fallback.

Requirement 1 ("完整数据包与整包回退"): everything the page reads — snapshot,
series, bars, analysis, fallback, status, plus a traceable header — travels in
ONE json object. The page has one entry point; nothing is fetched separately.

The packet is the contract surface between the daily pipeline (services/run_daily)
and the Vue dashboard. Assembly turns the real ``ComputedData`` into the
v0.1.0-compatible metric/series shape (only the values become real); validation
rejects anything missing, date-inconsistent, or AI-noncompliant so a half-built
packet can never be published.
"""

from __future__ import annotations

import json
import math
import os
from datetime import date
from pathlib import Path
from typing import Any

from ..ai import validator as ai_validator
from . import packet_display
from .chart_references import references_for
from .derive import BOTTOMS
from .metrics import INDICATOR_CATALOG, ComputedData, IndicatorSpec


# canonical metric id -> category id (fixed dashboard taxonomy).
_CATEGORY_BY_CANONICAL: dict[str, str] = {
    metric_id: category for metric_id, (category, _core) in INDICATOR_CATALOG.items()
}


SCHEMA_VERSION = "0.2.0"
CONFIG_VERSION = "0.2.0"
METRIC_COUNT = 16
CATEGORY_COUNT = 6


class PacketValidationError(ValueError):
    """Raised when a packet cannot be published (requirement 1 验收)."""


# ---------------------------------------------------------------------------
# Display formatting + tier
# ---------------------------------------------------------------------------

def _format_value(scaled: float, unit_kind: str) -> str:
    if unit_kind == "percent":
        return f"{scaled:.1f}%"
    if unit_kind == "zscore":
        return f"{scaled:.2f}"
    if unit_kind == "ratio":
        return f"{scaled:.2f}"
    if unit_kind == "small":
        return f"{scaled:.2f}"
    if unit_kind == "price":
        return f"${scaled:,.0f}"
    return f"{scaled:.2f}"


def _compute_tier(
    direction: str,
    references_raw: list[float],
    display_thresholds: list[dict],
    current_raw: float,
) -> tuple[str, str]:
    """Tier = how many *trigger* thresholds the current value has crossed.

    Thresholds whose display entry carries ``role == "neutral"`` (e.g. the
    self-4y-mean line on z-score metrics) are reference lines, not evidence
    depth, so they never count toward the tier.
    """
    triggered = 0
    for raw_value, display in zip(references_raw, display_thresholds):
        if display.get("role") == "neutral":
            continue
        if direction == "below":
            crossed = current_raw < raw_value
        else:
            crossed = current_raw > raw_value
        if crossed:
            triggered += 1
    if triggered == 0:
        return ("未进入观察区", "当前值未触及该指标的任何观察阈值。")
    if triggered == 1:
        return ("进入观察区", "当前值已触及该指标的第一档观察阈值。")
    return ("重点观察区", f"当前值已触及 {triggered} 档阈值，构成更强的该维度证据。")


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _build_metric(ind: IndicatorSpec) -> dict:
    display = packet_display.BY_CANONICAL[ind.id]
    scale = display.display_scale
    if not ind.references:
        raise PacketValidationError(f"指标 {ind.id} 没有 references")
    if len(ind.references) != len(display.thresholds):
        raise PacketValidationError(
            f"指标 {ind.id} references({len(ind.references)}) "
            f"与展示阈值({len(display.thresholds)})数量不一致"
        )
    if not ind.primary:
        raise PacketValidationError(f"指标 {ind.id} 序列为空")

    latest_day = max(ind.primary)
    current_raw = ind.primary[latest_day]
    references_raw = [ref["value"] for ref in ind.references]
    tier_label, tier_meaning = _compute_tier(ind.direction, references_raw, display.thresholds, current_raw)

    thresholds = []
    for ref, display_thr in zip(ind.references, display.thresholds):
        thresholds.append({
            "value": ref["value"] * scale,
            "direction": ind.direction,
            "label": display_thr["label"],
            "meaning": display_thr["meaning"],
        })

    return {
        "id": display.display_id,
        "label": display.label,
        "category": _CATEGORY_BY_CANONICAL[ind.id],
        "role": display.role,
        "unit": display.unit_label,
        "description": display.description,
        "formula": display.formula,
        "source": display.source,
        "method": display.method,
        "caveat": display.caveat,
        "current_value": current_raw * scale,
        "display_value": _format_value(current_raw * scale, display.unit_kind),
        "current_date": latest_day.isoformat(),
        "tier_label": tier_label,
        "tier_meaning": tier_meaning,
        "thresholds": thresholds,
    }


def _build_series_entry(ind: IndicatorSpec) -> dict:
    display = packet_display.BY_CANONICAL[ind.id]
    scale = display.display_scale
    points = [
        {"date": day.isoformat(), "value": value * scale}
        for day, value in sorted(ind.primary.items())
    ]
    chart_config = references_for(ind.id)
    chart_refs = chart_config["references"] if chart_config else ind.references
    chart_direction = chart_config["direction"] if chart_config else ind.direction
    thresholds = []
    for ref in chart_refs:
        label = ref["label"]
        meaning = next(
            (item["meaning"] for item in display.thresholds if item["label"] == label),
            f"指标验证参考线：{label}",
        )
        thresholds.append({
            "value": ref["value"] * scale,
            "direction": chart_direction,
            "label": label,
            "meaning": meaning,
        })

    # Keep the validation panel's complete line set in the public packet. The
    # primary line is always first; extra lines retain their id, label, axis,
    # date coverage and values. Indicator-axis lines use the display scale,
    # while price-axis lines remain in BTC/USD units.
    lines = [{
        "id": "primary",
        "label": ind.primary_line_label or ind.label,
        "axis": "indicator",
        "points": points,
    }]
    for line in ind.extra_lines:
        line_scale = scale if line.axis == "indicator" else 1.0
        lines.append({
            "id": line.id,
            "label": line.label,
            "axis": line.axis,
            "points": [
                {"date": day.isoformat(), "value": value * line_scale}
                for day, value in sorted(line.series.items())
            ],
        })
    return {"points": points, "thresholds": thresholds, "lines": lines}


def _build_bar(canonical_id: str, bar) -> dict:
    display = packet_display.BY_CANONICAL[canonical_id]
    scale = display.display_scale
    points = [
        {"date": day.isoformat(), "value": value * scale, "quality": "ok"}
        for day, value in sorted(bar.series.items())
    ]
    return {
        "id": display.display_id,
        "label": bar.label,
        "unit": display.unit_label,
        "description": bar.description,
        "source": bar.source,
        "method": bar.method,
        "caveat": bar.caveat,
        "points": points,
    }


def build_snapshot(computed: ComputedData) -> dict:
    """Snapshot block (snapshot_date, price, categories, 16 metrics).

    Extracted so the AI input builder can consume the same snapshot the page
    renders, before any analysis exists (requirement 4 AI input boundary).
    """
    data_date = computed.data_date
    price_now = computed.price[data_date]
    return {
        "snapshot_date": data_date.isoformat(),
        "price": {
            "current_value": price_now,
            "display_value": f"${price_now:,.0f}",
            "unit": "USD",
            "current_date": data_date.isoformat(),
        },
        "categories": [
            {"id": cid, "short": short, "name": name}
            for cid, (short, name) in packet_display.CATEGORIES.items()
        ],
        "metrics": [_build_metric(ind) for ind in computed.indicators],
    }


def build_packet(
    computed: ComputedData,
    *,
    analysis: dict | None,
    fallback: dict | None,
    today_available: bool,
    last_success_date: str | None,
    reason: str | None,
    run_id: str,
    generated_at: str,
) -> dict:
    """Assemble the single dashboard packet from real computed data.

    ``analysis`` and ``fallback`` must already be dashboard-format and
    AI-validated (see services.ai.validator). ``today_available`` decides
    whether ``analysis`` is shown; on failure the caller passes the previous
    success as ``fallback`` and ``reason``.
    """
    data_date = computed.data_date
    price_now = computed.price[data_date]
    snapshot = build_snapshot(computed)

    series_metrics = {packet_display.BY_CANONICAL[ind.id].display_id: _build_series_entry(ind) for ind in computed.indicators}
    bars = {canonical: _build_bar(canonical, bar) for canonical, bar in computed.bars.items()}

    shown_analysis = analysis if today_available else None
    analysis_date = None
    if shown_analysis is not None:
        analysis_date = shown_analysis.get("analysis_date")
    elif fallback is not None:
        analysis_date = fallback.get("analysis_date")

    packet = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": generated_at,
        "config_version": CONFIG_VERSION,
        "data_date": data_date.isoformat(),
        "analysis_date": analysis_date,
        "input_summary": {
            "category_count": CATEGORY_COUNT,
            "metric_count": METRIC_COUNT,
            "price": {"date": data_date.isoformat(), "value": price_now},
            "source": computed.source_metadata,
        },
        "snapshot": snapshot,
        "series": {
            "price": [
                {"date": day.isoformat(), "value": value}
                for day, value in sorted(computed.price.items())
            ],
            "metrics": series_metrics,
        },
        "bars": bars,
        "bottoms": [{"date": day.isoformat(), "label": label} for day, label in BOTTOMS],
        "analysis": shown_analysis,
        "fallback": fallback,
        "status": {
            "today_available": today_available,
            "last_success_date": last_success_date,
            "reason": reason,
        },
    }
    validate_packet(packet)
    return packet


# ---------------------------------------------------------------------------
# Contract validation (requirement 1 验收: reject incomplete / inconsistent)
# ---------------------------------------------------------------------------

_REQUIRED_METRIC_FIELDS = (
    "id", "label", "category", "role", "unit", "description", "formula",
    "source", "method", "caveat", "current_value", "display_value",
    "current_date", "tier_label", "tier_meaning", "thresholds",
)


def _validate_analysis_shape(payload: dict | None, where: str, errors: list[str]) -> None:
    if payload is None:
        return
    try:
        ai_validator.validate_analysis(payload)
    except ai_validator.InvalidAnalysisError as exc:
        for err in exc.errors:
            errors.append(f"{where}: {err}")


def validate_packet(packet: dict) -> None:
    """Raise PacketValidationError unless the packet is complete and consistent."""
    errors: list[str] = []

    for field in ("schema_version", "run_id", "generated_at", "data_date", "config_version"):
        if not packet.get(field):
            errors.append(f"缺少顶层字段: {field}")

    snapshot = packet.get("snapshot")
    if not isinstance(snapshot, dict):
        errors.append("缺少 snapshot")
    else:
        metrics = snapshot.get("metrics")
        if not isinstance(metrics, list):
            errors.append("snapshot.metrics 必须是列表")
        elif len(metrics) != METRIC_COUNT:
            errors.append(f"snapshot.metrics 必须为 {METRIC_COUNT} 个，实际 {len(metrics)}")
        else:
            for index, metric in enumerate(metrics):
                if not isinstance(metric, dict):
                    errors.append(f"snapshot.metrics[{index}] 必须是对象")
                    continue
                missing = [f for f in _REQUIRED_METRIC_FIELDS if f not in metric]
                if missing:
                    errors.append(f"snapshot.metrics[{index}] 缺字段: {', '.join(missing)}")
                thr = metric.get("thresholds")
                if not isinstance(thr, list) or not thr:
                    errors.append(f"snapshot.metrics[{index}].thresholds 必须非空列表")
        categories = snapshot.get("categories")
        if not isinstance(categories, list) or len(categories) != CATEGORY_COUNT:
            errors.append(f"snapshot.categories 必须为 {CATEGORY_COUNT} 个")

    series = packet.get("series")
    if not isinstance(series, dict):
        errors.append("缺少 series")
    else:
        if not isinstance(series.get("price"), list) or not series["price"]:
            errors.append("series.price 必须非空")
        series_metrics = series.get("metrics")
        if not isinstance(series_metrics, dict) or len(series_metrics) != METRIC_COUNT:
            errors.append(f"series.metrics 必须为 {METRIC_COUNT} 个")
        else:
            metric_ids = {m["id"] for m in snapshot.get("metrics", []) if isinstance(m, dict)} if isinstance(snapshot, dict) else set()
            if metric_ids and set(series_metrics) != metric_ids:
                errors.append("series.metrics 的键与 snapshot.metrics 的 id 不一致")
            for metric_id, entry in series_metrics.items():
                if not isinstance(entry, dict):
                    errors.append(f"series.metrics[{metric_id}] 必须是对象")
                    continue
                lines = entry.get("lines")
                if lines is None:
                    continue  # v0.2.3 packets remain readable.
                if not isinstance(lines, list) or not lines:
                    errors.append(f"series.metrics[{metric_id}].lines 必须是非空列表")
                    continue
                line_ids: set[str] = set()
                for line_index, line in enumerate(lines):
                    if not isinstance(line, dict):
                        errors.append(f"series.metrics[{metric_id}].lines[{line_index}] 必须是对象")
                        continue
                    missing_line = [field for field in ("id", "label", "axis", "points") if field not in line]
                    if missing_line:
                        errors.append(
                            f"series.metrics[{metric_id}].lines[{line_index}] 缺字段: {', '.join(missing_line)}"
                        )
                        continue
                    line_id = line.get("id")
                    if not isinstance(line_id, str) or not line_id:
                        errors.append(f"series.metrics[{metric_id}].lines[{line_index}].id 必须是非空字符串")
                    elif line_id in line_ids:
                        errors.append(f"series.metrics[{metric_id}].lines 出现重复 id: {line_id}")
                    else:
                        line_ids.add(line_id)
                    if line.get("axis") not in ("indicator", "price"):
                        errors.append(f"series.metrics[{metric_id}].lines[{line_index}].axis 无效")
                    points = line.get("points")
                    if not isinstance(points, list):
                        errors.append(f"series.metrics[{metric_id}].lines[{line_index}].points 必须是列表")
                    else:
                        for point_index, point in enumerate(points):
                            if (
                                not isinstance(point, dict)
                                or not isinstance(point.get("date"), str)
                                or not isinstance(point.get("value"), (int, float))
                                or not math.isfinite(float(point["value"]))
                            ):
                                errors.append(
                                    f"series.metrics[{metric_id}].lines[{line_index}].points[{point_index}] 无效"
                                )

    bars = packet.get("bars")
    if not isinstance(bars, dict) or len(bars) != 2:
        errors.append("bars 必须包含两个柱状系列")

    status = packet.get("status")
    if not isinstance(status, dict):
        errors.append("缺少 status")
    else:
        if not isinstance(status.get("today_available"), bool):
            errors.append("status.today_available 必须是布尔")

    # --- date consistency ---
    data_date = packet.get("data_date")
    if isinstance(snapshot, dict) and snapshot.get("snapshot_date") != data_date:
        errors.append("snapshot.snapshot_date 与 data_date 不一致")
    if isinstance(series, dict) and isinstance(series.get("price"), list) and series["price"]:
        last_point = series["price"][-1]
        if isinstance(last_point, dict) and last_point.get("date") != data_date:
            errors.append("series.price 末点日期与 data_date 不一致")

    status_ok = isinstance(status, dict) and status.get("today_available") is True
    analysis = packet.get("analysis")
    if status_ok:
        if not isinstance(analysis, dict):
            errors.append("today_available=true 时 analysis 不能为空")
        elif analysis.get("analysis_date") != data_date:
            errors.append("analysis.analysis_date 必须等于 data_date")
    else:
        if analysis is not None:
            errors.append("today_available=false 时 analysis 必须为 null")

    # --- AI compliance (forbidden trading/probability language) ---
    _validate_analysis_shape(analysis, "analysis", errors)
    _validate_analysis_shape(packet.get("fallback"), "fallback", errors)

    if errors:
        raise PacketValidationError("；".join(errors))


# ---------------------------------------------------------------------------
# Atomic publish + load (整包回退)
# ---------------------------------------------------------------------------

def write_packet_atomic(packet: dict, path: str | Path) -> None:
    """Validate then atomically replace the packet file (write tmp + replace).

    A half-written or invalid file can never be observed by readers: validation
    happens first, and the os-level replace is atomic on the same filesystem.
    """
    validate_packet(packet)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    text = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, target)


def load_packet(path: str | Path) -> dict | None:
    """Load and validate a previously published packet, or None if absent/invalid."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        packet = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        validate_packet(packet)
    except PacketValidationError:
        return None
    return packet
