"""PROTOTYPE: live public-source acquisition and explicitly experimental derivations."""

from __future__ import annotations

import csv
import hashlib
import http.client
import io
import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Iterable
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import Request, urlopen

from feasibility_logic import TimeSeries


CM_API = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
OBM_RAW_ROOT = "https://raw.githubusercontent.com/diegorllanos/open-bitcoin-metrics"
OBM_REPO_API = "https://api.github.com/repos/diegorllanos/open-bitcoin-metrics"
USER_AGENT = "btc-bear-market-dashboard-feasibility-prototype/0.1"
GENESIS_DATE = date(2009, 1, 3)
CVDD_CALIBRATION = 6_000_000.0


@dataclass(frozen=True)
class DataBundle:
    representatives: dict[str, TimeSeries]
    candidates: dict[str, tuple[TimeSeries, ...]]
    raw_series: tuple[TimeSeries, ...]
    source_metadata: dict[str, str]


def _get_bytes(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/csv,*/*",
            "Connection": "close",
        },
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except (http.client.IncompleteRead, TimeoutError, URLError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _finite_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def fetch_coinmetrics() -> tuple[dict[str, dict[date, float]], dict[str, str]]:
    metrics = ("CapMVRVCur", "CapMrktCurUSD", "PriceUSD", "SplyCur")
    params = {
        "assets": "btc",
        "metrics": ",".join(metrics),
        "frequency": "1d",
        "start_time": "2009-01-01",
        "page_size": "1000",
    }
    url = f"{CM_API}?{urlencode(params)}"
    payload = json.loads(_get_bytes(url))
    rows = list(payload.get("data", []))
    next_url = payload.get("next_page_url")
    while next_url:
        page = json.loads(_get_bytes(next_url))
        rows.extend(page.get("data", []))
        next_url = page.get("next_page_url")

    result = {metric: {} for metric in metrics}
    for row in rows:
        day = date.fromisoformat(row["time"][:10])
        for metric in metrics:
            parsed = _finite_float(row.get(metric))
            if parsed is not None:
                result[metric][day] = parsed
    metadata = {
        "coinmetrics_endpoint": url,
        "coinmetrics_rows_received": str(len(rows)),
        "coinmetrics_time_convention": "UTC 00:00 daily observation from API time field",
    }
    return result, metadata


def fetch_obm_revision() -> tuple[str, dict[str, str]]:
    url = f"{OBM_REPO_API}/commits/main"
    payload = json.loads(_get_bytes(url))
    revision = payload["sha"]
    return revision, {
        "obm_commit_sha": revision,
        "obm_commit_date": payload["commit"]["committer"]["date"],
        "obm_commit_url": payload["html_url"],
    }


def fetch_obm_scalar(series_id: str, revision: str = "main") -> tuple[dict[date, float], dict[str, str]]:
    url = f"{OBM_RAW_ROOT}/{revision}/metrics/{series_id}/{series_id}.csv"
    content = _get_bytes(url)
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    values: dict[date, float] = {}
    release_versions: set[str] = set()
    units: set[str] = set()
    frequencies: set[str] = set()
    for row in reader:
        parsed = _finite_float(row.get("value"))
        if parsed is None:
            continue
        values[date.fromisoformat(row["date"])] = parsed
        release_versions.add(row.get("release_version", ""))
        units.add(row.get("unit", ""))
        frequencies.add(row.get("frequency", ""))
    metadata = {
        f"{series_id}_url": url,
        f"{series_id}_release": ",".join(sorted(filter(None, release_versions))),
        f"{series_id}_declared_unit": ",".join(sorted(filter(None, units))),
        f"{series_id}_declared_frequency": ",".join(sorted(filter(None, frequencies))),
        f"{series_id}_sha256": hashlib.sha256(content).hexdigest(),
    }
    return values, metadata


def _series(
    family: str,
    key: str,
    label: str,
    unit: str,
    values: dict[date, float],
    source: str,
    lineage: str,
    experimental: bool = False,
) -> TimeSeries:
    return TimeSeries(family, key, label, unit, values, source, lineage, experimental)


def _derive_realized_cap(market_cap: dict[date, float], mvrv: dict[date, float]) -> dict[date, float]:
    return {
        day: market_cap[day] / mvrv[day]
        for day in market_cap.keys() & mvrv.keys()
        if mvrv[day] > 0
    }


def _derive_thermocap(issuance: dict[date, float], price: dict[date, float]) -> dict[date, float]:
    running = 0.0
    output: dict[date, float] = {}
    for day in sorted(issuance.keys() & price.keys()):
        running += issuance[day] * price[day]
        output[day] = running
    return output


def _derive_active_metrics(
    price: dict[date, float],
    obm_supply: dict[date, float],
    liveliness: dict[date, float],
    realized_cap: dict[date, float],
    thermocap: dict[date, float],
) -> tuple[dict[date, float], dict[date, float]]:
    tmmp: dict[date, float] = {}
    aviv: dict[date, float] = {}
    days = price.keys() & obm_supply.keys() & liveliness.keys() & realized_cap.keys() & thermocap.keys()
    for day in days:
        active_supply = obm_supply[day] * liveliness[day]
        investor_cap = realized_cap[day] - thermocap[day]
        if active_supply <= 0 or investor_cap <= 0:
            continue
        mean_price = investor_cap / active_supply
        tmmp[day] = mean_price
        aviv[day] = price[day] / mean_price
    return tmmp, aviv


def _derive_time_weighted_metrics(
    cdd: dict[date, float],
    liveliness: dict[date, float],
    price: dict[date, float],
) -> tuple[dict[date, float], dict[date, float]]:
    cumulative_cdd = 0.0
    cumulative_value_destroyed = 0.0
    cointime_price: dict[date, float] = {}
    cvdd: dict[date, float] = {}
    for day in sorted(cdd):
        cumulative_cdd += cdd[day]
        if day not in price:
            continue
        cumulative_value_destroyed += cdd[day] * price[day]
        live = liveliness.get(day)
        if live is not None and 0 < live < 1:
            cumulative_coin_days_created = cumulative_cdd / live
            coin_days_stored = cumulative_coin_days_created - cumulative_cdd
            if coin_days_stored > 0:
                cointime_price[day] = cumulative_value_destroyed / coin_days_stored
        market_age_days = (day - GENESIS_DATE).days
        if market_age_days > 0:
            cvdd[day] = cumulative_value_destroyed / (market_age_days * CVDD_CALIBRATION)
    return cointime_price, cvdd


def _derive_share(
    numerator: dict[date, float],
    denominator: dict[date, float],
    start_date: date | None = None,
) -> dict[date, float]:
    return {
        day: numerator[day] / denominator[day]
        for day in numerator.keys() & denominator.keys()
        if (start_date is None or day >= start_date)
        and denominator[day] > 0
        and 0 <= numerator[day] <= denominator[day]
    }


def fetch_all() -> DataBundle:
    cm, metadata = fetch_coinmetrics()
    obm_revision, revision_metadata = fetch_obm_revision()
    metadata.update(revision_metadata)
    obm_ids = (
        "obm_cdd_btcxdays_daily",
        "obm_liveliness_ratio_daily",
        "obm_supply_btc_daily",
        "obm_issuance_btc_daily",
        "obm_spent_value_btc_daily",
        "obm_spent_value_ge155d_btc_daily",
    )
    obm: dict[str, dict[date, float]] = {}
    for series_id in obm_ids:
        values, item_metadata = fetch_obm_scalar(series_id, obm_revision)
        obm[series_id] = values
        metadata.update(item_metadata)

    realized_cap = _derive_realized_cap(cm["CapMrktCurUSD"], cm["CapMVRVCur"])
    thermocap = _derive_thermocap(obm["obm_issuance_btc_daily"], cm["PriceUSD"])
    tmmp, aviv = _derive_active_metrics(
        cm["PriceUSD"],
        obm["obm_supply_btc_daily"],
        obm["obm_liveliness_ratio_daily"],
        realized_cap,
        thermocap,
    )
    cointime_price, cvdd = _derive_time_weighted_metrics(
        obm["obm_cdd_btcxdays_daily"],
        obm["obm_liveliness_ratio_daily"],
        cm["PriceUSD"],
    )
    ge155_share = _derive_share(
        obm["obm_spent_value_ge155d_btc_daily"],
        obm["obm_spent_value_btc_daily"],
        min(cm["PriceUSD"]),
    )

    source_cm = "Coin Metrics Community API"
    source_obm = "Open Bitcoin Metrics v0.1.0 rolling CSV"
    mvrv_series = _series(
        "market_valuation", "mvrv", "MVRV", "ratio", cm["CapMVRVCur"], source_cm,
        "Direct field CapMVRVCur",
    )
    cointime_series = _series(
        "time_weighted_valuation", "cointime_price_daily_reconstruction", "Cointime Price（日度重建）", "USD/BTC",
        cointime_price, f"{source_cm} + {source_obm}",
        "cumsum(PriceUSD * daily CDD) / cumulative coin-days stored; daily analogue of the published block-based model",
        True,
    )
    cvdd_series = _series(
        "time_weighted_valuation", "cvdd_daily_reconstruction", "CVDD（日度重建）", "USD/BTC",
        cvdd, f"{source_cm} + {source_obm}",
        "cumsum(PriceUSD * daily CDD) / (market age days * 6,000,000); calibration is model-specific, not a threshold",
        True,
    )
    tmmp_series = _series(
        "active_capital_valuation", "tmmp_daily_reconstruction", "True Market Mean Price（日度重建）", "USD/BTC",
        tmmp, f"{source_cm} + {source_obm}",
        "(Realized Cap - cumulative issuance-at-price Thermocap) / (OBM Supply * Liveliness)",
        True,
    )
    aviv_series = _series(
        "active_capital_valuation", "aviv_daily_reconstruction", "AVIV（日度重建）", "ratio",
        aviv, f"{source_cm} + {source_obm}",
        "PriceUSD / reconstructed True Market Mean Price",
        True,
    )
    holder_series = _series(
        "holder_behavior", "spent_value_ge155d_share", "≥155 天老币花费占比", "share",
        ge155_share, source_obm,
        "obm_spent_value_ge155d_btc_daily / obm_spent_value_btc_daily; raw UTXO spend, not LTH supply",
        False,
    )

    raw_series: list[TimeSeries] = [
        _series("raw", "cm_price", "Coin Metrics PriceUSD", "USD/BTC", cm["PriceUSD"], source_cm, "Direct field PriceUSD"),
        _series("raw", "cm_market_cap", "Coin Metrics CapMrktCurUSD", "USD", cm["CapMrktCurUSD"], source_cm, "Direct field CapMrktCurUSD"),
        _series("raw", "cm_mvrv", "Coin Metrics CapMVRVCur", "ratio", cm["CapMVRVCur"], source_cm, "Direct field CapMVRVCur"),
        _series("raw", "cm_supply", "Coin Metrics SplyCur", "BTC", cm["SplyCur"], source_cm, "Direct field SplyCur"),
    ]
    for series_id, label, unit in (
        ("obm_cdd_btcxdays_daily", "OBM CDD", "BTC-days"),
        ("obm_liveliness_ratio_daily", "OBM Liveliness", "ratio"),
        ("obm_supply_btc_daily", "OBM Supply", "BTC"),
        ("obm_issuance_btc_daily", "OBM Issuance", "BTC/day"),
        ("obm_spent_value_btc_daily", "OBM Spent Value", "BTC/day"),
        ("obm_spent_value_ge155d_btc_daily", "OBM ≥155d Spent Value", "BTC/day"),
    ):
        raw_series.append(_series("raw", series_id, label, unit, obm[series_id], source_obm, "Direct rolling CSV"))

    representatives = {
        "market_valuation": mvrv_series,
        "time_weighted_valuation": cointime_series,
        "active_capital_valuation": aviv_series,
        "holder_behavior": holder_series,
    }
    candidates = {
        "market_valuation": (mvrv_series,),
        "time_weighted_valuation": (cointime_series, cvdd_series),
        "active_capital_valuation": (tmmp_series, aviv_series),
        "holder_behavior": (holder_series,),
    }
    metadata.update({
        "obm_repository": "https://github.com/diegorllanos/open-bitcoin-metrics",
        "obm_time_convention": "UTC calendar day",
        "derivation_warning": "Cointime Price, CVDD, TMMP, AVIV and >=155d share are prototype reconstructions, not OBM-published scalar series",
        "holder_share_undefined_rule": "Days before the first Coin Metrics price or with zero total spent value are excluded; 0/0 is not coerced to zero",
    })
    return DataBundle(representatives, candidates, tuple(raw_series), metadata)
