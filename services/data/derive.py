"""Pure derivation + no-lookahead threshold methodology.

Migrated verbatim in behaviour from ``prototype-indicator-timeline/build_data.py``.
These are the project's core intellectual assets: cycle-honest (no-future-look)
thresholds and log+z-score cross-cycle normalization. Stdlib-only.

Window convention (lookahead-free):
* ``ANCHOR = 2018-01-01`` drops the immature pre-2018 market (MVRV-style peaks
  decay over cycles; early data pollutes cross-cycle absolute thresholds).
* ``CURRENT_CYCLE_START`` = last *completed* bear bottom. Honest thresholds use
  ONLY data at/before it, so the threshold for finding the current bottom is
  derived from past bears, never the current cycle or the future.
"""

from __future__ import annotations

import math
import statistics
from collections import deque
from datetime import date, timedelta


GENESIS = date(2009, 1, 3)

BOTTOMS = (
    (date(2011, 11, 18), "2011 熊底参考"),
    (date(2015, 1, 14), "2015 熊底参考"),
    (date(2018, 12, 15), "2018 熊底参考"),
    (date(2022, 11, 21), "2022 熊底参考"),
)

# Honest (no-lookahead) threshold window: mature market .. last completed bear.
ANCHOR = date(2018, 1, 1)
CURRENT_CYCLE_START = BOTTOMS[-1][0]

# Trailing z-score window (4 years) for cross-cycle normalization.
ZSCORE_WINDOW = 1460


def aligned_ratio(numerator: dict[date, float], denominator: dict[date, float]) -> dict[date, float]:
    return {
        day: numerator[day] / denominator[day]
        for day in numerator.keys() & denominator.keys()
        if denominator[day] != 0
    }


def aligned_difference(left: dict[date, float], right: dict[date, float]) -> dict[date, float]:
    return {day: left[day] - right[day] for day in left.keys() & right.keys()}


def aligned_product(left: dict[date, float], right: dict[date, float]) -> dict[date, float]:
    return {day: left[day] * right[day] for day in left.keys() & right.keys()}


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
    for day, value in sorted(values.items()):
        queue.append((day, value))
        total += value
        while queue and (day - queue[0][0]).days >= window:
            total -= queue.popleft()[1]
        if len(queue) == window:
            output[day] = total / window
    return output


def rolling_zscore(values: dict[date, float], window: int = ZSCORE_WINDOW) -> dict[date, float]:
    """Population (biased) z-score over a trailing ``window`` calendar-sample.

    Trailing = [day-W+1 .. day], causal (no lookahead). Population std matches
    the documented "4年滚动总体标准差" basis; MAD callers scale by 1.4826 themselves.
    """
    queue: deque[tuple[date, float]] = deque()
    total = 0.0
    total_sq = 0.0
    output: dict[date, float] = {}
    for day, value in sorted(values.items()):
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
    """Willy Woo 2019 fixed-6e6-constant CVDD floor + price-proximity (1/|%-dist|)."""
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
            relative_distance = abs(price_value / floor - 1.0)
            if relative_distance > 0:
                proximity[day] = 1.0 / relative_distance
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


def quantile(values: dict[date, float], probability: float) -> float:
    ordered = sorted(values.values())
    if not ordered:
        raise ValueError("empty quantile input")
    return _quantile_list(ordered, probability)


def _quantile_list(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def quantile_list(values: list[float], probability: float) -> float:
    """Public alias kept for callers mirroring the prototype's surface."""
    return _quantile_list(values, probability)


def past_cycle_quantile(values: dict[date, float], probability: float) -> float:
    """Empirical quantile over ONLY completed past-cycle data (no lookahead).

    A full-sample ``quantile(values, p)`` leaks the future AND the current cycle
    into the threshold. Restricting to ``ANCHOR..CURRENT_CYCLE_START`` means the
    threshold for finding the *current* bottom is derived solely from past bears.
    """
    sample = [value for day, value in values.items() if ANCHOR <= day <= CURRENT_CYCLE_START]
    if len(sample) < 30:
        # Series lacks enough pre-current-cycle history. Fall back to anchored
        # full sample: still drops immature pre-2018 data and contains no future,
        # but does include this cycle.
        sample = [value for day, value in values.items() if day >= ANCHOR]
    return _quantile_list(sample, probability)


def past_cycle_stats(values: dict[date, float]) -> dict[str, float]:
    """Mean / population-std / median / MAD over the no-lookahead past-cycle window."""
    sample = [value for day, value in values.items() if ANCHOR <= day <= CURRENT_CYCLE_START]
    if len(sample) < 30:
        sample = [value for day, value in values.items() if day >= ANCHOR]
    median = statistics.median(sample)
    mad = statistics.median([abs(value - median) for value in sample])
    return {
        "mean": statistics.mean(sample),
        "pstdev": statistics.pstdev(sample),
        "median": median,
        "mad": mad,
    }


def compare(derived: dict[date, float], direct: dict[date, float]) -> dict:
    """Reproducibility check vs a published direct counterpart."""
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
        "p95_relative_error": _quantile_list(errors, 0.95) if errors else None,
        "median_absolute_error": statistics.median(absolute),
    }


def ladder(level: float, values: dict[date, float]) -> dict[date, float]:
    """Scale a series by a constant — turns an MVRV threshold into a price ladder
    via Price = threshold x STH-RP."""
    return {day: level * value for day, value in values.items()}


def serialise(values: dict[date, float]) -> list[list]:
    return [[day.isoformat(), float(f"{value:.10g}")] for day, value in sorted(values.items())]


def quality(values: dict[date, float], today: date | None = None) -> dict:
    first = min(values)
    last = max(values)
    expected = (last - first).days + 1
    freshness_base = today if today is not None else date.today()
    return {
        "rows": len(values),
        "start": first.isoformat(),
        "end": last.isoformat(),
        "missing_calendar_days": expected - len(values),
        "freshness_days": max(0, (freshness_base - last).days),
    }
