"""v0.2.4 chart-data contract: exported references and validation lines survive packaging."""

from __future__ import annotations

import hashlib
import copy
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from services.data import derive
from services.data.packet import PacketValidationError, validate_packet


ROOT = Path(__file__).resolve().parents[2]
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"
TIMELINE_PATH = ROOT / "prototype-indicator-timeline" / "timeline-data.json"
CONFIG_PATH = ROOT / "specs" / "v0.2.4" / "btc-indicator-config-2026-07-28.json"
CONFIG_SHA256 = "435BB97DF65A69F1C50E084AB3C18A048D2AED57699B1E2945BDC1B72C2AFF81"
TIMELINE_SHA256 = "15C6FF03ABDD0663F9357BC8675D670C637C4F15574236915CBC5B48D6FA163A"
CHART_OPTION_PATH = ROOT / "dashboard" / "src" / "composables" / "useChartOption.ts"

DISPLAY_TO_SOURCE = {
    "mvrv": "mvrv",
    "aviv": "aviv",
    "sth-mvrv": "sth_mvrv_price",
    "psip": "psip",
    "sipl": "sipl",
    "rup": "relative_unrealized_profit",
    "rul-z": "relative_unrealized_loss_zscore_4y",
    "rc-npc": "realized_cap_relative_npc_30d",
    "asopr": "asopr",
    "hodler": "hodler_npc_30d",
    "spent155": "spent_value_ge155d_share",
    "seller": "seller_exhaustion",
    "puell": "puell_multiple",
    "thermo": "thermocap_multiple_zscore",
    "cvdd": "cvdd_proximity",
    "reserve": "reserve_risk_zscore",
}

PUBLIC_LABEL_RENAMES = {
    "10%分位定投区": "10%分位观察区",
}


def _load_config() -> dict:
    assert CONFIG_PATH.exists(), f"缺少指标验证导出：{CONFIG_PATH}"
    normalized = CONFIG_PATH.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    digest = hashlib.sha256(normalized).hexdigest().upper()
    assert digest == CONFIG_SHA256
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_packet_reproduces_exported_reference_lines_and_all_timeline_lines() -> None:
    if not TIMELINE_PATH.exists():
        pytest.skip("本地原型时间线未纳入生产仓库")
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    config = _load_config()
    assert hashlib.sha256(TIMELINE_PATH.read_bytes()).hexdigest().upper() == TIMELINE_SHA256
    timeline = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    timeline_by_id = {metric["id"]: metric for metric in timeline["metrics"]}
    snapshot_by_id = {metric["id"]: metric for metric in packet["snapshot"]["metrics"]}

    assert set(DISPLAY_TO_SOURCE) == set(packet["series"]["metrics"])

    for display_id, source_id in DISPLAY_TO_SOURCE.items():
        entry = packet["series"]["metrics"][display_id]
        snapshot = snapshot_by_id[display_id]
        exported = config["metrics"][source_id]
        scale = 100 if snapshot["unit"] == "%" else 1
        published_references = [
            reference
            for reference in exported["references"]
            if reference.get("label") != "无参考线"
        ]

        assert [(item["value"], item["label"]) for item in entry["thresholds"]] == [
            (reference["value"] * scale, PUBLIC_LABEL_RENAMES.get(reference["label"], reference["label"]))
            for reference in published_references
        ]
        assert [item["direction"] for item in entry["thresholds"]] == [
            exported["direction"] for _ in published_references
        ]

        expected_lines = timeline_by_id[source_id]["lines"]
        assert [line["id"] for line in entry["lines"]] == [line["id"] for line in expected_lines]
        for actual, expected in zip(entry["lines"], expected_lines):
            if display_id == "reserve" and actual["id"] == "primary":
                # v0.2.1 deliberately shortened the public-facing name while
                # preserving the z-score series and exported reference lines.
                assert actual["label"] == "Reserve Risk · 周期"
            else:
                assert actual["label"] == expected["label"]
            assert actual["axis"] == expected["axis"]
            expected_points = [
                {"date": day, "value": value * scale}
                for day, value in expected["series"]
            ]
            # The exported timeline is a frozen regression baseline ending on
            # 2026-07-27. Daily production packets must preserve its historical
            # shape while allowing the source to revise its most recent 90 days
            # and allowing the pipeline to append newer dates.
            actual_baseline = actual["points"][: len(expected_points)]
            assert [point["date"] for point in actual_baseline] == [
                point["date"] for point in expected_points
            ]
            stable_cutoff = (
                date.fromisoformat(expected_points[-1]["date"])
                - timedelta(days=90)
            )
            for actual_point, expected_point in zip(
                actual_baseline, expected_points
            ):
                if display_id == "sth-mvrv" and actual["id"] != "primary":
                    # The three STH-RP tactical ladders are rebuilt across the
                    # full history whenever their live daily ratios change.
                    continue
                if date.fromisoformat(actual_point["date"]) <= stable_cutoff:
                    assert actual_point["value"] == pytest.approx(
                        expected_point["value"], rel=1e-9, abs=1e-9
                    )

            appended = actual["points"][len(expected_points) :]
            if appended:
                assert all(
                    point["date"] > expected_points[-1]["date"]
                    for point in appended
                )


