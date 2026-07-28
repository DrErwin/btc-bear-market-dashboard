# 核心指标与辅助指标复核（2026-07-28）

## 结论

当前 16 项指标不应按“每项各投一票”处理。现阶段真正能够承担独立核心判断的只有两个证据维度：

1. **全市场估值：MVRV 是主锚，AVIV 只做同维度复核。**
2. **矿工收入压力：Puell Multiple 是独立主锚。**

当前没有合格的第三个独立核心维度。Seller Exhaustion Constant（卖方耗竭常数）是最值得继续验证的候选；CVDD 是第二候选，但项目目前“距离 CVDD 50%”的规则过宽，不能当作核心底部信号。

现有五个 `core` 标签中，HODLer Net Position Change 30d 与 `>=155d` 花费价值占比应立即降级：两者都先由 `MVRV < 1` 筛选，不是独立证据；当前数据还停在 2023-01-12，比分析日落后 1292 天。

## 什么才有资格叫“核心”

核心指标必须同时满足五条：

1. **意义直接**：直接描述深熊底部所需的经济状态，而不只是市场某个侧面。
2. **数据可用**：数据新鲜、可重复取得，并有明确的缺失和过期处理。
3. **跨周期稳定**：预先写下的规则能在多个完整周期工作，不依赖事后挑阈值。
4. **信号有选择性**：不会在大量普通交易日反复触发。
5. **证据相对独立**：不能只是另一个核心指标的换一种算法或同一数据的重复表达。

“曾在四次底部附近出现”只说明它可能有用，不等于它能独立确认底部。若两个指标几乎同步，它们只能算一类证据。

## 当前 16 项指标的分级

| 当前指标 | 建议位置 | 判断强度 | 原因与正确用法 |
|---|---|---:|---|
| MVRV | **核心锚** | 强 | 全市场市值相对已实现成本。`<1` 可表示市场整体低于链上成本，适合判断深熊估值环境；`<0.8` 是更深压力区，但仍不是精确日期计时器。 |
| AVIV | **核心复核** | 强复核、非独立 | 对“活跃投资者”调整后的估值指标。用途与 MVRV 很接近；本地历史相关性约 `0.991`，所以 MVRV 与 AVIV 合起来只算一张估值票。 |
| STH-MVRV tactical price | 普通辅助 | 中 | 观察短期持有者的成本与盈亏，适合识别短期压力、反弹和成本线收复，不代表全市场结构性底部。项目阈值还是自定义战术规则。 |
| Percent Supply in Profit（PSIP） | 普通辅助 | 中 | 说明有多少供应处于盈利，适合解释亏损覆盖面；它与 MVRV 属于同一“未实现盈亏”家族。 |
| Supply in Profit/Loss（SIPL） | 普通辅助 | 弱增量 | 与 PSIP 使用同一供应盈亏信息；本地序列相关性为 `1.000`，不得再投一票。 |
| Relative Unrealized Profit（RUP） | 普通辅助 | 中 | 描述未实现盈利规模，可说明泡沫消退和盈利压缩，但与 MVRV、PSIP 高度同源。 |
| Relative Unrealized Loss 4y z-score | **强辅助** | 中强 | 可补充“亏损是否极端”，但当前实现由其他盈亏数据推导，再做项目自定义四年标准化，不是独立核心。 |
| Realized Cap Relative NPC 30d | 普通辅助 | 弱到中 | 适合观察资金流入、流出及恢复是否有承接，不适合定位底部；当前宽阈值覆盖约 72.2% 的可用日期，选择性太弱。 |
| aSOPR | **强辅助** | 中强事件信号 | `<1` 表示花费者平均在亏损卖出，可识别投降或熊市压力；但同样会在普通熊市反复出现。本地规则产生约 502 个事件，不能单独定阶段。 |
| HODLer NPC 30d | **暂停计分** | 当前不可用 | 正值表示长期持有者净积累，不是底部专属；当前又被 `MVRV < 1` 筛选，历史窗口只覆盖 1/4，且数据过期。恢复新鲜数据后也只能做辅助。 |
| `>=155d` spent-value share | **暂停计分** | 当前不可用 | 老币花费既可能是熊市投降，也可能是牛市派发；155 天只是持有者分组边界。当前被 MVRV 筛选、事件碎片多、数据过期，只能解释行为。 |
| Seller Exhaustion Constant | **强辅助／第三核心候选** | 中强 | 指标本身专门寻找“低盈利供应 + 低波动”的卖方耗竭环境，方向最接近底部。但当前阈值是项目按历史分位数自定，约 25.8% 日期触发，尚缺少样本外验证。 |
| Puell Multiple | **核心锚** | 强 | 矿工日收入相对一年均值，提供与投资者估值不同的压力维度。官方说明 `<1` 是矿工收入受压，历史显著宏观底部常见于 `<0.5`；真正强证据应看深区，并考虑减半造成的机械下降。 |
| Thermocap Multiple 4y/log z-score | 普通辅助 | 弱到中 | 观察市值相对累计矿工安全支出，但跨周期基准会漂移；当前又是项目自定义的对数四年标准化，本地深阈值仅覆盖 2/4 底部窗口。 |
| CVDD proximity | **强辅助／候选** | 中强概念、当前规则弱 | CVDD 被提出为实验性底部模型，近期实证研究也使用非常接近模型线的条件；但项目当前“50% 以内”远宽于研究使用的 `1%` 条件，不能直接继承研究结论。 |
| Reserve Risk 4y/log z-score | 普通辅助 | 中等环境信号 | 低值说明价格相对长期持有者信心较低，适合识别长期价值区；低位可能持续很久，从熊市延伸到早期牛市，不是底部定时器。当前 z-score 也是项目自定义。 |

