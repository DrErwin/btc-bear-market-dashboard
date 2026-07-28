# 数据源公开展示与静态再分发许可审查（2026-07-28）

## 结论先行

**当前看板不能作为一个整体被认定为“已经明确获准公开展示和再分发”。**

| 来源 | 本项目当前用途 | 结论分类 | 可否继续公开放入 GitHub / Cloudflare 静态包 |
|---|---|---|---|
| BRK / Bitview | 通过 `https://bitview.space/api/series/bulk` 获取价格、链上基础日线，并自行派生多数指标 | **目前不能确认／应暂停公开再分发** | **不建议继续**，直到取得 Bitview/BRK 对“公开展示、缓存、静态 JSON 再分发、派生指标”的明确书面许可或公开条款。 |
| Open Bitcoin Metrics（OBM）v0.1.0 | 读取两份 CSV，计算 `≥155d 花费价值占比` | **允许但需署名**（CC BY 4.0；**不要求相同许可**） | 可以，但必须完成 CC BY 署名、链接、变更说明和不暗示背书；应改为固定版本来源。 |

原因很简单：**开源代码许可、允许调用 API、允许展示数据、允许把数据复制到自己的公开静态 JSON，这四件事不是同一件事。** 当前混合包中只要有一部分来源没有明确的再分发许可，整包公开就不能视为已获许可。

本记录是工程合规筛查，不是法律意见；若要长期公开运营、商业化或接受赞助，应让有资质的法律顾问复核。

## 审查范围与已确认的项目事实

本审查只覆盖当前真实数据路径，而非页面代码本身。

- [`services/data/fetch.py`](../services/data/fetch.py) 把 Bitview 定义为 `https://bitview.space/api/series/bulk`，并把 OBM 定义为 `diegorllanos/open-bitcoin-metrics` 的 `main/metrics` 原始 CSV。
- 当前公开包 [`dashboard/public/data/packet.json`](../dashboard/public/data/packet.json) 的 `input_summary.source` 同时记录 `BRK / Bitview` 和 `Open Bitcoin Metrics v0.1.0`；其中有完整价格线、16 个指标历史点和两个柱状系列。
- [`dashboard/src/composables/useDashboardData.ts`](../dashboard/src/composables/useDashboardData.ts) 直接向浏览器请求 `/data/packet.json`；该文件同时被 Git 跟踪，并由 [每日更新工作流](../.github/workflows/daily-update.yml) 提交。公开 GitHub 已使该 JSON 可取得；当当前构建部署到 Cloudflare 静态站点时，公开访问者也可直接取得该文件。

所以，静态 JSON 不只是“屏幕上显示一个图”：它把数据复制到本项目、向公众提供下载，并包含按本项目算法产生的派生数值。对许可审查而言，这属于**再分发／公开提供**。

## 来源一：BRK / Bitview

### 已查到的官方材料

