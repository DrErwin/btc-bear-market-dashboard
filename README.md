# BTC 熊底证据看板

公开、只读的研究型看板：把 16 个 BTC 周期指标整理成证据，展示当前市场压力、熊底证据形成过程、证据一致性、阈值位置、共享图表与持有者卖出柱状图。它不预测确切最低点，也不提供交易建议。

> 当前公开界面版本记录：`v0.2.4`；系统每天北京时间 12:00 自动尝试更新。2026-07-29 现场核对公开 `packet.json` 时，线上数据契约仍为 `schema/config 0.2.0`，因此“界面版本”和“数据契约版本”不能混为一谈。
>
> 当前本地实现基线：`v0.4.0`，运行包 `schema/config 0.4.0`。本版本把市场状态拆成“压力轴”和“筑底轴”，允许两条轴分别处于不同阶段；保留人工校准的观察／深度压力／极端压力档位，但不把它们组合成交易动作或单一总阶段。本地实现已提交并通过自动验收；公开部署仍以线上核验记录为准，尚未因本次变更自动发布。

## 在线访问

公开地址：[btc-bear-market-dashboard.erwinwu000.workers.dev](https://btc-bear-market-dashboard.erwinwu000.workers.dev/)

网页部署在 Cloudflare Workers Static Assets。GitHub 每日任务生成完整数据包并推送后，Cloudflare 自动重建同一公开地址。

## v0.2.0 能力

- **完整数据包 + AI 解释回退**：页面只读一份 `packet.json`；AI 失败时保留本次数据，并明确标记今日 AI 不可用，页面显示上一份成功解释。
- **图表时间轴与交互缩放**：6 月 / 1 年 / 2 年 / 4 年 / 全量预设、滚轮缩放、拖动平移、纵坐标随可视范围自动适配。
- **HODLer 投降 + ≥155d 花费价值柱状图**：主图下方两个独立柱状系列，与主图共享同一时间窗口。
- **每日自动更新**：GitHub Actions 每天北京时间 12:00 抓取公开链上数据 → 派生 16 指标 → GLM-5.2 深度分析 → 合规校验 → 原子发布；密钥只存 GitHub Secrets。

详见 [实现记录](specs/v0.2.0/implementation-record.md)与[验收记录](specs/v0.2.0/acceptance-record.md)。

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

指标派生、动态阈值方法与 log+4 年 z-score 跨周期归一化在 `services/data/`；证据职责、相关性家族、数据质量、时间线和前三个自然日上下文在 `services/evidence/`；双轴词汇表、AI 输入白名单与输出校验在 `services/ai/`。每日结果包是页面和 AI 共同读取的事实边界，AI 负责在有限框架内综合解释，不接收完整历史序列，也不能修改阈值。

本地 0.4.0 的统一验收入口为 `python tests/acceptance/run_acceptance.py`，它会运行 Python 契约测试、前端构建和 success／fallback／no-fallback／移动端浏览器场景。版本关系见 [版本文档索引](specs/README.md)，指标定义与可实现性见 [v0.1.0 指标研究](specs/v0.1.0/bear-market-indicator-expandability-research.md)。

仅作公开研究参考 · 不构成交易建议。
