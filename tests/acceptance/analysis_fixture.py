from __future__ import annotations

import copy


def build_valid_analysis(packet: dict) -> dict:
    """Return a compact analysis aligned with the checked-in current snapshot."""

    analysis = packet.get("analysis") or packet.get("fallback")
    if not isinstance(analysis, dict):
        raise AssertionError("当前数据包缺少可复用的有效分析")
    return copy.deepcopy(analysis)
