from __future__ import annotations

import json
from pathlib import Path

from services.data.packet import validate_packet


ROOT = Path(__file__).resolve().parents[2]


def load_packet() -> dict:
    return json.loads((ROOT / "dashboard" / "public" / "data" / "packet.json").read_text(encoding="utf-8"))


def test_checked_in_packet_is_a_v04_complete_evidence_package() -> None:
    packet = load_packet()
    validate_packet(packet)
    assert packet["schema_version"] == "0.4.0"
    assert packet["config_version"] == "0.4.0"
    assert len(packet["evidence_brief"]["metric_states"]) == 16
    assert set(packet["evidence_brief"]["axis_readiness"]) == {"pressure", "bottoming"}
    assert "allowed_stages" not in packet["evidence_brief"]


def test_analysis_has_two_independent_axes_and_six_detail_sections() -> None:
    analysis = load_packet()["analysis"]
    assert analysis["pressure_state"]
    assert analysis["bottoming_state"]
    assert len(analysis["detailed"]) == 6
