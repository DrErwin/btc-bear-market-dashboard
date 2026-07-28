# v0.2.1 — 实现记录

> 状态：已实现（两轮反馈）并通过 v0.2.0 验收回归。本文记录最终落地方式与关键文件；第一轮的两处误解已在第二轮纠正，下面按**最终状态**描述。
>
> ⚠️ 勘误（2026-07-28，v0.2.2 补）：第 4 节"按住拖动平移时间窗"与"Y 轴随可见切片自动 min/max"两项**实测未达成**——inside dataZoom 的 `moveOnMouseDrag` 与 tooltip axisPointer 共存时拖动不触发；阈值 markLine 在远端切片会落在自适应纵轴范围外不可见。已由 [v0.2.2 实现记录](../v0.2.2/implementation-record.md) 第 3、5 节修复（手动拖动平移、阈值值纳入 bounds）。

## 1. 范围

v0.2.0 上线后的看板交互与图表增强，来自两轮使用反馈（第一轮 5 条、第二轮 6 条）。仍只输出周期证据，不给交易建议。

## 2. 折叠左侧指标列（非分类）

第一轮误把上方**分类看板**（CategoryGrid）加了折叠；第二轮纠正为图表**左侧的指标列**（metric-rail）。

- `App.vue` 加 `railCollapsed` ref。折叠时 `.workbench.is-rail-collapsed`（`tokens.css`：`grid-template-columns:1fr` + `.metric-rail{display:none}`，复用 760px 断点写法），chart-column 自动占满宽度。
- 折叠态在 workbench 顶部显示一行紧凑指标 tab（`visibleMetrics` + `selectMetric`）+ "展开指标列"按钮；展开态恢复原 metric-rail，其头部（`.rail-heading`）加"收起指标列"按钮。
- CategoryGrid 恢复为常驻（无折叠）。

## 3. tier 三档命名与配色（压力红系）

`services/data/packet.py::_compute_tier` 输出「未进入观察区 / 进入观察区 / 重点观察区」（过 0 / 1 / ≥2 触发档；`role:"neutral"` 的中性线不计入）。配色为压力红系：

| 档位 | class | 颜色 |
|---|---|---|
| 未进入观察区 | `tier-none` | `--muted` 灰 |
| 进入观察区 | `tier-enter` | `--orange-deep` 橙 |
| 重点观察区 | `tier-key` | `--red`（新增 token `#c04a3a`）红 |

- 新建 `dashboard/src/utils/tier.ts::tierClass(label)`（文本→class），`MetricList.vue` 指标卡与 `SharedChart.vue` 的 `chart-facts` 复用。
- `tokens.css` 加 `.tier-none/.tier-enter/.tier-key`（淡背景，指标卡浅底用）；另加 `.chart-facts strong.tier-*`（深底 chart-card 用更亮字色，高 specificity 覆盖 `.chart-facts strong` 的白色）。

## 4. 图表时间轴、缩放与十字读数

- 预设范围按钮（6 月 / 1 年 / 2 年 / 4 年 / 全量）+ 当前可见范围文本。
- dataZoom slider + inside 联动主图与柱状图 x 轴；inside 设 `moveOnMouseDrag:true, moveOnMouseMove:false`——鼠标移动只出十字辅助线、不平移，按住拖动才平移时间窗，滚轮/slider 缩放。
- `tooltip.axisPointer.type:"cross"` + `axisPointer.link`：悬浮时同时显示垂直时间读数与水平指标值读数。
- Y 轴随可见切片自动 min/max（`bounds()`，留 8% padding）。
- 第二轮：grid `bottom:72` + slider `bottom:24`，x 轴日期标签不再被 slider 遮挡。

## 5. 历史熊底虚线

packet 透传 `bottoms`（`services/data/derive.py::BOTTOMS`：2011-11-18 / 2015-01-14 / 2018-12-15 / 2022-11-21）。`useChartOption` 把垂直虚线合并进指标 series 的 `markLine.data`（与水平阈值线同数组）。`types.ts` 加 `BottomMark`，`Packet`/`DashboardData` 加 `bottoms`，前端 legend 加"历史熊底"项。

## 6. 柱状图只在两个指标（按 id，非按类）

第一轮误用 `metric.category==="holders"`，导致 Seller Exhaustion 也带柱状图；第二轮改为 `["hodler","spent155"].includes(metric.id)`（`useChartOption` 的 `BAR_METRIC_IDS` + `SharedChart` 的 `isBarMetric`）。HODLer NPC + ≥155d 花费占比的柱状图只在看这两个指标时出现；图例开关、subtitle、bars-meta 说明区同步显隐。

## 7. BTC 价格对数坐标

`SharedChart` 加"线性 / 对数"切换（`logPrice` ref，默认线性）。`useChartOption` 的 `priceAxis` 据此 `type:"log"|"value"`；对数模式去掉 `min/max`（log 不接受 0/负 padding），让 ECharts 用 dataMin。price>0 满足 log 前提；指标轴与柱状图轴不变。

## 8. 核心/辅助标签颜色增强

`tokens.css` 的 `.metric-role.is-core`/`.is-supporting` 在原有文字+边框色基础上加淡 `background`（核心薄荷绿底、辅助灰底）。`SharedChart` 的 `chart-facts`"证据角色" `<strong>` 加 `is-core`/`is-supporting` class（`.chart-facts strong.is-*` 高 specificity 在深底上着色：核心 `--mint`、辅助 `--muted-dark`）。

## 9. 验收

- `cd dashboard && npm run build`：vue-tsc 无类型错误，585 模块。
- `python tests/acceptance/run_acceptance.py`：**37 passed + ACCEPTANCE PASS**（v0.1.0 success/fallback/no-fallback/responsive/keyboard/受限语言 回归通过）。
- 数据层 tier 命名 + bottoms 字段已随 packet 重新生成（`run_daily --mock-ai` + `build_fixtures`，三份 packet 一致）。

## 10. 关键文件

- 前端：`dashboard/src/utils/tier.ts`（新）、`composables/useChartOption.ts`、`components/{SharedChart,MetricList}.vue`、`App.vue`、`styles/tokens.css`、`types.ts`、`composables/useDashboardData.ts`
- 数据层：`services/data/packet.py`（tier 命名 + bottoms 字段）、`services/data/derive.py::BOTTOMS`
- 需求：`specs/v0.2.1/requirements.md`
