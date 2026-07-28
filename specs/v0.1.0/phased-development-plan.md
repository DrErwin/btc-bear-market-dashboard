# v0.1.0 — BTC 熊底证据看板：分阶段开发计划与验收标准

> 建议标签：`ready-for-agent`
>
> 配套文档：`specs/v0.1.0/public-bear-bottom-evidence-dashboard.md`（产品规格）、`specs/v0.1.0/indicator-validation-record.md`（指标验证快照）、`specs/v0.1.0/bear-market-indicator-expandability-research.md`（指标可实现性事实清单）。
>
> 本文件把“规格 + 线框 prototype + 指标验证 prototype”收敛成一份可执行的分阶段计划。每个阶段都能独立产出可测试的软件，并最终汇流到规格 §Testing Decisions 定义的最高级验收流。

> **实施状态注记（2026-07-27）**：`v0.1.0` 的固定数据展示版已部署至 [Cloudflare Workers Static Assets](https://btc-bear-market-dashboard.erwinwu000.workers.dev/)。这次实际部署采用 Worker 静态资产托管，而非本计划最初选择的 Cloudflare Pages；每日真实数据与 AI 自动更新仍未实施，转入 `v0.2.0` 范围。

---

## 0. 现状基线（已经在仓库里、可以直接复用的资产）

在写计划之前，先把三份已有资产定位清楚，避免重复造轮子。

| 资产 | 位置 | 复用判断 |
|---|---|---|
| **产品规格** | `specs/v0.1.0/public-bear-bottom-evidence-dashboard.md` | 需求唯一来源。已锁定版式（紧凑混合 Variant D）、词汇表、AI 输入/输出契约、测试决策、范围边界。本计划不修改规格，只实现它。 |
| **线框 prototype** | `prototype-dashboard-wireframe/`（4 个方案，`?variant=A\|B\|C\|D` 切换） | **版式已被采纳**：`variantD()`（融合紧凑版）= 规格 §Implementation Decisions 选定的紧凑混合方向。`app.js`/`styles.css` 的 DOM 骨架、响应式断点（1100px / 760px）、阶段轴样式可直接迁移。**抛弃**：模拟 SVG 图表、prototype 切换器、硬编码的 `analysis`/`metrics` 常量。 |
| **指标验证 prototype** | `prototype-indicator-timeline/` | 数据流水线 **可产品化复用**；验证台 UI **抛弃**。详见下表。 |

### `prototype-indicator-timeline/` 的逐项复用判断

| 文件 | 判断 | 说明 |
|---|---|---|
| `build_data.py`（904 行） | **保留并产品化** | 抓取（Bitview bulk + OBM CSV）、派生（AVIV/Puell/STH-MVRV/CVDD/各 z-score）、**无前视阈值方法**（`[2018-01-01, 上一轮熊底]` 窗口的 `past_cycle_quantile`/`past_cycle_stats`）、`log + 滚动 4 年 z-score` 跨周期归一化、`compare()` 复现性核对——这些都是项目最有价值的智力资产，stdlib-only、可直接迁移。 |
| `timeline-data.json` 数据契约 | **保留并演化** | `metric()` schema（`id/label/unit/description/formula/source/method/caveat/category/core/lines/line_modes/default_*/quality/reproduction_check`）是干净的自描述契约，前端可直接消费。 |
| `app.js`（781 行验证台） | **抛弃** | 三视图（逐项验证台 / 指标目录 / 验证进度）是给一个人用的复核工具，状态存 `localStorage`（还脆弱地绑定 `127.0.0.1:8123`），与公开看板的 IA 完全不同。 |
| `index.html`、`serve.py` | **抛弃** | prototype 启动器。 |
| ECharts 5.5.1（CDN） | **沿用** | 双轴时间序列 + markLine 阈值线 + dataZoom，验证台里已经把图表配置写得很完整，可作为公开看板共享图表的起点。 |
| `lthSthDistributionLines`、`availableLineModes` 死代码 | **删除** | `lth_sth_normalized_net_realized_pnl` 已被 `DISPLAY_CATALOG` 过滤掉，但 UI 代码还在；产品化时清理。 |

### 关键缺口（三份资产都还没有的部分）

1. **每日 AI 分析服务**——规格的核心，但两个 prototype 都没有实现。
2. **公开看板前端**——线框只证明了版式，没有真实数据绑定、没有失败/回退状态、没有 a11y。
3. **确定性验收门**——规格 §Testing Decisions 要求“一个最高级公开看板验收流”，但目前没有任何测试、没有 CI、没有依赖清单（无 `requirements.txt`/`package.json`）。
4. **每日定时与托管**——目前只在本机 `serve.py` 跑。

本计划就是按这四个缺口 + 流水线产品化来分阶段。

---

## 1. 总体架构与技术栈决策

### 1.1 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│  每日定时（cron / GitHub Actions，UTC 固定时刻，每天 1 次）          │
│                                                                  │
│  services/data/build_snapshot.py   ──►  artifacts/                │
│   · 抓取 Bitview + OBM                    ├─ snapshot.json   (AI 输入：当日值 + 定义 + 阈值，无历史) │
│   · 派生 16 个指标                        └─ series.json     (前端图表：完整价格 + 指标 + 阈值线)     │
│   · 复现性核对 + 质量诊断                                                        │
│                                                                  │
│  services/ai/run_daily_analysis.py ──►  artifacts/                │
│   · 读 snapshot.json                      ├─ analysis-current.json (今日成功结果)                   │
│   · 构造受约束的 AI 输入                   └─ analysis-fallback.json (上一份成功，回退用)            │
│   · 调用 LLM → 结构化输出                                                                           │
│   · 校验（词汇表 / 必填字段 / 禁止交易建议）→ 通过才落盘；失败触发回退                              │
└──────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  公开只读前端（静态站点）                                            │
│  dashboard/  · fetch snapshot + series + analysis-current          │
│             · 紧凑 AI 评价区 + 五阶段轴 + 三摘要 + 六类看板 + 共享图表 │
└──────────────────────────────────────────────────────────────────┘
```

两条不可混淆的数据通路（规格硬约束）：
- **AI 输入通路**（`snapshot.json`）：只含定义、角色、当前值、阈值。**不含**历史序列、趋势、新闻。
- **图表通路**（`series.json`）：完整历史，**只给前端**，AI 永远看不到。

### 1.2 技术栈决策（带推荐默认值，可在 Phase 0 推翻）

| 决策 | 状态 | 选定 | 理由 | 备选 |
|---|---|---|---|---|
| **前端框架** | ✅已定 | **Vue 3 + Vite + TypeScript**（`<script setup>` SFC） | 线框 render 函数与 SFC 模板近 1:1，迁移最直接；共享图响应式用 `ref`/`computed` 极简；solo 开发决策疲劳低（明细 §1.3） | React + Vite（生态/招聘更广，迁移成本略高） |
| **图表库** | ✅沿用 | **ECharts 5 + vue-echarts** | 验证 prototype 已写好双轴 + markLine + dataZoom 配置 | — |
| **数据/AI 后端** | — | **Python 3.11+，stdlib 优先** | 直接承接 `build_data.py`；AI 运行器同环境 | — |
| **LLM** | ✅已定（自有 API） | **Provider 无关**：抽象 `LLMClient` 接口，默认 **OpenAI 兼容**实现（`LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`） | 接你自有的 API；OpenAI 兼容协议覆盖 one-api / vLLM / FastChat / Azure / 本地推理等绝大多数网关 | Anthropic / 原生 SDK——加一个适配子类即可 |
| **每日定时** | ✅已定 | **GitHub Actions cron**（UTC 固定时刻） | 仓库已在 GitHub；artifact 可 commit 回 `main` 或推对象存储 | 自建 cron / Cloudflare Cron Triggers |
| **托管** | ✅已定 | **Cloudflare Pages**（静态 SPA） | 免费、自动 HTTPS、`fetch()` 静态 JSON 即可 | GitHub Pages（CDN 稍弱） |
| **阈值/指标配置** | — | **私有版本化配置文件**（`config/`，YAML） | 规格 §Out of Scope 明确“无公开管理界面”；配置走代码评审 | 私有 admin Web UI（本版本不做） |
| **持久化** | — | **JSON artifact 文件**，无数据库 | 状态只有“今日分析 + 一份回退”，无需 DB | — |

> **D-1 / D-2 / D-3 已定**：前端 = Vue 3 + Vite + TypeScript（明细见 §1.3）；LLM = provider 无关、默认 OpenAI 兼容（接你自有的 API）；托管 + 定时 = Cloudflare Pages + GitHub Actions cron。

### 1.3 前端技术栈明细（Vue 3，已定）

| 层 | 选型 | 说明 |
|---|---|---|
| 构建 | **Vite 5** | 静态 SPA（`vite build`）→ Cloudflare Pages。无需 SSR/SSG：内容为每日静态 JSON，运行时 `fetch`。 |
| 框架 | **Vue 3 `<script setup>` SFC + TypeScript（strict）** | 线框 `variantD()` 等 render 函数与 SFC 模板近 1:1，Phase 3 迁移最直接；共享图表随选中指标切换的响应式用 `ref`/`computed` 极简。 |
| 路由 | **无**（单页看板） | 日后若加独立“方法说明”页再引入 `vue-router`。 |
| 状态 | **组件本地 `ref`/`computed` + `composables/useDashboardData.ts`** | 状态简单且多为派生，暂不引入 Pinia；若复杂化再加。 |
| 样式 | **SFC `<style scoped>` + 全局 `styles/tokens.css`**（迁移线框 CSS 变量与 1100/760 断点） | 沿用线框手写 CSS 以保视觉一致；不引入 Tailwind/UnoCSS（设计为定制，非 utility 驱动）。 |
| 图表 | **vue-echarts（官方封装）+ ECharts 5** | 迁移验证 prototype 的双轴 + markLine 阈值 + dataZoom + `formatValue`。 |
| HTTP | **原生 `fetch`** | 拉 `snapshot` / `series` / `analysis-current` / `status` 四个静态 JSON。 |
| 单元测试 | **Vitest + @vue/test-utils** | 测纯逻辑：失败/回退判定、值格式化、阈值档位推导。 |
| 验收 / E2E | **Playwright**（Phase 4 确定性门） | 多视口 + 截图；断言外部行为而非 DOM 结构（规格 §Testing Decisions）。 |
| Lint / 格式 | **ESLint + Prettier + eslint-plugin-vue** | |

**线框 render 函数 → Vue SFC 映射**（Phase 3 落点）：

| 线框（`prototype-dashboard-wireframe/app.js`） | Vue SFC | 职责 |
|---|---|---|
| `topBar()` | `AppHeader.vue` | 品牌标 / 时间戳 / 方法说明入口 |
| `compactStageAxis()` + stage badge | `StageAxis.vue` | 五阶段轴，当前高亮 |
| AI 评价区（`hybrid-head` + `tri-analysis` + details） | `AiPanel.vue` + `SummaryBlocks.vue` + `DetailedAnalysis.vue` | 阶段+一句话+一致性同行、三摘要、可展开详情 |
| `categoryCards()` | `CategoryGrid.vue` | 六类网格 + AI 状态 |
| `metricCards()` | `MetricList.vue` / `MetricCard.vue` | 当前类指标卡，选中态 |
| `chart()` | `SharedChart.vue`（包 vue-echarts） | 单一共享图：价格+指标+阈值线 |
| `metricExplanation()` | `MetricExplanation.vue` | 含义/类别/角色/阈值语义/来源/限制 |
| `footer` | `DisclaimerFooter.vue` | 非交易建议声明 |
| —（新增） | `AnalysisUnavailable.vue` | 今日不可用 + 带日期回退 |
| 数据装配 | `composables/useDashboardData.ts` | fetch 四 JSON + 失败/回退判定 |

---

## 2. 阶段总览

| 阶段 | 目标 | 主要交付 | 可独立验证的产出 | 依赖 |
|---|---|---|---|---|
| **Phase 0** | 基线与契约 | 仓库骨架、依赖清单、`config/`（指标目录 + 阈值 + 词汇表）、固定 fixture | 配置可加载、fixture 通过 schema 校验 | — |
| **Phase 1** | 数据流水线产品化 | `services/data/`，产出 `snapshot.json` + `series.json` + 质量报告 | 指标数学与 prototype 误差 < 容差；无前视测试通过 | Phase 0 |
| **Phase 2** | 每日 AI 分析服务 | `services/ai/`，输入构造器 + 输出校验器 + 每日运行器 + 回退 | 契约测试（mock AI）全过；失败/回退正确 | Phase 0、Phase 1 的 snapshot |
| **Phase 3** | 公开看板前端 | `dashboard/`，Variant D 版式接真实数据 + 失败/回退态 + a11y | 所有状态可渲染；响应式 + 键盘可用 | Phase 0；可先用 fixture，后接 Phase 1/2 |
| **Phase 4** | 验收与自动化验证 | `tests/`，最高级确定性验收流 + 截图 | 验收流在无网络/无真实 AI 下全过 | Phase 1–3 |
| **Phase 5** | 部署与日常运维 | 上线 + 每日自动更新 + 监控 | 线上当日有分析；模拟失败后回退生效 | Phase 4 |

**并行机会**：Phase 3 可在 Phase 1/2 完成前用 Phase 0 的 fixture 先行开发 UI，缩短关键路径。

---

## 3. 各阶段详细计划与验收标准

### Phase 0 —— 基线与契约

**目标**：把规格里“固定”的东西（词汇表、指标目录、角色、阈值配置、测试 fixture）固化成机器可读的契约文件，并搭好仓库骨架与依赖清单。这一阶段不抓任何网络数据、不调任何 AI。

**交付物**：
- 仓库重组（保留 prototype 作为冻结参考）：
  ```
  btc-bear-market-dashboard/
  ├── config/                    # 私有、版本化（规格 §Out of Scope：无公开 UI）
  │   ├── indicators.yaml        # 16 个指标：id/label/category/role/formula/source/method/caveat/unit/log_available
  │   ├── thresholds.yaml        # 每指标阈值档位（多档）+ 方向 + 语义标签；含无前视分位线的计算口径说明
  │   ├── categories.yaml        # 六个定义类别 + 中文名
  │   └── vocab.yaml             # 五阶段 / 三档分类状态 / 三档证据一致性 + 数据不足
  ├── services/
  │   ├── data/                  # Phase 1
  │   └── ai/                    # Phase 2
  ├── dashboard/                 # Phase 3
  ├── tests/
  │   └── fixtures/              # 固定的 16 指标 snapshot + 固定的 mock AI 响应 + 失败 fixture
  ├── specs/                     # 已有
  ├── prototypes/                # 把现有 prototype-* 目录移入，冻结为参考
  ├── requirements.txt           # Python 依赖（Phase 1 起填充）
  ├── README.md                  # 如何跑流水线 / 看板 / 测试
  └── .gitignore
  ```
- `config/indicators.yaml`：以 `specs/v0.1.0/indicator-validation-record.md` §2 和 prototype `DISPLAY_CATALOG` 为准，落 16 个指标；6 类；5 核心 / 11 辅助（核心 = MVRV、AVIV、HODLer NPC·30d、≥155d 花费占比、Puell）。
- `config/thresholds.yaml`：每个指标的多档阈值 + `direction`（below/above）+ 每档的中文语义标签（如 MVRV：`1.0=成本平衡`、`0.8=深度低估`）。**阈值是配置，不冻结进规格**（规格 §Further Notes 明示）。
- `config/vocab.yaml`：五个市场阶段、`未确认/部分确认/充分确认`、`弱/中等/强`、`数据不足`。
- `tests/fixtures/snapshot.json`：固定的 16 指标当日快照（可用 prototype 现成的 `timeline-data.json` 抽取 `latest_value`/`latest_date` 构造）。
- `tests/fixtures/analysis-success.json`：一份合法的 mock AI 输出，覆盖规格 §Implementation Decisions 的全部必填字段。
- `tests/fixtures/analysis-failure.json`：触发失败/回退的 mock（如缺字段、含禁止的交易建议）。
- 依赖清单：`requirements.txt`（先放 `jsonschema`、`pyyaml`、`requests` 或沿用 stdlib `urllib`）。

**关键任务**：
1. 仓库重组：`git mv prototype-* prototypes/`，更新各 prototype 内的相对路径说明为“冻结参考”。
2. 把 `build_data.py` 里的 `DISPLAY_CATALOG` / `CATEGORY_ORDER` / 核心 bool / 静态 `references` 抽取成 `config/*.yaml`，并写一个 `config/loader.py` 校验加载（schema 用 `jsonschema`）。
3. 构造三份 fixture（成功 / 失败 / snapshot）。
4. 写 `README.md` 的“如何运行”骨架（流水线 / 看板 / 测试三段，先占位 Phase 1+ 命令）。

**验收标准（Phase 0）**：
- [ ] `config/loader.py` 能加载全部 `config/*.yaml`，并通过 jsonschema 校验；非法配置（如未知指标 id、未知类别、未知词汇）报错退出。
- [ ] `config/indicators.yaml` 恰好包含 16 个指标，每个都有 `category`、`role ∈ {核心, 辅助}`、`unit`、非空 `description`/`formula`/`source`。
- [ ] 6 个类别的指标分布与 `specs/v0.1.0/indicator-validation-record.md` §2 一致（估值2核心1辅助、供应4辅助、资本2辅助、持有者2核心1辅助、矿工1核心1辅助、锚定2辅助）。
- [ ] `config/vocab.yaml` 的市场阶段恰好 5 个、分类状态 3 档、一致性 3 档，外加 `数据不足`，且与规格 §Implementation Decisions 文本逐字一致。
- [ ] `tests/fixtures/analysis-success.json` 能通过 Phase 2 将要写的输出 schema（先在 fixture 里手工保证字段齐全）。
- [ ] `tests/fixtures/analysis-failure.json` 至少包含一种“禁止交易建议”和一种“缺必填段”的样例。
- [ ] `prototypes/` 下两个原型仍可由各自的 `serve.py` 单独启动（重组未破坏参考价值）。

---

### Phase 1 —— 数据流水线产品化

**目标**：把 `build_data.py` 从“一次性验证原型”升级为受配置驱动、产出双产物（AI 快照 + 图表序列）、带测试与质量门的生产流水线。**这一阶段不接 AI。**

**交付物**：
- `services/data/fetchers.py`：从 prototype 迁移 `get_bytes`/`fetch_bitview`/`fetch_obm_scalar`，保留重试、`User-Agent`、按 series 分块、版本号与时间戳捕获。
- `services/data/derive.py`：迁移全部派生函数（`derive_aviv`/`derive_puell`/`derive_sth_mvrv`/`derive_cvdd`/`normalised_net`/`rolling_mean`/`rolling_zscore`/`aligned_*`/`quantile*`/`past_cycle_*`）。
- `services/data/thresholds.py`：把无前视阈值计算（`past_cycle_quantile`/`past_cycle_stats`、`[2018-01-01, 上一轮熊底]` 窗口、`<30` 回退告警）单独成模块，**从 `config/thresholds.yaml` 读档位语义**，从 prototype 迁移计算口径。
- `services/data/build_snapshot.py`：编排入口。读 `config/`，抓取→派生→阈值→**输出两个 artifact**：
  - `artifacts/snapshot.json`：AI 输入。仅含每个指标的 `id/label/category/role/unit/description/current_value/current_date/tier_label/thresholds[]`（每档 `value`+`direction`+`meaning`）。**不含任何历史序列**。
  - `artifacts/series.json`：前端图表。完整价格 + 每指标 `lines[]` + 阈值线 + `quality` + `reproduction_check` + 数据来源版本。
- `services/data/tests/`：
  - `test_derive.py`：派生数学单元测试（AVIV/Puell/STH-MVRV/CVDD 等用固定小输入验算）。
  - `test_no_lookahead.py`：断言 `past_cycle_*` 窗口上界 = 上一轮熊底，当前周期与未来不参与阈值；`<30` 回退路径单独覆盖。
  - `test_reproduction.py`：用一份**冻结的离线 fixture 响应**（不触网），断言派生值与 vendor 成品的中位相对误差 < 容差（沿用 prototype `compare()` 阈值）。
  - `test_snapshot_boundary.py`：断言 `snapshot.json` 里**没有任何历史序列字段**（规格 §Testing Decisions 输入边界）。
- `requirements.txt` 填充：`requests`（或继续 stdlib）、`jsonschema`、`pyyaml`、`pytest`。

**关键任务**：
1. 把 `build_data.py` 拆成 `fetchers.py`/`derive.py`/`thresholds.py`/`build_snapshot.py`，删除被 `DISPLAY_CATALOG` 过滤掉的死指标构造（`relative_unrealized_loss`、`thermocap_multiple` 原值、`reserve_risk` 原值、`lth_sth_*`、`normalized_net_realized_pnl` 等），或显式记录“保留计算但不导出”。
2. 把硬编码的 `DISPLAY_CATALOG`/`CATEGORY_ORDER`/静态 `references` 改为从 `config/*.yaml` 驱动。
3. 抓取层增加“离线 fixture 模式”：当环境变量指向本地缓存的 Bitview/OBM 响应时，`fetch_*` 读本地、不触网——这是 Phase 4 确定性测试的前置。
4. `build_snapshot.py` 输出 `snapshot.json` 前，跑一遍输入边界自检（序列字段必须为零）。
5. 迁移 `compare()` 复现性核对到 `series.json.reproduction_check`，质量诊断到 `quality`。

**验收标准（Phase 1）**：
- [ ] `python -m services.data.build_snapshot --offline --fixture tests/fixtures/network/` 在**无网络**下成功产出 `snapshot.json` 与 `series.json`。
- [ ] `snapshot.json` 仅含当前值与定义；`test_snapshot_boundary.py` 断言任何 `series`/`lines`/历史数组不出现在 snapshot 中。
- [ ] `series.json` 的 16 个指标结构与 prototype `timeline-data.json` 的 `metric()` schema 对齐；`reproduction_check.median_relative_error` 对有 vendor 成品的指标低于 prototype 既有阈值。
- [ ] `test_no_lookahead.py` 通过：人为篡改“当前周期及之后”的输入值，阈值结果不变。
- [ ] `test_derive.py` 全过：AVIV/Puell/STH-MVRV/CVDD/各 z-score 在固定输入下输出与手算一致。
- [ ] `config/thresholds.yaml` 改一个档位 → 重跑 → `snapshot.json` 与 `series.json` 的阈值随之变化（配置驱动可证）。
- [ ] 质量诊断字段（`rows/missing_calendar_days/freshness_days`）出现在 `series.json` 每个 metric 与顶层 `price_quality`。

---

### Phase 2 —— 每日 AI 分析服务

**目标**：实现规格的核心新增件——每日跑一次、读受约束快照、产出结构化分析、校验后才落盘、失败走回退。**真实 LLM 与 mock 都要支持**，但确定性测试只用 mock。

**交付物**：
- `services/ai/input_builder.py`：读 `snapshot.json` + `config/vocab.yaml`（阶段定义、分类状态定义）+ `config/indicators.yaml`（含义/类别/角色）+ `config/thresholds.yaml`（每档含义），组装 AI 输入。**严格只含规格 §Implementation Decisions 列出的字段**。
- `services/ai/prompt.py`：系统/用户 prompt 模板。约束 AI：只能用固定词汇表；先给六类各自选状态、再选总阶段；区分核心/辅助；必须包含支持/反面/下一阶段条件；禁止任何买卖建议/入场价/仓位/杠杆/数值概率。
- `services/ai/contract.py`：用 jsonschema 定义的 **AI 输出 schema**：
  - `stage ∈ {5 阶段} ∪ {数据不足}`
  - `consistency ∈ {弱, 中等, 强}`（`数据不足` 时可缺）
  - `summary`（一句话）
  - `core_support` / `main_obstacle` / `next_stage_condition`（三段紧凑摘要）
  - `categories[6]`：每个 `{category, status ∈ {未确认,部分确认,充分确认}}`，六类齐全
  - `supporting_evidence` / `contrary_evidence` / `next_stage_confirmation`（详细段）
  - 禁止字段：`buy`/`sell`/`entry_price`/`position`/`leverage`/`probability`/`confidence_pct` 等任意数值概率或交易指令
- `services/ai/validator.py`：
  - schema 校验；
  - 词汇表校验（stage/status/consistency 必须在白名单）；
  - 六类齐全校验；
  - **文本禁令扫描**：对 narrative 字段做关键词/模式扫描（买卖建议、入场价、百分比概率等），命中即拒。
  - 任一不通过 → 抛 `InvalidAnalysisError`，不落盘。
- `services/ai/llm_client.py`：provider 无关抽象（`LLMClient` 接口）。默认 `OpenAICompatibleClient` 读 `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`；结构化输出优先 `response_format=json_schema`，端点不支持时退回严格 prompt + JSON 解析。接你自有的 API 端点。
- `services/ai/runner.py`：通过 `llm_client` 调用，重试/超时。**校验始终以 `validator.py` 为准，与 provider 无关。** 支持 `--mock tests/fixtures/analysis-success.json` 用于确定性测试。
- `services/ai/run_daily_analysis.py`：编排入口。
  - 读今日 `snapshot.json` → 构造输入 → 调用 → 校验 → 通过则写 `artifacts/analysis-current.json`（带 `analysis_date`），并把上一份成功复制到 `artifacts/analysis-fallback.json`（带 `analysis_date`）。
  - 失败（API 错、校验拒、超时）→ **不覆盖** `analysis-current.json`；写一个 `artifacts/status.json` 标记 `{today_available: false, last_success_date, reason}`；前端据此显示“今日不可用 + 回退”。
  - 维持**最多一份回退**（规格 §Implementation Decisions：只保留上一份成功）。
- `services/ai/tests/`：
  - `test_input_boundary.py`：断言生成的 AI 输入**不含**历史序列/趋势/新闻/外部研究（规格 §Testing Decisions 输入边界）。
  - `test_validator_accept.py`：`analysis-success.json` 通过。
  - `test_validator_reject.py`：`analysis-failure.json` 的每种非法样例（未知阶段、缺类、含 `probability`、含“买入”、缺必填段）都被拒。
  - `test_fallback.py`：mock LLM 抛错 → `analysis-current.json` 不变、`status.json.today_available=false`、`analysis-fallback.json` 带正确日期。
  - `test_daily_idempotent.py`：同一天重复跑不重复调用、不产出不同结论（规格 User Story 35）。

**关键任务**：
1. 先写 `contract.py` + `validator.py` + 拒绝测试（TDD：让 fixture 失败样例先红）。
2. 写 `input_builder.py` + 输入边界测试。
3. 写 `runner.py` 的 mock 路径，跑通端到端。
4. 接真实 LLM，做一次“维护者烟囱测试”（不是验收门）。
5. 写 `run_daily_analysis.py` 的回退/状态机。

**验收标准（Phase 2）**：
- [ ] `python -m services.ai.run_daily_analysis --snapshot tests/fixtures/snapshot.json --mock tests/fixtures/analysis-success.json` 产出合法 `analysis-current.json`。
- [ ] `test_input_boundary.py` 通过：序列、趋势字段、新闻、外部研究、用户组合信息均不出现在 AI 输入。
- [ ] `test_validator_reject.py` 对每一种非法输出都拒绝并触发失败处理。
- [ ] `test_fallback.py` 通过：mock 失败时今日不落盘新结论、`status.json` 标记不可用、回退带真实上一份日期。
- [ ] `analysis-current.json` 的 `stage`/`consistency`/六类 `status` 全部在 `config/vocab.yaml` 白名单内。
- [ ] 无任何数值概率字段；narrative 中无买卖/入场价/仓位/杠杆措辞（禁令扫描通过）。
- [ ] **可选维护者烟囱**：真实 LLM 跑一次，人工确认叙事合理；此步**不进**确定性验收门（规格 §Testing Decisions）。

---

### Phase 3 —— 公开看板前端

**目标**：把线框 Variant D 从“模拟数据”升级为“接真实 artifact、含失败/回退态、响应式 + 键盘可访问”的公开只读看板。技术栈锁定 **Vue 3 + Vite + TypeScript**（见 §1.3）。

**交付物**：
- Vite 项目骨架：`dashboard/`（`index.html` + `src/` + `styles/tokens.css`）。`package.json` 依赖：`vue`、`vue-echarts`、`echarts`；dev：`vite`、`@vitejs/plugin-vue`、`typescript`、`vue-tsc`、`vitest`、`@vue/test-utils`、`eslint` + `eslint-plugin-vue`、`prettier`。
- 数据装配：`src/composables/useDashboardData.ts` —— `fetch('snapshot.json')` + `fetch('series.json')` + `fetch('analysis-current.json')` + `fetch('status.json')`，合并并做失败/回退判定（`status.today_available === false` → 显示回退并标日期）。
- 组件（每个一个 `<script setup>` SFC，对应线框 render 函数，见 §1.3 映射）：
  - `AppHeader.vue`：品牌标 / 每日分析时间戳 / 方法说明入口。
  - `AiPanel.vue`（含 `SummaryBlocks.vue`、`DetailedAnalysis.vue`）：紧凑 AI 评价区。桌面：阶段 + 一句话 + 一致性**同一横排**（规格 §Implementation Decisions：一致性不得独占整行）。三摘要块（核心支撑 / 主要阻力 / 下一阶段条件）。详细分析默认折叠、可展开。
  - `StageAxis.vue`：五阶段横向进度轴。过去阶段完成、当前高亮、未来可见但不可用；**不暗示数值概率或必然前进**。
  - `CategoryGrid.vue`：六类紧凑网格，每类显示 AI 选定的 `status`（未确认/部分确认/充分确认），文字 + 颜色双重编码。
  - `MetricList.vue` / `MetricCard.vue`：当前类别的指标列表（左栏）。每卡：名称、角色（核心/辅助，可文字区分）、当前值、当前阈值档、短状态。**不显示距下一档距离**（规格 User Story 19）。选中态可见（User Story 21）。
  - `SharedChart.vue`（包 `vue-echarts`）：**单一共享图表**。切指标只更新此图与解释区，不为每卡内联图表（规格 §Implementation Decisions）。图含 BTC 价格 + 所选指标 + 配置的阈值线。
  - `MetricExplanation.vue`：含义 / 类别 / 角色 / 阈值语义 / 数据来源 / 已知限制。
  - `AnalysisUnavailable.vue`：今日不可用态——“今日 AI 分析不可用”+ 回退结论标真实日期 + 看板仍可用；无回退时清晰不可用态而非编造分析（规格 User Story 36/37、§Testing Decisions 失败 fixture）。
  - `DisclaimerFooter.vue`：页脚声明“研究导向的周期证据，非交易建议”。
- 图表配置：把 `prototype-indicator-timeline/app.js` 的双轴 + markLine 阈值 + dataZoom + 单位格式化（`formatValue`/`axisLabelFormatter`）抽到 `src/composables/useChartOption.ts`，由 `SharedChart.vue` 消费。
- 样式：迁移 `prototype-dashboard-wireframe/styles.css` 的设计变量与 1100px / 760px 断点到 `styles/tokens.css` + 各 SFC `<style scoped>`；移除 prototype 标记。
- 响应式：390px 移动端五阶段点全可见、无横向溢出（规格 §Testing Decisions）。
- a11y：所有控件键盘可达；颜色必伴文字标签；`aria-expanded`/`aria-selected`/`aria-label` 齐全。

**关键任务**：
1. 迁移线框 `variantD()` 的 DOM 结构与 `styles.css`，去掉 prototype 切换器与模拟数据常量。
2. 接 `fetch`：先用 Phase 0 fixture，再切 Phase 1/2 真实 artifact。
3. 实现共享图表：把验证 prototype 的 ECharts 配置搬到 `shared-chart.js`，改成“单图随选中指标切换”。
4. 实现失败/回退态分支。
5. 响应式与 a11y 走查。

**验收标准（Phase 3）**：
- [ ] 成功态：顶部显示固定阶段；五阶段轴同排且恰一个标记为当前；一致性标签 + 一句话可见；三摘要块渲染；详细分析可展开/收起。
- [ ] 桌面 1440×900 视口下，六类看板顶部边缘**不滚动可见**（规格 §Testing Decisions；线框 Variant D 已验证）。
- [ ] 六类状态全可见；16 个指标出现在正确类别下；核心/辅助可由**文字**区分。
- [ ] 点任一指标 → 单一共享图表更新为“BTC 价格 + 该指标 + 阈值线”；选中卡片保持可见选中态。
- [ ] 卡片**不**显示“距下一档距离”；页面**不**渲染任何概率/买卖/入场价/仓位/杠杆措辞。
- [ ] 失败态（喂 `status.today_available=false` fixture）：页面声明今日不可用；有回退则展示并标真实日期；无回退则清晰不可用态、不编造结论；16 指标看板仍可用。
- [ ] 390px 移动视口：五阶段点全可见、无横向溢出；结论与分析单列可读；大图可用（简化或全屏）。
- [ ] 所有指标卡与分析控件可用键盘操作（Tab/Enter/Space/方向键）；状态含义有文字、不仅靠颜色。

---

### Phase 4 —— 验收与自动化验证

**目标**：实现规格 §Testing Decisions 要求的“一个最高级公开看板验收流”，作为合并/上线的**确定性门**。无网络、无付费 API、无真实 AI、无生产数据即可跑。

**交付物**：
- `tests/acceptance/test_success_flow.py`：喂 `tests/fixtures/snapshot.json` + `tests/fixtures/analysis-success.json`，驱动前端（Playwright/headless）断言成功态全部外部行为（规格 §Testing Decisions 成功 fixture 全部 pass criteria）。
- `tests/acceptance/test_failure_flow.py`：喂失败 fixture，断言失败/回退全部 pass criteria。
- `tests/acceptance/test_ai_contract.py`：直接调 `services.ai.validator`，覆盖契约 pass criteria（白名单/六类齐全/必填段/禁止字段拒绝）。
- `tests/acceptance/test_input_boundary.py`：断言 AI 输入边界 pass criteria（含定义/角色/当前值/阈值；不含历史/趋势/新闻/外部研究/组合信息）。
- `tests/acceptance/test_responsive.py`：Playwright 多视口（桌面代表尺寸、390px 移动）断言响应式 pass criteria；并产出桌面/移动**截图**（成功态 + 失败回退态）。
- `tests/acceptance/test_a11y.py`：键盘穿越指标卡与详细分析控件；颜色伴文字。
- 统一入口：`pytest tests/acceptance -m acceptance`（或一个 `make acceptance` / 脚本），**离线全过**。
- CI：GitHub Actions workflow 在 PR 上跑 `acceptance`。

**关键任务**：
1. 选 Playwright（Python 或 Node）做无头浏览器断言；截图 artifact 上传。
2. 让前端支持“fixture 注入模式”（通过 URL 参数或环境变量指向 fixture），避免验收依赖真实 fetch。
3. 把规格 §Testing Decisions 每条 pass criteria 一一映射成一个断言。
4. CI workflow：装依赖 → 跑 `services.data.build_snapshot --offline` → 跑 `services.ai.run_daily_analysis --mock` → 跑 `pytest tests/acceptance`。

**验收标准（Phase 4）**：
- [ ] `pytest tests/acceptance` 在**断网**机器上全过（fixture 注入，无任何真实网络/LLM 调用）。
- [ ] 规格 §Testing Decisions 的“成功 fixture / 失败 fixture / AI 响应契约 / 输入边界 / 响应式”五组 pass criteria **逐条**有对应断言且通过。
- [ ] 产出 4 张截图：桌面成功态、桌面失败回退态、移动成功态、移动失败回退态，存入 review 证据。
- [ ] CI 在 PR 上自动跑 acceptance，红则阻断合并。
- [ ] 维护者烟囱（真实 LLM）是**独立**脚本，**不**在 acceptance 路径上（规格 §Testing Decisions）。
- [ ] 断言只查外部行为与稳定契约（阶段名、指标计数、可见文本、图表存在性），**不**断言 DOM 结构/样式实现/私有模块边界（规格 §Testing Decisions）。

---

### Phase 5 —— 部署与日常运维

**目标**：把“每日自动更新 + 公开只读访问 + 失败可恢复”落地到生产。

**交付物**：
- 每日定时：GitHub Actions cron（UTC 固定时刻，每天 1 次）→ `build_snapshot`（触网）→ `run_daily_analysis`（真实 LLM）→ 把 `artifacts/*.json` commit 回 `main`（或推对象存储）。
- 托管：静态站点（**Cloudflare Pages**）自动部署 `dashboard/` + `artifacts/`。
- 监控：每日 run 失败 → Action 标红 + 通知维护者（规格：失败不等于市场结论，必须被人知道）；`series.json` 的 `freshness_days` 超阈值告警。
- 回退演练：人为让某天 LLM 失败，确认线上显示“今日不可用 + 昨日回退带日期”。
- 隐私/合规复核：确认 Bitview/OBM 数据再分发条款允许公开展示（`specs/v0.1.0/bear-market-indicator-expandability-research.md` §数据来源事实 已警示）。

**关键任务**：
1. 写 `services/data/build_snapshot.py` 的“生产模式”（触网、写 artifact）与 Actions workflow。
2. 配 LLM 凭据为 Actions secret。
3. 配静态托管 + 部署钩子。
4. 写失败通知（GitHub Issue / 邮件 / webhook）。
5. 上线前做一次完整的“成功 → 强制失败 → 恢复”演练。

**验收标准（Phase 5）**：
- [ ] 线上当日在定时后有当日 `analysis_date` 的分析可见；同日刷新结论不变（规格 User Story 35）。
- [ ] 人为让一次定时失败 → 线上正确显示“今日 AI 分析不可用”+ 带日期的回退（或无回退的不可用态）；下一次成功后恢复当日结论，回退被替换为新的“上一份成功”（规格 §Implementation Decisions：仅保留一份回退）。
- [ ] 公开端只读：访客无法改阈值/指标/结论（规格 §Out of Scope）。
- [ ] 数据时效告警就位：`freshness_days` 超限触发维护者通知。
- [ ] 数据再分发合规已人工复核并记录结论。

---

## 4. 全局验收标准（合并/上线的最终门）

下表把规格 §Testing Decisions 的全部 pass criteria 映射到阶段，作为“完成”的单一事实来源。

| # | pass criteria（规格） | 验证阶段 | 验证手段 |
|---|---|---|---|
| G1 | 顶部固定阶段显示 | P3/P4 | `test_success_flow` |
| G2 | 五阶段同排、恰一个标记当前 | P3/P4 | `test_success_flow` |
| G3 | 一致性标签 + 一句话可见、桌面同行 | P3/P4 | `test_success_flow` + 截图 |
| G4 | 三摘要块（核心支撑/主要阻力/下一阶段条件）渲染 | P3/P4 | `test_success_flow` |
| G5 | 详细分析可展开/收起、默认收起 | P3/P4 | `test_success_flow` |
| G6 | 1440×900 桌面下六类看板顶部不滚动可见 | P3/P4 | `test_responsive` + 桌面截图 |
| G7 | 六类状态全可见；16 指标在正确类别；核心/辅助文字可分 | P3/P4 | `test_success_flow` |
| G8 | 点指标 → 单一共享图表更新（价格+指标+阈值线）；选中态保持 | P3/P4 | `test_success_flow` |
| G9 | 无概率/买卖/入场价/仓位/杠杆措辞 | P2/P3/P4 | `test_validator_reject` + 前端扫描 |
| G10 | 失败：声明今日不可用；有回退才展示并标日期；无回退不编造；看板仍可用 | P2/P3/P4 | `test_failure_flow` + 截图 |
| G11 | AI 契约：仅白名单阶段/状态/一致性；六类齐全；支持/反面/下一阶段必填；非法拒绝 | P2/P4 | `test_ai_contract` |
| G12 | 输入边界：AI 输入含定义/角色/当前值/阈值；不含历史/趋势/新闻/外部研究/组合 | P1/P2/P4 | `test_input_boundary` |
| G13 | 响应式：桌面可读；移动无横向溢出；390px 五阶段点全可见 | P3/P4 | `test_responsive` + 移动截图 |
| G14 | 键盘可操作；状态含义有文字不仅靠颜色 | P3/P4 | `test_a11y` |
| G15 | 验收流无网络/无付费 API/无真实 AI/无生产数据可跑 | P4 | 离线 `pytest tests/acceptance` |
| G16 | 测试断言外部行为与稳定契约，不断言 DOM/样式/私有边界 | P4 | 代码评审 |
| G17 | 维护者烟囱独立、非验收门 | P2 | 流程检查 |
| G18 | review 证据含验收命令结果 + 桌面/移动（成功 + 失败）截图 | P4 | 截图 artifact |

任一未过 = 该阶段未完成。

---

## 5. 风险与待决策点

| 编号 | 项 | 说明 / 建议 |
|---|---|---|
| **D-1** ✅已定 | 前端框架 | **Vue 3 + Vite + TypeScript**；明细见 §1.3。 |
| **D-2** ✅已定 | LLM | **Provider 无关**，默认 OpenAI 兼容（接你自有 API，env 配 `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`）。Phase 2 抽象 `LLMClient`。 |
| **D-3** ✅已定 | 托管 + 定时 | **Cloudflare Pages + GitHub Actions cron**。 |
| **D-4** | 阈值冻结时点 | `config/thresholds.yaml` 的无前视窗口上界 = 上一轮熊底（2022-11-21）。未来进入新一轮后，窗口口径需重新评审（prototype 已用 `CURRENT_CYCLE_START`）。 |
| **R-1** | 数据再分发合规 | `specs/v0.1.0/bear-market-indicator-expandability-research.md` 警示“可公开读取 ≠ 可任意再分发”。上线前必须复核 Bitview/OBM 条款。**Phase 5 阻塞项**。 |
| **R-2** | LLM 偶发非法输出 | 即便 prompt 约束，LLM 仍可能吐概率/买卖措辞。靠 `validator.py` 兜底拒绝 + 回退（Phase 2 已覆盖）。 |
| **R-3** | `series.json` 体积 | prototype 已 3.5MB。公开站需 gzip + 考虑抽样/分段加载，否则移动端首屏受损。Phase 1/3 处理。 |
| **R-4** | 单一核心维度被当多票 | MVRV+AVIV 同维度、HODLer NPC+≥155d 同维度（`specs/v0.1.0/indicator-validation-record.md` §核心使用规则）。AI prompt 必须明示“同维度互证不重复计分”，否则结论偏乐观。Phase 2 prompt 任务覆盖。 |
| **R-5** | 图表与 AI 数据不同源日期 | 规格 §Further Notes：本版本不要求 AI 调和不同来源日期。但前端展示需标注各指标 `current_date`，避免误读为同日。Phase 3。 |

---

## 6. 粗略工作量估算（仅作排期参考）

> 假设 1 名熟悉 Python + 前端的工程师全职。不含合规复核等待时间。

| 阶段 | 估算 | 关键路径？ |
|---|---|---|
| Phase 0 | 2–3 天 | 是（契约先行） |
| Phase 1 | 5–8 天（含无前视测试与离线 fixture 化） | 是 |
| Phase 2 | 5–7 天（契约/校验/回退，TDD） | 是 |
| Phase 3 | 8–12 天（含响应式 + a11y + 失败态） | 可与 P1/P2 部分并行（用 fixture） |
| Phase 4 | 4–6 天（Playwright + 截图 + CI） | 否（依赖 P1–P3） |
| Phase 5 | 3–5 天（部署 + 定时 + 演练） | 否 |
| **合计** | **约 4–6 周** | 关键路径约 3–4 周（P0→P1→P2，P3 并行） |

---

## 7. 与规格的范围边界对账（防止越界）

本计划严格遵守规格 §Out of Scope。明确**不做**：买卖/入场价/仓位/杠杆建议；数值概率；AI 读历史/趋势/新闻；超过 16 指标；AI 改定义/类别/角色/阈值；公开编辑阈值；公开管理界面；账户/偏好/个性化；历史判断归档；AI 阶段选择的历史回测；邮件/推送/通知；日内/按需 AI；显示距下一档距离；自动调和不同来源日期；声称识别确切周期最低点。

如实施中发现某需求触及上述边界，**停并回到规格**，不在本计划内私扩。
