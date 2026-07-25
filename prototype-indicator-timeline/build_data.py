"""PROTOTYPE — build a flat indicator-validation dataset from public daily series.

This script deliberately has no dependency on the retired dashboard design.  It
fetches public base series, derives the indicators that can be reproduced
lightly, records direct-source checks, and writes one JSON payload for the local
interactive validation workbench.
"""

from __future__ import annotations

import csv
import http.client
import io
import json
import math
import statistics
import time
from collections import deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "timeline-data.json"
SCRIPT_OUTPUT = HERE / "timeline-data.js"
BITVIEW = "https://bitview.space/api/series/bulk"
BITVIEW_ORIGIN = date(2009, 1, 1)
OBM_ROOT = "https://raw.githubusercontent.com/diegorllanos/open-bitcoin-metrics/main/metrics"
USER_AGENT = "btc-indicator-validation-prototype/0.2"
GENESIS = date(2009, 1, 3)

BOTTOMS = (
    (date(2011, 11, 18), "2011 熊底参考"),
    (date(2015, 1, 14), "2015 熊底参考"),
    (date(2018, 12, 15), "2018 熊底参考"),
    (date(2022, 11, 21), "2022 熊底参考"),
)

BITVIEW_SERIES = (
    "price",
    "market_cap",
    "realized_cap",
    "liveliness",
    "subsidy_cumulative_usd",
    "subsidy_sum_24h_usd",
    "sth_supply",
    "sth_realized_cap",
    "asopr_24h",
    "hodled_or_lost_supply",
    "supply",
    "supply_in_profit",
    "supply_in_loss",
    "unrealized_profit",
    "coindays_destroyed_sum_24h",
    "realized_profit_sum_24h",
    "realized_loss_sum_24h",
    "sth_realized_profit_sum_24h",
    "sth_realized_loss_sum_24h",
    "lth_realized_profit_sum_24h",
    "lth_realized_loss_sum_24h",
    "reserve_risk",
    "price_volatility_1m",
    # Direct counterparts used only for reproducibility checks.
    "mvrv",
    "puell_multiple",
    "sth_mvrv",
    "supply_in_profit_share_ratio",
    "unrealized_profit_to_mcap_ratio",
    "realized_cap_delta_1m_rate_ratio",
    "realized_cap_delta_1w_rate_ratio",
    "seller_exhaustion",
    "thermo_cap_multiple",
)


