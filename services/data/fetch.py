"""Public daily-series ingestion for the dashboard data pipeline.

Migrated verbatim in behaviour from ``prototype-indicator-timeline/build_data.py``
so the production fetch path is identical to the validated prototype. Stdlib-only.
"""

from __future__ import annotations

import csv
import http.client
import io
import json
import math
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "btc-bear-bottom-dashboard/0.2"
BITVIEW = "https://bitview.space/api/series/bulk"
BITVIEW_ORIGIN = date(2009, 1, 1)
OBM_ROOT = "https://raw.githubusercontent.com/diegorllanos/open-bitcoin-metrics/main/metrics"

# Every base series the dashboard derives from, plus the direct counterparts
# kept only for reproducibility checks (compare() in derive.py).
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

# Long-coin spent-value series come from Open Bitcoin Metrics (CSV), used for the
# >=155d capitulation confirmation line (requirement 3 bars source).
OBM_LONG_SPENT_TOTAL = "obm_spent_value_btc_daily"
OBM_LONG_SPENT_GE155D = "obm_spent_value_ge155d_btc_daily"


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


def _finite(value: object) -> float | None:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def fetch_bitview() -> tuple[dict[str, dict[date, float]], dict]:
    """Fetch every BITVIEW_SERIES as day-indexed floats plus provider metadata.

    Bitview enforces a weighted response budget; chunk_size=2 keeps even two
    full-history F64 series under the limit.
    """
    output: dict[str, dict[date, float]] = {}
    stamps: set[str] = set()
    versions: dict[str, int] = {}
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
                parsed = _finite(raw_value)
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
        parsed = _finite(row.get("value"))
        if parsed is not None:
            values[date.fromisoformat(row["date"])] = parsed
    if not values:
        raise RuntimeError(f"OBM series is empty: {series_id}")
    return values


def fetch_obm_spent() -> tuple[dict[date, float], dict[date, float], dict]:
    total = fetch_obm_scalar(OBM_LONG_SPENT_TOTAL)
    long = fetch_obm_scalar(OBM_LONG_SPENT_GE155D)
    metadata = {
        "provider": "Open Bitcoin Metrics v0.1.0",
        "endpoint_root": OBM_ROOT,
        "series": [OBM_LONG_SPENT_TOTAL, OBM_LONG_SPENT_GE155D],
    }
    return total, long, metadata
