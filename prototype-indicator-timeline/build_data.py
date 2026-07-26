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

# Methodology window for honest (no-lookahead) thresholds:
#   - ANCHOR drops the immature pre-2018 market (MVRV-style peaks decay over
#     cycles; early data pollutes cross-cycle absolute thresholds).
#   - CURRENT_CYCLE_START = last *completed* bear bottom. Honest thresholds use
#     ONLY data at/before it, so the threshold for finding the current bottom is
#     derived from past bears, never the current cycle or the future.
ANCHOR = date(2018, 1, 1)
CURRENT_CYCLE_START = BOTTOMS[-1][0]

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


def past_cycle_quantile(values: dict[date, float], probability: float) -> float:
    """Empirical quantile over ONLY completed past-cycle data (no lookahead).

    A full-sample ``quantile(values, p)`` leaks the future AND the current cycle
    into the threshold -- the lookahead bias flagged in the handoff. Restricting
    the sample to ``ANCHOR..CURRENT_CYCLE_START`` (i.e. up to the last completed
    bear bottom) means the threshold for finding the *current* bottom is derived
    solely from past bears, matching the project methodology ("past bears ->
    threshold -> current bear") rather than fitting a static truth to history.
    """
    sample = [value for day, value in values.items() if ANCHOR <= day <= CURRENT_CYCLE_START]
    if len(sample) < 30:
        # Series lacks enough pre-current-cycle history (e.g. a late-starting
        # cohort). Fall back to anchored full sample: still drops immature
        # pre-2018 data and contains no future, but does include this cycle.
        sample = [value for day, value in values.items() if day >= ANCHOR]
        print(
            f"  warn: past-cycle sample too small for p={probability}; "
            f"using anchored full sample ({len(sample)} pts, includes current cycle)"
        )
    return quantile_list(sample, probability)


def past_cycle_stats(values: dict[date, float]) -> dict[str, float]:
    """Mean / population-std / median / MAD over the no-lookahead past-cycle window.

    Same window convention as ``past_cycle_quantile`` ([ANCHOR, CURRENT_CYCLE_START],
    with the <30 fallback), so the STH-MVRV tactical-price statistical methods are
    computed on identical, lookahead-free data. Population std matches
    ``rolling_zscore``'s basis; MAD is returned raw (callers scale by 1.4826 for a
    sigma-equivalent).
    """
    sample = [value for day, value in values.items() if ANCHOR <= day <= CURRENT_CYCLE_START]
    if len(sample) < 30:
        sample = [value for day, value in values.items() if day >= ANCHOR]
        print(
            f"  warn: past-cycle sample too small for stats; "
            f"using anchored full sample ({len(sample)} pts, includes current cycle)"
        )
    median = statistics.median(sample)
    mad = statistics.median([abs(value - median) for value in sample])
    return {
        "mean": statistics.mean(sample),
        "pstdev": statistics.pstdev(sample),
        "median": median,
        "mad": mad,
    }


