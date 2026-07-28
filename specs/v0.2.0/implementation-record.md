# v0.2.0 — 实现记录

> 状态：四大需求已实现并通过验收。本文记录落地方式、关键文件、数据包结构与密钥边界，作为 v0.2.0 的实现真相来源。

## 1. 范围

把公开看板从“可本地验收的固定数据页面”升级为“每天自动更新、整包一致、可按时间查看证据变化”的公开研究工具。仍只输出周期证据，不给买卖/概率/仓位建议。

## 2. 需求一：完整数据包与整包回退

**单一数据包** `dashboard/public/data/packet.json`。前端只有一个入口（`dashboard/src/composables/useDashboardData.ts`），不再分别抓取 snapshot/series/analysis/status。数据包结构（`Packet` 类型见 `dashboard/src/types.ts`，组装见 `services/data/packet.py::build_packet`）：

| 字段 | 内容 |
|---|---|
| `schema_version` / `config_version` | `"0.2.0"`，追踪数据包与配置版本 |
| `run_id` / `generated_at` | 本次运行的唯一 id 与 UTC 时间，可追溯 |
| `data_date` / `analysis_date` | 实际数据日期 / 当前展示分析日期 |
| `input_summary` | 类别数、指标数、当日价格、数据源 stamps（AI 输入摘要可追溯） |
| `snapshot` | 当日 16 指标快照 + 当前值 + 自动档位（tier）+ 阈值 |
| `series` | 价格 + 16 指标历史日线 + 阈值线 |
| `bars` | 需求三两个柱状系列 |
| `analysis` / `fallback` / `status` | 当日 AI / 上一份成功 AI / today_available 状态 |

**契约**（`services/data/packet.py::validate_packet`）：拒绝缺任一必填部分、metric 数量不为 16、日期不一致（snapshot_date / series 末点 / analysis_date 任一 ≠ data_date）、`today_available` 与 analysis 是否在场不一致、AI 输出含禁止措辞。`write_packet_atomic` 先校验再 tmp+rename 原子替换，读者永不会看到半成品。

**整包回退**（`services/run_daily.py`）：
- 数据源抓取失败 / 数据日期过期 → `outcome=skipped`，**不覆盖**上一份完整包。
- AI 失败（无 key / 调用错 / 输出不合规）→ 发布当日完整包（snapshot/series/bars 为当日真实值），`analysis=null`、`fallback=上一份成功 analysis`、`status.today_available=false`，`outcome=published-fallback`。
- 全部成功 → `outcome=published-fresh`。
- 每次成功发布前，上一份归档到 `artifacts/packet-archive/{data_date}.json`，保留最近 7 份。

## 3. 需求二：图表时间轴与交互缩放

`dashboard/src/components/SharedChart.vue` + `dashboard/src/composables/useChartOption.ts`。

- 时间范围预设按钮：6 月 / 1 年 / 2 年 / 4 年 / 全量，外加当前可见范围文本（`rangeLabel`）。
- `dataZoom` 同时驱动主图与柱状图 x 轴（slider + inside），滚轮缩放、slider 拖动平移。
- 纵坐标随可见切片自动 min/max（`bounds()` 对可见区间算 price/indicator/bars 各轴范围并留 8% padding）。
- 主图、阈值 markLine、下方柱状图始终同一时间窗口；切换指标保持时间范围，点“全量/重置”回全量。
- 移动端等价（slider + inside 在触屏可用），toolbar 响应式换行。

## 4. 需求三：HODLer 投降 + ≥155d 花费价值柱状图

主图下方独立柱状 grid，与主图同步时间轴（`SharedChart` 双 grid + 共享 dataZoom）：

1. **HODLer 投降卖出尖峰（占供应 %）** — `[HODLedOrLostSupply(t) − …(t−30d)] / Supply`，仅保留 MVRV<1 低估期。
2. **≥155d 花费价值占比** — `Spent Value >=155d / Total Spent Value`，仅保留 MVRV<1。

各项独立名称/单位/来源/口径/数据质量提示（`bars-meta` 区 + tooltip）；缺失日期不前向填充（柱体仅出现在有值日），零分母与非低估期由派生层过滤记为不可判定（不写入该日）。两者**不**合并为单一“卖压分数”。

