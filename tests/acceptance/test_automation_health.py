from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.automation_health import (
    DailyAutomationDegraded,
    PacketDateRegression,
    check_daily_outcome,
    check_packet_regression,
)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_packet_guard_rejects_a_fixture_that_moves_production_date_backwards(tmp_path: Path) -> None:
    previous = tmp_path / "previous.json"
    current = tmp_path / "current.json"
    _write_json(previous, {"data_date": "2026-07-29"})
    _write_json(current, {"data_date": "2026-07-28"})

    with pytest.raises(PacketDateRegression, match="2026-07-29.*2026-07-28"):
        check_packet_regression(previous, current)


def test_packet_guard_allows_same_or_newer_date(tmp_path: Path) -> None:
    previous = tmp_path / "previous.json"
    current = tmp_path / "current.json"
    _write_json(previous, {"data_date": "2026-07-29"})

    for data_date in ("2026-07-29", "2026-07-30"):
        _write_json(current, {"data_date": data_date})
        check_packet_regression(previous, current)


@pytest.mark.parametrize("outcome", ["published-fallback", "skipped"])
def test_daily_health_marks_stale_or_fallback_runs_as_degraded(tmp_path: Path, outcome: str) -> None:
    log_path = tmp_path / "run-log.jsonl"
    log_path.write_text(
        json.dumps({"run_id": "test", "outcome": outcome, "reason": "fixture"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DailyAutomationDegraded, match=outcome):
        check_daily_outcome(log_path)


@pytest.mark.parametrize("outcome", ["published-fresh", "published-data-insufficient"])
def test_daily_health_accepts_published_current_analysis(tmp_path: Path, outcome: str) -> None:
    log_path = tmp_path / "run-log.jsonl"
    log_path.write_text(json.dumps({"run_id": "test", "outcome": outcome}) + "\n", encoding="utf-8")
    check_daily_outcome(log_path)
