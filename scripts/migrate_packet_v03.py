"""Migrate checked-in dashboard packets to the v0.3 evidence contract.

This is an offline fixture migration.  It preserves the complete chart data,
then recomputes the deterministic evidence brief and replaces only the old
stage explanation with the v0.3 mock explanation so the public page exercises
the same contract as ``--mock-ai`` daily runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ai.provider import _mock_analysis  # noqa: E402
from services.data.packet import _decorate_snapshot_with_evidence  # noqa: E402
from services.evidence.compiler import compile_evidence  # noqa: E402


PACKET_DIR = ROOT / "dashboard" / "public" / "data"


def migrate(path: Path, current_analysis: dict | None) -> None:
    packet = json.loads(path.read_text(encoding="utf-8"))
    snapshot = packet["snapshot"]
    brief = compile_evidence(snapshot, analysis_date=packet["data_date"])
    _decorate_snapshot_with_evidence(snapshot, brief)

    packet["schema_version"] = "0.3.0"
    packet["config_version"] = "0.3.0"
    packet["evidence_brief"] = brief

    if current_analysis is not None:
        packet["analysis"] = current_analysis
    if packet.get("fallback") is not None:
        packet["fallback"] = current_analysis

    status = packet.setdefault("status", {})
    status["data_insufficient"] = not brief["data_quality"]["stage_ready"]
    status["data_quality"] = brief["data_quality"]
    path.write_text(json.dumps(packet, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    source = json.loads((PACKET_DIR / "packet.json").read_text(encoding="utf-8"))
    snapshot = source["snapshot"]
    brief = compile_evidence(snapshot, analysis_date=source["data_date"])
    analysis = _mock_analysis(source["data_date"], brief)

    migrate(PACKET_DIR / "packet.json", analysis)
    migrate(PACKET_DIR / "packet-failure.json", None)
    migrate(PACKET_DIR / "packet-no-fallback.json", None)

    # The fallback fixtures point at the migrated current explanation, while
    # no-fallback remains deliberately empty.
    failure_path = PACKET_DIR / "packet-failure.json"
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    failure["fallback"] = analysis
    failure["status"]["today_available"] = False
    failure["analysis"] = None
    failure_path.write_text(json.dumps(failure, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    no_fallback_path = PACKET_DIR / "packet-no-fallback.json"
    no_fallback = json.loads(no_fallback_path.read_text(encoding="utf-8"))
    no_fallback["fallback"] = None
    no_fallback["analysis"] = None
    no_fallback["status"]["today_available"] = False
    no_fallback_path.write_text(json.dumps(no_fallback, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("migrated packet.json, packet-failure.json, packet-no-fallback.json to v0.3.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
