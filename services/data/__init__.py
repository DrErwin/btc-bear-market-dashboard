"""BTC bear-bottom evidence dashboard — data pipeline.

Split out of the validated ``prototype-indicator-timeline/build_data.py`` so the
production daily-update path reuses the exact derivation logic:

* ``fetch``    — public daily-series ingestion (Bitview bulk + Open Bitcoin Metrics CSV).
* ``derive``   — pure derivation + the no-lookahead threshold methodology.
* ``metrics``  — orchestrates raw series -> the 16-indicator catalogue + thresholds.
* ``packet``   — assembles the single dashboard data packet and enforces its contract.

All modules stay Python-stdlib-only so the offline acceptance flow and the
GitHub Actions runner need no extra packages for the data path.
"""

from __future__ import annotations
