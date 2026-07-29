# BTC 熊底证据看板：版本文档索引

本目录按版本保存需求、验证和开发资料，避免把已经验收的内容与下一版计划混在一起。

| 版本 | 状态 | 文档 | 使用方式 |
|---|---|---|---|
| `v0.1.0` | 历史版本（固定数据展示版） | [产品规格](v0.1.0/public-bear-bottom-evidence-dashboard.md) · [开发计划与验收](v0.1.0/phased-development-plan.md) · [指标验证记录](v0.1.0/indicator-validation-record.md) · [指标可实现性事实清单](v0.1.0/bear-market-indicator-expandability-research.md) · [上线记录](v0.1.0/deployment-record.md) | 最初的固定数据公开版本，现已由每日真实数据版本替代。 |
| `v0.2.0` | 已上线（每日自动更新） | [需求](v0.2.0/requirements.md) · [实现记录](v0.2.0/implementation-record.md) · [验收记录](v0.2.0/acceptance-record.md) | 完整数据包、AI 解释回退、图表时间轴/缩放、HODLer 投降柱状图、每天北京时间 12:00 自动更新与 GLM-5.2 分析。 |
| `v0.2.1` | 已实现 | [需求](v0.2.1/requirements.md) · [实现记录](v0.2.1/implementation-record.md) | 折叠左侧指标列、tier 三档红系配色、图表时间轴/缩放/十字、熊底虚线、价格对数坐标、柱状图按指标 id、核心/辅助标签配色。 |
| `v0.2.2` | 已实现 | [需求](v0.2.2/requirements.md) · [实现记录](v0.2.2/implementation-record.md) | 删除多余 eyebrow、修复图表内拖动平移时间窗、曲线开关合并进四项图例、纵坐标自适应时阈值线始终可见。 |
| `v0.2.3` | 已实现 | [需求](v0.2.3/requirements.md) · [实现记录](v0.2.3/implementation-record.md) | 图表高度可拖动并记忆、柱状图单绘图区底部叠加、删除图表说明、观察区改为文字颜色。 |
| `v0.2.4` | 当前公开界面版本记录 | [需求](v0.2.4/requirements.md) · [实现记录](v0.2.4/implementation-record.md) · [图表配置](v0.2.4/btc-indicator-config-2026-07-28.json) | 图表参考线、多曲线、3 日／7 日平滑线、曲线开关与自适应纵轴；本版本只记录图表层。线上数据契约现场核对仍为 `0.2.0`。 |
| `v0.3.0` | 历史版本（已被 v0.4.0 取代） | [体系设计](v0.3.0/indicator-evidence-system-design.md) · [工作计划](v0.3.0/indicator-evidence-system-work-plan.md) · [验收记录](v0.3.0/acceptance-record.md) | 建立指标角色、数据质量闸门和证据编译思路；其中单一 `allowed_stages` 阶段契约仅保留作历史记录。 |
| `v0.3.1` | 历史本地基线（已被 v0.4.0 取代） | [需求](v0.3.1/requirements.md) · [实现记录](v0.3.1/implementation-record.md) | 统一状态阈值与图表阈值；阈值数值、方向、顺序和人工三档含义由 v0.4.0 继续保留。 |
| `v0.4.0` | 本地已实现并验收，未部署 | [实施规格](v0.4.0/implementation-spec.md) · [实现记录](v0.4.0/implementation-record.md) · [验收记录](v0.4.0/acceptance-record.md) · [历史窗口验证](v0.4.0/lookback-validation.json) · [状态模型设计](v0.4.0/market-state-model-design.md) | 双轴市场状态（压力轴 + 筑底轴）、稳定档位身份、指标职责与相关性家族、有限时间线、前三个自然日上下文、六段详细解释和完整结果包。 |

## 版本规则

- `v0.1.0` 是最初的固定数据历史版本。
- `v0.2.0` 至 `v0.2.4` 记录每日更新和图表交互的演进；当前公开界面版本记录为 `v0.2.4`，线上数据契约仍为 `0.2.0`。
- `v0.3.0` 和 `v0.3.1` 是历史实现记录；其中的 `allowed_stages` 与旧单阶段输出不再是当前运行契约。
- `v0.4.0` 是当前本地运行基线，建立在既有指标派生和图表能力之上，但用压力轴与筑底轴替代单一总阶段。
- v0.4.0 的 `schema/config` 均为 `0.4.0`；公开线上版本仍需单独部署和核验，不能由本地验收自动推断。
- “本地已验收”不等于“已上线”；必须有提交、推送、部署和线上核验记录后才能改为已发布。
- 需要发布新的功能时，先更新对应版本的需求与验收标准，再修改代码。
