from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from services.ai import provider
from services.data import packet


ROOT = Path(__file__).resolve().parents[2]
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"
FAILURE_PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet-failure.json"
NO_FALLBACK_PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet-no-fallback.json"


@pytest.fixture
def good() -> dict:
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def test_checked_in_packet_is_valid_and_single_entry() -> None:
    payload = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    packet.validate_packet(payload)
    assert payload["schema_version"] == "0.4.0"
    assert payload["snapshot"]["snapshot_date"] == payload["data_date"]


def test_rejects_old_stage_or_allowed_range(good: dict) -> None:
    good["evidence_brief"]["allowed_stages"] = ["旧阶段"]
    with pytest.raises(packet.PacketValidationError):
        packet.validate_packet(good)


def test_rejects_analysis_date_mismatch(good: dict) -> None:
    good["analysis"]["analysis_date"] = "2020-01-01"
    with pytest.raises(packet.PacketValidationError):
        packet.validate_packet(good)


def test_failure_packet_keeps_previous_v04_analysis() -> None:
    failure = json.loads(FAILURE_PACKET_PATH.read_text(encoding="utf-8"))
    packet.validate_packet(failure)
    assert failure["analysis"] is None
    assert failure["fallback"]["pressure_state"]
    assert failure["fallback"]["bottoming_state"]
    assert failure["status"]["today_available"] is False


def test_no_fallback_packet_retains_facts_without_analysis() -> None:
    no_fallback = json.loads(NO_FALLBACK_PACKET_PATH.read_text(encoding="utf-8"))
    packet.validate_packet(no_fallback)
    assert no_fallback["analysis"] is None
    assert no_fallback["fallback"] is None
    assert no_fallback["snapshot"]["metrics"]


def test_mock_provider_returns_compliant_v04_analysis() -> None:
    payload = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    analysis, reason = provider.call_ai(payload["snapshot"], data_date=payload["data_date"], mock=True)
    assert reason is None
    assert analysis and analysis["pressure_state"] and analysis["bottoming_state"]
