from __future__ import annotations

import copy
import json
from pathlib import Path

from services.ai.provider import call_ai
from services.data.packet import validate_packet
from services import run_daily


ROOT = Path(__file__).resolve().parents[2]


def _packet() -> dict:
    return json.loads((ROOT / "dashboard" / "public" / "data" / "packet.json").read_text(encoding="utf-8"))


def test_mock_daily_analysis_contains_both_axes_and_full_explanation() -> None:
    packet = _packet()
    analysis, reason = call_ai(packet["snapshot"], data_date=packet["data_date"], mock=True, evidence_brief=packet["evidence_brief"])
    assert reason is None
    assert analysis is not None
    assert set(analysis["detailed"]) == {
        "pressure_reason",
        "bottoming_reason",
        "evidence_timeline",
        "contrary_or_gaps",
        "repair_exit",
        "next_evidence",
    }


def test_fallback_is_only_a_complete_v04_analysis() -> None:
    payload = _packet()
    failure = copy.deepcopy(payload)
    previous = failure["analysis"] or failure["fallback"]
    assert isinstance(previous, dict)
    failure["analysis"] = None
    failure["fallback"] = previous
    failure["status"] = {**failure["status"], "today_available": False, "reason": "模拟 AI 失败"}
    validate_packet(failure)
    assert failure["fallback"]["pressure_state"]
    assert "stage" not in failure["fallback"]


def test_previous_packet_archives_by_its_own_data_date(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    archive_dir = tmp_path / "archive"
    packet_path.write_text(json.dumps({"data_date": "2026-07-28", "schema_version": "0.4.0"}), encoding="utf-8")

    run_daily._archive_previous(packet_path, archive_dir, keep=7)

    archived = archive_dir / "2026-07-28.json"
    assert archived.exists()
    assert json.loads(archived.read_text(encoding="utf-8"))["data_date"] == "2026-07-28"
