# 16 项指标参数的行业共识复核

> 日期：2026-07-29  
> 范围：复核 `services/data/metrics.py` 与当前 `dashboard/public/data/packet.json` 中展示的 16 项指标。  
> 边界：只讨论指标定义、阈值证据和历史识别能力；不提供交易建议，也不把历史相关性当成未来预测能力。

## 1. 先说结论

严格来说，链上指标没有类似会计准则那样的“统一行业标准”。这里把“公认参数”限定为：指标原作者、Glassnode 官方文档、ARK/Glassnode 白皮书或同行评审论文明确写出的数值或窗口。

当前配置可分成三层：

1. **当前触发线有较强一手来源支持**：MVRV `1 / 0.8`、AVIV `0.55`、PSIP `50%` 与约 `40%–45%`、SIPL `50%`、Relative Unrealized Profit 约 `30%`、aSOPR `1`、Puell Multiple `1 / 0.5`。
2. **原始指标参数被认可，但当前触发线是项目自定义**：STH-MVRV、HODLer NPC、`≥155d` 花费价值占比、Seller Exhaustion、CVDD、Reserve Risk、Realized Cap NPC。
3. **当前变换和触发线主要是项目自定义**：RUL 四年 z-score、Thermocap 四年 log z-score，以及上述指标使用的历史 `5% / 10% / 90%` 分位线。

因此，不能说“16 项都有公认阈值”。更准确的说法是：**7 项至少有一条当前数值线得到一手来源直接支持；其余多数只有定义、观察方向或基础窗口得到支持，页面上的具体触发线仍需项目自己的跨周期验证。**

## 2. 判定标准

| 级别 | 含义 |
|---|---|
| A：一手数值支持 | 原作者、官方指标文档、联合白皮书或同行评审研究明确给出相同或非常接近的数值和含义 |
| B：自然数学分界 | 数值由公式直接决定，例如比率 `1` 表示盈亏平衡、变化率 `0` 表示扩张与收缩分界；它有清晰含义，但不自动代表“熊底有效” |
| C：项目校准 | 项目自行选择窗口、分位、z-score、距离或组合条件；可以合理，但不属于行业共识 |

“A”和“B”可以同时成立。例如 MVRV `1` 既是数学上的成本平衡点，也被官方文档长期作为熊市压力线使用。

## 3. 逐项复核

