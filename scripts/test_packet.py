"""End-to-end packet assembly + contract check on real data.

Runs the real pipeline, builds a packet (with a mock AI analysis so the
today_available=true path is exercised), validates the contract, and writes the
result to a temp file via the atomic path to confirm round-trip integrity.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ai import provider  # noqa: E402
from services.data import fetch, metrics, packet  # noqa: E402
from services.evidence.compiler import compile_evidence  # noqa: E402


MOCK_ANALYSIS = {
    "analysis_date": None,  # filled to data_date at runtime
    "stage": "筑底证据积累期",
    "consistency": "中等",
    "summary": "多类证据向底部结构收敛，但尚未形成完整一致性。",
    "compact": {
        "support": {"title": "估值 + 矿工压力", "text": "核心估值与矿工压力类别已进入观察区。"},
        "obstacle": {"title": "持有者行为仍在积累", "text": "持有者类别证据仍需更多独立确认。"},
        "next": {"title": "核心类别继续收敛", "text": "等待更多核心类别同步确认。"},
    },
    "categories": [
        {"id": "valuation", "status": "充分确认", "note": ""},
        {"id": "supply", "status": "部分确认", "note": ""},
        {"id": "capital", "status": "部分确认", "note": ""},
        {"id": "holders", "status": "充分确认", "note": ""},
        {"id": "miners", "status": "部分确认", "note": ""},
        {"id": "anchors", "status": "未确认", "note": ""},
    ],
    "detailed": {
        "supporting": "估值与矿工压力类别提供核心支持证据。",
        "contrary": "持有者行为的投降信号仍不充分。",
        "next_stage": "需要核心类别与支持证据形成更完整的一致性。",
    },
}


def main() -> int:
    print("fetching ...")
    raw, bv = fetch.fetch_bitview()
    total, long, obm = fetch.fetch_obm_spent()
    computed = metrics.compute_indicators(raw, total, long, {"bitview": bv, "obm": obm})
    data_date = computed.data_date.isoformat()
    print(f"data_date={data_date} indicators={len(computed.indicators)}")

    # Path A: today unavailable, no fallback.
    pkt_fail = packet.build_packet(
        computed,
        analysis=None, fallback=None,
        today_available=False, last_success_date=None, reason="AI 暂不可用",
        run_id="test-fail-001", generated_at="2026-07-27T00:00:00Z",
    )
    assert pkt_fail["status"]["today_available"] is False
    assert pkt_fail["analysis"] is None
    print(f"Path A (failure) OK: analysis=null, reason={pkt_fail['status']['reason']}")

    # Path B: today available with mock analysis.
    snapshot = packet.build_snapshot(computed)
    evidence_brief = compile_evidence(snapshot, analysis_date=data_date)
    mock = provider._mock_analysis(data_date, evidence_brief)
    pkt_ok = packet.build_packet(
        computed,
        analysis=mock, fallback=None,
        today_available=True, last_success_date=data_date, reason=None,
        run_id="test-ok-001", generated_at="2026-07-27T00:00:00Z",
    )
    assert pkt_ok["status"]["today_available"] is True
    assert pkt_ok["analysis"]["stage"] in evidence_brief["allowed_stages"]
    print(f"Path B (success) OK: stage={pkt_ok['analysis']['stage']}")

    # Structure summary.
    m0 = pkt_ok["snapshot"]["metrics"][0]
    print(f"\nmetric sample ({m0['id']}): current={m0['current_value']} display='{m0['display_value']}' "
          f"tier='{m0['tier_label']}' thresholds={len(m0['thresholds'])}")
    print(f"series.metrics={len(pkt_ok['series']['metrics'])} price_points={len(pkt_ok['series']['price'])}")
    for bid, bar in pkt_ok["bars"].items():
        print(f"bar {bid}: {len(bar['points'])} pts, label='{bar['label']}'")

    # Atomic round-trip.
    tmp_path = ROOT / "artifacts" / "_tmp_packet_test.json"
    packet.write_packet_atomic(pkt_ok, tmp_path)
    reloaded = packet.load_packet(tmp_path)
    assert reloaded is not None and reloaded["run_id"] == "test-ok-001"
    tmp_path.unlink()
    print("\natomic write + reload + revalidate OK")

    # Contract must reject a date-inconsistent packet.
    bad = json.loads(json.dumps(pkt_ok))
    bad["analysis"]["analysis_date"] = "2020-01-01"  # mismatch with data_date
    try:
        packet.validate_packet(bad)
        print("CONTRACT FAIL: inconsistent analysis_date was accepted")
        return 1
    except packet.PacketValidationError as exc:
        print(f"contract correctly rejected date mismatch: {exc}")

    print("\nPACKET BUILD + CONTRACT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
