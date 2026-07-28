# BTC 熊底证据看板：版本文档索引

本目录按版本保存需求、验证和开发资料，避免把已经验收的内容与下一版计划混在一起。

| 版本 | 状态 | 文档 | 使用方式 |
|---|---|---|---|
| `v0.1.0` | 已上线（固定数据展示版） | [产品规格](v0.1.0/public-bear-bottom-evidence-dashboard.md) · [开发计划与验收](v0.1.0/phased-development-plan.md) · [指标验证记录](v0.1.0/indicator-validation-record.md) · [指标可实现性事实清单](v0.1.0/bear-market-indicator-expandability-research.md) · [上线记录](v0.1.0/deployment-record.md) | 当前公开版本，已部署但尚未接入每日真实数据与 AI 自动更新。 |
| `v0.2.0` | 已实现（待配置 Secret 后首次自动更新上线） | [需求](v0.2.0/requirements.md) · [实现记录](v0.2.0/implementation-record.md) · [验收记录](v0.2.0/acceptance-record.md) | 完整数据包+整包回退、图表时间轴/缩放、HODLer 投降柱状图、每日自动更新管线与 GitHub Actions。 |
| `v0.2.1` | 待开发 | [需求](v0.2.1/requirements.md) | 看板可折叠、tier 三档观察区命名、柱状图归入图表内部并解耦指标切换、鼠标移动时间轴、熊底虚线+悬浮十字读数。 |

## 版本规则

- `v0.1.0` 记录当前已上线的固定数据版本；只修正文档错误，不在其中新增下一版功能。
- `v0.2.0` 承载下一版需求、设计、实施计划和验收证据；未实现内容不得写成当前能力。
- 需要发布新的功能时，先更新对应版本的需求与验收标准，再修改代码。
