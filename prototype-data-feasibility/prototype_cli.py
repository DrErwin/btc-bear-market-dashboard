"""PROTOTYPE — throwaway terminal shell for four-family data feasibility."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from data_sources import fetch_all
from feasibility_logic import FAMILY_LABELS, build_feasibility_state


BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"


def _fmt(value, unit: str | None = None) -> str:
    if value is None:
        return "—"
    if unit == "USD/BTC":
        return f"${value:,.2f}"
    if unit == "USD":
        return f"${value:,.0f}"
    if unit == "share":
        return f"{value * 100:.3f}%"
    if unit == "ratio":
        return f"{value:.4f}"
    return f"{value:,.4f}"


def _clear() -> None:
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def render_summary(state: dict) -> str:
    lines = [
        f"{BOLD}PROTOTYPE — 四证据家族最小状态{RESET}",
        f"评估日: {state['as_of']}  共同截止日: {state['common_cutoff']}  "
        f"共同滞后: {state['common_cutoff_lag_days']} 天",
        f"数据可行性: {BOLD}{state['data_feasibility_verdict']}{RESET}",
        f"证据结论: 灰 / 未评估（没有设置正式阈值）",
        "",
        f"{'家族':<12} {'候选代表':<31} {'数据状态':<12} {'最新日期':<12} {'共同日数值':>16}",
        "-" * 92,
    ]
    for item in state["families"]:
        lines.append(
            f"{item['family_label']:<12} {item.get('metric_label', '—'):<31} "
            f"{item['data_state']:<12} {item.get('latest_date', '—'):<12} "
            f"{_fmt(item.get('aligned_value'), item.get('unit')):>16}"
        )
    lines.extend(["", f"{DIM}状态理由{RESET}"])
    for item in state["families"]:
        lines.append(f"- {item['family_label']}: {item['reason']}")
    return "\n".join(lines)


def render_coverage(state: dict) -> str:
    lines = [
        f"{BOLD}原始序列覆盖、缺失与新鲜度{RESET}",
        f"{'序列':<31} {'起始':<12} {'结束':<12} {'行数':>7} {'缺失':>7} {'最长断档':>9} {'滞后':>7}",
        "-" * 98,
    ]
    for item in state["raw_series_profiles"]:
        lines.append(
            f"{item['label']:<31} {item['coverage_start'] or '—':<12} {item['coverage_end'] or '—':<12} "
            f"{item['row_count']:>7} {str(item['missing_days']):>7} {str(item['longest_gap_days']):>9} "
            f"{str(item['freshness_lag_days']):>5} 天"
        )
    lines.extend([
        "",
        f"{DIM}注：缺失按各序列自身首尾日期之间的 UTC 日历日计算；首日前没有覆盖不计作断档。{RESET}",
    ])
    return "\n".join(lines)


def render_history(state: dict) -> str:
    lines = [
        f"{BOLD}主要熊市阶段基础覆盖检查（非回测、无阈值）{RESET}",
        "每个样本仅检查目标日前后 3 天内是否存在四家族数据，并显示原始/派生数值。",
        "",
    ]
    family_order = tuple(FAMILY_LABELS)
    for sample in state["history_samples"]:
        lines.append(f"{sample['sample']} / {sample['target_date']} / coverage={sample['coverage_check']}")
        for family in family_order:
            value = sample["values"][family]
            if value is None:
                rendered = "—"
            else:
                rendered = f"{value['date']}  {_fmt(value['value'], value['unit'])}  距目标 {value['distance_days']} 天"
            lines.append(f"  - {FAMILY_LABELS[family]}: {rendered}")
        lines.append("")
    lines.append(f"{DIM}这些数值只证明历史样本可被表示，不证明指标有效，也不冻结任何阈值。{RESET}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Throwaway BTC evidence-family data feasibility prototype")
    parser.add_argument("--once", action="store_true", help="print summary, coverage and history, then exit")
    parser.add_argument("--max-lag-days", type=int, default=3, help="prototype freshness budget; not a product threshold")
    parser.add_argument("--as-of", type=date.fromisoformat, help="fixed evaluation date in YYYY-MM-DD")
    parser.add_argument("--json-out", type=Path, help="optional path for a JSON snapshot")
    return parser.parse_args()


def load_state(as_of: date, max_lag_days: int) -> dict:
    bundle = fetch_all()
    return build_feasibility_state(
        bundle.representatives,
        bundle.candidates,
        bundle.raw_series,
        as_of,
        max_lag_days,
        bundle.source_metadata,
    )


def main() -> int:
    args = parse_args()
    if args.max_lag_days < 0:
        raise SystemExit("--max-lag-days must be >= 0")
    as_of = args.as_of or datetime.now(timezone.utc).date()
    print("正在拉取公开日度数据……", flush=True)
    state = load_state(as_of, args.max_lag_days)

    if args.json_out:
        args.json_out.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.once or not sys.stdin.isatty():
        print(render_summary(state))
        print("\n" + render_coverage(state))
        print("\n" + render_history(state))
        return 0

    mode = "s"
    while True:
        _clear()
        if mode == "s":
            print(render_summary(state))
        elif mode == "c":
            print(render_coverage(state))
        elif mode == "b":
            print(render_history(state))
        elif mode == "j":
            print(json.dumps(state, ensure_ascii=False, indent=2))
        print("\n[s] 最小状态  [c] 覆盖/缺失  [b] 熊市样本  [j] JSON  [r] 重新拉取  [q] 退出")
        command = input("> ").strip().lower()[:1]
        if command == "q":
            return 0
        if command == "r":
            state = load_state(as_of, args.max_lag_days)
            mode = "s"
        elif command in {"s", "c", "b", "j"}:
            mode = command


if __name__ == "__main__":
    raise SystemExit(main())

