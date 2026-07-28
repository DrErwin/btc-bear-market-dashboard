from __future__ import annotations

import json
from pathlib import Path

from services.data.packet import validate_packet


ROOT = Path(__file__).resolve().parents[2]
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"


def load_packet() -> dict:
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def test_checked_in_packet_is_a_v03_complete_evidence_package() -> None:
    packet = load_packet()
    validate_packet(packet)
    assert packet["schema_version"] == "0.3.0"
    assert packet["config_version"] == "0.3.0"
    assert len(packet["snapshot"]["metrics"]) == 16
    assert len(packet["evidence_brief"]["metric_states"]) == 16
    assert packet["analysis"]["stage"] in packet["evidence_brief"]["allowed_stages"]


def test_checked_in_packet_separates_role_from_judgment_status() -> None:
    packet = load_packet()
    by_id = {metric["id"]: metric for metric in packet["snapshot"]["metrics"]}
    assert by_id["mvrv"]["role"] == "核心锚"
    assert by_id["aviv"]["role"] == "核心复核"
    assert by_id["rul-z"]["role"] == "强辅助"
    assert by_id["hodler"]["role"] == "辅助"
    assert by_id["hodler"]["availability_status"] == "display_only"
    assert by_id["spent155"]["availability_status"] == "display_only"
    assert by_id["cvdd"]["availability_status"] == "validation_pending"
    assert by_id["hodler"]["judgment_eligible"] is False
    assert by_id["spent155"]["judgment_eligible"] is False
    assert by_id["cvdd"]["judgment_eligible"] is False


def test_checked_in_packet_exposes_strong_auxiliary_pressure_when_present() -> None:
    packet = load_packet()
    if packet["evidence_brief"]["strong_auxiliary_themes"]:
        assert packet["analysis"].get("pressure_summary")
        assert "压力" in packet["analysis"]["pressure_summary"]
        assert "阶段上限" not in packet["analysis"]["pressure_summary"]
