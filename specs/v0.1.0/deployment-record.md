# v0.1.0 — 上线记录

## 发布状态

- **版本**：`v0.1.0`
- **状态**：已上线（固定数据展示版）
- **发布日期**：2026-07-27
- **公开地址**：[https://btc-bear-market-dashboard.erwinwu000.workers.dev/](https://btc-bear-market-dashboard.erwinwu000.workers.dev/)
- **代码仓库**：[DrErwin/btc-bear-market-dashboard](https://github.com/DrErwin/btc-bear-market-dashboard)
- **托管方式**：Cloudflare Workers Static Assets

## 已核实内容

- Cloudflare Worker `btc-bear-market-dashboard` 的 `workers.dev` 公开访问已启用；
- 最新部署版本已 100% 接收流量；
- 公开网址返回 HTTP 200，并返回看板的 HTML 首页；
- 当前公开站点使用 `dashboard/` 构建出的静态资源。

## 当前范围边界

本次上线证明 `v0.1.0` 页面可以被公开访问，但不代表每日数据与 AI 分析已经自动更新。当前站点仍使用固定 fixture 数据。

以下能力留给 `v0.2.0`：

- 完整数据包与整包回退；
- 图表时间范围选择、缩放和拖动；
- HODLer 投降卖出与 `>=155d` 花费价值柱状图；
- 数据和 AI 分析的每日自动更新。
