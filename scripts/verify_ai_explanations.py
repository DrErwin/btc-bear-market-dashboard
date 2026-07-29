"""Run repeatable v0.4 AI explanation checks against fixed evidence scenarios.

With ``--real`` and ``AI_API_KEY`` this calls the configured provider.  Without
that flag it uses the deterministic mock path used by local acceptance.  The
artifact records dual-axis states and readiness; it never reports a legacy
single-stage range as an answer.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ai import provider, semantic_validator, validator  # noqa: E402
from services.ai.input_builder import build_evidence_input  # noqa: E402
from services.data.packet import _decorate_snapshot_with_evidence  # noqa: E402
from services.evidence.compiler import compile_evidence  # noqa: E402
from tests.acceptance.evidence_test_utils import clone_snapshot  # noqa: E402


FIXTURE_PATH = ROOT / "tests" / "fixtures" / "evidence" / "v0.3.0-scenarios.json"
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"
ARTIFACT_DIR = ROOT / "artifacts" / "review-evidence" / "v0.4.0"


def _load_scenarios() -> list[dict]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    templates = fixture["metric_templates"]
    scenarios: list[dict] = []
    for raw in fixture["scenarios"]:
        metrics = {metric_id: dict(template) for metric_id, template in templates.items()}
        for metric_id, override in raw.get("metric_overrides", {}).items():
            metrics[metric_id].update(override)
        scenarios.append({**raw, "analysis_date": fixture["analysis_date"], "metrics": metrics})
    return scenarios


def _snapshot_for_scenario(base_snapshot: dict, scenario: dict) -> dict:
    snapshot = clone_snapshot(base_snapshot)
    by_canonical = {}
    from services.evidence.catalog import canonical_id_for_snapshot_id  # local import keeps script startup clear

    for metric in snapshot["metrics"]:
        by_canonical[canonical_id_for_snapshot_id(metric["id"])] = metric
    for canonical_id, fact in scenario["metrics"].items():
        metric = by_canonical[canonical_id]
        metric["current_value"] = fact["current_value"]
        metric["current_date"] = fact["metric_date"]
    snapshot["snapshot_date"] = scenario["analysis_date"]
    return snapshot


def _compact_analysis(analysis: dict | None) -> dict | None:
    if analysis is None:
        return None
    return {
        "analysis_date": analysis.get("analysis_date"),
        "pressure_state": analysis.get("pressure_state"),
        "bottoming_state": analysis.get("bottoming_state"),
        "consistency": analysis.get("consistency"),
        "summary": analysis.get("summary"),
        "compact": analysis.get("compact"),
        "detailed": analysis.get("detailed"),
    }


def run(*, real: bool) -> tuple[dict, int]:
    base_packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    base_snapshot = base_packet["snapshot"]
    records: list[dict] = []
    failures: list[str] = []

    for scenario in _load_scenarios():
        snapshot = _snapshot_for_scenario(base_snapshot, scenario)
        brief = compile_evidence(snapshot, analysis_date=scenario["analysis_date"])
        _decorate_snapshot_with_evidence(snapshot, brief)
        ai_input = build_evidence_input(snapshot, evidence_brief=brief)
        analysis, reason = provider.call_ai(
            snapshot,
            data_date=scenario["analysis_date"],
            mock=not real,
            evidence_brief=brief,
        )
        if analysis is None:
            failures.append(f"{scenario['id']}: no v0.4 analysis: {reason}")
        else:
            try:
                validator.validate_analysis(analysis)
                semantic_validator.validate_analysis_semantics(analysis, ai_input)
            except validator.InvalidAnalysisError as exc:
                failures.append(f"{scenario['id']}: {'; '.join(exc.errors[:3])}")
        records.append(
            {
                "scenario_id": scenario["id"],
                "description": scenario["description"],
                "axis_readiness": brief["axis_readiness"],
                "ai_input": ai_input,
                "provider_mode": "real" if real else "mock",
                "analysis": _compact_analysis(analysis),
                "reason": reason,
            }
        )

    artifact = {
        "artifact_version": "0.4.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_mode": "real" if real else "mock",
        "records": records,
        "failures": failures,
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "ai-explanations.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"provider_mode": artifact["provider_mode"], "scenarios": len(records), "failures": failures}, ensure_ascii=False))
    return artifact, 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify v0.4 AI explanations against fixed evidence briefs")
    parser.add_argument("--real", action="store_true", help="call the configured AI provider instead of mock mode")
    args = parser.parse_args()
    _, code = run(real=args.real)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