1. [Bitcoin Research Kit（BRK）官方仓库](https://github.com/bitcoinresearchkit/brk) 将 Bitview 说明为其官方免费托管实例，并说明 BRK 可自托管。
2. [Bitview 官方 API 文档](https://bitview.space/api)、[OpenAPI 文档](https://bitview.space/openapi.json) 和 [官方机器可读 API 说明](https://bitview.space/llms.txt) 明确提供 `GET /api/series/bulk`，并说明 API 无需认证、可查询链上时间序列并取得 JSON/CSV。
3. [BRK 的官方 LICENSE](https://github.com/bitcoinresearchkit/brk/blob/main/LICENSE) 是 MIT：它授权复制、修改、发布和分发 **“Software and associated documentation files”**，但这是一份软件许可。

### 分层判断

| 层面 | 结论 | 为什么不能外推 |
|---|---|---|
| BRK 代码 | **明确允许**，按 MIT 的保留版权与许可通知条件使用。 | 这只覆盖从仓库取得的软件和文档，不自动覆盖 Bitview 托管服务返回的数据库、时间序列或其缓存副本。 |
| Bitview API 调用 | **可确认存在公开查询接口**。 | API 文档说明“怎么查询”，并没有等于授予“把返回结果公开复制到另一个站点”的许可。 |
| Bitview 数据公开展示 | **未能确认**。 | 已审阅的官方 Bitview API/BRK 页面没有找到针对托管 API 输出的独立数据许可、署名规则、缓存规则或公开展示授权。 |
| Bitview 数据静态再分发 | **未能确认／应暂停**。 | `packet.json` 会长期公开保存、让访客下载并含有大段历史数据和派生结果；不能仅凭 MIT 代码许可或 API 可访问性推断允许。 |

### 可执行决定

在得到明确授权前，应把下列行为视为暂停项：

- 向公开 GitHub 提交含真实 Bitview 历史数据的 `packet.json`；
- 在 Cloudflare 静态站点向公众提供该 JSON；
- 在页面中公开展示由这些 Bitview 序列直接或间接派生的历史曲线、当前值和柱状值。

这不是断言 Bitview 禁止上述用途，而是说：**截至本次核查，没有足够的一手许可文本证明它允许。** “未能确认”时最稳妥的公开策略就是暂停再分发。

### 建议向 Bitview / BRK 获取的书面确认

通过 [BRK 官方仓库](https://github.com/bitcoinresearchkit/brk) 的公开联系渠道或维护者联系渠道，明确询问并保存答复：

1. 是否允许在公开、免费的研究型网页中展示 Bitview API 返回的历史序列；
2. 是否允许每日缓存、把完整或部分历史序列放进可下载的静态 JSON，并同时托管在 GitHub 与 Cloudflare；
3. 是否允许基于这些序列计算并公开派生指标、阈值和图表；
4. 是否有署名、链接、商用、频率、缓存期限、删除或速率限制要求；
5. 是否有适用于托管 API 输出的数据许可 URL，而不只是 BRK 源码的 MIT LICENSE。

在取得答复后，应把原文链接、答复日期、适用范围和产品内署名方式写入仓库；不要只凭口头理解。

## 来源二：Open Bitcoin Metrics（OBM）

### 已查到的官方材料

1. [OBM 官方仓库](https://github.com/diegorllanos/open-bitcoin-metrics) 将项目称为官方仓库，并在 README 中声明：代码为 MIT，数据和文档为 CC BY 4.0。
2. 本项目实际使用的两份指标说明也分别写明该许可：
   - [`obm_spent_value_btc_daily`](https://github.com/diegorllanos/open-bitcoin-metrics/blob/main/metrics/obm_spent_value_btc_daily/README.md)
   - [`obm_spent_value_ge155d_btc_daily`](https://github.com/diegorllanos/open-bitcoin-metrics/blob/main/metrics/obm_spent_value_ge155d_btc_daily/README.md)
3. 作者发布的 [OBM v0.1.0 Zenodo 归档记录](https://doi.org/10.5281/zenodo.21156871) 明确写明：CSV 数据和文档为 **CC BY 4.0**，Python 脚本为 **MIT**；该记录是带版本号的固定数据集归档。
4. [CC BY 4.0 官方许可说明](https://creativecommons.org/licenses/by/4.0/) 允许复制、再分发和改编（包括商业用途），条件是给出适当署名、提供许可链接、说明是否做了修改，并且不得附加限制他人行使许可权利的条款。

### 分层判断

| 层面 | 结论 | 对本项目的含义 |
|---|---|---|
| OBM Python 代码 | **明确允许**，MIT。 | 仅在项目复制其脚本时需要保留 MIT 通知；本项目当前主要读取 CSV。 |
| OBM CSV 数据与文档 | **允许但需署名**，CC BY 4.0。 | 可以公开展示、复制到静态 JSON、再分发和计算派生比率。**不要求把整个看板也改成 CC BY 或相同许可。** |
| 本项目的 `≥155d 花费价值占比` | **允许但需署名**。 | 它由两份 OBM CSV 计算、再以 `MVRV < 1` 过滤；这是应说明的变更／派生方式。 |
| “OBM 支持或认可本看板” | **不允许这样暗示**。 | CC BY 要求署名，但不允许把署名写成来源方对本产品的背书。 |

### OBM 上线前必须完成的署名

在公开页的“数据来源”或“方法与许可”区域，以及仓库 README 中放入可见、可点击的文字。可直接采用下面的模板（按实际版本和变更更新）：

> 部分数据来源：**Open Bitcoin Metrics (OBM) v0.1.0，Diego R. Llanos**，以 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 提供；原始数据与版本归档见 [Zenodo](https://doi.org/10.5281/zenodo.21156871) 和 [OBM 仓库](https://github.com/diegorllanos/open-bitcoin-metrics)。本看板使用 `obm_spent_value_btc_daily` 与 `obm_spent_value_ge155d_btc_daily` 计算比率，并按本看板方法筛选／绘图；该改动不代表 OBM 作者对本看板的认可或背书。

还应做到：

- 在公开的 `packet.json` 里保留来源、系列 ID、版本、许可 URL 和“本项目已派生／筛选”的标记；
- 链接 CC BY 4.0 许可，并在更新算法、过滤规则或重算数据时更新变更说明；
- 不用 DRM、登录壁垒或与 CC BY 冲突的附加条款限制获得 OBM 部分数据的用户；
- 不把 OBM 的 CC BY 许可误写为“同许可（ShareAlike）”要求：CC BY 只有署名等条件，不含 SA 条款。

### 当前实现的版本风险

虽然 OBM v0.1.0 的作者归档已明确许可，但当前抓取 URL 使用的是 GitHub 的可变 `main` 分支，而不是固定的 v0.1.0 归档文件或固定 commit。该仓库当前根目录也没有可见的 `LICENSE` / `DATA_LICENSE` 文件，GitHub API 的仓库级 `license` 字段为 `null`；许可声明存在于 README、指标文档与官方 Zenodo 归档中。

因此，建议把读取来源改为与 [Zenodo v0.1.0](https://doi.org/10.5281/zenodo.21156871) 一致的固定版本，或至少固定到可复核 commit SHA，并在包内记录版本和 hash。这样可以避免“页面写 v0.1.0，实际却抓到后续滚动文件”的追溯问题。

## 静态 JSON 为什么属于再分发

CC BY 的官方法律文本把向公众提供、公开展示、复制、分发和让公众可按自己时间访问材料都列入 “Share”。本项目的公开静态包满足这一特征：

1. 抓取服务把上游值复制进本地；
2. `packet.json` 将这些值与派生指标编码成可读取的数据文件；
3. GitHub 保存并公开该文件；
4. 当前构建一旦部署为公开 Cloudflare 静态页面，浏览器即可直接下载 `/data/packet.json`。

因此，哪怕页面只显示图表而没有“下载 CSV”按钮，公开数据包仍应按再分发处理。对 OBM，这触发 CC BY 的署名、许可链接和改动说明；对 Bitview，正是需要先取得明确授权的原因。

## 建议的公开发布门槛

在没有新许可前，采用以下门槛最稳妥：

1. **立即边界：** 不再公开发布含真实 Bitview 数据的包；公开代码可继续保留，但应改用不含真实数据的演示 fixture，或仅在本地／受控环境使用真实包。
2. **Bitview 解锁条件：** 获得覆盖“公开显示 + 缓存 + 静态 JSON 再分发 + 派生指标”的书面授权或公开数据许可，并遵守其署名与访问规则。
3. **OBM 解锁条件：** 使用上面的 CC BY 署名文本，固定版本或 commit，记录系列 ID 和本项目的派生方法。
4. **替代路径：** 若 Bitview 不授予再分发许可，可利用 BRK 的 MIT 代码在自有节点上重算所需序列，避免把 Bitview 托管 API 输出复制到公开包；但该替代路径仍应单独核查任何第三方价格输入、品牌使用和发布说明。
5. **复核记录：** 每次更换数据源、许可、API 版本或发布方式后重新审查；API 可用性和页面文字会变化，不应永久依赖本记录。

## 来源与访问日期

所有外部资料均在 **2026-07-28** 访问；仅使用来源方或许可方的一手／官方材料。

- [BRK 官方仓库](https://github.com/bitcoinresearchkit/brk)
- [BRK 官方 MIT LICENSE](https://github.com/bitcoinresearchkit/brk/blob/main/LICENSE)
- [Bitview 官方 API 文档](https://bitview.space/api)
- [Bitview 官方 OpenAPI 文档](https://bitview.space/openapi.json)
- [Bitview 官方机器可读 API 说明](https://bitview.space/llms.txt)
- [OBM 官方仓库](https://github.com/diegorllanos/open-bitcoin-metrics)
- [OBM 总花费价值系列说明](https://github.com/diegorllanos/open-bitcoin-metrics/blob/main/metrics/obm_spent_value_btc_daily/README.md)
- [OBM ≥155 日花费价值系列说明](https://github.com/diegorllanos/open-bitcoin-metrics/blob/main/metrics/obm_spent_value_ge155d_btc_daily/README.md)
- [OBM v0.1.0 官方 Zenodo 归档](https://doi.org/10.5281/zenodo.21156871)
- [CC BY 4.0 官方许可](https://creativecommons.org/licenses/by/4.0/)
- [CC BY 4.0 官方法律文本](https://creativecommons.org/licenses/by/4.0/legalcode.en)
