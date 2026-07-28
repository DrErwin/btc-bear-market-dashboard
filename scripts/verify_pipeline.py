"""Verify the migrated services/data pipeline matches the validated prototype.

Runs the real fetch+derive path, prints a summary, and (if the prototype's
timeline-data.json exists) cross-checks every indicator's latest value against
it. Run from the repo root:

    python scripts/verify_pipeline.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.data import fetch, metrics  # noqa: E402


def main() -> int:
    print("fetching Bitview + OBM ...")
    raw, bv_meta = fetch.fetch_bitview()
    obm_total, obm_long, obm_meta = fetch.fetch_obm_spent()
    source_metadata = {"bitview": bv_meta, "obm": obm_meta}
    print(f"  bitview series={len(raw)} obm_total={len(obm_total)} obm_long={len(obm_long)}")

    result = metrics.compute_indicators(raw, obm_total, obm_long, source_metadata)
    print(f"\nindicators={len(result.indicators)} price_rows={len(result.price)} data_date={result.data_date}")
    by_id = {ind.id: ind for ind in result.indicators}
    catalogue = list(metrics.INDICATOR_CATALOG)
    missing = [mid for mid in catalogue if mid not in by_id]
    if missing:
        print(f"  MISSING indicators: {missing}")
        return 1
    extra = [ind.id for ind in result.indicators if ind.id not in metrics.INDICATOR_CATALOG]
    if extra:
        print(f"  UNEXPECTED indicators: {extra}")
        return 1

    print(f"\n{'id':<34} {'latest_date':<12} {'latest_value':>16}  category/core")
    for ind in result.indicators:
        latest_day = max(ind.primary)
        print(f"  {ind.id:<32} {latest_day.isoformat():<12} {ind.primary[latest_day]:>16.6g}  {ind.category}/{ind.core}")

    # bars
    print(f"\nbars: {list(result.bars)}")
    for bar in result.bars.values():
        print(f"  {bar.id}: {len(bar.series)} non-null days")

    # Parity vs prototype timeline-data.json (if present).
    proto = ROOT / "prototype-indicator-timeline" / "timeline-data.json"
    if proto.exists():
        payload = json.loads(proto.read_text(encoding="utf-8"))
        proto_by_id = {m["id"]: m for m in payload.get("metrics", [])}
        print(f"\nparity vs {proto.name} ({len(proto_by_id)} proto metrics):")
        mismatches = 0
        for mid, ind in by_id.items():
            if mid not in proto_by_id:
                continue
            mine = ind.primary[max(ind.primary)]
            theirs = proto_by_id[mid]["latest_value"]
            rel = abs(mine - theirs) / (abs(theirs) or 1e-12)
            flag = "" if rel < 1e-9 else "  <-- MISMATCH"
            if rel >= 1e-9:
                mismatches += 1
            print(f"  {mid:<32} mine={mine:.10g} proto={theirs:.10g} rel={rel:.3g}{flag}")
        if mismatches:
            print(f"\nPARITY FAIL: {mismatches} indicator(s) differ")
            return 1
        print("\nPARITY OK: every shared indicator matches the prototype exactly.")
    else:
        print("\n(prototype timeline-data.json not found — run build_data.py to enable parity check)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
