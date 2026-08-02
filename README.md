# BTC 熊底证据看板

**BTC 熊底证据看板（BTC Bear-Bottom Evidence Dashboard）**是一个公开、只读的比特币链上周期研究工具。它不寻找某个“神奇的最低点”，而是把熊底视为一段持续发生的过程，帮助普通用户分别看清两个问题：**当前市场压力有多深，以及熊市筑底过程走到了哪里。**

[打开在线看板](https://btc-bear-market-dashboard.erwinwu000.workers.dev/) · 发起与维护：[@ErwinWu000](https://x.com/ErwinWu000)

> [!IMPORTANT]
> 这是市场状态研究工具，不是交易信号工具。它不预测精确最低点，也不提供买卖、仓位、杠杆、价格目标、收益概率或择时建议。

## 关键事实

| 项目 | 说明 |
| --- | --- |
| 产品名称 | BTC 熊底证据看板 / BTC Bear-Bottom Evidence Dashboard |
| 研究对象 | BTC 熊市中的市场压力、熊底形成、市场修复与离开熊底窗口 |
| 核心输出 | 压力轴、筑底过程轴、证据一致性、近三日变化和详细解释 |
| 证据范围 | 当前版本覆盖 6 类、16 项 BTC 链上与周期指标 |
| 阈值框架 | 每项指标保留人工复盘历史熊市后确定的观察、深度压力和极端压力档位 |
| AI 的职责 | 在固定事实和边界内综合解释证据，不修改指标值、阈值或数据日期 |
| 更新方式 | 以每日快照呈现；是否可用于当天判断，以页面日期和数据质量标记为准 |
| 使用语言 | 中文与 English |
| 产品性质 | 公开、只读、可复核、非交易建议 |

## 如何判断 BTC 是否接近熊底？

单个指标进入低位，只能说明某一类压力或异常正在出现，不能证明 BTC 已经见底。熊底通常包含多个阶段：市场估值下降、持有人或矿工承压、卖方逐渐耗竭、资金开始承接、证据持续聚合，随后才可能进入修复并离开熊底窗口。

因此，看板不输出简单的“见底／未见底”，而是同时描述两条彼此独立的状态轴。

| 状态轴 | 它回答的问题 | 可能状态 |
| --- | --- | --- |
| **压力轴** | 当前 BTC 全市场承受的估值、亏损和收入压力有多深？ | 压力尚未明显、进入观察、深度压力、极端压力、数据不足 |
| **筑底过程轴** | 投降、卖方耗竭、承接与修复证据走到了哪一步？ | 未见筑底结构、筑底线索出现、筑底证据聚合、筑底证据较完整、市场修复中、已离开底部窗口、数据不足 |

两条轴可以处在不同位置。例如，市场可以已经进入深度压力，但筑底证据仍然零散；也可以在压力缓解后继续处于市场修复阶段。**压力很深，不等于熊底已经形成。**

## 看板怎样形成结论？

1. **系统固定事实。** 指标值、日期、阈值方向、当前档位和数据新鲜度先由数据系统确定。
2. **人工阈值保留原意。** 观察、深度压力和极端压力来自对历史熊市的人工复盘，用来描述单项指标当前所处的压力区间，不直接宣布“熊底已到”。
3. **指标分组提供判断框架。** 16 项指标按 6 类证据组织，帮助 AI 分辨不同市场现象；框架不会被拆成大量机械打分规则。
4. **AI 做有限度的综合判断。** AI 只能在允许的市场状态中选择，并说明支持证据、相反证据、数据缺口和判断理由。
5. **相关指标不会重复计票。** 观察同一现象的指标只用于互相核对，不能伪装成多份独立证据。
6. **每天参考前三个自然日。** 状态变化需要结合最近三天判断连续性；发生变化时，看板会简要说明原因并保留详细解释。
7. **过期或缺失数据暂停参与。** 这些指标仍可供历史查看，但不会被当作当天市场证据。

## 看板包含哪些 BTC 指标？

“链上指标”是根据 Bitcoin 区块链上的持币、转账、成本和花费记录计算出的观察量。看板把当前 16 项指标放入 6 个证据组，让每一组只回答一个清楚的问题。

| 证据组 | 当前指标 | 普通人可以用它理解什么 |
| --- | --- | --- |
| **估值与成本** | MVRV、AVIV、STH-MVRV | 市场整体和近期买入者，距离自己的持币成本有多远 |
| **供应盈亏** | PSIP、SIPL、Relative Unrealized Profit、RUL · 4 年 z-score | 处于盈利或亏损的 BTC 有多少，账面压力覆盖得有多广 |
| **链上资本流** | Realized Cap Relative NPC · 30d、aSOPR | 真正发生换手的币是在赚钱卖、亏钱卖，还是出现资金修复 |
| **持有者行为** | HODLer NPC · 30d、≥155d 花费价值占比、Seller Exhaustion Constant | 长期持有人是否开始花费老币，卖方压力是否出现耗竭线索 |
| **矿工压力** | Puell Multiple、Thermocap Multiple · 周期 z | 矿工收入相对历史是否受到明显挤压 |
| **长期成本锚** | CVDD 接近程度、Reserve Risk · 周期 z | 当前市场距离长期成本与持币信念参考区有多远 |

每个指标页面都提供：

- **指标公式**：这个数字怎样计算；
- **指标含义**：它实际描述哪一种市场现象；
- **指标使用**：它适合回答什么、不适合单独证明什么；
- **指标来源**：用于核对定义、口径和原始研究。

部分指标定义与方法来源：

- [Glassnode：MVRV Ratio](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/mvrv-ratio)
- [ARK × Glassnode：Cointime Economics（AVIV）](https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARK%20Invest%20x%20Glassnode_White%20Paper_Cointime%20Economics_Final.pdf)
- [Glassnode：Puell Multiple](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-issuance/puell-multiple)
- [Glassnode：Reserve Risk](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-days-destroyed/reserve-risk)
- [Willy Woo：CVDD 原始说明](https://woobull.com/experiments-on-cumulative-destruction/)
- [Open Bitcoin Metrics：≥155 天花费价值序列](https://github.com/diegorllanos/open-bitcoin-metrics/tree/main/metrics/obm_spent_value_ge155d_btc_daily)

这些来源帮助复核指标定义，不代表任何来源为本看板的市场状态结论背书。当天结论仍以看板中实际显示的日期、数值、阈值和数据质量为准。

## 看板提供什么功能？

- **双轴市场状态**：分别描述市场压力和熊底形成过程，不把复杂市场压缩成一个标签。
- **每日 AI 解读**：先给简短结论，再解释压力、筑底、近三日变化、相反证据、修复条件和下一步观察重点。
- **历史共享图表**：把 BTC 价格、指标曲线、历史熊底参考和人工阈值放在同一时间范围内检查。
- **单项指标复核**：查看当前值、档位、阈值、日期、公式、含义、用法与来源。
- **证据一致性提示**：显示不同市场维度的证据是否互相支持，而不是只看指标数量。
- **数据质量控制**：明确区分当前可用、缺失、过期和仅供展示的数据。
- **中英文界面**：中文与 English 使用相同的指标值、阈值、状态和证据。英文 AI 译文校验失败时，页面显示不可用提示，中文判断继续有效。

## 普通用户怎样阅读看板？

1. **先看压力轴**，了解市场成本、亏损和矿工收入压力是否正在加深。
2. **再看筑底过程轴**，判断投降、卖方耗竭、承接和修复证据是否开始形成。
3. **查看近三日变化**，确认今天的状态是延续、加强、减弱，还是仅由短期数据变化造成。
4. **阅读相反证据与缺口**，避免只挑支持自己预期的指标。
5. **进入单项指标**，用历史图表、阈值和来源复核 AI 为什么这样解释。

## 这个看板适合谁？

- 想用普通语言理解 BTC 熊市与链上周期指标的人；
- 研究 Bitcoin 市场周期、持有人行为、矿工压力和长期成本的人；
- 希望检查 AI 结论依据，而不是只接受一句“见底了”的人；
- 需要公开、可复核、非交易建议型 BTC 熊底研究工具的人。

## 常见问题

### BTC 现在是否处于熊底？

这是一个会随每日数据变化的问题。请查看[在线看板](https://btc-bear-market-dashboard.erwinwu000.workers.dev/)中的快照日期、压力轴、筑底过程轴、近三日变化和数据质量。README 只说明判断方法，不保存一个永远不变的市场结论。

### 这个看板能找到 BTC 的精确最低点吗？

不能。它描述熊市压力、筑底证据和修复过程，不预测某一天或某个价格就是最低点。

### 为什么不能只看 MVRV 或 Puell Multiple？

MVRV 主要观察投资者成本压力，Puell Multiple 主要观察矿工收入压力。它们来自不同市场维度，可以互相补充，但任何单项指标都不足以证明筑底过程已经完成。

### 人工阈值会直接决定 AI 的结论吗？

不会。人工阈值告诉 AI 每项指标当前处于观察、深度压力还是极端压力区间；AI 仍需结合不同证据组、相反事实、数据质量和近三日连续性进行综合解释。

### AI 会修改指标阈值或自由创造规则吗？

不会。AI 不能改动指标值、阈值、日期和允许状态，也不能给出交易建议；但它可以在这些边界内判断不同证据的重要性，避免整个产品退化成机械计票。

### 数据过期时会怎样？

过期、缺失或仅供展示的指标仍可用于历史研究，但会暂停参与当天市场状态判断。

### 这是抄底工具或投资建议吗？

不是。看板不输出买卖动作、仓位、杠杆、价格预测、收益承诺或成功概率。

## English overview: BTC Bear-Bottom Evidence Dashboard

The **BTC Bear-Bottom Evidence Dashboard** is a public, read-only Bitcoin on-chain cycle research tool maintained by [@ErwinWu000](https://x.com/ErwinWu000). It treats a bear-market bottom as a process rather than a single date or price.

It answers two independent questions:

1. **Pressure depth:** How severe are market-wide valuation, loss, and miner-income pressures?
2. **Bottoming process:** How far have capitulation, seller exhaustion, absorption, and market repair progressed?

The dashboard currently organizes 16 indicators into six evidence groups: valuation and cost, supply profit and loss, on-chain capital flows, holder behaviour, miner pressure, and long-term cost anchors. It provides daily snapshots, three-day continuity context, historical charts, threshold context, data-quality labels, plain-language indicator explanations, source links, and bounded AI analysis in Chinese and English.

The AI may interpret fixed evidence within allowed market states. It cannot change values or thresholds, and it does not provide price targets, position sizing, leverage, trading timing, or investment advice.

[Open the BTC Bear-Bottom Evidence Dashboard](https://btc-bear-market-dashboard.erwinwu000.workers.dev/)

仅作公开研究参考 · 不构成交易建议。
