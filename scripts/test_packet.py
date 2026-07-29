"""End-to-end packet assembly and v0.4 contract check on real data.

This maintenance script runs the fetch/derive path, creates a deterministic
dual-axis mock analysis, validates the complete packet, and checks atomic
write/read integrity. It is not the offline acceptance entry point.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ai import provider  # noqa: E402
from services.ai.input_builder import build_evidence_input  # noqa: E402
from services.data import fetch, metrics, packet  # noqa: E402
from services.evidence.compiler import compile_evidence  # noqa: E402


def main() -> int:
    print("fetching ...")
    raw, bv = fetch.fetch_bitview()
    total, long, obm = fetch.fetch_obm_spent()
    computed = metrics.compute_indicators(raw, total, long, {"bitview": bv, "obm": obm})
    data_date = computed.data_date.isoformat()
    print(f"data_date={data_date} indicators={len(computed.indicators)}")

    pkt_fail = packet.build_packet(
        computed,
        analysis=None,
        fallback=None,
        today_available=False,
        last_success_date=None,
        reason="AI 暂不可用",
        run_id="test-fail-001",
        generated_at="2026-07-27T00:00:00Z",
    )
    assert pkt_fail["status"]["today_available"] is False
    assert pkt_fail["analysis"] is None
    print(f"Path A (failure) OK: analysis=null, reason={pkt_fail['status']['reason']}")

    snapshot = packet.build_snapshot(computed)
    evidence_brief = compile_evidence(snapshot, analysis_date=data_date)
    ai_input = build_evidence_input(snapshot, evidence_brief=evidence_brief)
    mock = provider._mock_analysis(data_date, evidence_brief, ai_input)
    pkt_ok = packet.build_packet(
        computed,
        analysis=mock,
        fallback=None,
        today_available=True,
        last_success_date=data_date,
        reason=None,
        run_id="test-ok-001",
        generated_at="2026-07-27T00:00:00Z",
    )
    assert pkt_ok["status"]["today_available"] is True
    assert pkt_ok["analysis"]["pressure_state"]
    assert pkt_ok["analysis"]["bottoming_state"]
    print(
        f"Path B (success) OK: pressure={pkt_ok['analysis']['pressure_state']} "
        f"bottoming={pkt_ok['analysis']['bottoming_state']}"
    )

    metric = pkt_ok["snapshot"]["metrics"][0]
    print(
        f"\nmetric sample ({metric['id']}): current={metric['current_value']} "
        f"display='{metric['display_value']}' tier='{metric['tier_label']}' "
        f"thresholds={len(metric['thresholds'])}"
    )
    print(f"series.metrics={len(pkt_ok['series']['metrics'])} price_points={len(pkt_ok['series']['price'])}")
    for bid, bar in pkt_ok["bars"].items():
        print(f"bar {bid}: {len(bar['points'])} pts, label='{bar['label']}'")

    tmp_path = ROOT / "artifacts" / "_tmp_packet_test.json"
    packet.write_packet_atomic(pkt_ok, tmp_path)
    reloaded = packet.load_packet(tmp_path)
    assert reloaded is not None and reloaded["run_id"] == "test-ok-001"
    tmp_path.unlink()
    print("\natomic write + reload + revalidate OK")

    bad = json.loads(json.dumps(pkt_ok))
    bad["analysis"]["analysis_date"] = "2020-01-01"
    try:
        packet.validate_packet(bad)
        print("CONTRACT FAIL: inconsistent analysis_date was accepted")
        return 1
    except packet.PacketValidationError as exc:
        print(f"contract correctly rejected date mismatch: {exc}")

    print("\nPACKET BUILD + V0.4 CONTRACT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