## 5. 需求四：数据与 AI 分析每日自动更新

**数据管线**（`services/data/`，stdlib-only，迁移自 `prototype-indicator-timeline/build_data.py` 并逐位对齐）：
- `fetch.py`：Bitview bulk API（32 序列）+ Open Bitcoin Metrics CSV（≥155d 花费）。
- `derive.py`：派生函数 + 无前视阈值方法（`ANCHOR=2018-01-01`，`CURRENT_CYCLE_START=2022 熊底`）+ log+4 年滚动 z-score。
- `metrics.py`：编排 16 指标 + 阈值 + 柱状系列。
- `packet.py` / `packet_display.py`：组装数据包 + 稳定的展示身份。

**AI 边界**（`services/ai/`）：
- `contract.py`：固定阶段/类别/状态/一致性词汇表 + JSON schema。
- `input_builder.py`：从 snapshot 白名单取字段，剥离 series/来源/历史，只发可公开归纳的指标事实。
- `validator.py`：拒绝禁止措辞（买卖/概率/杠杆等）、未知词汇、缺字段。
- `provider.py`：OpenAI 兼容 chat 调用（默认 GLM 开放平台），所有失败返回 `(None, reason)` 触发回退。

**主链路** `services/run_daily.py`：抓取 → 新鲜度检查 → 派生 → AI → 校验 → 组装 → 归档上一份 → 原子发布 → 追加 `artifacts/run-log.jsonl` 审计日志。

**自动运行** `.github/workflows/daily-update.yml`：每日 UTC 01:13 + 手动触发；装 Python → 跑 `run_daily.py`（`AI_API_KEY`/`AI_BASE_URL`/`AI_MODEL` 只来自 GitHub Secrets）→ `npm run build` 验证 → commit `packet.json` + run-log → push 触发 Cloudflare 重建部署。无自建服务器、无自有域名，继续用 `*.workers.dev`。

**密钥边界**：API key 只在 GitHub Actions Secret / 运行环境；不进前端代码、不进 `packet.json`、不进 run-log、不进 stdout（`provider.call_ai` 失败原因截断且不含 key，`test_api_key_never_leaks_in_reason` 覆盖）。

## 6. 开发前待确认项的最终决策

| 待确认事项 | 决策 | 依据 |
|---|---|---|
| HODLer 投降卖出尖峰的正式定义 | `hodler_npc_30d`（HODLer 30d 净持仓变化 / 供应，MVRV<1 gated）；原 BTC 口径=Glassnode LTH-Net Position Change | build_data 既有 core 实现；OBM ≥155d 花费为确认线 |
| ≥155d 花费价值占比 | `spent_value_ge155d_share`（Open Bitcoin Metrics） | 公开可自动更新源 |
| 默认时间范围 | 6 月 / 1 年 / 2 年 / 4 年 / 全量 | 周期指标需多年窗口；6 月看近期投降 |
| 每日更新时刻 | UTC 01:13 | 晚于数据源 00:00 稳定出数，避开整点 fleet |
| 可保留历史数据包数量 | 最近 7 份（`artifacts/packet-archive/`） | 回退 + 审计足够，不撑大仓库（archive 不进 git） |
| 16 个指标可自动更新 | 全部基于 Bitview + OBM 公开日线 | `verify_pipeline.py` 16 指标 parity 通过 |

## 7. 关键文件清单

- 数据管线：`services/data/{fetch,derive,metrics,packet,packet_display}.py`
- AI 边界：`services/ai/{contract,input_builder,validator,provider}.py`
- 每日主链路：`services/run_daily.py`
- 前端：`dashboard/src/types.ts`、`composables/{useDashboardData,useChartOption}.ts`、`components/SharedChart.vue`、`App.vue`
- 数据包：`dashboard/public/data/packet.json`（线上）+ `packet-failure.json` / `packet-no-fallback.json`（固定验收 fixture）
- 自动运行：`.github/workflows/daily-update.yml`
- 工具脚本：`scripts/{verify_pipeline,test_packet,build_fixtures}.py`
- 测试：`tests/acceptance/{run_acceptance,test_ai_contract,test_input_boundary,test_packet_contract}.py`
