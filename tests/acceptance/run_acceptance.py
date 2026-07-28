"""Offline public-dashboard acceptance gate.

The page is served from the already-built dashboard/dist directory. All four
fixtures are local JSON files, so this flow does not need network access or a
live model.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.request import urlopen

import pytest
from PIL import Image
from playwright.sync_api import Page, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dashboard" / "dist"
EVIDENCE = ROOT / "artifacts" / "review-evidence" / "v0.3.0"
# 4173 is commonly occupied by another local prototype in this workspace.
PORT = 4175
BASE_URL = f"http://127.0.0.1:{PORT}/"


def load_success_analysis() -> dict:
    packet_path = DIST / "data" / "packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    analysis = packet.get("analysis") or packet.get("fallback")
    if not isinstance(analysis, dict):
        raise RuntimeError("数据包缺少可展示的 AI 分析或回退结论")
    return analysis


def load_packet_fixture(name: str = "packet.json") -> dict:
    return json.loads((DIST / "data" / name).read_text(encoding="utf-8"))


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
    for term in (
        "概率",
        "买入",
        "建议卖出",
        "应该卖出",
        "可以卖出",
        "入场价",
        "仓位",
        "杠杆",
        "核心锚",
        "核心复核",
        "强辅助",
        "阶段上限",
        "抬高阶段",
        "替代核心",
        "allowed_stages",
        "triggered",
        "evidence_use",
        "机器规定",
        "系统不允许",
    ):
        assert term not in text, f"AI 分析区不应出现受限表达：{term}"


def assert_bar_visual_height(page: Page, kind: str, minimum: int = 90) -> None:
    path = EVIDENCE / f"bar-visibility-{kind}.png"
    page.locator(".shared-chart").screenshot(path=str(path))
    image = Image.open(path).convert("RGB")
    width, height = image.size
    rows: list[int] = []
    for y in range(int(height * 0.35), int(height * 0.82)):
        count = 0
        for x in range(width):
            r, g, b = image.getpixel((x, y))
            if kind == "hodler":
                is_bar_pixel = r > g + 18 and g > b + 8 and r > 55
            else:
                is_bar_pixel = b > r + 12 and b > g + 8 and b > 55
            if is_bar_pixel:
                count += 1
        if count >= 8:
            rows.append(y)
    assert rows and max(rows) - min(rows) + 1 >= minimum, (
        f"{kind} 柱状图可见高度应至少为 {minimum}px，实际为 "
        f"{(max(rows) - min(rows) + 1) if rows else 0}px"
    )


def assert_chart_canvas_changes(before_name: str, after_name: str, minimum: int = 120) -> None:
    """A legend switch must change the rendered chart, not only its button state."""
    before_path = EVIDENCE / before_name
    after_path = EVIDENCE / after_name
    before = Image.open(before_path).convert("RGB")
    after = Image.open(after_path).convert("RGB")
    changed = sum(left != right for left, right in zip(before.get_flattened_data(), after.get_flattened_data()))
    assert changed >= minimum, f"曲线开关应改变图表画布，实际变化像素为 {changed}"


def assert_chart_contains_colour(
    image_name: str,
    colour: tuple[int, int, int],
    minimum: int = 30,
    tolerance: int = 32,
) -> None:
    """Check that a required ECharts line is visibly painted on the canvas."""
    image = Image.open(EVIDENCE / image_name).convert("RGB")
    red, green, blue = colour
    matches = sum(
        abs(pixel[0] - red) <= tolerance and abs(pixel[1] - green) <= tolerance and abs(pixel[2] - blue) <= tolerance
        for pixel in image.get_flattened_data()
    )
    assert matches >= minimum, f"应在图表中看到指定参考线颜色，实际像素为 {matches}"


def assert_chart_excludes_colour(
    image_name: str,
    colour: tuple[int, int, int],
    maximum: int = 8,
    tolerance: int = 16,
) -> None:
    """Secondary indicator lines must not silently return to the retired purple."""
    image = Image.open(EVIDENCE / image_name).convert("RGB")
    red, green, blue = colour
    matches = sum(
        abs(pixel[0] - red) <= tolerance and abs(pixel[1] - green) <= tolerance and abs(pixel[2] - blue) <= tolerance
        for pixel in image.get_flattened_data()
    )
    assert matches <= maximum, f"图表不应出现已淘汰的紫色次要线，实际像素为 {matches}"


def success_flow(page: Page) -> None:
    analysis = load_success_analysis()
    page.set_viewport_size({"width": 1440, "height": 900})
    open_page(page)

    expect(page.locator("h1")).to_contain_text(analysis["stage"])
    for stage in ("尚未进入熊底观察期", "熊市下行期", "深度压力期", "筑底证据积累期", "熊底证据充分期"):
        expect(page.get_by_text(stage, exact=True).first).to_be_visible()
    assert page.locator(".stage-stop.is-current").count() == 1
    expect(page.get_by_text("证据一致性", exact=True)).to_be_visible()
    expect(page.locator(".evaluation-summary")).to_be_visible()
    for title in (
        analysis["compact"]["support"]["title"],
        analysis["compact"]["obstacle"]["title"],
        analysis["compact"]["next"]["title"],
    ):
        expect(page.get_by_text(title, exact=True)).to_be_visible()

    detail = page.locator(".detail-toggle")
    expect(detail).to_have_attribute("aria-expanded", "false")
    detail.click()
    expect(detail).to_have_attribute("aria-expanded", "true")
    expect(page.get_by_text("核心依据", exact=True)).to_be_visible()
    if analysis.get("pressure_summary"):
        expect(page.get_by_text("阶段内部压力", exact=True)).to_be_visible()
    detail.click()
    expect(detail).to_have_attribute("aria-expanded", "false")

    board_box = page.locator(".evidence-board").bounding_box()
    assert board_box and board_box["y"] < 900, "1440x900 首屏应看到分类看板顶部"
    assert page.locator(".category-grid .category-card").count() == 6
    availability_by_id = {
        metric["id"]: metric.get("availability_status")
        for metric in load_packet_fixture()["snapshot"]["metrics"]
    }
    assert availability_by_id["hodler"] == "display_only"
    assert availability_by_id["spent155"] == "display_only"
    assert availability_by_id["cvdd"] == "validation_pending"
    expected_status_counts = Counter(item["status"] for item in analysis["categories"])
    for status in ("未确认", "部分确认", "充分确认"):
        assert page.get_by_text(status, exact=True).count() == expected_status_counts[status]

    categories = {
        "valuation": ["MVRV", "AVIV", "STH-MVRV 战术价位"],
        "supply": ["PSIP", "SIPL", "Relative Unrealized Profit", "RUL · 4年 z-score"],
        "capital": ["Realized Cap Relative NPC · 30d", "aSOPR"],
        "holders": ["HODLer NPC · 30d", "≥155d 花费价值占比", "Seller Exhaustion Constant"],
        "miners": ["Puell Multiple", "Thermocap Multiple · 周期 z"],
        "anchors": ["CVDD 接近程度", "Reserve Risk · 周期"],
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
            if metric_label in ("HODLer NPC · 30d", "≥155d 花费价值占比"):
                legend_text = page.locator(".chart-legend").inner_text()
                assert metric_label not in legend_text, "柱状指标不应显示重复的指标线开关"
                assert "阈值线" not in legend_text, "柱状指标不应显示对应的阈值线开关"
                assert page.locator(".chart-legend .legend-line.indicator").count() == 0
                assert page.locator(".chart-legend .legend-line.threshold").count() == 0
            elif metric_label == "STH-MVRV 战术价位":
                legend_text = page.locator(".chart-legend").inner_text()
                assert metric_label not in legend_text, "STH-MVRV 主指标线不应保留图例开关"
                expect(page.locator(".chart-legend")).to_contain_text("5%分位 × STH-RP")
                expect(page.locator(".chart-legend")).to_contain_text("阈值线")
            else:
                expect(page.locator(".chart-legend")).to_contain_text(metric_label)
                expect(page.locator(".chart-legend")).to_contain_text("阈值线")

    # v0.2.4: every validation-panel curve is represented in the shared chart,
    # and the exported reference names are exposed to the accessible chart
    # label as well as rendered by ECharts markLine labels.
    page.get_by_text("估值与成本", exact=True).click()
    page.locator(".metric-card").filter(has_text="STH-MVRV 战术价位").first.click()
    sth_aria = page.locator(".shared-chart").get_attribute("aria-label") or ""
    for label in ("5%分位 × STH-RP", "1.5σ × STH-RP", "1.5·MAD × STH-RP", "1.5·MAD（无前视）"):
        assert label in sth_aria, f"STH-MVRV 图表缺少曲线/参考线：{label}"
    assert "STH-MVRV 战术价位（三法合并）" not in sth_aria, "STH-MVRV 主指标线不应参与图表"
    expect(page.locator(".chart-legend")).to_contain_text("5%分位 × STH-RP")

    page.get_by_text("供应盈亏", exact=True).click()
    page.locator(".metric-card").filter(has_text="SIPL").first.click()
    sipl_aria = page.locator(".shared-chart").get_attribute("aria-label") or ""
    for label in ("Supply in Profit / Loss", "Supply in Loss", "盈利% − 亏损%", "两线理论交错参考"):
        assert label in sipl_aria, f"SIPL 图表缺少曲线/参考线：{label}"

    page.get_by_text("链上资本流", exact=True).click()
    page.locator(".metric-card").filter(has_text="aSOPR").first.click()
    asopr_aria = page.locator(".shared-chart").get_attribute("aria-label") or ""
    for label in ("aSOPR", "3日滞后均值（趋势辅助）", "7日滞后均值（趋势辅助）", "投降"):
        assert label in asopr_aria, f"aSOPR 图表缺少曲线/参考线：{label}"

    page.get_by_text("长期成本锚", exact=True).click()
    page.locator(".metric-card").filter(has_text="CVDD 接近程度").first.click()
    cvdd_aria = page.locator(".shared-chart").get_attribute("aria-label") or ""
    for label in ("CVDD 接近程度", "CVDD 价格地板", "高于CVDD 50%"):
        assert label in cvdd_aria, f"CVDD 图表缺少曲线/参考线：{label}"

    for category_name, metric_label, reference_labels in (
        ("估值与成本", "MVRV", ("成本平衡线", "深度低估观察线")),
        ("矿工压力", "Thermocap Multiple", ("z·过去周期10%分位（先触发）", "z·过去周期5%分位（深部）", "自身4年均值（中性）")),
        ("长期成本锚", "Reserve Risk", ("z·过去周期10%分位", "z·过去周期5%分位")),
    ):
        page.get_by_text(category_name, exact=True).click()
        page.locator(".metric-card").filter(has_text=metric_label).first.click()
        aria = page.locator(".shared-chart").get_attribute("aria-label") or ""
        for label in reference_labels:
            assert label in aria, f"{metric_label} 图表缺少参考线：{label}"

    assert_no_restricted_language(page)
    page.screenshot(path=str(EVIDENCE / "desktop-success.png"), full_page=True)


def failure_flow(page: Page) -> None:
    failure_packet = load_packet_fixture("packet-failure.json")
    fallback = failure_packet.get("fallback") or {}
    page.set_viewport_size({"width": 1440, "height": 900})
    open_page(page, "failure")
    expect(page.get_by_text("今日 AI 分析不可用", exact=True)).to_be_visible()
    expect(page.get_by_text(str(fallback.get("analysis_date")), exact=True)).to_be_visible()
    expect(page.get_by_text(str(fallback.get("stage")), exact=True).first).to_be_visible()
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


def chart_interaction_flow(page: Page) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    open_page(page)
    page.evaluate("localStorage.removeItem('btc-dashboard.chart-height.v1')")
    page.reload(wait_until="networkidle")
    expect(page.locator(".evidence-board")).to_be_visible()

    chart = page.locator(".shared-chart-wrap")
    handle = page.locator(".chart-resize-handle")
    chart_box = chart.bounding_box()
    assert chart_box and abs(chart_box["height"] - 420) < 1, "图表默认高度应为 420px"
    assert page.locator(".chart-subtitle").count() == 0, "图表标题下方说明应已删除"

    page.get_by_text("持有者行为", exact=True).click()
    page.locator(".metric-card").filter(has_text="HODLer NPC · 30d").first.click()
    expect(page.locator("#chart-title")).to_have_text("HODLer NPC · 30d")
    expect(page.locator(".chart-legend")).to_contain_text("HODLer 投降卖出尖峰")
    legend_text = page.locator(".chart-legend").inner_text()
    assert ">=155d 花费价值占比" not in legend_text, "HODLer 页面不应显示 ≥155d 柱状图"
    assert "HODLer NPC · 30d" not in legend_text, "柱状指标不应再显示重复的指标线开关"
    assert "阈值线" not in legend_text, "柱状指标不应显示对应的阈值线开关"
    assert page.locator(".chart-legend .legend-line.indicator").count() == 0
    assert page.locator(".chart-legend .legend-line.threshold").count() == 0
    expect(page.locator(".shared-chart")).to_have_attribute("aria-label", "BTC 价格、HODLer 柱状图、历史熊底共享图表")
    assert page.locator(".bars-empty-note").count() == 0, "全量范围应能看到柱状数据"
    assert_bar_visual_height(page, "hodler")

    page.locator(".metric-card").filter(has_text="≥155d 花费价值占比").first.click()
    expect(page.locator("#chart-title")).to_have_text("≥155d 花费价值占比")
    expect(page.locator(".chart-legend")).to_contain_text(">=155d 花费价值占比")
    legend_text = page.locator(".chart-legend").inner_text()
    assert "HODLer 投降卖出尖峰" not in legend_text, "≥155d 页面不应显示 HODLer 柱状图"
    assert "≥155d 花费价值占比" not in legend_text, "柱状指标不应再显示重复的指标线开关"
    expect(page.locator(".shared-chart")).to_have_attribute("aria-label", "BTC 价格、≥155d 柱状图、历史熊底共享图表")
    assert_bar_visual_height(page, "spent155")

    tier = page.locator(".metric-tier").first
    background = tier.evaluate("element => getComputedStyle(element).backgroundColor")
    assert background in ("transparent", "rgba(0, 0, 0, 0)"), "观察区状态不应使用文字背景色"

    handle_box = handle.bounding_box()
    assert handle_box
    handle.scroll_into_view_if_needed()
    handle_box = handle.bounding_box()
    assert handle_box and 0 <= handle_box["y"] <= 900, "图表高度手柄应能滚动到视口内"
    page.mouse.move(handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    page.mouse.down()
    page.mouse.move(handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2 + 120)
    page.mouse.up()
    chart_box = chart.bounding_box()
    assert chart_box and abs(chart_box["height"] - 540) < 2, "拖动手柄应增加图表高度"

    page.reload(wait_until="networkidle")
    expect(page.locator(".evidence-board")).to_be_visible()
    chart_box = page.locator(".shared-chart-wrap").bounding_box()
    assert chart_box and abs(chart_box["height"] - 540) < 2, "刷新后应保留图表高度"

    handle = page.locator(".chart-resize-handle")
    handle.focus()
    handle.press("End")
    assert page.locator(".chart-resize-handle").get_attribute("aria-valuenow") == "760"
    handle.press("Home")
    assert page.locator(".chart-resize-handle").get_attribute("aria-valuenow") == "320"
    handle.press("ArrowDown")
    assert page.locator(".chart-resize-handle").get_attribute("aria-valuenow") == "344"

    page.get_by_text("持有者行为", exact=True).click()
    page.locator(".metric-card").filter(has_text="HODLer NPC · 30d").first.click()
    page.get_by_role("button", name="1 年", exact=True).click()
    expect(page.locator(".bars-empty-note")).to_be_visible()
    page.get_by_role("button", name="全量", exact=True).click()
    expect(page.locator(".bars-empty-note")).to_have_count(0)
    page.screenshot(path=str(EVIDENCE / "desktop-bars-overlay.png"), full_page=True)

    page.evaluate("localStorage.setItem('btc-dashboard.chart-height.v1', '9999')")
    page.reload(wait_until="networkidle")
    expect(page.locator(".evidence-board")).to_be_visible()
    assert page.locator(".chart-resize-handle").get_attribute("aria-valuenow") == "420", "非法高度应回到默认值"


def chart_curve_toggle_flow(page: Page) -> None:
    """v0.2.4 final controls: hide STH primary; group SIPL; split aSOPR."""
    page.set_viewport_size({"width": 1440, "height": 900})
    open_page(page)

    page.get_by_text("估值与成本", exact=True).click()
    page.locator(".metric-card").filter(has_text="STH-MVRV 战术价位").first.click()
    sth_legend = page.locator(".chart-legend")
    sth_text = sth_legend.inner_text()
    assert "STH-MVRV 战术价位" not in sth_text, "STH-MVRV 主线不应保留图例开关"
    for label in ("5%分位 × STH-RP", "1.5σ × STH-RP", "1.5·MAD × STH-RP"):
        expect(sth_legend.get_by_role("button", name=label, exact=True)).to_be_visible()
    page.locator(".shared-chart").screenshot(path=str(EVIDENCE / "v024-sth-primary-hidden.png"))
    assert_chart_contains_colour("v024-sth-primary-hidden.png", (222, 138, 87))
    for colour in ((214, 93, 82), (78, 155, 115), (93, 143, 203)):
        assert_chart_contains_colour("v024-sth-primary-hidden.png", colour)
    assert_chart_excludes_colour("v024-sth-primary-hidden.png", (167, 122, 194))

    page.get_by_text("供应盈亏", exact=True).click()
    page.locator(".metric-card").filter(has_text="SIPL").first.click()
    sipl_legend = page.locator(".chart-legend")
    sipl_pair = sipl_legend.get_by_role("button", name="SIPL", exact=True)
    sipl_gap = sipl_legend.get_by_role("button", name="SIPL 差值", exact=True)
    expect(sipl_pair).to_have_attribute("aria-pressed", "true")
    expect(sipl_gap).to_have_attribute("aria-pressed", "true")
    assert sipl_legend.get_by_role("button", name="Supply in Loss", exact=True).count() == 0
    page.locator(".shared-chart").screenshot(path=str(EVIDENCE / "sipl-pair-before.png"))
    sipl_pair.focus()
    sipl_pair.press("Space")
    expect(sipl_pair).to_have_attribute("aria-pressed", "false")
    expect(sipl_gap).to_have_attribute("aria-pressed", "true")
    page.wait_for_timeout(150)
    page.locator(".shared-chart").screenshot(path=str(EVIDENCE / "sipl-pair-after.png"))
    assert_chart_canvas_changes("sipl-pair-before.png", "sipl-pair-after.png")
    sipl_pair.press("Space")
    expect(sipl_pair).to_have_attribute("aria-pressed", "true")
    page.locator(".shared-chart").screenshot(path=str(EVIDENCE / "sipl-gap-before.png"))
    sipl_gap.click()
    expect(sipl_pair).to_have_attribute("aria-pressed", "true")
    expect(sipl_gap).to_have_attribute("aria-pressed", "false")
    page.wait_for_timeout(150)
    page.locator(".shared-chart").screenshot(path=str(EVIDENCE / "sipl-gap-after.png"))
    assert_chart_canvas_changes("sipl-gap-before.png", "sipl-gap-after.png")

    page.get_by_text("链上资本流", exact=True).click()
    page.locator(".metric-card").filter(has_text="aSOPR").first.click()
    asopr_legend = page.locator(".chart-legend")
    asopr = asopr_legend.get_by_role("button", name="aSOPR", exact=True)
    asopr_3d = asopr_legend.get_by_role("button", name="3日滞后均值（趋势辅助）", exact=True)
    asopr_7d = asopr_legend.get_by_role("button", name="7日滞后均值（趋势辅助）", exact=True)
    for control in (asopr, asopr_3d, asopr_7d):
        expect(control).to_have_attribute("aria-pressed", "true")
    page.locator(".shared-chart").screenshot(path=str(EVIDENCE / "asopr-3d-before.png"))
    for colour in ((214, 93, 82), (78, 155, 115)):
        assert_chart_contains_colour("asopr-3d-before.png", colour)
    assert_chart_excludes_colour("asopr-3d-before.png", (167, 122, 194))
    page.get_by_role("button", name="1 年", exact=True).click()
    page.wait_for_timeout(150)
    page.locator(".shared-chart").screenshot(path=str(EVIDENCE / "v024-asopr-adaptive-axis-1y.png"))
    asopr_3d.click()
    expect(asopr).to_have_attribute("aria-pressed", "true")
    expect(asopr_3d).to_have_attribute("aria-pressed", "false")
    expect(asopr_7d).to_have_attribute("aria-pressed", "true")
    page.wait_for_timeout(150)
    page.locator(".shared-chart").screenshot(path=str(EVIDENCE / "asopr-3d-after.png"))
    assert_chart_canvas_changes("asopr-3d-before.png", "asopr-3d-after.png")

    page.get_by_text("长期成本锚", exact=True).click()
    page.locator(".metric-card").filter(has_text="Reserve Risk").first.click()
    expect(page.locator("#chart-title")).to_have_text("Reserve Risk · 周期")
    reserve_aria = page.locator(".shared-chart").get_attribute("aria-label") or ""
    assert "Reserve Risk · 周期归一化 z" not in reserve_aria
    page.screenshot(path=str(EVIDENCE / "v024-curve-toggle-controls.png"), full_page=True)


def ai_contract_flow() -> None:
    result = pytest.main(
        [
            "-q",
            str(ROOT / "tests" / "acceptance" / "test_ai_contract.py"),
            str(
                ROOT
                / "tests"
                / "acceptance"
                / "test_ai_semantic_contract.py"
            ),
            str(
                ROOT
                / "tests"
                / "acceptance"
                / "test_daily_automation.py"
            ),
            str(ROOT / "tests" / "acceptance" / "test_input_boundary.py"),
            str(ROOT / "tests" / "acceptance" / "test_packet_contract.py"),
            str(ROOT / "tests" / "acceptance" / "test_v024_chart_data.py"),
            str(ROOT / "tests" / "acceptance" / "test_evidence_contract.py"),
            str(ROOT / "tests" / "acceptance" / "test_evidence_fixtures.py"),
            str(ROOT / "tests" / "acceptance" / "test_evidence_freshness.py"),
            str(ROOT / "tests" / "acceptance" / "test_core_dimensions.py"),
            str(ROOT / "tests" / "acceptance" / "test_auxiliary_themes.py"),
            str(ROOT / "tests" / "acceptance" / "test_stage_guardrail.py"),
            str(ROOT / "tests" / "acceptance" / "test_v03_ai_boundary.py"),
            str(ROOT / "tests" / "acceptance" / "test_v03_packet_contract.py"),
        ]
    )
    if result != pytest.ExitCode.OK:
        raise AssertionError(f"AI 契约验收失败，pytest exit code={result}")


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT))
    npm = "npm.cmd" if os.name == "nt" else "npm"
    build = subprocess.run(
        [npm, "run", "build"],
        cwd=ROOT / "dashboard",
        check=False,
        text=True,
    )
    if build.returncode != 0:
        raise AssertionError(f"前端构建失败，exit code={build.returncode}")
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
            chart_interaction_flow(page)
            chart_curve_toggle_flow(page)
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
