"""One offline acceptance entry point for the v0.4 packet-to-page seam."""

from __future__ import annotations

import os
import copy
import json
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.data.packet import validate_packet  # noqa: E402
DASHBOARD = ROOT / "dashboard"
EVIDENCE = ROOT / "artifacts" / "review-evidence" / "v0.4.0"


def _run(command: list[str], *, cwd: Path) -> None:
    if command and command[0] == "npm" and os.name == "nt":
        command = ["npm.cmd", *command[1:]]
    print(f"[acceptance] {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


def _browser_checks() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment gate
        raise SystemExit(f"Playwright 不可用: {exc}")

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    success_packet = json.loads((DASHBOARD / "public" / "data" / "packet.json").read_text(encoding="utf-8"))

    def packet_with_readiness(*, pressure_ready: bool, bottoming_ready: bool) -> dict:
        packet = copy.deepcopy(success_packet)
        readiness = packet["evidence_brief"]["axis_readiness"]
        for axis, ready in (("pressure", pressure_ready), ("bottoming", bottoming_ready)):
            readiness[axis]["ready"] = ready
            readiness[axis]["timeline_complete"] = ready
            if not ready:
                readiness[axis]["missing_metric_ids"] = [f"{axis}_fixture_metric"]
                readiness[axis]["missing_reasons"] = ["固定验收夹具模拟该轴数据不足"]
        packet["status"]["data_insufficient"] = not (pressure_ready and bottoming_ready)
        packet["status"]["axis_readiness"] = readiness
        packet["analysis"]["pressure_state"] = packet["analysis"]["pressure_state"] if pressure_ready else "数据不足"
        packet["analysis"]["bottoming_state"] = packet["analysis"]["bottoming_state"] if bottoming_ready else "数据不足"
        if not pressure_ready and not bottoming_ready:
            packet["analysis"]["consistency"] = None
        packet["analysis"]["state_changes"]["pressure"]["to"] = packet["analysis"]["pressure_state"]
        packet["analysis"]["state_changes"]["bottoming"]["to"] = packet["analysis"]["bottoming_state"]
        validate_packet(packet)
        return packet

    handler = partial(SimpleHTTPRequestHandler, directory=str(DASHBOARD / "dist"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        time.sleep(1.0)
        with sync_playwright() as playwright:
            browser_kwargs = {"headless": True}
            edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
            if edge.exists():
                browser_kwargs["executable_path"] = str(edge)
            browser = playwright.chromium.launch(**browser_kwargs)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.on("console", lambda message: print(f"[browser console] {message.type}: {message.text}"))
            page.on("pageerror", lambda error: print(f"[browser error] {error}"))
            page.on("response", lambda response: print(f"[browser response] {response.status}: {response.url}") if response.status >= 400 else None)
            page.goto(f"{base_url}/?fixture=success", wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            page.locator("#evaluation-title").wait_for(timeout=10000)
            body = page.locator("body").inner_text()
            assert "压力尚未明显" in body or "进入观察" in body or "深度压力" in body or "极端压力" in body or "数据不足" in body
            assert any(state in body for state in ("未见筑底结构", "筑底线索出现", "筑底证据聚合", "筑底证据较完整", "市场修复中", "已离开底部窗口", "数据不足"))
            assert page.locator(".dual-axis-summary").count() == 1
            assert page.locator(".stage-axis").count() == 0
            assert page.get_by_role("button", name="查看完整分析").count() == 1
            page.get_by_role("button", name="查看完整分析").click()
            assert page.locator(".detail-drawer article").count() == 6
            body = page.locator("body").inner_text()
            for forbidden in ("定投", "抄底", "大力抄底", "允许阶段", "阶段上限", "allowed_stages"):
                assert forbidden not in body
            page.screenshot(path=str(EVIDENCE / "success-desktop.png"), full_page=True)

            keyboard = browser.new_page(viewport={"width": 1440, "height": 900})
            keyboard.goto(f"{base_url}/?fixture=success", wait_until="networkidle")
            toggle = keyboard.get_by_role("button", name="查看完整分析")
            toggle.focus()
            toggle.press("Enter")
            assert keyboard.locator(".detail-drawer article").count() == 6
            keyboard.screenshot(path=str(EVIDENCE / "success-keyboard.png"), full_page=True)

            partial_page = browser.new_page(viewport={"width": 1440, "height": 900})
            partial_page.route(
                "**/data/packet.json",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(packet_with_readiness(pressure_ready=True, bottoming_ready=False), ensure_ascii=False),
                ),
            )
            partial_page.goto(f"{base_url}/?fixture=success", wait_until="networkidle")
            assert "部分市场状态数据不足" in partial_page.locator("body").inner_text()
            assert "数据不足" in partial_page.locator("body").inner_text()
            partial_page.screenshot(path=str(EVIDENCE / "partial-data.png"), full_page=True)

            both_missing = browser.new_page(viewport={"width": 1440, "height": 900})
            both_missing.route(
                "**/data/packet.json",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(packet_with_readiness(pressure_ready=False, bottoming_ready=False), ensure_ascii=False),
                ),
            )
            both_missing.goto(f"{base_url}/?fixture=success", wait_until="networkidle")
            assert both_missing.locator("body").inner_text().count("数据不足") >= 2

            mobile = browser.new_page(viewport={"width": 390, "height": 900})
            mobile.goto(f"{base_url}/?fixture=success", wait_until="networkidle")
            assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
            mobile.screenshot(path=str(EVIDENCE / "success-mobile.png"), full_page=True)

            fallback = browser.new_page(viewport={"width": 1440, "height": 900})
            fallback.goto(f"{base_url}/?fixture=failure", wait_until="networkidle")
            assert "回退至" in fallback.locator("body").inner_text()
            no_fallback = browser.new_page(viewport={"width": 1440, "height": 900})
            no_fallback.goto(f"{base_url}/?fixture=no-fallback", wait_until="networkidle")
            assert "没有上一份完整双轴结果" in no_fallback.locator("body").inner_text()
            keyboard.close()
            partial_page.close()
            both_missing.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def main() -> int:
    _run(["npm", "run", "build"], cwd=DASHBOARD)
    _run([sys.executable, "-m", "pytest", "-q", "tests/acceptance"], cwd=ROOT)
    _browser_checks()
    print("[acceptance] PASS: v0.4 complete packet -> page seam")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
