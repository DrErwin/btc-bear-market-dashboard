"""PROTOTYPE — one-command local server for the indicator timeline."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "timeline-data.json"


class QuietHandler(SimpleHTTPRequestHandler):
    """Avoid request-log writes after the launcher yields its terminal."""

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="refetch public source data")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    if args.refresh or not DATA.exists():
        subprocess.run([sys.executable, str(HERE / "build_data.py")], check=True)

    os.chdir(HERE)
    url = f"http://127.0.0.1:{args.port}/index.html?variant=A"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), QuietHandler)
    print("PROTOTYPE — BTC 指标验证台")
    print(url)
    print("按 Ctrl+C 停止。")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
