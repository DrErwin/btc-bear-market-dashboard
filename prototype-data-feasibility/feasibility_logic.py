"""PROTOTYPE: pure feasibility and alignment logic; no network or terminal I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite
from typing import Mapping, Sequence


@dataclass(frozen=True)
class TimeSeries:
    family: str
    key: str
    label: str
    unit: str
    values: Mapping[date, float]
    source: str
    lineage: str
    experimental: bool = False


FAMILY_LABELS = {
    "market_valuation": "市场估值",
    "time_weighted_valuation": "时间加权估值",
    "active_capital_valuation": "活跃资本估值",
    "holder_behavior": "持有者行为",
}


BEAR_MARKET_SAMPLES = (
    ("2011 熊市低位", date(2011, 11, 18)),
    ("2015 熊市低位", date(2015, 1, 14)),
    ("2018 熊市低位", date(2018, 12, 15)),
    ("2020 流动性冲击", date(2020, 3, 16)),
    ("2022 熊市低位", date(2022, 11, 21)),
)


def _missing_dates(values: Mapping[date, float]) -> list[date]:
    if not values:
        return []
    first = min(values)
    last = max(values)
    missing: list[date] = []
    cursor = first
    while cursor <= last:
        if cursor not in values:
            missing.append(cursor)
        cursor += timedelta(days=1)
    return missing


def _longest_gap(missing: Sequence[date]) -> int:
    if not missing:
        return 0
    longest = current = 1
    for previous, item in zip(missing, missing[1:]):
        if item == previous + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def profile_series(series: TimeSeries, as_of: date) -> dict:
    valid = {d: v for d, v in series.values.items() if isfinite(v)}
    if not valid:
        return {
            "key": series.key,
            "label": series.label,
            "unit": series.unit,
            "source": series.source,
            "lineage": series.lineage,
            "experimental": series.experimental,
            "row_count": 0,
            "coverage_start": None,
            "coverage_end": None,
            "freshness_lag_days": None,
            "missing_days": None,
            "longest_gap_days": None,
            "invalid_values": len(series.values),
        }

    missing = _missing_dates(valid)
    last = max(valid)
    return {
        "key": series.key,
        "label": series.label,
        "unit": series.unit,
        "source": series.source,
        "lineage": series.lineage,
        "experimental": series.experimental,
        "row_count": len(valid),
        "coverage_start": min(valid).isoformat(),
        "coverage_end": last.isoformat(),
        "freshness_lag_days": max(0, (as_of - last).days),
        "missing_days": len(missing),
        "longest_gap_days": _longest_gap(missing),
        "invalid_values": len(series.values) - len(valid),
    }


def build_feasibility_state(
    representatives: Mapping[str, TimeSeries],
    candidates: Mapping[str, Sequence[TimeSeries]],
    raw_series: Sequence[TimeSeries],
    as_of: date,
    max_lag_days: int,
    source_metadata: Mapping[str, str],
) -> dict:
    required = tuple(FAMILY_LABELS)
    unavailable = [family for family in required if family not in representatives or not representatives[family].values]

    common_dates: set[date] | None = None
    for family in required:
        if family in unavailable:
            continue
        dates = set(representatives[family].values)
        common_dates = dates if common_dates is None else common_dates & dates
    common_cutoff = max(common_dates) if common_dates else None

    families: list[dict] = []
    for family in required:
        item = representatives.get(family)
        if item is None or not item.values:
            families.append({
                "family": family,
                "family_label": FAMILY_LABELS[family],
                "metric": None,
                "data_state": "not_ready",
                "evidence_state": "not_evaluated",
                "reason": "没有可用候选序列",
            })
            continue

        profile = profile_series(item, as_of)
        latest = max(item.values)
        reasons: list[str] = []
        if common_cutoff is None or common_cutoff not in item.values:
            data_state = "not_ready"
            reasons.append("无法形成四家族共同日期")
            aligned_value = None
        else:
            aligned_value = item.values[common_cutoff]
            if profile["freshness_lag_days"] > max_lag_days:
                reasons.append(f"源数据落后 {profile['freshness_lag_days']} 天，超过原型预算 {max_lag_days} 天")
            if profile["missing_days"]:
                reasons.append(f"覆盖期内缺 {profile['missing_days']} 天")
            if item.experimental:
                reasons.append("实验派生，尚未与独立实现交叉验证")
            data_state = "conditional" if reasons else "ready"

        families.append({
            "family": family,
            "family_label": FAMILY_LABELS[family],
            "metric": item.key,
            "metric_label": item.label,
            "unit": item.unit,
            "data_state": data_state,
            "evidence_state": "not_evaluated",
            "latest_date": latest.isoformat(),
            "latest_value": item.values[latest],
            "aligned_date": common_cutoff.isoformat() if common_cutoff else None,
            "aligned_value": aligned_value,
            "freshness_lag_days": profile["freshness_lag_days"],
            "missing_days": profile["missing_days"],
            "source": item.source,
            "lineage": item.lineage,
            "experimental": item.experimental,
            "reason": "；".join(reasons) if reasons else "数据获取、日度覆盖和原型新鲜度检查通过",
            "candidate_metrics": [candidate.key for candidate in candidates.get(family, ())],
        })

    states = {item["data_state"] for item in families}
    if unavailable or common_cutoff is None or "not_ready" in states:
        verdict = "no-go"
    elif "conditional" in states:
        verdict = "conditional go"
    else:
        verdict = "go"

    aligned_lag = max(0, (as_of - common_cutoff).days) if common_cutoff else None
    if aligned_lag is not None and aligned_lag > max_lag_days and verdict == "go":
        verdict = "conditional go"

    raw_profiles = [profile_series(series, as_of) for series in raw_series]
    history = build_history_samples(representatives)
    return {
        "prototype_question": "四证据家族能否用公开数据完成历史获取、UTC 日度对齐、缺失和新鲜度识别，并产出最小状态？",
        "as_of": as_of.isoformat(),
        "prototype_freshness_budget_days": max_lag_days,
        "common_cutoff": common_cutoff.isoformat() if common_cutoff else None,
        "common_cutoff_lag_days": aligned_lag,
        "data_feasibility_verdict": verdict,
        "overall_evidence_state": "gray_not_evaluated",
        "overall_evidence_reason": "本原型没有设定或校准证据阈值，不计算红黄绿证据结论",
        "families": families,
        "raw_series_profiles": raw_profiles,
        "history_samples": history,
        "source_metadata": dict(source_metadata),
    }


def build_history_samples(representatives: Mapping[str, TimeSeries]) -> list[dict]:
    output: list[dict] = []
    for label, target in BEAR_MARKET_SAMPLES:
        row: dict = {"sample": label, "target_date": target.isoformat(), "values": {}}
        complete = True
        for family in FAMILY_LABELS:
            series = representatives.get(family)
            if series is None or not series.values:
                row["values"][family] = None
                complete = False
                continue
            nearest = min(series.values, key=lambda d: abs((d - target).days))
            distance = abs((nearest - target).days)
            if distance > 3:
                row["values"][family] = None
                complete = False
            else:
                row["values"][family] = {
                    "date": nearest.isoformat(),
                    "distance_days": distance,
                    "value": series.values[nearest],
                    "unit": series.unit,
                }
        row["coverage_check"] = "pass" if complete else "gap"
        output.append(row)
    return output

