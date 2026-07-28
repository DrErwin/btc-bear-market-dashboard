# v0.2.2 — 下一阶段需求（图表交互修复与精简）

> 状态：已实现（见 [实现记录](implementation-record.md)）。基于 v0.2.1 实现后的使用反馈。本文记录用户提出的 4 条改进。其中第 2、4 条是 v0.2.1 已声明但实际未达成的行为，属修复；第 1、3 条是精简与合并。

## 1. 删除「共享图表 / 独立于 AI 输入」标题

图表卡片头部当前有一行 eyebrow「共享图表 / 独立于 AI 输入」（`SharedChart.vue` chart-head 内的 `<span class="eyebrow">`）。该文案多余，删除；保留指标名 `h3` 与 subtitle。

> 用户原话："删除'共享图表 / 独立于 AI 输入'"。

## 2. 图表内按住拖动可平移时间窗（修复 v0.2.1 第 4 条未生效项）

v0.2.1 第 4 条已确认并写进实现记录：鼠标移动只出十字辅助线、不平移；**按住拖动**平移时间窗，滚轮/slider 缩放。代码里也配了 inside dataZoom 的 `moveOnMouseDrag:true, moveOnMouseMove:false`（`useChartOption.ts`）。

但实际在图上**按住拖动无法平移时间范围**——只有下方 slider 拖柄和滚轮缩放能改范围。需求：让图表画布内的按住拖动真正能平移可见时间窗（与 slider 联动，range 按钮高亮同步切换为「自定义」）。

排查方向（实现阶段定）：inside dataZoom 的 `moveOnMouseDrag` 与 `tooltip.trigger:"axis"` + `axisPointer.type:"cross"` 存在手势冲突，crosshair 占用了 mousemove/drag 事件；可能需调整 tooltip/axisPointer 配置，或改用更可靠的拖动平移方案（如 graphic 拖把手 / roam）。不改变"移动出十字、不平移"的既有承诺。

> 用户原话："图表拖动鼠标还是没法更改时间范围。"

## 3. 曲线开关合并进四项图例（去掉重复 legend）

当前图表有**两份图例**：

- ECharts 原生 `legend`（`useChartOption.ts` option.legend，`top:0`）：可点击切换显隐，但只含「BTC 价格 / 指标名 /（柱状图指标名）」，**没有**阈值线、历史熊底。
- 自定义 HTML `.chart-legend`（`SharedChart.vue`）：静态展示「BTC 价格 / 指标名 / 阈值线 / 历史熊底（+柱状色块）」，**不可点击**。

两份重复且功能割裂。需求：**只保留一份图例**，即显示「BTC 价格 / 指标曲线 / 阈值线 / 历史熊底」的那份，并把曲线开关（点击显隐）做进这一份里——每项点击可切换对应曲线/线条的显示；删除原生 ECharts legend，不再"多做一份"。

实现注意：阈值线、历史熊底是 markLine（非独立 series，原生 legend 无法直接切换），需把"阈值线""历史熊底"做成可整体显隐的开关（点击切 markLine 组的 show，或拆成独立 series 由 legend 驱动）。BTC 价格、指标曲线本身是 series，可直接切换。柱状图两项（仅 hodler/spent155 时出现）的开关同样并入此图例。

> 用户原话："图表的曲线开关不用多做一份，就放在 BTC 价格 / MVRV / 阈值线 / 历史熊底 那里面。"

## 4. 纵坐标动态调整时阈值线始终可见（修复 v0.2.1 自适应出界项）

指标 y 轴的 min/max 由 `bounds()` 按当前可见切片的数据值 ±8% padding 计算（`useChartOption.ts`：`indBounds = bounds(indicatorValues.slice(...))`）。水平阈值线（markLine `yAxis: threshold.value`，挂在指标 series 上、属指标轴）的 y 值**未纳入 bounds**——当可见切片的指标值离阈值较远时（如 MVRV 切片在 1.5–2.2、阈值在 1.0），阈值线被算到指标轴范围之外而**不可见**。

需求：动态调整纵坐标时，阈值线**始终在画面内可见**——指标 y 轴的自适应范围必须把阈值值纳入计算（如 `bounds([...indicatorValues, ...thresholdValues])`），保证阈值线不超出轴范围。

实现注意：纳入阈值会压缩数据纵向幅度（阈值远离时数据被压扁），需在"始终显示阈值"与"数据可辨"间取平衡（如对阈值纳入做合理 cap 或仅向外扩展不内缩），具体策略实现阶段定；价格轴、柱状轴不受影响。

> 用户原话："图表动态调整纵坐标的时候要时刻能显示阈值线。"

---

## 备注

- 第 2、4 条属于 v0.2.1 已声明行为的修复，实现后应同步在 v0.2.1 实现记录中标注"实测未达成，由 v0.2.2 修复"，避免记录与实际不符。
- 第 1、3 条为精简性改动，不改变数据口径与 AI/回退链路，预期无需改 `services/` 数据层，仅前端 `SharedChart.vue` + `useChartOption.ts`（+ 可能 `tokens.css` 图例样式）。
- 验收沿用 v0.2.0 回归（success/fallback/no-fallback/responsive/keyboard/受限语言），并补充：拖动平移、四项图例可点切换、阈值线在远端切片仍可见的手动核对。