## 本地数据给出的关键证据

- MVRV 与 AVIV：全样本相关性约 `0.991`；即使只看 `MVRV <= 1.2` 的压力区，仍约 `0.970`。
- PSIP 与 SIPL：相关性 `1.000`，是重复信息。
- MVRV 与 Puell 深阈值的日期重合度明显较低，说明 Puell 确实增加了不同的矿工压力证据。
- HODLer NPC 与 `>=155d` 当前最后日期都是 2023-01-12；不能把旧值呈现成“当前状态”。
- 当前 AI 输入只带指标值和角色，没有把每项指标日期一起带入；若不先做时效闸门，过期数据可能看起来像今天的证据。

这些统计是本项目的探索性历史复核，不是未来预测准确率。特别是“落在历史底部前后 180 天”属于较宽窗口，不能等同于精确择时能力。

## 网络一手资料怎样使用这些指标

- Glassnode 对 [MVRV](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/mvrv-ratio) 的定义是市场市值除以已实现市值；低于 1 常出现在晚期熊市、投降与积累阶段。其用途是判断估值环境，不是保证某天为最低点。
- [Cointime Economics 白皮书](https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARK%20Invest%20x%20Glassnode_White%20Paper_Cointime%20Economics_Final.pdf) 将 AVIV 定义为活跃投资者估值框架。它改进了成本基础，但仍属于 MVRV 式估值家族。
- Glassnode 的 [STH-MVRV](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/sth-mvrv) 用来观察短期持有者成本和盈亏；[PSIP](https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/percent-supply-in-profit)、[Supply in Profit](https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/supply-in-profit) 与 [Supply in Loss](https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/supply-in-loss) 都属于供应盈亏描述。
- Glassnode 对 [aSOPR](https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/asopr-adjusted-sopr) 的解释表明，低于 1 可能代表亏损卖出、投降或持续熊市，因此更适合作为事件确认。
- Glassnode 对 [Puell Multiple](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-issuance/puell-multiple) 的说明把 `<1` 视为矿工收入压力，并指出历史显著宏观底部常见于 `<0.5`。
- Glassnode 对 [Reserve Risk](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-days-destroyed/reserve-risk) 的说明指出低风险区可能持续较长时间，因此它更像宏观背景。
- ARK 对 [Seller Exhaustion Constant](https://www.ark-invest.com/articles/analyst-research/valuing-bitcoin) 的设计目标是识别卖方可能已经耗竭的环境；指标概念有针对性，但不验证本项目自定阈值。
- CVDD 的提出者把它称为累计销毁价值的[实验性模型](https://woobull.com/experiments-on-cumulative-destruction/)。2026 年同行评审研究在回测中使用“价格距离 CVDD 不超过 1%”的严格条件，并明确提醒周期样本少、阈值可能有事后偏差：[论文全文](https://osuva.uwasa.fi/server/api/core/bitstreams/6575b90c-6140-44e7-a798-011a1793d134/content)。
- Glassnode 的 [长期／短期持有者方法](https://docs.glassnode.com/guides-and-tutorials/metric-guides/long-and-short-term-holder-supply/supply-held-by-long-and-short-term-holders) 将 155 天用作行为分组边界；它本身不是“老币花费必然见底”的规则。

## 建议的产品判断规则

1. **先过数据闸门**：任何过期、缺失或来源降级的指标都不计分，也不以“当前值”交给 AI。
2. **按独立维度投票**：MVRV + AVIV 合计一张估值票；Puell 是一张矿工压力票。
3. **区分观察线与深压力线**：例如 Puell `<1` 只表示承压，`<0.5` 才升级为强证据；MVRV 也应区分 `<1` 与更深区。
4. **辅助指标不能单独抬高阶段**：它们只能解释核心信号、确认投降／恢复，或在相互矛盾时阻止系统给出“证据充分”。
5. **第三核心必须先验证**：优先验证 Seller Exhaustion，其次用严格、预先声明的 CVDD 距离规则验证；通过样本外与时效测试后再升级。

因此，最清楚的界面分组不是“5 个核心 + 11 个辅助”，而是：

- **核心锚**：MVRV、Puell Multiple。
- **核心复核**：AVIV（和 MVRV 合计一票）。
- **强辅助／核心候选**：Seller Exhaustion、CVDD proximity。
- **强辅助事件或严重度说明**：aSOPR、Relative Unrealized Loss z-score。
- **普通解释型辅助**：STH-MVRV、PSIP、SIPL、RUP、Realized Cap NPC、Thermocap z-score、Reserve Risk z-score。
- **暂停计分**：HODLer NPC、`>=155d` spent-value share，直到数据恢复新鲜；恢复后仍是辅助。

本研究只用于判断“熊底证据与市场阶段”，不提供交易建议、概率、价格目标、仓位或杠杆意见。
