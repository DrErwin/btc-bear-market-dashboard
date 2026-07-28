# BTC 熊底证据看板

公开、只读的研究型看板：把 16 个 BTC 周期指标整理成六类证据，展示当前市场阶段、证据一致性、阈值位置、共享图表与持有者卖出柱状图。它不预测确切最低点，也不提供交易建议。

> 当前线上版本：`v0.1.0`（固定数据展示版，已上线）；`v0.2.0` 已实现（真实每日数据、图表时间轴/缩放、HODLer 投降柱状图、每日自动更新），待配置 Secret 后首次自动更新上线。

## 在线访问

公开地址：[btc-bear-market-dashboard.erwinwu000.workers.dev](https://btc-bear-market-dashboard.erwinwu000.workers.dev/)

`v0.1.0` 部署在 Cloudflare Workers Static Assets。`v0.2.0` 上线后同一地址将切换为每日真实数据。

## v0.2.0 能力

- **完整数据包 + 整包回退**：页面只读一份 `packet.json`；每日更新要么整包成功，要么继续展示上一份完整成功包，不混用不同日期的数据。
- **图表时间轴与交互缩放**：6 月 / 1 年 / 2 年 / 4 年 / 全量预设、滚轮缩放、拖动平移、纵坐标随可视范围自动适配。
- **HODLer 投降 + ≥155d 花费价值柱状图**：主图下方两个独立柱状系列，与主图共享同一时间窗口。
- **每日自动更新**：GitHub Actions 每日 UTC 01:13 抓取公开链上数据 → 派生 16 指标 → 受约束 AI 分析 → 校验 → 原子发布；密钥只存 GitHub Secrets。

详见 [实现记录](specs/v0.2.0/implementation-record.md) 与 [验收记录](specs/v0.2.0/acceptance-record.md)。

## 本地运行

前端：

```powershell
cd dashboard
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:4173/`。

生成真实数据包（Python，stdlib-only，无需额外依赖）：

```powershell
python services/run_daily.py --mock-ai
```

`--mock-ai` 用固定合规分析（无需 AI key）；配置 `AI_API_KEY` / `AI_BASE_URL` / `AI_MODEL` 环境变量后去掉该参数即调用真实 AI。

## 构建网页

```powershell
cd dashboard
npm run build
```

构建后静态网页位于 `dashboard/dist/`，可部署到任意静态托管。Cloudflare 会在 git push 后自动重建部署。

页面状态可通过 URL 切换（验收用）：

- `?fixture=success`：今日成功分析（默认）
- `?fixture=failure`：今日失败，展示上一份成功回退
- `?fixture=no-fallback`：今日失败且没有上一份成功结果

## 数据与口径

指标派生、无前视阈值方法与 log+4 年 z-score 跨周期归一化在 `services/data/`；固定阶段词汇表、AI 输入白名单与输出校验在 `services/ai/`。指标定义与可实现性见 [v0.1.0 指标研究](specs/v0.1.0/bear-market-indicator-expandability-research.md)。

仅作公开研究参考 · 不构成交易建议。
