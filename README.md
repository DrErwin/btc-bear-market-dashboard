# BTC 熊底证据看板

这是一个公开、只读的研究型看板：它把固定的 16 个 BTC 周期指标整理成六类证据，展示当前市场阶段、证据一致性、阈值位置和共享图表。它不预测确切最低点，也不提供交易建议。

## 本地运行

```powershell
cd dashboard
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:4173/`。

## 构建网页

页面使用 `dashboard/public/data/` 中的固定 JSON，不需要网络、付费 API 或真实 AI：

```powershell
cd dashboard
npm run build
```

构建后的静态网页位于 `dashboard/dist/`，可部署到任意静态网站托管服务。

页面状态可通过 URL 切换：

- `?fixture=success`：今日成功分析
- `?fixture=failure`：今日失败，展示 2026-07-26 回退
- `?fixture=no-fallback`：今日失败且没有上一份成功结果
