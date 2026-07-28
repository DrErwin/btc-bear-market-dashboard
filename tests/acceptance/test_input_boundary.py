from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path

from services.ai.input_builder import build_ai_input


ROOT = Path(__file__).resolve().parents[2]
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"


def load_snapshot() -> dict:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    return packet["snapshot"]


def walk_keys(value: object):
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_input_builder_emits_only_the_approved_snapshot_boundary() -> None:
    snapshot = load_snapshot()
    request = build_ai_input(load_snapshot())

    assert set(request) == {
        "market_stage_definitions",
        "category_status_definitions",
        "consistency_definitions",
        "category_definitions",
        "metrics",
    }
    assert len(request["metrics"]) == 16

    assert [item["stage"] for item in request["market_stage_definitions"]] == [
        "尚未进入熊底观察期",
        "熊市下行期",
        "深度压力期",
        "筑底证据积累期",
        "熊底证据充分期",
        "数据不足",
    ]
    assert [item["status"] for item in request["category_status_definitions"]] == [
        "未确认",
        "部分确认",
        "充分确认",
    ]
    assert [item["consistency"] for item in request["consistency_definitions"]] == [
        "弱",
        "中等",
        "强",
    ]

    metric_keys = {
        "id",
        "name",
        "meaning",
        "category",
        "role",
        "current_value",
        "thresholds",
    }
    threshold_keys = {"value", "direction", "label", "meaning"}
    source_by_id = {metric["id"]: metric for metric in snapshot["metrics"]}

    for metric in request["metrics"]:
        assert set(metric) == metric_keys
        source = source_by_id[metric["id"]]
        assert metric["name"] == source["label"]
        assert metric["meaning"] == source["description"]
        assert metric["category"] == source["category"]
        assert metric["role"] == source["role"]
        assert metric["current_value"] == source["current_value"]
        trigger_thresholds = [
            threshold
            for threshold in source["thresholds"]
            if threshold.get("role", "trigger") != "neutral"
        ]
        assert len(metric["thresholds"]) == len(trigger_thresholds)
        assert all(set(threshold) == threshold_keys for threshold in metric["thresholds"])


def test_input_builder_excludes_neutral_chart_reference_lines() -> None:
    snapshot = copy.deepcopy(load_snapshot())
    thermocap = next(
        metric for metric in snapshot["metrics"] if metric["id"] == "thermo"
    )
    neutral = next(
        threshold
        for threshold in thermocap["thresholds"]
        if threshold["label"] == "自身4年均值（中性）"
    )
    neutral["role"] = "neutral"

    request = build_ai_input(snapshot)
    ai_thermocap = next(
        metric for metric in request["metrics"] if metric["id"] == "thermo"
    )

    assert all(
        threshold["label"] != "自身4年均值（中性）"
        for threshold in ai_thermocap["thresholds"]
    )


def test_input_builder_excludes_history_external_context_and_raw_source_metadata() -> None:
    request = build_ai_input(load_snapshot())
    keys = {key.casefold() for key in walk_keys(request)}

    forbidden_keys = {
        "series",
        "trend",
        "news",
        "external",
        "external_research",
        "user_portfolio",
        "portfolio",
        "price",
        "snapshot_date",
        "current_date",
        "display_value",
        "formula",
        "source",
        "method",
        "caveat",
        "tier_label",
        "tier_meaning",
    }
    assert keys.isdisjoint(forbidden_keys)
