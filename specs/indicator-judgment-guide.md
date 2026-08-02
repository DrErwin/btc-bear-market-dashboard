# 指标判断说明（当前 16 项基线）

> 版本：`judgment-guide.v1`
>
> 用途：给公开读者解释指标，也为 v0.4.2 计划中的 AI 解释提供可追溯的人工语义。
> 边界：指标描述链上持币成本、盈亏、花费和矿工收入的历史状态；它们不预测最低价，也不构成买卖、仓位、价格或时间建议。

## 怎么读这份说明

- **公式**说明面板实际计算的量。标为“项目变换”的部分，是为了让不同时间段更容易比较而加入的处理，不是行业统一固定线。
- **为什么有用**说明它要回答的市场问题。
- **普通人怎么用**说明应如何理解当前数值和阈值状态。它只用于理解“压力、修复或筑底过程”，不能单独宣布已经见底。
- 页面已经把相关指标分为同一类。读者应看不同问题是否得到一致回答，而不是把相似指标机械相加。

当前面板仍展示 16 项指标。**SIPL** 在本说明中保留，是为了如实描述当前基线；v0.4.2 计划把它从未来的活动指标集合移除，以免与 PSIP 重复。

## 1. 全市场估值与成本

### MVRV

- **公式：**`Market Cap / Realized Cap`（市值 ÷ 已实现市值）。
- **为什么有用：**它把市场今天给所有 BTC 的总估值，和这些 BTC 上次移动时形成的全网成本基础相比。它可以回答：全市场整体离成本有多远、账面压力是否普遍。
- **普通人怎么用：**把它理解为“大家手里币现在总价，相比整体买入成本贵不贵”。数值下降、尤其接近或低于 1，表示更多持有人接近或处于账面亏损；这说明压力变大，不表示某天必然是底部。它与 Puell Multiple 一起看，能把“投资者成本压力”和“矿工收入压力”分开看。
- **限制：**MVRV 与 AVIV 都在看成本和估值，不能当作两份独立投票。
- **来源：**[Glassnode：MVRV Ratio](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/mvrv-ratio)。

### AVIV

- **公式：**`(Market Cap × Liveliness) / (Realized Cap − Thermocap)`。
- **为什么有用：**它聚焦活跃价值与投资者成本基础的关系，补充普通 MVRV 对“哪些币真正活跃”的区分。
- **普通人怎么用：**把它理解为“只看真正重新流动的币后，市场相对投资者成本处在哪”。低值表示活跃投资者的成本压力较大；它应当用来复核 MVRV 的估值背景，而不是自己宣布市场进入某个状态。
- **限制：**与 MVRV 属同一估值家族；面板采用 ARK × Glassnode 的原始公式自行计算，不能把其他供应商的同名成品序列当作完全相同口径。
- **来源：**[ARK × Glassnode：Cointime Economics](https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARK%20Invest%20x%20Glassnode_White%20Paper_Cointime%20Economics_Final.pdf)。

### STH-MVRV 战术价位

- **公式：**`Price × STH Supply / STH Realized Cap`。面板再以历史 5% 分位、`均值 − 1.5σ`、`中位数 − 1.5 × 1.4826 × MAD` 形成三条实时参考线；对应价位为参考比值乘以 STH 已实现价格。
- **为什么有用：**它只看持币不足 155 天的短期持有者，因此比全市场成本指标更敏感，能观察近期入场者是否承受浮亏。
- **普通人怎么用：**把它理解为“最近约五个月买币的人，平均赚还是亏”。数值越低，近期买入者的压力通常越大；若之后回升，只能说明这一群人的成本压力在缓解，仍要与 aSOPR 和已实现市值变化一起看。
- **限制：**155 天是通用持有人划分，三条统计参考线是本项目每日用当前历史重算的工具，不是固定行业标准线。
- **来源：**[Glassnode：STH-MVRV](https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/sth-mvrv)。

