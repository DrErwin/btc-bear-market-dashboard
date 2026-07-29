# v0.2.4 — 实现记录

> 状态：已实现并通过本地验收。本版本记录图表参考线与时间线曲线同步；状态阈值统一属于后续 [v0.3.1](../v0.3.1/implementation-record.md)。

## 1. 实现内容

- 仓库保存了本次指标配置 `specs/v0.2.4/btc-indicator-config-2026-07-28.json`，SHA-256 为 `435BB97DF65A69F1C50E084AB3C18A048D2AED57699B1E2945BDC1B72C2AFF81`。
- 配置中的参考线数量、数值、方向和名称进入 `series.metrics[].thresholds`。
- STH-MVRV 图表不绘制水平参考线，因此不显示“阈值线”开关；三条 STH-RP 战术价格曲线继续保留。
- 数据包新增向后兼容的 `series.metrics[].lines[]`：每条线保留 `id`、`label`、`axis` 和逐日 `points`。固定包由指标验证时间线同步脚本生成，后端日包组装也会保留主线与额外线。
- `useChartOption.ts` 将可见指标验证曲线作为独立 ECharts 系列绘制：指标轴线使用指标纵轴，价格轴线使用 BTC 价格纵轴；所有指标数据线改为细实线，次要线固定按红、绿、蓝循环，参考线与熊底线保留更细的虚线。`sth-mvrv.primary` 只留在数据包，不再渲染、提示或进入图例。
- `SharedChart.vue` 将图例与图表共用曲线可见性规则：SIPL 的 `SIPL` 开关同时控制 Profit/Loss，`SIPL 差值` 单独控制差值；aSOPR 的原始、3 日、7 日线分别独立开关。其他指标保持既有行为，HODLer 与 ≥155d 仍然只显示各自柱状图及右轴参考线。
- Reserve Risk 的所有看板展示名改为 `Reserve Risk · 周期`；原始 z-score 计算不变，图表参考线使用本次配置。状态阈值不属于本版本范围。
- 保留 v0.2.3 的图表高度、缩放、时间拖动、十字读数、历史熊底线、全屏和手机布局行为。
- 指标纵轴改为与指标验证面板一致的可见区间自适应：当前范围内取指标线的 2%／98% 分位，纳入全部参考线后上下各留 8% 空白。这样少数极端历史点不会把日常波动压得过平；BTC 价格轴与柱状图右轴未改。

## 2. 验收结果

- `cd dashboard && npm run build`：通过，Vue 类型检查与 Vite 构建成功；保留既有 bundle size warning。
- 本版本最初验收时，`python -m pytest -q tests/acceptance` 为 41 项通过。
- `python tests/acceptance/run_acceptance.py`：通过，覆盖成功、回退、无回退、桌面／390px 响应式、键盘与受限语言检查。
- 浏览器验收覆盖 STH 主线缺席、SIPL 分组开关、aSOPR 独立开关、红绿蓝细实线、无紫色次要线，以及 1 年范围的自适应纵轴。

## 3. 复核证据

- `artifacts/review-evidence/v0.3.0/desktop-success.png`
- `artifacts/review-evidence/v0.3.0/desktop-bars-overlay.png`
- `artifacts/review-evidence/v0.3.0/mobile-success.png`
- `artifacts/review-evidence/v0.3.0/v024-sth-primary-hidden.png`
- `artifacts/review-evidence/v0.3.0/v024-curve-toggle-controls.png`
- `artifacts/review-evidence/v0.3.0/asopr-3d-before.png`（全量范围）
- `artifacts/review-evidence/v0.3.0/v024-asopr-adaptive-axis-1y.png`（1 年范围自适应纵轴）

## 4. 兼容性边界

- v0.2.4 本身没有改变数据源、AI 输入输出、阶段判断或部署配置。
- 后续 v0.3.1 复用本版本图表配置统一了状态阈值；该变化不回写为 v0.2.4 的能力。
- `points` 与 `thresholds` 保留；旧数据包没有 `lines` 时前端回退为单条主线，新增数据包按验证面板清单显示全部曲线。
- 不提供交易建议、价格预测、仓位或杠杆建议。