| # | 指标与当前参数 | 共识层级 | 一手来源支持了什么 | 历史效果与主要局限 |
|---:|---|---|---|---|
| 1 | **MVRV**：`<1`、`<0.8` | `1`：A+B；`0.8`：A（经验深区） | Glassnode 将 `<1` 解释为市场价值低于全网已实现成本，历史上常见于投降和熊市后段；其后续深度研究也把 `<0.8` 量化为极低区。[Glassnode MVRV 指南](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/mvrv-ratio)、[Glassnode 深度研究](https://research.glassnode.com/mastering-the-mvrv-ratio/) | `1` 的经济含义最清楚；`0.8` 有公开历史证据，但仍是经验深区。两者都可能持续一段时间，不等于当日见底。 |
| 2 | **AVIV**：`<0.65`、`<0.55` | `0.55`：A；`0.65`：C | ARK 与 Glassnode 的 Cointime Economics 白皮书明确写出：AVIV 低于 `0.55` 表示历史“超卖”区域，`1` 是中点；没有给出 `0.65`。[Cointime Economics 白皮书](https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARK%20Invest%20x%20Glassnode_White%20Paper_Cointime%20Economics_Final.pdf) | `0.55` 有原作者支持，但白皮书仍是历史样本总结，不是独立预测保证；AVIV 与 MVRV 同属成本基础视角，不应重复算作两票。 |
| 3 | **STH-MVRV 战术价位**：过去周期 `5%` 分位、`均值−1.5σ`、`中位数−1.5×MADσ` | C；原始 `155d` 和 `STH-MVRV=1` 为 A+B | Glassnode 官方定义使用 `<155 天` 的短期持有者，并把 `STH-MVRV=1` 视为该群体盈亏平衡；当前三条低位线并非官方参数。[STH-MVRV](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/sth-mvrv)、[Glassnode 对 1.0 的应用](https://research.glassnode.com/the-week-onchain-week-10-2023/) | `1` 对解释群体是否浮亏有效；当前三法适合做项目内相对极端度比较，但结果依赖选取的 2018–2022 样本窗口，换周期会变。项目基础数据的短期群体口径还需与 Glassnode 的 `<155d` 实体调整口径分别标注。 |
| 4 | **PSIP**：`<50%`、`<40%` | A+B | Glassnode 原始研究用 `<50%` 辅助识别市场底部；后续研究指出此前熊市低位常在约 `40%–45%` 的供应盈利区间。[原始研究](https://research.glassnode.com/dissecting-bitcoins-unrealised-on-chain-profit-loss/)、[2022 历史复核](https://research.glassnode.com/the-week-onchain-week-26-2022/) | 两条线都有公开历史依据，属于当前配置中依据较强的一组。但 PSIP 只测“亏损覆盖面”，丢失币、长期不动币和实体调整会改变可比性；它也不能单独识别精确底部。 |
| 5 | **SIPL**：盈利供应 `<50%`；同时展示亏损供应和差值 | B，且由 PSIP 的 A 证据间接支持 | 盈利供应 `50%` 与亏损供应 `50%` 是同一供应拆分的数学平衡点；Glassnode 的 PSIP 研究支持观察 `<50%`，但 SIPL 并不是另一份独立证据。[Glassnode PSIP](https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/percent-supply-in-profit) | 容易理解，效果与 PSIP 相同；因为两者来自同一底层事实，不能重复计数。 |
| 6 | **Relative Unrealized Profit**：`<40%`、`<30%` | `30%`：A；`40%`：C/观察线 | Glassnode 定义为未实现盈利除以市值，并在 2022 年研究中指出，历史上压缩至约市值的 `30%` 与卖压缓和相伴；没有把 `40%` 定义成统一阈值。[指标定义](https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-profit)、[历史应用](https://research.glassnode.com/the-week-onchain-week-41-2022/) | `30%` 有历史解释；`40%` 更适合作为较早的观察线。该指标只看利润一侧，不等同于 NUPL，也会受长期不动或丢失供应影响。 |
| 7 | **RUL · 四年 z-score**：`>2`、`>2.5` | C | Glassnode 支持 Relative Unrealized Loss 的原始定义，但没有支持“先取四年滚动 z-score，再用 `2 / 2.5`”作为 BTC 熊底标准。[Glassnode Unrealized Loss](https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-loss) | z-score 能把不同量级放到同一尺度；但 RUL 分布右偏，`2σ` 不等于固定罕见概率，窗口长度和异常值会显著改变信号。 |
| 8 | **Realized Cap Relative NPC · 30d**：`>0` | `30d`：A/常用口径；`0`：B | Glassnode 使用 30 日 Realized Cap 变化衡量月度资本流入/流出；正负号的意义由公式直接决定。[Glassnode 30 日应用](https://research.glassnode.com/2022-bear-of-historic-proportions/)、[Realized Cap 定义](https://docs.glassnode.com/guides-and-tutorials/metric-guides/realized-capitalization) | 适合描述资本由收缩转向扩张，但 `>0` 在正常扩张阶段很常见，更像“恢复确认”而不是“底部压力”阈值；项目使用相对变化率也与官方常见的绝对变化或 z-score 版本不完全相同。 |
| 9 | **aSOPR**：`<1`；`3d/7d` 均线只展示 | A+B | SOPR `1` 是花费币的已实现盈亏平衡；aSOPR 官方口径排除寿命不足 1 小时的 UTXO，以减少找零和中继交易噪声。[SOPR](https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/sopr-spent-output-profit-ratio)、[aSOPR](https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/asopr-adjusted-sopr) | `<1` 能确认链上花费者总体实现亏损；但普通回调也会出现，单日尖峰噪声大。3/7 日均线改善可读性，却会削弱和延迟投降尖峰。 |
| 10 | **HODLer NPC · 30d**：`0`、过去低估期 `10% / 5%` 分位 | `30d` 与 `0`：A+B；分位、除以供应和 `MVRV<1` 过滤：C | Glassnode 将 HODLer NPC 定义为长期持有者的月度净变化，负值表示兑现/减少，正值表示净积累。[API 定义](https://docs.glassnode.com/basic-api/endpoints/indicators)、[30 日解释](https://research.glassnode.com/the-week-onchain-week-45-2022/) | 30 日方向有行业使用基础；项目的“占供应百分比 + 仅保留 MVRV<1 + 历史分位”是二次改造。传统 HODLer NPC 的正值还可能受累积定义封顶，Glassnode 自己也提示 LTH NPC 是更平衡的替代。[方法比较](https://research.glassnode.com/quantifying-bitcoin-hodler-supply/) |
| 11 | **≥155d 花费价值占比**：过去低估期 `90%` 分位 | `155d`：A；占比、`MVRV<1` 过滤和 `90%` 分位：C | Glassnode 根据 UTXO 再花费概率曲线，把约 `155 天` 设为长短期持有者分界，并在实体口径中用以 155 天为中点、宽度 10 天的平滑函数。[155 天方法](https://research.glassnode.com/quantifying-bitcoin-hodler-supply/)、[官方指标指南](https://docs.glassnode.com/guides-and-tutorials/metric-guides/long-and-short-term-holder-supply/supply-held-by-long-and-short-term-holders) | `155d` 是当前 16 项中最明确的行为研究参数之一；但页面计算的是“花费价值占比”，并不能证明老币以亏损卖出。`90%` 分位只有项目样本意义。 |
| 12 | **Seller Exhaustion Constant**：PSIP × 30 日价格波动；过去周期 `10%` 分位 | 公式和 `30d`：A；ARK 的 `≤0.01`：A（经验线）；项目 `10%` 分位：C | ARK 与 David Puell 原始定义就是供应盈利百分比乘以过去 30 日价格波动，并指出低波动与高亏损同时出现曾与投降和筑底相伴；ARK 后续月报使用过 `≤0.01` 的经验线，但它并非当前项目的分位阈值。[ARK 原作者页面](https://www.ark-invest.com/articles/analyst-research/valuing-bitcoin)、[ARK 原始白皮书](https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARKInvest_123021_Whitepaper_OnChainData.pdf)、[ARK 2023 年 1 月月报](https://assets.arkinvest.com/media-8e522a83-1b23-4d58-a202-792712f8d2d3/7d69c331-1167-4d90-84ef-b91794a0a1f8/The-Bitcoin-Monthly-January-2023.pdf) | 组合概念合理，但项目 `10%` 分位不能继承 `0.01` 的历史说明；证据主要来自少数案例，且波动率实现方式和 PSIP 口径都会改变数值。 |
| 13 | **Puell Multiple**：`<1`、`<0.5`；分母 365 日均值 | A+B | Glassnode 官方指南明确：`<1` 表示矿工收入低于一年基准、可能承压；历史重大宏观底部曾出现在 `<0.5`。365 日均值是原指标定义的一部分。[Glassnode Puell Multiple](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-issuance/puell-multiple) | 当前数值线与官方最一致。但减半会机械地把指标约减半，因此 `<1` 可能仅反映相对收入下降，不能单独把市场阶段推到“熊市下行”或“底部”。 |
| 14 | **Thermocap Multiple · 四年 log z-score**：过去周期 `10% / 5%` 分位和 `z=0` | 原始 Thermocap：A；全部当前触发线：C；`z=0`：B | Glassnode/Coin Metrics 支持 Thermocap 为累计矿工收入、Market Cap/Thermocap 为相对矿工安全支出的估值比率；Glassnode 历史研究还显示原始低位倍数会跨周期漂移。没有一手来源支持当前“log + 1460 日滚动 z + 分位”的阈值。[Glassnode Mining API](https://docs.glassnode.com/basic-api/endpoints/mining)、[Glassnode 历史研究](https://research.glassnode.com/the-week-on-chain-week-38-2021/) | 周期标准化能缓解原值长期漂移，`z=0` 只表示等于自身滚动均值。当前分位线是项目校准，不是矿工成本的公认边界。 |
| 15 | **CVDD 接近程度**：`1 / abs(Price/CVDD−1) > 2`，即相对距离约 `<50%` | CVDD 公式与 600 万常数：A；接近度变换和 50%：C | Willy Woo 原文给出 CVDD 公式并说明 `6,000,000` 是用于图形校准的任意常数。2026 年同行评审论文在三个周期中测试的是价格距 CVDD **不超过 1%**，而不是 50%；CVDD 入场相对随机时间多数情况下更好，但只有三个周期。[原作者](https://woobull.com/experiments-on-cumulative-destruction/)、[同行评审论文](https://doi.org/10.1016/j.ribaf.2026.103486) | 当前 50% 距离过宽，不能由原作者或论文支持；按当前倒数刻度，论文的 1% 规则约对应 `proximity ≥100`。CVDD 更适合长期底部接近度，不提供短期方向或顶部信号。 |
| 16 | **Reserve Risk · 四年 log z-score**：过去周期 `10% / 5%` 分位和 `z=0` | 原始指标及绝对 `0.0026`：A；当前 z-score 线：C；`z=0`：B | Glassnode 官方指南把原始 Reserve Risk `<0.0026` 描述为历史低估区，也明确指出低位可能持续很久；当前页面没有使用这条绝对线，而是另做四年标准化。[Glassnode Reserve Risk](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-days-destroyed/reserve-risk) | 原值有公开经验线，但 HODL Bank 是累计量，跨周期会漂移；项目改为滚动 z-score有合理动机，却失去了“官方阈值”身份，必须独立验证。 |

## 4. “效果如何”应怎样理解

### 4.1 一手来源能支持的最强结论

- MVRV `<1`、aSOPR `<1`、STH-MVRV `<1`、Realized Cap 变化 `0` 线首先是**经济含义明确的平衡线**，不是“预测准确率”。
- AVIV `<0.55`、Puell `<0.5`、PSIP 约 `40%–45%`、Relative Unrealized Profit 约 `30%` 属于**原作者或官方研究总结出的历史极端区**。
- `155d` 是基于历史再花费概率推导的持有者分类参数，支持的是**群体划分**，并不支持页面的 `90%` 分位触发线。
- CVDD 是少数获得同行评审跨周期检验的相关指标之一。该研究覆盖 2013-12-07 至 2025-04-12 的三个周期，采用“距 CVDD 不超过 1%”的规则；它的结果不能替页面的 50% 规则背书。

### 4.2 证据仍然很有限

2026 年的同行评审研究只直接测试了 NUPL、MVRV **Z-score** 和 CVDD，而本看板使用的是普通 MVRV Ratio，且没有 NUPL。论文明确承认：

- 样本只有三个完整周期；
- 不存在普遍接受的退出阈值；
- 部分阈值可能包含事后选择偏差；
- 市场结构变化可能让指标逐渐失效。

因此，不能把该论文的成绩外推到全部 16 项，也不能把官方图表上的历史对应关系表述成未来有效率。

## 5. 对当前看板的参数治理建议

1. 在配置中给每条线增加 `parameter_basis`：
   - `creator_or_official`
   - `mathematical_boundary`
   - `project_calibrated`
2. 对混合型指标同时标出“公认部分”和“自定义部分”。例如：
   - `≥155d`：官方行为分类；
   - `低估期 90% 分位`：项目校准。
3. 优先保留可解释的平衡线和有原作者支持的深压线；分位/z-score 线应显示校准窗口、样本量和版本。
4. CVDD 当前 50% 规则继续保持“待验证”，不要参与阶段判断；若测试论文的 1% 规则，应作为新的候选版本单独回测，不能直接覆盖。
5. Puell `<1` 只表达矿工收入承压；它太接近“一年均值以下”的宽泛状态，不应单独决定市场阶段。
6. PSIP 与 SIPL、MVRV 与 AVIV 等共享底层事实的指标，只能相互复核，不能重复计票。

## 6. 来源清单

- Glassnode 官方指标指南：[MVRV](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/mvrv-ratio)、[STH-MVRV](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/sth-mvrv)、[PSIP](https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/percent-supply-in-profit)、[Unrealized Profit](https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-profit)、[Unrealized Loss](https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-loss)、[SOPR](https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/sopr-spent-output-profit-ratio)、[aSOPR](https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/asopr-adjusted-sopr)、[Puell Multiple](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-issuance/puell-multiple)、[Reserve Risk](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-days-destroyed/reserve-risk)。
- ARK Invest 与 Glassnode：[Cointime Economics](https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARK%20Invest%20x%20Glassnode_White%20Paper_Cointime%20Economics_Final.pdf)；ARK Invest：[On-Chain Data Framework](https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARKInvest_123021_Whitepaper_OnChainData.pdf)。
- Glassnode 原始研究：[155 天持有者分类](https://research.glassnode.com/quantifying-bitcoin-hodler-supply/)、[供应盈亏结构](https://research.glassnode.com/dissecting-bitcoins-unrealised-on-chain-profit-loss/)。
- Willy Woo：[Experiments on Cumulative Destruction](https://woobull.com/experiments-on-cumulative-destruction/)。
- Grobys, Näsmän & Sandretto (2026)：[Using on-chain data to predict Bitcoin cycles](https://doi.org/10.1016/j.ribaf.2026.103486)，*Research in International Business and Finance*, 89, 103486。