def ladder(level: float, values: dict[date, float]) -> dict[date, float]:
    """Scale a series by a constant -- turns an MVRV threshold into a price ladder
    via Price = threshold x STH-RP."""
    return {day: level * value for day, value in values.items()}


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
    sth_mvrv = derive_sth_mvrv(raw)
    hodler_npc = lag_change(raw["hodled_or_lost_supply"], 30, False)
    hodler_npc_share = aligned_ratio(hodler_npc, raw["supply"])
    # HODLer selling spikes (negative NPC) = capitulation at bear bottoms, but
    # also distribution at bull tops. Gate to MVRV<1 to isolate bear capitulation
    # (Glassnode LTH Capitulation Risk: MVRV<1 & SOPR<1). Deep-sell thresholds
    # are no-lookahead past-cycle percentiles of the normalized NPC.
    hodler_npc_capitulation = {
        day: hodler_npc_share[day]
        for day in hodler_npc_share
        if day in mvrv and mvrv[day] < 1.0
    }
    hodler_deep_10 = past_cycle_quantile(hodler_npc_share, 0.10)
    hodler_deep_5 = past_cycle_quantile(hodler_npc_share, 0.05)
    long_spent_share = aligned_ratio(obm_long, obm_total)
    # Old-coin spending is dual-natured: tops = profit-taking distribution,
    # bottoms = loss capitulation. Gate the share to MVRV<1 undervaluation days
    # so spikes there mark capitulation (Glassnode's LTH Capitulation Risk uses
    # MVRV<1 AND SOPR<1; we keep MVRV<1 here for more visible events). This is a
    # confirmation line, not a standalone trigger.
    spent_share_undervalued = {
        day: long_spent_share[day]
        for day in long_spent_share
        if day in mvrv and mvrv[day] < 1.0
    }
    psip = aligned_ratio(raw["supply_in_profit"], raw["supply"])
    supply_loss_share = aligned_ratio(raw["supply_in_loss"], raw["supply"])
    rup = aligned_ratio(raw["unrealized_profit"], raw["market_cap"])
    rup_zscore = rolling_zscore(rup, 1460)
    # Relative Unrealized Loss has no published Bitview stock series (only the profit
    # stock exists); derive via the exact identity NUPL = RUP - RUL  <=>  RUL = RUP -
    # NUPL, with NUPL = 1 - 1/MVRV (Unrealized P/L = Market Cap - Realized Cap).
    # mvrv is computed above. Clipped at 0 to absorb rounding noise.
    nupl = {day: 1.0 - 1.0 / value for day, value in mvrv.items() if value}
    rul = {day: max(0.0, rup[day] - nupl[day]) for day in rup.keys() & nupl.keys()}
    rul_zscore = rolling_zscore(rul, 1460)
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

    # --- No-lookahead reference thresholds (Task A) -------------------------
    # These six lines used to be full-sample quantiles, i.e. the threshold
    # "knew the future". They now use only completed past-cycle data. The
    # console prints the migration (old full-sample -> new past-cycle) so the
    # shift is visible for manual review.
    honest_targets = {
        "spent_share_q90": (long_spent_share, 0.9),
        "sth_net_q05": (sth_net, 0.05),
        "net_realized_q05": (net_realized, 0.05),
        "reserve_risk_q10": (raw["reserve_risk"], 0.1),
        "seller_exhaustion_q10": (seller_exhaustion, 0.1),
        "thermocap_q10": (thermocap_multiple, 0.1),
    }
    honest: dict[str, float] = {}
    print("threshold migration (full-sample -> past-cycle, lookahead removed):")
    for key, (series, probability) in honest_targets.items():
        old_value = quantile(series, probability)
        honest[key] = past_cycle_quantile(series, probability)
        print(f"  {key:<26} {old_value:>14.6g} -> {honest[key]:>14.6g}")

    # --- STH-MVRV tactical-price levels (three statistical methods) ---
    # Price = STH-MVRV x STH-RP, so an MVRV low-threshold x STH-RP(t) is a concrete
    # buy-price ladder. Thresholds computed on the no-lookahead past-cycle window.
    sth_rp = aligned_ratio(raw["sth_realized_cap"], raw["sth_supply"])
    sth_stats = past_cycle_stats(sth_mvrv)
    _sigma = sth_stats["pstdev"]
    _mad_sigma = 1.4826 * sth_stats["mad"]
    sth_levels = {
        "q5": past_cycle_quantile(sth_mvrv, 0.05),
        "mean_1_5": sth_stats["mean"] - 1.5 * _sigma,
        "median_1_5": sth_stats["median"] - 1.5 * _mad_sigma,
    }
    sth_ladders = {key: ladder(level, sth_rp) for key, level in sth_levels.items()}
    _latest_rp = sth_rp[max(sth_rp)]
    print("STH-MVRV tactical-price levels (window [2018, 2022-bottom], no lookahead):")
    for _key in ("q5", "mean_1_5", "median_1_5"):
        print(f"  {_key:<12} MVRV={sth_levels[_key]:.5f}  -> price~${sth_levels[_key] * _latest_rp:,.0f}")

    # --- Reserve Risk log z-score (cross-cycle normalization) ---
    # RR = Price / HODL Bank; HODL Bank is a monotonic cumulative, so RR's
    # absolute level drifts down ~0.4x per cycle (2013->2017->2021->2024 cycle
    # peaks: 1.5e-4 -> 7.0e-5 -> 2.8e-5 -> 1.0e-5). Fixed absolute thresholds
    # (Glassnode 0.002/0.0027) are permanently tripped this cycle, and the
    # past-cycle quantile is biased low by the drift. log() turns the
    # exponential decline linear; a trailing 4y (1460d) z-score then measures
    # high/low vs RR's own recent cycle, so tops/bottoms land at comparable z
    # across cycles. Thresholds are z-quantiles on the no-lookahead window.
    rr = raw["reserve_risk"]
    log_rr = {day: math.log(value) for day, value in rr.items() if value > 0}
    rr_zscore = rolling_zscore(log_rr, 1460)
    rr_z_q10 = past_cycle_quantile(rr_zscore, 0.10)
    rr_z_q05 = past_cycle_quantile(rr_zscore, 0.05)
    _latest_rr_z = rr_zscore[max(rr_zscore)]
    print("Reserve Risk log z-score (trailing 4y, cross-cycle normalized):")
    print(f"  current z = {_latest_rr_z:.3f}")
    print(f"  past-cycle 10%ile z = {rr_z_q10:.3f}  |  5%ile z = {rr_z_q05:.3f}")

    # --- Thermocap Multiple log z-score (relative-cycle view) ---
    # Thermocap = MarketCap / cumulative subsidy. Unlike RR, structural drift
    # here is mild: tops oscillate (2013/2017/2021 = 60/74/51) and the bottom
    # slowly RISES (halvings slow the denominator, baseline mcap creeps up:
    # 4.7 -> 5.7 -> 6.8). So z-score isn't fixing a severe monotonic decline
    # (there isn't one) -- it removes the slow bottom creep and gives a
    # "hot/cold vs its own 4y cycle" view. Absolute tops/bots (5-7 bot, 50-74
    # top) stay valid; this is a supplementary relative-heat lens.
    log_tc = {day: math.log(value) for day, value in thermocap_multiple.items() if value > 0}
    tc_zscore = rolling_zscore(log_tc, 1460)
    tc_z_q10 = past_cycle_quantile(tc_zscore, 0.10)
    tc_z_q05 = past_cycle_quantile(tc_zscore, 0.05)
    _latest_tc_z = tc_zscore[max(tc_zscore)]
    print("Thermocap Multiple log z-score (trailing 4y, relative-cycle view):")
    print(f"  current z = {_latest_tc_z:.3f}")
    print(f"  past-cycle 10%ile z = {tc_z_q10:.3f}  |  5%ile z = {tc_z_q05:.3f}")

    # --- aSOPR trailing-SMA secondary lines (causal / no-lookahead) ---
    # Daily aSOPR is jagged (weekly cadence + one-off old-coin spends). A trailing
    # SMA cleans the regime/trend view BUT erases the capitulation spike that LEADS
    # the bottom (~10d). So raw stays primary -- the capitulation band fires on raw;
    # these SMAs are trend/regime aides only. rolling_mean is causal ([day-W+1, day]).
    asopr_3d = rolling_mean(raw["asopr_24h"], 3)
    asopr_7d = rolling_mean(raw["asopr_24h"], 7)

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
            "sth_mvrv", "STH-MVRV", "ratio", "150日以内UTXO的市场价值相对其已实现成本。",
            "Price × STH Supply / STH Realized Cap", "BRK / Bitview 基础日线", "自行计算（150日 cohort）", sth_mvrv,
            [reference(1.0, "短期持有者盈亏线"), reference(0.9, "浮亏观察线")], "below",
            caveat="这是 BRK 150 日 cohort，不是 Glassnode 155 日实体调整口径。",
            check=compare(sth_mvrv, raw["sth_mvrv"]),
        ),
        metric(
            "sth_mvrv_price", "STH-MVRV 战术价位（三法合并）", "ratio",
            "STH-MVRV 三套统计抄底档合并：5%分位 / 1.5σ / 1.5·MAD；价位阶梯 = 档位 × STH-RP（Price = STH-MVRV × STH-RP）。",
            "Q5 / (mean−1.5σ) / (median−1.5·1.4826·MAD)，各 × STH-RP；阈值在无前视窗口 [2018,2022底] 上算",
            "BRK / Bitview 基础日线", "自行计算（无前视）", sth_mvrv,
            [
                reference(sth_levels["q5"], "5%分位（无前视）"),
                reference(sth_levels["mean_1_5"], "1.5σ（无前视）"),
                reference(sth_levels["median_1_5"], "1.5·MAD（无前视）"),
            ], "below",
            extra_lines=[
                ("q5_price", "5%分位 × STH-RP", sth_ladders["q5"], "price"),
                ("mean_1_5_price", "1.5σ × STH-RP", sth_ladders["mean_1_5"], "price"),
                ("median_1_5_price", "1.5·MAD × STH-RP", sth_ladders["median_1_5"], "price"),
            ],
            caveat="三法对照：5%分位最浅(挂高先成交)、1.5σ居中偏浅(MVRV右偏致σ偏松)、1.5·MAD最深(抄深)。references[0]=5%分位为触发线。阈值无前视。",
        ),
        metric(
            "asopr", "aSOPR", "ratio", "排除寿命不足一小时输出后的已花费盈亏倍数。",
            "Adjusted spent value at spend / value at creation", "BRK / Bitview", "公开成品日线", raw["asopr_24h"],
            [reference(1.0, "已实现盈亏平衡")], "below",
            extra_lines=[
                ("sma_3d", "3日滞后均值（趋势辅助）", asopr_3d, "indicator"),
                ("sma_7d", "7日滞后均值（趋势辅助）", asopr_7d, "indicator"),
            ],
            caveat="完整复算需要逐UTXO花费成本，本原型直接使用透明开源计算链的成品日线。原始日线为投降尖峰信号（触发线挂原始）；3d/7d为滞后均值（rolling_mean，无前视），仅作制度/趋势可读性辅助——会削平并滞后尖峰，不作触发。",
        ),
        metric(
            "hodler_npc_30d", "HODLer 投降卖出尖峰 · 占供应%", "percent",
            "HODLed or Lost Supply 的30日净积累占供应。负尖峰=大额卖出：牛市=派发、熊底=投降；用 MVRV<1 门控副线隔离熊市投降。",
            "[HODLedOrLostSupply(t) − HODLedOrLostSupply(t−30d)] / Supply",
            "BRK / Bitview 基础日线", "自行计算（% of supply）", hodler_npc_share,
            [
                reference(hodler_deep_10, "深卖阈值·10%分位（无前视）"),
                reference(hodler_deep_5, "深卖阈值·5%分位（无前视）"),
                reference(0.0, "积累/卖出分界"),
            ], "below",
            extra_lines=[("hodler_npc_capitulation", "低估期卖出（MVRV<1）", hodler_npc_capitulation, "indicator")],
            caveat="投降是尖峰事件、不平滑。深卖阈值=过去周期[2018,2022底]NPC的5/10%分位（无前视）；副线只在 MVRV<1 显示=熊市投降（与 Glassnode LTH Capitulation Risk 同路）。原BTC口径=Glassnode LTH-NetPositionChange。",
        ),
        metric(
            "spent_value_ge155d_share", ">=155d 花费价值占比", "percent",
            "币龄至少155天的花费价值占全部花费价值比例（老币花费）。顶底都会spike：顶部=获利派发，底部=投降；降为确认指标。",
            "Spent Value >=155d / Total Spent Value", "Open Bitcoin Metrics v0.1.0", "自行计算", long_spent_share,
            [reference(honest["spent_share_q90"], "过去周期90%分位（无前视）")], "above",
            extra_lines=[("undervalued_old_spent", "低估期老币花费（MVRV<1）", spent_share_undervalued, "indicator")],
            caveat="老币花费顶底双峰、单独不定向；副线只在 MVRV<1 低估期显示该占比——此时的 spike 才是投降性熊底确认（参考 Glassnode LTH Capitulation Risk 思路）。不作独立触发。主线是UTXO花费价值占比，不是LTH供应。",
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
            "relative_unrealized_loss", "Relative Unrealized Loss", "percent",
            "全网未实现亏损占市场价值的比例。底部 spike（投降）；跨周期峰值随市场成熟衰减。",
            "Unrealized Loss / Market Cap (derived = RUP - (1 - 1/MVRV))",
            "BRK / Bitview 基础日线", "自行计算（恒等式推导，Bitview 无未实现亏损存量序列）", rul,
            [reference(0.4, "高未实现亏损参考"), reference(0.6, "深度投降观察线")], "above",
            caveat="Bitview 无未实现亏损存量；按 NUPL=RUP−RUL、NUPL=1−1/MVRV 恒等式推导。"
            "亏损侧振荡器，底部向上 spike（与 RUP 顶部 spike 镜像）。原始峰值跨周期衰减：2018底≈0.76、2022底≈0.66。",
        ),
        metric(
            "relative_unrealized_loss_zscore_4y", "RUL 4年滚动 z-score", "zscore",
            "Relative Unrealized Loss 相对过去1460日均值的标准差位置（底部 spike → 正向 z）。",
            "(RUL - rolling mean 1460d) / rolling population std 1460d",
            "由本原型基于 RUL（推导值）计算", "自行计算", rul_zscore,
            [reference(2.0, "高于均值2σ（投降区）"), reference(2.5, "高于均值2.5σ（深度投降）")], "above",
            caveat="RUL 强右偏（+1.67），单σ偏松；历史大底 z≈+2.8~+2.9、COVID≈+2.0。"
            "这是明确版本化的4年滚动总体标准差，不冒充唯一官方RUL标准差。",
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
            [reference(0.0, "LTH/STH 净盈亏分界"), reference(honest["sth_net_q05"], "STH过去周期5%分位（无前视）")], "below",
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
            [reference(0.0, "净盈亏分界"), reference(honest["net_realized_q05"], "过去周期5%分位（无前视）")], "below",
        ),
        metric(
            "reserve_risk", "Reserve Risk", "small",
            "价格相对HODL Bank的水平，结合长期持有信念与出售激励。",
            "Price / HODL Bank（BRK 实现）", "BRK / Bitview", "公开成品日线", raw["reserve_risk"],
            [reference(honest["reserve_risk_q10"], "过去周期10%分位（无前视）")], "below",
            caveat="完整复算依赖VOCDD与HODL Bank历史状态，本原型绑定BRK公开实现。绝对值因 HODL Bank 累积每轮约 ×0.4 下移，固定阈值（如 0.002）在本轮永久失效；跨周期判断请用 reserve_risk_zscore。",
        ),
        metric(
            "reserve_risk_zscore", "Reserve Risk · 周期归一化 z", "zscore",
            "Reserve Risk 经 log + 4年滚动 z-score，消除分母 HODL Bank 累积导致的结构性下移，使各轮周期顶/底可比。",
            "z[ log(Reserve Risk), trailing 1460d ]；阈值 = z 的过去周期分位（无前视）",
            "BRK / Bitview", "自行计算（无前视）", rr_zscore,
            [
                reference(rr_z_q10, "z·过去周期10%分位（先触发）"),
                reference(rr_z_q05, "z·过去周期5%分位（深部）"),
                reference(0.0, "自身4年均值（中性）"),
            ], "below",
            caveat="Reserve Risk = Price / HODL Bank，分母 HODL Bank 为单调累积量，致绝对值每轮约 ×0.4 下移（2013→2024 周期顶 1.5e-4→1.0e-5），固定绝对阈值（如 0.002）在本轮永久失效。本指标对 log(RR) 取 trailing 4 年（1460d）z-score：把指数下移转线性后衡量相对本周期的高低，跨周期可比。z<0 = 低于自身4年均值；阈值用 z 的过去周期分位（无前视）。原始绝对值见 Reserve Risk 指标，切勿套 0.002。",
        ),
        metric(
            "seller_exhaustion", "Seller Exhaustion Constant", "small",
            "低盈利供应与低波动共同出现的卖方耗竭状态。",
            "PSIP × BRK 30d Price Volatility", "BRK / Bitview 基础日线", "自行计算", seller_exhaustion,
            [reference(honest["seller_exhaustion_q10"], "过去周期10%分位（无前视）")], "below",
            check=compare(seller_exhaustion, raw["seller_exhaustion"]),
        ),
        metric(
            "thermocap_multiple", "Thermocap Multiple", "ratio",
            "市场价值相对累计矿工补贴美元价值的倍数。",
            "Market Cap / Subsidy Cumulative USD", "BRK / Bitview 基础日线", "自行计算", thermocap_multiple,
            [reference(honest["thermocap_q10"], "过去周期10%分位（无前视）")], "below",
            caveat="历史熊底倍数会跨周期漂移（顶部周期振荡、底部缓升）；分位线基于过去周期、无前视。相对周期的过热/过冷视角见 thermocap_multiple_zscore。",
            check=compare(thermocap_multiple, raw["thermo_cap_multiple"]),
        ),
        metric(
            "thermocap_multiple_zscore", "Thermocap Multiple · 周期归一化 z", "zscore",
            "Thermocap Multiple 经 log + 4年滚动 z-score，消除底部缓升、提供相对自身周期的过热/过冷视角。",
            "z[ log(Thermocap Multiple), trailing 1460d ]；阈值 = z 的过去周期分位（无前视）",
            "BRK / Bitview", "自行计算（无前视）", tc_zscore,
            [
                reference(tc_z_q10, "z·过去周期10%分位（先触发）"),
                reference(tc_z_q05, "z·过去周期5%分位（深部）"),
                reference(0.0, "自身4年均值（中性）"),
            ], "below",
            caveat="Thermocap = MarketCap / 累积矿工补贴。与 Reserve Risk 不同，本指标结构性下移轻微：顶部周期振荡（2013/2017/2021 = 60/74/51，2017 最高），底部反因减半放缓分母而缓升（4.7→5.7→6.8）。故 z-score 在此非修严重下移，而是消除底部缓升 + 提供“相对自身4年周期是否过热”的视角（绝对阈值底部5-7/顶部50-74仍有效）。z<0 = 低于自身4年均值；阈值用 z 的过去周期分位（无前视）。",
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
            "默认分位线基于过去周期数据（锚定2018、截止上一轮熊底），不含未来/本轮信息，可作为诚实阈值参考。",
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