## 2. 全网账面盈亏

### PSIP（盈利供应占比）

- **公式：**`Supply in Profit / Total Supply`。
- **为什么有用：**它显示有多少 BTC 的当前价格高于其上次移动时的价格，是观察全网盈利覆盖面的直接方法。
- **普通人怎么用：**把它理解为“每 100 枚币中，有多少枚目前是赚钱的”。数值变低代表处于浮亏的币变多，说明全网压力更广；数值变高代表盈利覆盖面扩大。它只说明账面状态，不说明这些币会不会卖。
- **限制：**SIPL、Seller Exhaustion 与它共享供应盈亏事实，不能把它们当作彼此独立的证据。
- **来源：**[Glassnode：Percent Supply in Profit](https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/percent-supply-in-profit)。

### SIPL（盈利／亏损供应）

- **公式：**`盈利占比 = Supply in Profit / Supply`；`亏损占比 = Supply in Loss / Supply`；`差额 = 盈利占比 − 亏损占比`。
- **为什么有用：**它把 PSIP 的另一面直接展示出来，方便看盈利币和亏损币谁更多。
- **普通人怎么用：**把它理解为“赚钱的币和亏钱的币，哪一边更多”。差额为负说明亏损供应更多；它只是帮助理解供应盈亏的构成，不是一条额外的独立信号。
- **限制：**这是当前 16 项基线中的历史说明。v0.4.2 计划从活动产品集合中删除它，保留 PSIP 作为同一现象的主要入口。
- **来源：**[Glassnode：Profit/Loss (Supply)](https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply)。

### Relative Unrealized Profit（相对未实现盈利）

- **公式：**`Unrealized Profit / Market Cap`。
- **为什么有用：**它衡量全网尚未卖出、但账面已经盈利的金额占市场价值的比例，可观察潜在获利了结压力。
- **普通人怎么用：**把它理解为“全网还没卖、但账面已经赚到的钱有多少”。数值低说明可兑现的账面利润较少；数值高说明账面浮盈更充足。它反映的是“手上可能赚了多少”，不是已经发生的卖出。
- **限制：**与 PSIP、RUL 同属供应盈亏背景，应合起来解释，不应重复计数。
- **来源：**[Glassnode：Unrealized Profit](https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-profit)。

### RUL · 4 年 z-score（相对未实现亏损）

- **公式：**原始 `RUL = Unrealized Loss / Market Cap`；面板以 `RUL = RUP − NUPL` 推导，再显示`(当日 RUL − 过去 1460 日均值) / 过去 1460 日总体标准差`。
- **为什么有用：**原始 RUL 衡量全网尚未卖出的账面亏损；z-score 把它换成“相对过去四年是否异常”的尺度，便于观察压力深度。
- **普通人怎么用：**把它理解为“今天全网被套得有多严重，和过去四年的通常水平相比”。数值越高，表示账面亏损相对自身历史越突出；这是深度压力的背景证据，不能单独证明筑底完成。
- **限制：**4 年 z-score 和阈值是本项目的标准化处理，不是原始 RUL 的统一固定规则。
- **来源：**[Glassnode：Unrealized Loss](https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-loss)、[NUPL 定义](https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/nupl-net-unrealized-profit-loss)。

## 3. 实际换手、投降与修复

### Realized Cap Relative NPC · 30d

