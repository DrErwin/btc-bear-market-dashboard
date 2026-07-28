# v0.2.2 — 实现记录

> 状态：已实现并通过 v0.2.0 验收回归。本文记录 4 条图表交互修复/精简的最终落地方式。其中第 3、5 节是 v0.2.1 已声明但实测未达成的行为，本轮修复。

## 1. 范围

v0.2.1 后的使用反馈 4 条：删多余 eyebrow、修复图表内拖动平移、曲线开关合并进四项图例、纵坐标自适应时阈值线始终可见。仅前端，不动数据层 / AI / 回退链路。

## 2. 删除「共享图表 / 独立于 AI 输入」eyebrow

`SharedChart.vue` chart-head 内 `<span class="eyebrow">共享图表 / 独立于 AI 输入</span>` 删除；保留指标名 `h3` 与 subtitle。

## 3. 图表内拖动平移时间窗（修复 v0.2.1 第 4 条未生效）

- **现象**：v0.2.1 配了 inside dataZoom `moveOnMouseDrag:true`，但浏览器实测**按住拖动无效**（滚轮缩放有效）。查证为 ECharts inside dataZoom 的 `moveOnMouseDrag` 与 `tooltip.axisPointer.type:"cross"` 共存时的已知冲突——社区多报，配置本身是推荐写法但拖动仍不触发（[Apache ECharts Drag 指南](https://echarts.apache.org/handbook/en/how-to/interaction/drag/)、[echarts#20991](https://github.com/apache/echarts/issues/20991)）。
- **方案**：改为**手动拖动平移**。`SharedChart` 用 `chartWrapRef` 包裹 `VChart`，`@mousedown`（仅左键、且不在底部 60px slider/轴标签区——那块留给 ECharts）记录起点 `clientX` 与起点 `zoom`；`window` 级 `mousemove` 按像素位移换算成百分比平移 `zoom.value`（右拖"抓"住图露出更早数据 → start/end 降；左拖反之），`mouseup` 收尾。`zoom.value` 驱动 slider + inside 一起更新，range 按钮高亮切到「自定义」。`onBeforeUnmount` 移除监听。
- `useChartOption` 的 inside dataZoom 关掉 `moveOnMouseDrag:false`（避免与手动处理冲突），保留 `zoomOnMouseWheel:true`、`moveOnMouseMove:false`。十字辅助线、滚轮缩放、slider 拖柄行为不变。
- **验证**：1 年预设下右拖 200px → 范围 `2025-07-28 ~ 2026-07-27` 变 `2025-02-08 ~ 2026-02-08`；左拖 200px → 回到 `2025-07-28 ~ 2026-07-27`。双向可用，方向符合"抓取"直觉。

## 4. 曲线开关合并进四项图例（去重）

- **现状**：两份图例——ECharts 原生 `legend`（可点切换，但只含 BTC 价格 / 指标 / 柱状，**无**阈值线 / 熊底）+ 自定义 HTML `.chart-legend`（静态、四项全、**不可点**）。
- **方案**：删 `useChartOption` 的 `legend` 整段（含 `legendData`）；HTML `.chart-legend` 由 `<span>` 改为 `<button>` 开关。新增 `ChartVisibility`（`price/indicator/thresholds/bottoms/hodler/spent`）ref，注入 `useChartOption`。`SharedChart` 一并移除 `LegendComponent` 注册。
- **可见性驱动**：BTC 价格 / 指标 / 柱状用对应 series 的 `lineStyle.opacity` / `areaStyle.opacity` / `itemStyle.opacity`（0/1）；阈值线、历史熊底是 markLine 组，按开关决定是否纳入 indicator series 的 `markLine.data`——故可与指标曲线**独立显隐**（关曲线留阈值，或关阈值留熊底）。状态在切换指标时保留。
- `tokens.css`：`.chart-legend span` → `.chart-legend button`（按钮 reset + hover 边框 + `.is-off{opacity:.35}`）。
- **验证**：点掉「BTC 价格」→ 价格线 / 面消失，MVRV 线、橙色阈值虚线、蓝灰熊底虚线仍在，按钮变暗；`aria-pressed` 与 `.is-off` 正确切换。

## 5. 阈值线始终可见（修复 v0.2.1 自适应出界）

- `useChartOption`：`indBounds` 原仅按可见切片指标值算，阈值 markLine（挂在指标轴）会落在自适应范围外而不可见（如 MVRV 切片在 1.5–2.2、阈值在 1.0 时）。改为 `bounds([...可见指标值, ...阈值值])`，阈值必落在轴范围内。
- 价格轴、柱状轴不变。纳入阈值会压缩数据纵向幅度（阈值远离时数据被压扁），符合"时刻显示阈值线"诉求；未加 cap（需求明确要"始终显示"，权衡由用户接受）。
- **验证**：全量范围（2010-08-16 → 2026-07-27）下橙色阈值虚线横贯可见。

## 6. 验收

- `cd dashboard && npm run build`：vue-tsc 无类型错误，585 模块。
- 浏览器（http://127.0.0.1:5180）手动核对四项均达成：eyebrow 已删、拖动双向平移、图例点击切换隐藏、阈值线全量可见。
- `python tests/acceptance/run_acceptance.py`：**37 passed + ACCEPTANCE PASS**（v0.1.0 success/fallback/no-fallback/responsive/keyboard/受限语言 回归通过）。

## 7. 关键文件

- 前端：`dashboard/src/components/SharedChart.vue`（删 eyebrow、手动拖动、图例改 button、`visibility` ref）、`composables/useChartOption.ts`（`ChartVisibility` 类型、删 `legend`、阈值纳入 `bounds`、inside `moveOnMouseDrag:false`）、`styles/tokens.css`（`.chart-legend button` 开关样式）。
- 需求：`specs/v0.2.2/requirements.md`。

## 8. 与 v0.2.1 记录的关系

v0.2.1 实现记录第 4 节"按住拖动平移时间窗"与"Y 轴随可见切片自动 min/max"两项，实测未完全达成（拖动无效、阈值线远端切片不可见）；本轮第 3、5 节为对应修复，并已在 v0.2.1 记录顶部加勘误注。
