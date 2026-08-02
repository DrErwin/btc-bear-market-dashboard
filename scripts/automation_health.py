"""Health checks for the production packet and the daily automation result."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import date
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_PATH = "dashboard/public/data/packet.json"
DEFAULT_LOG_PATH = ROOT / "artifacts" / "run-log.jsonl"
HEALTHY_OUTCOMES = {"published-fresh", "published-data-insufficient"}


class PacketDateRegression(RuntimeError):
    """Raised when a committed production packet moves to an older data date."""


class DailyAutomationDegraded(RuntimeError):
    """Raised when the latest daily run did not publish a current analysis."""


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} 必须包含一个 JSON 对象")
    return value


def _data_date(packet: Mapping[str, object], source: str) -> date:
    raw = packet.get("data_date")
    if not isinstance(raw, str):
        raise ValueError(f"{source} 缺少 data_date")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{source} 的 data_date 无效: {raw}") from exc


def check_packet_values(previous: Mapping[str, object], current: Mapping[str, object]) -> None:
    previous_date = _data_date(previous, "上一版生产数据包")
    current_date = _data_date(current, "当前生产数据包")
    if current_date < previous_date:
        raise PacketDateRegression(
            f"生产数据日期从 {previous_date.isoformat()} 回退到 {current_date.isoformat()}；"
            "请把测试数据放入 tests/fixtures，不要覆盖 dashboard/public/data/packet.json"
        )


def check_packet_regression(previous_path: Path, current_path: Path) -> None:
    check_packet_values(_load_json(previous_path), _load_json(current_path))


def _git_json(revision: str, path: str) -> dict:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise ValueError(f"{revision}:{path} 必须包含一个 JSON 对象")
    return value


def check_git_packet_regression(base_revision: str, head_revision: str, packet_path: str) -> None:
    check_packet_values(
        _git_json(base_revision, packet_path),
        _git_json(head_revision, packet_path),
    )


def _last_log_record(log_path: Path) -> dict:
    records = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        raise DailyAutomationDegraded("运行日志为空，无法确认每日更新结果")
    value = json.loads(records[-1])
    if not isinstance(value, dict):
        raise DailyAutomationDegraded("最后一条运行日志不是 JSON 对象")
    return value


def check_daily_outcome(log_path: Path) -> dict:
    record = _last_log_record(log_path)
    outcome = record.get("outcome")
    if outcome not in HEALTHY_OUTCOMES:
        reason = record.get("reason") or "未记录原因"
        raise DailyAutomationDegraded(f"{outcome}: {reason}")
    return record


def _write_github_summary(title: str, body: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write(f"## {title}\n\n{body}\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    packet = subparsers.add_parser("packet-regression")
    packet.add_argument("--base", required=True)
    packet.add_argument("--head", required=True)
    packet.add_argument("--packet-path", default=DEFAULT_PACKET_PATH)

    outcome = subparsers.add_parser("daily-outcome")
    outcome.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "packet-regression":
            check_git_packet_regression(args.base, args.head, args.packet_path)
            print("Production packet date did not regress.")
        else:
            record = check_daily_outcome(args.log_path)
            message = f"outcome={record.get('outcome')} run_id={record.get('run_id')}"
            print(message)
            _write_github_summary("Daily automation healthy", message)
    except (DailyAutomationDegraded, PacketDateRegression, ValueError, OSError, subprocess.SubprocessError) as exc:
        message = str(exc).replace("\r", " ").replace("\n", " ")
        print(f"::error title=Daily automation degraded::{message}")
        _write_github_summary("Daily automation degraded", message)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