- **公式：**`Realized Cap(t) / Realized Cap(t−30d) − 1`。
- **为什么有用：**已实现市值会在币真正换手时按新的价格记录成本；它的月度变化能反映这种“资金账本”在扩张还是收缩。
- **普通人怎么用：**把它理解为“最近一个月，真正换手后留在链上的资金账本是在增加还是减少”。由负转正或持续改善可作为修复背景；仍不能只凭它宣布市场已经走出压力。
- **限制：**30 日变化是项目派生指标，不是独立熊底证明。
- **来源：**[Glassnode：Realized Capitalization](https://docs.glassnode.com/guides-and-tutorials/metric-guides/realized-capitalization)。

### aSOPR

- **公式：**`花费输出在花费时的美元价值 / 创建时的美元价值`，并排除寿命少于 1 小时的输出。
- **为什么有用：**它看当天真正换手的币总体是在实现盈利还是亏损；剔除找零和中继交易后，噪声较少。
- **普通人怎么用：**把它理解为“今天真正卖出去的币，平均是赚着卖、亏着卖，还是回本卖”。低于 1 表示当天实现亏损较多；持续低于 1 说明投降压力仍值得关注。面板的 3／7 日均线只为看趋势，不能替代原始值触发。
- **限制：**单日换手会有噪声；实现亏损加大不等于已完成筑底。
- **来源：**[Glassnode：SOPR](https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/sopr-spent-output-profit-ratio)、[aSOPR](https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/asopr-adjusted-sopr)。

### HODLer NPC · 30d

- **公式：**`[Hodled or Lost Supply(t) − Hodled or Lost Supply(t−30d)] / Supply`；面板仅显示 `MVRV < 1` 的日期。
- **为什么有用：**它观察长期不动／冷存储供应在一个月内的净变化，补充了解长期持有人是在积累还是减少。
- **普通人怎么用：**把它理解为“长期被拿着不动的币，这个月是在变多，还是被拿出来卖了”。低估期中负值表示长期不动供应减少，正值表示积累；它应被当作投降或承接的背景，而不是独立确认。
- **限制：**只保留 `MVRV < 1` 是本项目为了避免把高位派发混入低估期行为的过滤。该指标当前仅展示，数据较旧时不参与状态判断。
- **来源：**[Glassnode：量化 BTC 持有人供应](https://research.glassnode.com/quantifying-bitcoin-hodler-supply/)。

### ≥155d 花费价值占比

- **公式：**`花费价值中币龄 ≥155 天的部分 / 全部花费价值`；面板仅显示 `MVRV < 1` 的日期。
- **为什么有用：**它观察老币在当天花费价值中的比例，可补充长期持有人是否变得活跃。
- **普通人怎么用：**把它理解为“今天被花掉的币里，有多少价值来自放了至少五个月的老币”。低估期中占比升高，说明老币活动增多；它需要和 aSOPR 等实际盈亏证据一起看，不能直接称为亏损卖出。
- **限制：**155 天是持有人分类的常用边界；“占比、低估期过滤和历史分位”都是项目处理。该指标当前仅展示，不独立触发状态。
- **来源：**[Glassnode：155 天持有人方法](https://research.glassnode.com/quantifying-bitcoin-hodler-supply/)、[Open Bitcoin Metrics 原始序列](https://github.com/diegorllanos/open-bitcoin-metrics/tree/main/metrics/obm_spent_value_ge155d_btc_daily)。

### Seller Exhaustion Constant

- **公式：**`PSIP × 30 日价格波动`。
- **为什么有用：**它同时要求盈利供应偏低和市场波动收缩，试图观察卖方压力是否正在被消化。
- **普通人怎么用：**把它理解为“很多币还没回本，同时价格已经不怎么大起大落”。数值较低可作为“卖方可能接近耗尽”的线索；必须与实际亏损、矿工压力等不同维度交叉阅读。
- **限制：**它复用 PSIP，不能与 PSIP 独立计票；低波动不代表市场一定反转。
- **来源：**面板按上述公开基础字段自行计算；[Glassnode 指标目录](https://docs.glassnode.com/basic-api/endpoints/indicators)提供同名指标序列。

## 4. 矿工压力

### Puell Multiple

- **公式：**`当日矿工新发币美元收入 / 该收入的 365 日平均值`。
- **为什么有用：**矿工有持续的设备、电力和运营成本。收入相对一年均值偏低时，矿工财务压力可能上升，是与投资者成本不同的一条证据维度。
- **普通人怎么用：**把它理解为“矿工今天新挖币赚的钱，和过去一年平均比有多少”。数值越低，矿工收入压力通常越大；它有助于判断压力是否不仅发生在投资者一侧。
- **限制：**减半会机械性减少新发币收入，不能把每次低值都解释成市场突然恶化；它不能单独定位底部。
- **来源：**[Glassnode：Puell Multiple](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-issuance/puell-multiple)。

### Thermocap Multiple · 周期 z

- **公式：**原始倍数为 `Market Cap / 累计矿工补贴美元价值`；面板显示 `log(原始倍数)` 的 1460 日滚动 z-score。
- **为什么有用：**它把市场总估值放在历史矿工累计获得的网络安全补贴背景下，用于观察当前周期相对自身是偏冷还是偏热。
- **普通人怎么用：**把它理解为“市场现在给比特币的总估值，和矿工长期累计获得的报酬相比处在什么位置”。较低的周期 z-score 表示相对自身过去四年更冷；它是矿工压力的背景补充，不是矿工当天利润率。
- **限制：**log 与 4 年 z-score 是项目变换，目的是降低减半和长期累积造成的结构漂移；不能直接套用原始倍数的固定线。
- **来源：**[Glassnode：Thermocap 的周期背景说明](https://research.glassnode.com/the-week-on-chain-week-38-2021/)。

## 5. 长期成本锚与持币信念

### CVDD 接近程度

- **公式：**`CVDD = 累计(CDD × Price) / (市场存续天数 × 6,000,000)`；面板显示 `1 / |Price / CVDD − 1|`。
- **为什么有用：**CVDD 使用老币被花费时消耗的“币天”，构造长期成本／底部参考线。面板把距离取倒数，方便直接表示“接近程度”。
- **普通人怎么用：**把它理解为“把老币长期没动的时间价值算进去，得到一条长期底部参考线；数字越大，说明当前价格越靠近它”。它只说明接近长期参考区，不能预测价格一定会在这里停止下跌。
- **限制：**`6,000,000` 是该原始图表版本的校准常数；“接近程度”倒数与页面阈值是项目变换，不能与其他 CVDD 版本混用。
- **来源：**[Willy Woo：CVDD 原始说明](https://woobull.com/experiments-on-cumulative-destruction/)。

### Reserve Risk · 周期 z

- **公式：**原始 `Reserve Risk = Price / HODL Bank`；面板显示 `log(Reserve Risk)` 的 1460 日滚动 z-score。
- **为什么有用：**价格越高，持有人越有动机卖；长期持有人选择不卖所累积的机会成本称为 HODL Bank。这个指标比较“卖出的诱因”和“坚持持有的信念”。
- **普通人怎么用：**把它理解为“现在的价格有多诱人卖出，相比长期持有人一直不卖所积累的信念有多强”。较低的周期 z-score 代表相对本周期更低的数值，可作长期压力／承接背景；需要与其它维度共同解释。
- **限制：**HODL Bank 是长期累积量，原始数值会跨周期漂移；因此面板使用 log 与 4 年 z-score。不要把原始 Reserve Risk 的固定线直接套到面板 z-score 上。
- **来源：**[Glassnode：Reserve Risk](https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-days-destroyed/reserve-risk)。

## 使用底线

1. 先看面板给出的两个市场状态，再用指标卡核对理由；不要把单项指标当作最终结论。
2. 同一类指标只回答同一个问题的不同侧面：MVRV／AVIV、PSIP／SIPL／Seller Exhaustion 都不应被重复计算成多份独立证据。
3. 数值、阈值和数据日期必须一起看。数据缺失、过期或仅供展示时，不能把它解释为支持或反对证据。
4. “压力很深”和“已经形成可持续筑底”不是同一句话。前者可以由成本、亏损或矿工压力说明；后者还需要不同维度的相互支持与后续修复过程。
