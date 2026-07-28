# v0.2.3 — 实现记录

> 状态：已实现并通过本地验收。范围限定为前端图表布局、交互和观察区配色；数据层、AI 契约和部署配置未改变。

## 1. 实现内容

- `SharedChart.vue` 删除图表标题下的重复说明，新增 `320–760px` 高度拖动手柄、键盘调整、触摸支持和 `localStorage` 记忆。默认高度为 `420px`，非法保存值恢复默认；全屏时使用屏幕可用高度。
- `useChartOption.ts` 将柱状数据键对齐到 `hodler_npc_30d` 与 `spent_value_ge155d_share`，取消第二个 grid，让当前指标对应的柱子与主图共用一个绘图区和时间轴，并通过右侧独立纵坐标将柱子放大到主图底部约 40% 区域。
- 选中 HODLer 或 ≥155d 柱状指标时，只渲染对应的一组柱子；同时直接移除对应指标线系列和阈值线开关，保留 BTC 价格线与历史熊底线作为时间参照。
- 缺失柱状日期保持为空；时间窗没有柱状数据时显示提示，不做前向填充。
- `tokens.css` 移除观察区状态背景色，保留灰/橙/红三档文字颜色。
- `tests/acceptance/run_acceptance.py` 增加标题、高度拖动与刷新记忆、键盘边界、真实柱状数据、当前柱状系列与右轴映射、最小可见柱高、无数据提示、纯文字配色和截图检查。

## 2. 验收结果

- `cd dashboard && npm run build`：通过，Vue 类型检查通过，Vite 构建完成（585 modules；保留原有 bundle size warning）。
- `python tests/acceptance/run_acceptance.py`：通过，37 项契约测试通过，并输出 `ACCEPTANCE PASS`。
- 浏览器检查覆盖：桌面柱状叠加、高度拖动/刷新记忆/非法值回退、1 年范围无柱状数据提示、全量范围柱状数据恢复、390px 响应式无横向溢出。

## 3. 复核证据

- `artifacts/review-evidence/desktop-bars-overlay.png`
- `artifacts/review-evidence/mobile-success.png`
- `artifacts/review-evidence/desktop-success.png`

## 4. 兼容性边界

本版没有修改 packet schema、数据源、AI 输入输出、Python 服务、Cloudflare 配置或 Git 发布状态。图表高度偏好只存在当前浏览器的 `btc-dashboard.chart-height.v1` 本地存储中。
