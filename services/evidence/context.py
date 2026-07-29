"""Previous-three-natural-day context for the v0.4 AI input."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def is_v04_analysis(value: object) -> bool:
    return isinstance(value, Mapping) and isinstance(value.get("pressure_state"), str) and isinstance(value.get("bottoming_state"), str)


def _record_for_packet(packet: Mapping[str, Any]) -> tuple[str, Mapping[str, Any] | None, str]:
    status = packet.get("status")
    today_available = bool(status.get("today_available")) if isinstance(status, Mapping) else False
    analysis = packet.get("analysis")
    fallback = packet.get("fallback")
    if today_available and is_v04_analysis(analysis):
        return "current", analysis, str(packet.get("analysis_date") or analysis.get("analysis_date") or "")
    if is_v04_analysis(fallback):
        return "fallback", fallback, str(fallback.get("analysis_date") or packet.get("analysis_date") or "")
    if analysis is not None or fallback is not None:
        return "incompatible", None, str(packet.get("analysis_date") or "")
    return "missing", None, str(packet.get("analysis_date") or "")


def build_previous_three_day_context(
    analysis_date: str | date,
    records: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return exactly the three natural dates before ``analysis_date``.

    Missing dates remain explicit.  A fallback is labelled as a fallback and
    is never promoted to a newly judged day.  Pre-v0.4 analysis is retained as
    an incompatible record instead of being guessed into two axes.
    """

    if isinstance(analysis_date, date):
        day = analysis_date
    else:
        day = _parse_date(analysis_date)
    if day is None:
        raise ValueError("analysis_date 无效")
    by_date: dict[date, dict[str, Any]] = {}
    for packet in records or []:
        status, analysis, raw_date = _record_for_packet(packet)
        record_date = _parse_date(raw_date) or _parse_date(packet.get("data_date"))
        if record_date is None:
            continue
        item: dict[str, Any] = {
            "date": record_date.isoformat(),
            "status": status,
            "analysis_date": raw_date or None,
            "pressure_state": analysis.get("pressure_state") if analysis else None,
            "bottoming_state": analysis.get("bottoming_state") if analysis else None,
            "consistency": analysis.get("consistency") if analysis else None,
            "reason": analysis.get("summary") if analysis else "旧版本或不完整结果不能转换为双轴状态。",
        }
        by_date[record_date] = item

    result: list[dict[str, Any]] = []
    for offset in (3, 2, 1):
        target = day - timedelta(days=offset)
        result.append(by_date.get(target, {
            "date": target.isoformat(),
            "status": "missing",
            "analysis_date": None,
            "pressure_state": None,
            "bottoming_state": None,
            "consistency": None,
            "reason": "该自然日没有完整的 v0.4 判断结果。",
        }))
    return result


def state_change_facts(
    previous_context: Sequence[Mapping[str, Any]],
    current: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare today with the nearest usable prior v0.4 result."""

    def prior_for(axis: str) -> Mapping[str, Any] | None:
        key = f"{axis}_state"
        return next(
            (
                item
                for item in reversed(list(previous_context))
                if item.get("status") in {"current", "fallback"} and item.get(key)
            ),
            None,
        )

    pressure_rank = {
        "压力尚未明显": 0,
        "进入观察": 1,
        "深度压力": 2,
        "极端压力": 3,
    }
    bottoming_rank = {
        "未见筑底结构": 0,
        "筑底线索出现": 1,
        "筑底证据聚合": 2,
        "筑底证据较完整": 3,
        "市场修复中": 4,
        "已离开底部窗口": 5,
    }

    def reason_for(axis: str, old: object, new: object, changed: bool) -> str:
        if not changed:
            return "与最近可用结果相比没有明确状态变化。"
        if old == "数据不足" or new == "数据不足":
            return "可用数据或时间线发生变化，当前状态需要按新的数据边界重新判断。"
        ranks = pressure_rank if axis == "pressure" else bottoming_rank
        old_rank = ranks.get(str(old))
        new_rank = ranks.get(str(new))
        if axis == "bottoming" and str(new) in {"市场修复中", "已离开底部窗口"}:
            return "修复相关证据出现或持续，筑底过程进入修复/离开窗口的不同阶段。"
        if old_rank is not None and new_rank is not None and new_rank > old_rank:
            return "最新事实显示相关证据比最近可用结果更深或更完整。"
        if old_rank is not None and new_rank is not None and new_rank < old_rank:
            return "最新事实显示相关证据减弱，或过程出现回退。"
        return "最新事实与最近可用结果的组合发生变化。"

    result: dict[str, Any] = {}
    for axis in ("pressure", "bottoming"):
        key = f"{axis}_state"
        prior = prior_for(axis)
        old = prior.get(key) if prior else None
        new = current.get(key)
        changed = bool(old and new and old != new)
        result[axis] = {
            "changed": changed,
            "from": old,
            "to": new,
            "reason": reason_for(axis, old, new, changed),
            "compared_date": prior.get("date") if prior else None,
        }
    return result


__all__ = ["is_v04_analysis", "build_previous_three_day_context", "state_change_facts"]
