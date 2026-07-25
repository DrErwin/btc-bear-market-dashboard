# Bitcoin 熊市指标可实现性事实清单

更新时间：2026-07-22

## 本文只保留什么

本文是系统完全重建后的唯一事实底稿，只记录已经核查为**可以取得数据并展示，或可以用公开输入自行计算**的指标。

本文不保留旧系统的指标家族、代表关系、评分、权重、阈值、状态机、历史评级、验证优先级、页面结构或产品决策。后续系统设计不得把这里的排列顺序解释成优先级，也不得把“可实现”解释成“适合计分”或“已经证明能稳定识别熊底”。

“已验证可实现”在本文中的含义是以下至少一项成立：

- 已确认存在可持续读取的公开日线；
- 已确认公开基础输入足够，公式可以确定性复算；
- 已确认本地已有方法能够生成该指标，并且数据字段、单位和日期语义可以说明。

## 已验证可实现的指标

| 指标 | 可实现方式 | 已确认的数据或计算路线 | 必须保留的事实边界 |
| --- | --- | --- | --- |
| MVRV | 直接读取或自行计算 | Coin Metrics `CapMVRVCur`；Bitview；也可用 `Market Cap / Realized Cap` | 自算时必须使用同一 UTC 日、同一价格口径的市值与已实现市值 |
| AVIV（ARK × Glassnode 原始定义） | 自行计算 | Bitview `market_cap`、`liveliness`、`realized_cap`、`subsidy_cumulative_usd`；公式为 `(market_cap × liveliness) / (realized_cap - subsidy_cumulative_usd)` | Bitview 成品 `aviv_ratio`不是这一公式，不能作为原始 AVIV 的替代 |
| Puell Multiple | 直接读取或自行计算 | Bitview 成品日线；或用 Coin Metrics `IssTotUSD`除以其 365 日均值 | 不同发行收入定价和日期口径会产生可见差异，展示时应标明方法来源 |
| Realized Cap Relative Net Position Change（30 日） | 直接读取或自行计算 | Bitview `realized_cap_delta_1m_rate_ratio`；或由 Realized Cap 计算 `(RC_t - RC_t-30) / RC_t-30` | 这是 BRK 分母口径；不能静默标成使用当日 `RC_t`作分母的其他版本 |
| Realized Cap Net Position Change（7 日） | 直接读取或自行计算 | Bitview `realized_cap_delta_1w`及相对变化序列；或由 Realized Cap 日线计算 7 日差值/比率 | 必须明确展示的是绝对差值、相对变化，还是其他序列的 7 日均线 |
| STH-MVRV | 直接读取 | Bitview `sth_mvrv` | 已确认路线采用 BRK `<150 天`UTXO cohort；不能标成 Glassnode `<155 天`实体调整口径 |
| aSOPR | 直接读取 | Bitview `asopr_24h` | 指标排除寿命小于一小时的花费输出；日期按来源 UTC 日语义处理 |
| HODLer Net Position Change | 自行计算 | Bitview `hodled_or_lost_supply`的 30 日历日差值 | 这是由项目计算的差值，不应表述成来源直接提供的成品净头寸指标 |
| 长币龄花费价值占比 | 直接读取 | 公开 UTXO 年龄分组花费序列，可形成 `>=150d`；若取得同口径数据也可形成 `>=155d` | 150 日与155日必须拆成不同方法版本，不能静默互换 |
| Percent Supply in Profit（PSIP） | 直接读取或自行计算 | Bitview `supply_in_profit_share_ratio`；也可由 UTXO 成本基础统计盈利供应占比 | 与 Supply in Profit/Loss 双线是同一底层事实的不同表达 |
| Supply in Profit / Supply in Loss（SIPL） | 直接读取或自行计算 | Bitview `supply_in_profit`、`supply_in_loss`；也可由 UTXO 成本基础分类求和 | 在覆盖完整时两者近似互补；交错点近似等价于 PSIP 穿越 50% |
| Relative Unrealized Profit（RUP）及统计带 | 基础值直接读取；统计带自行计算 | Bitview `unrealized_profit_to_mcap_ratio`；均值、标准差或 z-score 由该日线计算 | 统计带没有唯一公式；扩展窗口、滚动窗口、预热期和标准差定义必须显式版本化 |
| CVDD 及价格接近程度 | 自行计算 | 可按固定 600 万校准常数的原始累计 CDD 美元价值公式计算 CVDD；接近程度可算 `Price / CVDD - 1` | 600 万常数版与供应归一化版不是同一指标，必须分别命名 |
| 全链 LTH/STH Realized Profit/Loss | 直接读取 | Bitview/BRK 的全链 UTXO cohort 已实现利润与亏损日线，包括 STH/LTH profit/loss sum | 已确认的是全链 150 日 cohort，不是“转入交易所”子集，也不是专有实体调整序列 |
| Normalized Net Realized Profit/Loss | 自行计算 | `(realized_profit_sum_24h - realized_loss_sum_24h) / market_cap`；所需 Bitview 日线均已确认可读 | 必须固定利润、亏损的符号约定以及市值日期；不可只比较未归一化美元峰值 |
| Reserve Risk | 直接读取；具备公开复算实现 | Bitview `reserve_risk`；BRK 有公开源码和所需 coin-days/HODL Bank 计算链 | 不同 VOCDD 平滑和 HODL Bank 实现可能形成不同版本，必须绑定具体源码版本 |
| Seller Exhaustion Constant | 直接读取或自行计算 | Bitview `seller_exhaustion`；也可按 `PSIP × 30 日价格波动率`计算 | 必须固定30日波动率的收益定义、样本口径和年化方式 |
| Thermocap Multiple | 直接读取或自行计算 | Bitview `thermo_cap_multiple`；也可计算 `Market Cap / subsidy_cumulative_usd` | Thermocap 应使用累计矿工补贴美元价值；不能混入手续费后仍沿用同名公式 |

## 数据来源事实

- 上表涉及的 Bitview/BRK 指标及基础日线已经完成可访问性核查。
- Coin Metrics Community 可提供 MVRV、发行收入以及重建 Realized Cap 所需的公开数据路线。
- 自行运行完整 BRK 计算链需要 Bitcoin Core、历史价格与较大的本地索引；使用托管 Bitview 日线不需要在网站侧运行完整节点。
- “数据可公开读取”不自动等于允许任意原始数据再分发。后续系统若收费、提供下载或形成数据服务，需要重新核查来源条款。

## 本清单不作出的结论

- 不判断哪个指标应该成为核心指标。
- 不判断指标之间如何分组或聚合。
- 不保留旧系统的验证优先级。
- 不声明任何阈值能够预测最低价。
- 不把有限历史响应写成未来准确率。

后续重建设计应从本清单重新选择研究问题、证据关系和验证方法，不继承旧系统结构。
