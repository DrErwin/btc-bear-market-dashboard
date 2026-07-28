"""Offline public-dashboard acceptance gate.

The page is served from the already-built dashboard/dist directory. All four
fixtures are local JSON files, so this flow does not need network access or a
live model.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dashboard" / "dist"
EVIDENCE = ROOT / "artifacts" / "review-evidence"
# 4173 is commonly occupied by another local prototype in this workspace.
PORT = 4175
BASE_URL = f"http://127.0.0.1:{PORT}/"


def wait_for_server() -> None:
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urlopen(BASE_URL, timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("本地页面服务未在 15 秒内启动")


def start_server() -> subprocess.Popen[str]:
    if not DIST.exists():
        raise RuntimeError("找不到 dashboard/dist，请先运行 npm run build")
    return subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=DIST,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def open_page(page: Page, fixture: str = "success") -> None:
    page.goto(f"{BASE_URL}?fixture={fixture}", wait_until="networkidle")
    expect(page.locator(".evidence-board")).to_be_visible()


def assert_no_restricted_language(page: Page) -> None:
    # Only the AI analysis region is assertion-checked: indicator descriptions
    # legitimately use factual words like "卖出" (HODLer capitulation selling),
    # which are observations, not advice. Forbidden trading/probability ADVICE
    # is enforced in the AI-generated analysis only.
    shell = page.locator(".evaluation-shell")
    text = shell.inner_text() if shell.count() else ""
    for term in ("概率", "买入", "卖出", "入场价", "仓位", "杠杆"):
        assert term not in text, f"AI 分析区不应出现受限表达：{term}"


def success_flow(page: Page) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    open_page(page)

    expect(page.locator("h1")).to_contain_text("筑底证据积累期")
    for stage in ("尚未进入熊底观察期", "熊市下行期", "深度压力期", "筑底证据积累期", "熊底证据充分期"):
        expect(page.get_by_text(stage, exact=True).first).to_be_visible()
    assert page.locator(".stage-stop.is-current").count() == 1
    expect(page.get_by_text("证据一致性", exact=True)).to_be_visible()
    expect(page.locator(".evaluation-summary")).to_be_visible()
    for title in ("估值 + 矿工压力", "持有者行为仍在积累", "核心类别继续收敛"):
        expect(page.get_by_text(title, exact=True)).to_be_visible()

    detail = page.locator(".detail-toggle")
    expect(detail).to_have_attribute("aria-expanded", "false")
    detail.click()
    expect(detail).to_have_attribute("aria-expanded", "true")
    expect(page.get_by_text("支持证据", exact=True)).to_be_visible()
    detail.click()
    expect(detail).to_have_attribute("aria-expanded", "false")

    board_box = page.locator(".evidence-board").bounding_box()
    assert board_box and board_box["y"] < 900, "1440x900 首屏应看到分类看板顶部"
    assert page.locator(".category-grid .category-card").count() == 6
    assert page.get_by_text("充分确认", exact=True).count() >= 2
    assert page.get_by_text("部分确认", exact=True).count() >= 4

    categories = {
        "valuation": ["MVRV", "AVIV", "STH-MVRV 战术价位"],
        "supply": ["PSIP", "SIPL", "Relative Unrealized Profit", "RUL · 4年 z-score"],
        "capital": ["Realized Cap Relative NPC · 30d", "aSOPR"],
        "holders": ["HODLer NPC · 30d", "≥155d 花费价值占比", "Seller Exhaustion Constant"],
        "miners": ["Puell Multiple", "Thermocap Multiple · 周期 z"],
        "anchors": ["CVDD 接近程度", "Reserve Risk · 周期 z"],
    }
    category_buttons = page.locator(".category-grid .category-card")
    for index, (category_id, metrics) in enumerate(categories.items()):
        category_buttons.nth(index).click()
        assert page.locator(".metric-card").count() == len(metrics), category_id
        for metric_label in metrics:
            expect(page.locator(".metric-card").filter(has_text=metric_label).first).to_be_visible()
            page.locator(".metric-card").filter(has_text=metric_label).first.click()
            expect(page.locator("#chart-title")).to_have_text(metric_label)
            expect(page.locator(".chart-legend")).to_contain_text("BTC 价格")
            expect(page.locator(".chart-legend")).to_contain_text(metric_label)
            expect(page.locator(".chart-legend")).to_contain_text("阈值线")

    assert_no_restricted_language(page)
    page.screenshot(path=str(EVIDENCE / "desktop-success.png"), full_page=True)


def failure_flow(page: Page) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    open_page(page, "failure")
    expect(page.get_by_text("今日 AI 分析不可用", exact=True)).to_be_visible()
    expect(page.get_by_text("2026-07-26", exact=True)).to_be_visible()
    expect(page.get_by_text("深度压力期", exact=True).first).to_be_visible()
    assert page.locator(".category-grid .category-card").count() == 6
    assert page.locator(".metric-card").count() == 3
    page.screenshot(path=str(EVIDENCE / "desktop-fallback.png"), full_page=True)

    page.set_viewport_size({"width": 390, "height": 844})
    open_page(page, "failure")
    expect(page.get_by_text("今日 AI 分析不可用", exact=True)).to_be_visible()
    page.screenshot(path=str(EVIDENCE / "mobile-fallback.png"), full_page=True)

    page.set_viewport_size({"width": 1440, "height": 900})
    open_page(page, "no-fallback")
    expect(page.get_by_text("今日 AI 分析不可用", exact=True)).to_be_visible()
    expect(page.get_by_text("目前没有上一份成功结果", exact=False)).to_be_visible()
    assert page.locator("#evaluation-title").count() == 0, "无回退时不应编造当前阶段"
    assert page.locator(".category-grid .category-card").count() == 6


def responsive_and_keyboard_flow(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    open_page(page)
    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    assert not overflow, "390px 页面不能产生横向溢出"
    assert page.locator(".stage-stop").count() == 5
    for stop in page.locator(".stage-stop").all():
        box = stop.bounding_box()
        assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390, "阶段点必须完整落在移动视口内"

    first_metric = page.locator(".metric-card").first
    first_metric.focus()
    first_id = page.evaluate("document.activeElement && document.activeElement.id")
    first_metric.press("ArrowDown")
    next_id = page.evaluate("document.activeElement && document.activeElement.id")
    assert first_id != next_id and next_id.startswith("metric-"), "指标卡应支持方向键移动"

    detail = page.locator(".detail-toggle")
    detail.focus()
    detail.press("Enter")
    expect(detail).to_have_attribute("aria-expanded", "true")
    page.screenshot(path=str(EVIDENCE / "mobile-success.png"), full_page=True)


def ai_contract_flow() -> None:
    result = pytest.main(
        [
            "-q",
            str(ROOT / "tests" / "acceptance" / "test_ai_contract.py"),
            str(ROOT / "tests" / "acceptance" / "test_input_boundary.py"),
            str(ROOT / "tests" / "acceptance" / "test_packet_contract.py"),
        ]
    )
    if result != pytest.ExitCode.OK:
        raise AssertionError(f"AI 契约验收失败，pytest exit code={result}")


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT))
    ai_contract_flow()
    server = start_server()
    try:
        wait_for_server()
        with sync_playwright() as playwright:
            installed = sorted(
                Path.home().glob("AppData/Local/ms-playwright/chromium-*/chrome-win*/chrome.exe"),
                reverse=True,
            )
            launch_options = {"headless": True}
            if installed:
                launch_options["executable_path"] = str(installed[0])
            browser = playwright.chromium.launch(**launch_options)
            page = browser.new_page()
            success_flow(page)
            failure_flow(page)
            responsive_and_keyboard_flow(page)
            browser.close()
        print("ACCEPTANCE PASS: success, fallback, no-fallback, responsive, keyboard, and restricted-language checks")
        print(f"Evidence: {EVIDENCE}")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