def get_bytes(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/csv,*/*", "Connection": "close"},
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=90) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, http.client.IncompleteRead, ConnectionError) as error:
            last_error = error
            if attempt < 3:
                time.sleep(0.8 * (attempt + 1))
    assert last_error is not None
    raise last_error


def finite(value: object) -> float | None:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def fetch_bitview() -> tuple[dict[str, dict[date, float]], dict]:
    output: dict[str, dict[date, float]] = {}
    stamps: set[str] = set()
    versions: dict[str, int] = {}
    # Bitview enforces a weighted response budget. Two full-history daily
    # series stay below the current 320k limit even when both are F64.
    chunk_size = 2
    for offset in range(0, len(BITVIEW_SERIES), chunk_size):
        names = BITVIEW_SERIES[offset : offset + chunk_size]
        params = {"index": "day", "series": ",".join(names), "start": "2009-01-01"}
        payload = json.loads(get_bytes(f"{BITVIEW}?{urlencode(params)}"))
        if not isinstance(payload, list) or len(payload) != len(names):
            raise RuntimeError(f"Bitview bulk response mismatch for {names}")
        for name, item in zip(names, payload):
            start = int(item["start"])
            values: dict[date, float] = {}
            for index, raw_value in enumerate(item.get("data", [])):
                parsed = finite(raw_value)
                if parsed is not None:
                    values[BITVIEW_ORIGIN + timedelta(days=start + index)] = parsed
            if not values:
                raise RuntimeError(f"Bitview series is empty: {name}")
            output[name] = values
            versions[name] = int(item["version"])
            if item.get("stamp"):
                stamps.add(str(item["stamp"]))
    return output, {
        "provider": "BRK / Bitview",
        "endpoint": "https://bitview.space/api/series/bulk",
        "index_origin": BITVIEW_ORIGIN.isoformat(),
        "stamps": sorted(stamps),
        "versions": versions,
    }


def fetch_obm_scalar(series_id: str) -> dict[date, float]:
    url = f"{OBM_ROOT}/{series_id}/{series_id}.csv"
    text = get_bytes(url).decode("utf-8-sig")
    values: dict[date, float] = {}
    for row in csv.DictReader(io.StringIO(text)):
        parsed = finite(row.get("value"))
        if parsed is not None:
            values[date.fromisoformat(row["date"])] = parsed
    if not values:
        raise RuntimeError(f"OBM series is empty: {series_id}")
    return values


def aligned_ratio(numerator: dict[date, float], denominator: dict[date, float]) -> dict[date, float]:
    return {
        day: numerator[day] / denominator[day]
        for day in numerator.keys() & denominator.keys()
        if denominator[day] != 0
    }


def lag_change(values: dict[date, float], days: int, relative: bool) -> dict[date, float]:
    output: dict[date, float] = {}
    for day, value in values.items():
        previous = values.get(day - timedelta(days=days))
        if previous is None or (relative and previous == 0):
            continue
        output[day] = value / previous - 1 if relative else value - previous
    return output


def rolling_mean(values: dict[date, float], window: int) -> dict[date, float]:
    queue: deque[tuple[date, float]] = deque()
    total = 0.0
    output: dict[date, float] = {}
    for day in sorted(values):
        value = values[day]
        queue.append((day, value))
        total += value
        while queue and (day - queue[0][0]).days >= window:
            total -= queue.popleft()[1]
        if len(queue) == window:
            output[day] = total / window
    return output


def rolling_zscore(values: dict[date, float], window: int) -> dict[date, float]:
    queue: deque[tuple[date, float]] = deque()
    total = 0.0
    total_sq = 0.0
    output: dict[date, float] = {}
    for day in sorted(values):
        value = values[day]
        queue.append((day, value))
        total += value
        total_sq += value * value
        while queue and (day - queue[0][0]).days >= window:
            _, removed = queue.popleft()
            total -= removed
            total_sq -= removed * removed
        if len(queue) != window:
            continue
        mean = total / window
        variance = max(0.0, total_sq / window - mean * mean)
        if variance > 0:
            output[day] = (value - mean) / math.sqrt(variance)
    return output


def derive_aviv(raw: dict[str, dict[date, float]]) -> dict[date, float]:
    names = ("market_cap", "liveliness", "realized_cap", "subsidy_cumulative_usd")
    days = set.intersection(*(set(raw[name]) for name in names))
    output: dict[date, float] = {}
    for day in days:
        investor_cap = raw["realized_cap"][day] - raw["subsidy_cumulative_usd"][day]
        if investor_cap > 0:
            output[day] = raw["market_cap"][day] * raw["liveliness"][day] / investor_cap
    return output


def derive_puell(raw: dict[str, dict[date, float]]) -> dict[date, float]:
    subsidy = raw["subsidy_sum_24h_usd"]
    average = rolling_mean(subsidy, 365)
    return aligned_ratio(subsidy, average)


def derive_sth_mvrv(raw: dict[str, dict[date, float]]) -> dict[date, float]:
    days = raw["price"].keys() & raw["sth_supply"].keys() & raw["sth_realized_cap"].keys()
    return {
        day: raw["price"][day] * raw["sth_supply"][day] / raw["sth_realized_cap"][day]
        for day in days
        if raw["price"][day] > 0 and raw["sth_realized_cap"][day] > 0
    }


def derive_cvdd(raw: dict[str, dict[date, float]]) -> tuple[dict[date, float], dict[date, float]]:
    price = raw["price"]
    cdd = raw["coindays_destroyed_sum_24h"]
    running_value_destroyed = 0.0
    cvdd: dict[date, float] = {}
    proximity: dict[date, float] = {}
    for day in sorted(cdd):
        price_value = price.get(day)
        if price_value is not None and price_value > 0:
            running_value_destroyed += cdd[day] * price_value
        age_days = (day - GENESIS).days
        if age_days <= 0 or running_value_destroyed <= 0:
            continue
        floor = running_value_destroyed / (age_days * 6_000_000.0)
        cvdd[day] = floor
        if price_value is not None and floor > 0:
            proximity[day] = price_value / floor - 1.0
    return cvdd, proximity


def normalised_net(
    profit: dict[date, float], loss: dict[date, float], market_cap: dict[date, float]
) -> dict[date, float]:
    days = profit.keys() & loss.keys() & market_cap.keys()
    return {
        day: (profit[day] - loss[day]) / market_cap[day]
        for day in days
        if market_cap[day] > 0
    }


def normalised_component(
    values: dict[date, float], market_cap: dict[date, float], sign: float = 1.0
) -> dict[date, float]:
    return {
        day: sign * values[day] / market_cap[day]
        for day in values.keys() & market_cap.keys()
        if market_cap[day] > 0
    }


def derive_seller_exhaustion(raw: dict[str, dict[date, float]], psip: dict[date, float]) -> dict[date, float]:
    return aligned_product(psip, raw["price_volatility_1m"])


def aligned_product(left: dict[date, float], right: dict[date, float]) -> dict[date, float]:
    return {day: left[day] * right[day] for day in left.keys() & right.keys()}


def quantile(values: dict[date, float], probability: float) -> float:
    ordered = sorted(values.values())
    if not ordered:
        raise ValueError("empty quantile input")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def compare(derived: dict[date, float], direct: dict[date, float]) -> dict:
    errors: list[float] = []
    absolute: list[float] = []
    for day in derived.keys() & direct.keys():
        expected = direct[day]
        actual = derived[day]
        absolute.append(abs(actual - expected))
        if abs(expected) > 1e-12:
            errors.append(abs(actual - expected) / abs(expected))
    if not absolute:
        return {"overlap_rows": 0}
    return {
        "overlap_rows": len(absolute),
        "median_relative_error": statistics.median(errors) if errors else None,
        "p95_relative_error": quantile_list(errors, 0.95) if errors else None,
        "median_absolute_error": statistics.median(absolute),
    }


def quantile_list(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def serialise(values: dict[date, float]) -> list[list]:
    return [[day.isoformat(), float(f"{value:.10g}")] for day, value in sorted(values.items())]


def quality(values: dict[date, float]) -> dict:
    first = min(values)
    last = max(values)
    expected = (last - first).days + 1
    return {
        "rows": len(values),
        "start": first.isoformat(),
        "end": last.isoformat(),
        "missing_calendar_days": expected - len(values),
        "freshness_days": max(0, (date.today() - last).days),
    }


def reference(value: float, label: str) -> dict:
    return {"value": float(f"{value:.10g}"), "label": label}


def metric(
    metric_id: str,
    label: str,
    unit: str,
    description: str,
    formula: str,
    source: str,
    method: str,
    primary: dict[date, float],
    references: list[dict],
    direction: str,
    *,
    primary_line_label: str | None = None,
    primary_line_mode: str | None = None,
    extra_lines: list[tuple] | None = None,
    caveat: str = "",
    check: dict | None = None,
) -> dict:
    primary_line = {"id": "primary", "label": primary_line_label or label, "axis": "indicator", "series": serialise(primary)}
    if primary_line_mode:
        primary_line["mode"] = primary_line_mode
    lines = [primary_line]
    for item in extra_lines or []:
        line_id, line_label, values, axis, *optional_mode = item
        line = {"id": line_id, "label": line_label, "axis": axis, "series": serialise(values)}
        if optional_mode:
            line["mode"] = optional_mode[0]
        lines.append(line)
    line_modes = list(dict.fromkeys(line.get("mode") for line in lines if line.get("mode")))
    latest_day = max(primary)
    indicator_values = [value for line in lines if line["axis"] == "indicator" for _, value in line["series"]]
    return {
        "id": metric_id,
        "label": label,
        "unit": unit,
        "description": description,
        "formula": formula,
        "source": source,
        "method": method,
        "caveat": caveat,
        "lines": lines,
        "line_modes": line_modes,
        "default_line_mode": primary_line_mode or (line_modes[0] if line_modes else "all"),
        "default_references": references,
        "default_direction": direction,
        "indicator_log_available": bool(indicator_values) and min(indicator_values) > 0,
        "latest_date": latest_day.isoformat(),
        "latest_value": primary[latest_day],
        "quality": quality(primary),
        "reproduction_check": check,
    }


def main() -> int:
    raw, bitview_metadata = fetch_bitview()
    obm_total = fetch_obm_scalar("obm_spent_value_btc_daily")
    obm_long = fetch_obm_scalar("obm_spent_value_ge155d_btc_daily")

    mvrv = aligned_ratio(raw["market_cap"], raw["realized_cap"])
    aviv = derive_aviv(raw)
    puell = derive_puell(raw)
    rc_30d = lag_change(raw["realized_cap"], 30, True)
    rc_7d = lag_change(raw["realized_cap"], 7, True)
    sth_mvrv = derive_sth_mvrv(raw)
    hodler_npc = lag_change(raw["hodled_or_lost_supply"], 30, False)
    long_spent_share = aligned_ratio(obm_long, obm_total)
    psip = aligned_ratio(raw["supply_in_profit"], raw["supply"])
    supply_loss_share = aligned_ratio(raw["supply_in_loss"], raw["supply"])
    rup = aligned_ratio(raw["unrealized_profit"], raw["market_cap"])
    rup_zscore = rolling_zscore(rup, 1460)
    cvdd, cvdd_proximity = derive_cvdd(raw)
    sth_net = normalised_net(raw["sth_realized_profit_sum_24h"], raw["sth_realized_loss_sum_24h"], raw["market_cap"])
    lth_net = normalised_net(raw["lth_realized_profit_sum_24h"], raw["lth_realized_loss_sum_24h"], raw["market_cap"])
    sth_profit_component = normalised_component(raw["sth_realized_profit_sum_24h"], raw["market_cap"])
    sth_loss_component = normalised_component(raw["sth_realized_loss_sum_24h"], raw["market_cap"], -1.0)
    lth_profit_component = normalised_component(raw["lth_realized_profit_sum_24h"], raw["market_cap"])
    lth_loss_component = normalised_component(raw["lth_realized_loss_sum_24h"], raw["market_cap"], -1.0)
    net_realized = normalised_net(raw["realized_profit_sum_24h"], raw["realized_loss_sum_24h"], raw["market_cap"])
    seller_exhaustion = derive_seller_exhaustion(raw, psip)
    thermocap_multiple = aligned_ratio(raw["market_cap"], raw["subsidy_cumulative_usd"])

    metrics = [
        metric(
            "mvrv", "MVRV", "ratio", "市场价值相对全市场已实现成本基础。", "Market Cap / Realized Cap",
            "BRK / Bitview 基础日线", "自行计算", mvrv,
            [reference(1.0, "成本平衡线"), reference(0.8, "深度低估观察线")], "below",
            check=compare(mvrv, raw["mvrv"]),
        ),
        metric(
            "aviv", "AVIV", "ratio", "活跃价值相对投资者成本基础。",
            "(Market Cap × Liveliness) / (Realized Cap - Thermocap)",
            "BRK / Bitview 四条基础日线", "自行计算（ARK × Glassnode 原始定义）", aviv,
            [reference(0.65, "低估观察线"), reference(0.55, "深度低估参考")], "below",
            caveat="Bitview 成品 aviv_ratio 使用不同分子，本原型不拿它作同公式误差检查。",
        ),
        metric(
            "puell_multiple", "Puell Multiple", "ratio", "每日矿工补贴美元收入相对其一年均值。",
            "Subsidy USD / 365d Average Subsidy USD（BRK 按块计算后下采样）", "BRK / Bitview", "公开成品日线；另做日度复算核对", raw["puell_multiple"],
            [reference(1.0, "低收入区上界"), reference(0.5, "历史深压参考")], "below",
            caveat="本原型按日线复算与BRK按块计算后下采样存在可见口径差，因此主图采用BRK成品值，误差卡保留差异。",
            check=compare(puell, raw["puell_multiple"]),
        ),
        metric(
            "realized_cap_relative_npc_30d", "Realized Cap Relative NPC · 30d", "percent",
            "已实现市值相对30日前的变化。", "RC(t) / RC(t-30d) - 1",
            "BRK / Bitview Realized Cap", "自行计算", rc_30d,
            [reference(0.0, "资本扩张/收缩分界")], "above",
            check=compare(rc_30d, raw["realized_cap_delta_1m_rate_ratio"]),
        ),
        metric(
            "realized_cap_relative_npc_7d", "Realized Cap Relative NPC · 7d", "percent",
            "已实现市值相对7日前的短期变化。", "RC(t) / RC(t-7d) - 1",
            "BRK / Bitview Realized Cap", "自行计算", rc_7d,
            [reference(0.0, "短期扩张/收缩分界")], "above",
            check=compare(rc_7d, raw["realized_cap_delta_1w_rate_ratio"]),
        ),
        metric(
            "sth_mvrv", "STH-MVRV", "ratio", "150日以内UTXO的市场价值相对其已实现成本。",
            "Price × STH Supply / STH Realized Cap", "BRK / Bitview 基础日线", "自行计算（150日 cohort）", sth_mvrv,
            [reference(1.0, "短期持有者盈亏线"), reference(0.9, "浮亏观察线")], "below",
            caveat="这是 BRK 150 日 cohort，不是 Glassnode 155 日实体调整口径。",
            check=compare(sth_mvrv, raw["sth_mvrv"]),
        ),
        metric(
            "asopr", "aSOPR", "ratio", "排除寿命不足一小时输出后的已花费盈亏倍数。",
            "Adjusted spent value at spend / value at creation", "BRK / Bitview", "公开成品日线", raw["asopr_24h"],
            [reference(1.0, "已实现盈亏平衡")], "below",
            caveat="完整复算需要逐UTXO花费成本，本原型直接使用透明开源计算链的成品日线。",
        ),
        metric(
            "hodler_npc_30d", "HODLer Net Position Change · 30d", "btc",
            "HODLed or Lost Supply 的30日净变化。", "HODLedOrLostSupply(t) - HODLedOrLostSupply(t-30d)",
            "BRK / Bitview 基础日线", "自行计算", hodler_npc,
            [reference(0.0, "净积累/净释放分界"), reference(-50_000.0, "释放压力观察线")], "above",
        ),
        metric(
            "spent_value_ge155d_share", ">=155d 花费价值占比", "percent",
            "币龄至少155天的花费价值占全部花费价值比例。",
            "Spent Value >=155d / Total Spent Value", "Open Bitcoin Metrics v0.1.0", "自行计算", long_spent_share,
            [reference(quantile(long_spent_share, 0.9), "全样本90%分位（探索）")], "above",
            caveat="该序列是UTXO花费价值占比，不是LTH供应，也不等同交易所流入。",
        ),
        metric(
            "psip", "Percent Supply in Profit", "percent", "当前价格高于创建时价格的供应占比。",
            "Supply in Profit / Total Supply", "BRK / Bitview 基础日线", "自行计算", psip,
            [reference(0.5, "盈亏供应平衡"), reference(0.4, "广泛浮亏参考")], "below",
            check=compare(psip, raw["supply_in_profit_share_ratio"]),
        ),
        metric(
            "sipl", "Supply in Profit / Loss", "percent", "盈利供应与亏损供应两条曲线的交错。",
            "Profit Share = Supply in Profit / Supply; Loss Share = Supply in Loss / Supply",
            "BRK / Bitview 基础日线", "自行计算", psip,
            [reference(0.5, "两线理论交错参考")], "below",
            extra_lines=[("loss_share", "Supply in Loss", supply_loss_share, "indicator")],
            caveat="与 PSIP 是同一底层供应盈亏事实的双线表达。",
        ),
        metric(
            "relative_unrealized_profit", "Relative Unrealized Profit", "percent",
            "全网未实现盈利占市场价值的比例。", "Unrealized Profit / Market Cap",
            "BRK / Bitview 基础日线", "自行计算", rup,
            [reference(0.4, "低未实现盈利参考"), reference(0.3, "深低值观察线")], "below",
            check=compare(rup, raw["unrealized_profit_to_mcap_ratio"]),
        ),
        metric(
            "relative_unrealized_profit_zscore_4y", "RUP 4年滚动 z-score", "zscore",
            "Relative Unrealized Profit 相对过去1460日均值的标准差位置。",
            "(RUP - rolling mean 1460d) / rolling population std 1460d",
            "由本原型基于 RUP 计算", "自行计算", rup_zscore,
            [reference(-1.0, "低于均值1σ"), reference(-1.5, "低于均值1.5σ")], "below",
            caveat="这是明确版本化的4年滚动总体标准差，不冒充唯一官方RUP标准差。",
        ),
        metric(
            "cvdd_proximity", "CVDD 接近程度", "ratio",
            "BTC价格相对固定600万常数CVDD价格地板的距离。",
            "Price / [cumsum(CDD × Price) / (MarketAgeDays × 6,000,000)] - 1",
            "BRK / Bitview Price 与 CDD 基础日线", "自行计算（Willy Woo 2019 固定常数版）", cvdd_proximity,
            [reference(0.5, "高于CVDD 50%"), reference(0.0, "触及CVDD")], "below",
            extra_lines=[("cvdd", "CVDD 价格地板", cvdd, "price")],
            caveat="供应归一化CVDD是另一版本；本视图不混用。",
        ),
        metric(
            "lth_sth_normalized_net_realized_pnl", "LTH / STH Net Realized P/L", "percent",
            "长期与短期UTXO的每日已实现净盈亏占市值比例，两条曲线放在一起观察。",
            "Cohort Net P/L = (Cohort Realized Profit - Cohort Realized Loss) / Market Cap",
            "BRK / Bitview 基础日线", "自行计算（全链150日 cohort）", sth_net,
            [reference(0.0, "LTH/STH 净盈亏分界"), reference(quantile(sth_net, 0.05), "STH全样本5%分位（探索）")], "below",
            primary_line_label="STH Net Realized P/L",
            primary_line_mode="net",
            extra_lines=[
                ("lth_net_pnl", "LTH Net Realized P/L", lth_net, "indicator", "net"),
                ("sth_profit", "STH Realized Profit / Market Cap", sth_profit_component, "indicator", "split"),
                ("sth_loss", "STH Realized Loss / Market Cap", sth_loss_component, "indicator", "split"),
                ("lth_profit", "LTH Realized Profit / Market Cap", lth_profit_component, "indicator", "split"),
                ("lth_loss", "LTH Realized Loss / Market Cap", lth_loss_component, "indicator", "split"),
            ],
            caveat="可切换净盈亏双线或盈利/亏损四线；亏损按负值绘制。均为全链UTXO cohort，不是转入交易所子集。",
        ),
        metric(
            "normalized_net_realized_pnl", "Net Realized P/L / Market Cap", "percent",
            "全网每日已实现净盈亏占市值比例。",
            "(Realized Profit - Realized Loss) / Market Cap", "BRK / Bitview 基础日线", "自行计算", net_realized,
            [reference(0.0, "净盈亏分界"), reference(quantile(net_realized, 0.05), "全样本5%分位（探索）")], "below",
        ),
        metric(
            "reserve_risk", "Reserve Risk", "small",
            "价格相对HODL Bank的水平，结合长期持有信念与出售激励。",
            "Price / HODL Bank（BRK 实现）", "BRK / Bitview", "公开成品日线", raw["reserve_risk"],
            [reference(quantile(raw["reserve_risk"], 0.1), "全样本10%分位（探索）")], "below",
            caveat="完整复算依赖VOCDD与HODL Bank历史状态，本原型绑定BRK公开实现。",
        ),
        metric(
            "seller_exhaustion", "Seller Exhaustion Constant", "small",
            "低盈利供应与低波动共同出现的卖方耗竭状态。",
            "PSIP × BRK 30d Price Volatility", "BRK / Bitview 基础日线", "自行计算", seller_exhaustion,
            [reference(quantile(seller_exhaustion, 0.1), "全样本10%分位（探索）")], "below",
            check=compare(seller_exhaustion, raw["seller_exhaustion"]),
        ),
        metric(
            "thermocap_multiple", "Thermocap Multiple", "ratio",
            "市场价值相对累计矿工补贴美元价值的倍数。",
            "Market Cap / Subsidy Cumulative USD", "BRK / Bitview 基础日线", "自行计算", thermocap_multiple,
            [reference(quantile(thermocap_multiple, 0.1), "全样本10%分位（探索）")], "below",
            caveat="历史熊底倍数会跨周期漂移；分位线只供探索。",
            check=compare(thermocap_multiple, raw["thermo_cap_multiple"]),
        ),
    ]

    price = {day: value for day, value in raw["price"].items() if value > 0}
    payload = {
        "prototype": True,
        "question": "逐项叠加BTC价格、指标曲线与可编辑参考线，观察各指标是否能稳定提供熊底证据。",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_sources": {
            "bitview": bitview_metadata,
            "obm": {
                "provider": "Open Bitcoin Metrics v0.1.0",
                "endpoint_root": OBM_ROOT,
                "series": ["obm_spent_value_btc_daily", "obm_spent_value_ge155d_btc_daily"],
            },
        },
        "price": serialise(price),
        "price_quality": quality(price),
        "bottoms": [{"date": day.isoformat(), "label": label, "price": price.get(day)} for day, label in BOTTOMS],
        "metrics": metrics,
        "notes": [
            "这是一次性验证原型，不是交易信号或生产系统。",
            "参考线和有效/待定/无效判断只保存在当前页面内存，刷新后重置。",
            "带“全样本分位”的默认线含前视信息，只用于肉眼探索，不可直接当回测阈值。",
            "价格和指标各有独立线性/对数坐标开关；含零或负值的指标不能使用对数坐标。",
        ],
    }
    compact_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(compact_json, encoding="utf-8")
    SCRIPT_OUTPUT.write_text(f"window.__TIMELINE_DATA__={compact_json};\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.2f} MiB)")
    print(f"wrote {SCRIPT_OUTPUT} ({SCRIPT_OUTPUT.stat().st_size / 1024 / 1024:.2f} MiB)")
    print(f"price rows={len(price)} metrics={len(metrics)} latest={max(price)}")
    for item in metrics:
        check = item.get("reproduction_check") or {}
        median = check.get("median_relative_error")
        suffix = f" median-check={median:.4%}" if isinstance(median, float) else ""
        print(f"  {item['id']}: {item['quality']['rows']} rows through {item['latest_date']}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