def test_packet_rejects_malformed_line_axis_or_duplicate_id() -> None:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    bad_axis = copy.deepcopy(packet)
    bad_axis["series"]["metrics"]["sth-mvrv"]["lines"][1]["axis"] = "wrong"
    with pytest.raises(PacketValidationError):
        validate_packet(bad_axis)

    duplicate = copy.deepcopy(packet)
    duplicate["series"]["metrics"]["sipl"]["lines"][1]["id"] = "primary"
    with pytest.raises(PacketValidationError):
        validate_packet(duplicate)


def test_status_thresholds_match_chart_thresholds_except_dynamic_sth() -> None:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    snapshot_by_id = {metric["id"]: metric for metric in packet["snapshot"]["metrics"]}

    for display_id in DISPLAY_TO_SOURCE:
        snapshot_thresholds = snapshot_by_id[display_id]["thresholds"]
        chart_thresholds = packet["series"]["metrics"][display_id]["thresholds"]
        if display_id == "sth-mvrv":
            assert chart_thresholds == []
            assert [item["label"] for item in snapshot_thresholds] == [
                "观察区",
                "深度压力区",
                "极端压力区",
            ]
            assert all(isinstance(item["value"], (int, float)) for item in snapshot_thresholds)
            continue
        assert [
            (item["value"], item["direction"], item["label"])
            for item in snapshot_thresholds
        ] == [
            (item["value"], item["direction"], item["label"])
            for item in chart_thresholds
        ]


def test_sth_status_statistics_recalculate_when_latest_history_changes() -> None:
    start = date(2018, 1, 1)
    history = {
        start + timedelta(days=index): 1.0 + index / 100
        for index in range(40)
    }
    before_q5 = derive.live_anchored_quantile(history, 0.05)
    before_stats = derive.live_anchored_stats(history)
    history[start + timedelta(days=40)] = 0.1

    assert derive.live_anchored_quantile(history, 0.05) != before_q5
    assert derive.live_anchored_stats(history)["mean"] != before_stats["mean"]


def test_reserve_risk_display_label_is_period_only_in_every_fixture() -> None:
    """The dashboard-facing name removes ``z`` without changing z-score data."""
    for name in ("packet.json", "packet-failure.json", "packet-no-fallback.json"):
        packet = json.loads((ROOT / "dashboard" / "public" / "data" / name).read_text(encoding="utf-8"))
        reserve = next(metric for metric in packet["snapshot"]["metrics"] if metric["id"] == "reserve")
        assert reserve["label"] == "Reserve Risk · 周期"


def test_indicator_axis_uses_validation_workbench_percentile_bounds() -> None:
    """The public chart must use the validation panel's robust visible-range axis rule."""
    source = CHART_OPTION_PATH.read_text(encoding="utf-8")
    for expected in (
        "function adaptiveIndicatorBounds",
        "quantile(sortedValues, 0.02)",
        "quantile(sortedValues, 0.98)",
        "adaptiveIndicatorBounds(lineValues(\"indicator\"), thresholdValues)",
        "minimum - span * 0.08",
        "maximum + span * 0.08",
    ):
        assert expected in source
