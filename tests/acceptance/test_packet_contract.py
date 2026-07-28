"""Requirement 1 + 4 contract tests for the single dashboard packet.

Covers the acceptance criteria:
* "自动化测试能拒绝缺少任一必填部分、日期不一致或 AI 输出不合规的数据包"
* whole-packet fallback semantics (today unavailable => analysis null,
  previous success carried as fallback, packet still complete and valid)
* the AI provider returns (None, reason) on every failure mode so run_daily
  never publishes a half-built packet
* the API key is never required locally and never appears in outputs
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.ai import provider  # noqa: E402
from services.data import packet  # noqa: E402
from services.data.packet import PacketValidationError  # noqa: E402


PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"


@pytest.fixture(scope="session")
def good_packet() -> dict:
    packet_data = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    if packet_data["analysis"] is None:
        # The public packet may legitimately be in whole-packet fallback mode.
        # Contract mutation tests need a canonical success packet regardless of
        # today's provider state, so promote the visible fallback in-memory.
        packet_data["analysis"] = copy.deepcopy(packet_data["fallback"])
        packet_data["status"] = {
            "today_available": True,
            "last_success_date": packet_data["analysis"]["analysis_date"],
            "reason": None,
        }
    return packet_data


@pytest.fixture
def good(good_packet: dict) -> dict:
    return copy.deepcopy(good_packet)


def _rejected(payload: dict) -> None:
    with pytest.raises(PacketValidationError):
        packet.validate_packet(payload)


# --- Requirement 1: reject incomplete packets ---

def test_rejects_missing_snapshot(good: dict) -> None:
    del good["snapshot"]
    _rejected(good)


def test_rejects_missing_series(good: dict) -> None:
    del good["series"]
    _rejected(good)


def test_rejects_missing_bars(good: dict) -> None:
    del good["bars"]
    _rejected(good)


def test_rejects_missing_status(good: dict) -> None:
    del good["status"]
    _rejected(good)


def test_rejects_wrong_metric_count(good: dict) -> None:
    good["snapshot"]["metrics"].append(copy.deepcopy(good["snapshot"]["metrics"][0]))
    _rejected(good)


def test_rejects_wrong_category_count(good: dict) -> None:
    good["snapshot"]["categories"].pop()
    _rejected(good)


# --- Requirement 1: reject date-inconsistent packets ---

def test_rejects_snapshot_date_mismatch(good: dict) -> None:
    good["snapshot"]["snapshot_date"] = "2020-01-01"
    _rejected(good)


def test_rejects_series_end_mismatch(good: dict) -> None:
    good["series"]["price"][-1]["date"] = "2020-01-01"
    _rejected(good)


def test_rejects_analysis_date_mismatch(good: dict) -> None:
    good["analysis"]["analysis_date"] = "2020-01-01"
    _rejected(good)


# --- Requirement 1: today_available must agree with analysis presence ---

def test_rejects_today_available_without_analysis(good: dict) -> None:
    good["analysis"] = None
    _rejected(good)


def test_rejects_analysis_present_when_unavailable(good: dict) -> None:
    good["status"]["today_available"] = False
    _rejected(good)


# --- Requirement 1/4: reject AI-noncompliant language anywhere in analysis/fallback ---

def test_rejects_forbidden_ai_language_in_analysis(good: dict) -> None:
    good["analysis"]["summary"] = "建议买入并提高仓位"
    _rejected(good)


def test_rejects_forbidden_probability_in_fallback(good: dict) -> None:
    if good.get("fallback") is None:
        good["fallback"] = copy.deepcopy(good["analysis"])
    good["fallback"]["detailed"]["supporting"] = "熊底概率为 78%"
    _rejected(good)


# --- Atomic publish never writes an invalid packet ---

def test_write_atomic_rejects_invalid(good: dict, tmp_path: Path) -> None:
    del good["snapshot"]
    target = tmp_path / "packet.json"
    with pytest.raises(PacketValidationError):
        packet.write_packet_atomic(good, target)
    assert not target.exists()


def test_load_returns_none_for_invalid(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert packet.load_packet(bad) is None


def test_load_returns_none_when_absent(tmp_path: Path) -> None:
    assert packet.load_packet(tmp_path / "absent.json") is None


# --- Requirement 1: traceable header ---

def test_packet_header_is_traceable(good: dict) -> None:
    for field in ("schema_version", "run_id", "generated_at", "data_date", "config_version", "analysis_date"):
        assert field in good
    assert good["input_summary"]["metric_count"] == 16
    assert good["input_summary"]["category_count"] == 6


# --- Requirement 1: whole-packet fallback keeps the previous success ---

def test_failure_packet_keeps_previous_analysis(good: dict) -> None:
    previous_analysis = copy.deepcopy(good["analysis"])
    previous_date = previous_analysis["analysis_date"]

    fail = copy.deepcopy(good)
    fail["analysis"] = None
    fail["analysis_date"] = previous_date
    fail["fallback"] = previous_analysis
    fail["status"] = {
        "today_available": False,
        "last_success_date": previous_date,
        "reason": "AI 分析不可用（模拟）",
    }
    # The failure packet is still a COMPLETE, contract-valid packet — it simply
    # surfaces the previous success as fallback. Nothing is half-built.
    packet.validate_packet(fail)
    assert fail["analysis"] is None
    assert fail["fallback"]["stage"] == previous_analysis["stage"]
    assert fail["status"]["last_success_date"] == previous_date


# --- Requirement 4: provider failure modes all return (None, reason) ---

def test_provider_no_key_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
    analysis, reason = provider.call_ai({}, data_date="2026-07-27", mock=False)
    assert analysis is None
    assert isinstance(reason, str) and reason


def test_provider_mock_returns_compliant() -> None:
    analysis, reason = provider.call_ai({}, data_date="2026-07-27", mock=True)
    assert reason is None
    assert analysis is not None
    assert analysis["stage"] == "筑底证据积累期"
    assert analysis["analysis_date"] == "2026-07-27"


def test_api_key_never_leaks_in_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_API_KEY", "sk-SECRET-TOKEN-VALUE")
    # Force the chat call to fail fast so we exercise the failure path.
    monkeypatch.setattr(provider, "_chat", lambda *a, **k: (_ for _ in ()).throw(ConnectionError("refused")))
    analysis, reason = provider.call_ai({}, data_date="2026-07-27", mock=False)
    assert analysis is None
    assert "SECRET" not in (reason or "")
    assert "sk-" not in (reason or "")


# --- Requirement 4: a data-source failure must NOT overwrite the previous packet ---

def test_run_daily_data_source_failure_skips_publish(
    good_packet: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import run_daily

    packet_path = tmp_path / "packet.json"
    packet.write_packet_atomic(good_packet, packet_path)
    previous_run_id = good_packet["run_id"]

    def boom() -> tuple[dict, dict]:
        raise ConnectionError("simulated data-source outage")

    monkeypatch.setattr(run_daily.fetch, "fetch_bitview", boom)

    rc = run_daily.run(
        mock_ai=False,
        packet_path=packet_path,
        log_path=tmp_path / "run-log.jsonl",
        archive_dir=tmp_path / "archive",
        max_stale_days=2,
        keep_history=7,
    )

    assert rc == 0
    # The previous complete packet is left untouched.
    result = packet.load_packet(packet_path)
    assert result is not None
    assert result["run_id"] == previous_run_id
    # The run log records a skipped run (no half-built packet published).
    log = (tmp_path / "run-log.jsonl").read_text(encoding="utf-8")
    assert '"outcome": "skipped"' in log
    assert "数据源抓取失败" in log
