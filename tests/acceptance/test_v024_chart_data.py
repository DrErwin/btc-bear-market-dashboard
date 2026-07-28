"""v0.2.4 chart-data contract: exported references and validation lines survive packaging."""

from __future__ import annotations

import hashlib
import copy
import json
from pathlib import Path

import pytest

from services.data.packet import PacketValidationError, validate_packet


ROOT = Path(__file__).resolve().parents[2]
PACKET_PATH = ROOT / "dashboard" / "public" / "data" / "packet.json"
TIMELINE_PATH = ROOT / "prototype-indicator-timeline" / "timeline-data.json"
CONFIG_PATH = Path(r"C:\Users\57652\Downloads\btc-indicator-config-2026-07-28.json")
CONFIG_SHA256 = "CAD0028AF77A30065A42D0C47181DEB8256434DC2410C4B2128391D4477EBC98"
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


def _load_config() -> dict:
    assert CONFIG_PATH.exists(), f"缺少指标验证导出：{CONFIG_PATH}"
    digest = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest().upper()
    assert digest == CONFIG_SHA256
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_packet_reproduces_exported_reference_lines_and_all_timeline_lines() -> None:
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

        assert [(item["value"], item["label"]) for item in entry["thresholds"]] == [
            (reference["value"] * scale, reference["label"])
            for reference in exported["references"]
        ]
        assert [item["direction"] for item in entry["thresholds"]] == [
            exported["direction"] for _ in exported["references"]
        ]

        expected_lines = timeline_by_id[source_id]["lines"]
        assert [line["id"] for line in entry["lines"]] == [line["id"] for line in expected_lines]
        for actual, expected in zip(entry["lines"], expected_lines):
            assert actual["label"] == expected["label"]
            assert actual["axis"] == expected["axis"]
            assert actual["points"] == [
                {"date": day, "value": value * scale}
                for day, value in expected["series"]
            ]


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
