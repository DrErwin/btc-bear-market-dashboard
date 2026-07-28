# v0.3.0 指标证据体系验收记录

日期：2026-07-28  
版本：`0.3.0`

## 已完成的产品行为

- 16 项指标继续全部展示；角色改为核心锚、核心复核、强辅助、辅助。
- MVRV 与 AVIV 共用估值维度，AVIV 只做复核；Puell 是独立矿工压力维度。
- HODLer NPC、`>=155d` 花费价值占比在当前数据状态下标为仅供展示；CVDD 标为待验证。
- MVRV/Puell 任一关键锚缺失或过期时，系统生成“数据不足”状态且不调用 AI。
- 机器生成 `allowed_stages`；AI 输出必须在允许范围内。
- 强辅助主题进入 `pressure_summary`，解释阶段内部压力，但不能抬高核心阶段上限。
- AI 输入改为证据简报，不携带图表历史、来源元数据、公式或密钥。
- 页面显示角色、数据状态、过期原因和普通人可读的综合解释；详细区分核心依据、压力补充、相反证据、下一阶段条件和数据限制。
- 三个离线数据包已迁移到 schema/config `0.3.0`，保持整包回退结构。

## 机器验收证据

| 入口 | 结果 |
|---|---|
| `python -m pytest -q` | `95 passed` |
| `cd dashboard; npm run build` | TypeScript 检查与 Vite 构建通过；仅有既有 bundle 大小警告 |
| `python tests/acceptance/run_acceptance.py` | `ACCEPTANCE PASS`；构建、离线契约、Playwright 桌面/移动检查全部通过 |
| `python scripts/test_packet.py` | 真实数据抓取、v0.3 数据包组装、原子写入和日期契约通过 |
| `python services/run_daily.py --mock-ai --packet-path artifacts/_v03_run_packet.json ...` | `published-fresh`；输出包的 schema/config 为 `0.3.0` |
| `python scripts/verify_ai_explanations.py` | 10 个固定场景，`failures=[]`，当前环境使用可复现 mock 模式 |

验收产物目录：`artifacts/review-evidence/v0.3.0/`。其中 `ai-explanations.json` 保存脱敏证据简报、允许阶段、AI 输入摘要和输出。

## 独立 AI 解释复核

按用户要求，AI 解读质量由独立子代理审查 `ai-explanations.json`，重点检查综合解释、强辅助压力说明、阶段越权、指标复述和普通人可读性。复审已确认五项检查全部通过，报告判定 **PASS**：`artifacts/review-evidence/v0.3.0/ai-explanations-subagent-review.md`。

本机未配置 `AI_API_KEY`，因此未执行真实远程模型调用；`scripts/verify_ai_explanations.py --real` 已保留为有密钥环境的同一质量门入口，密钥不会写入产物。

## 发布边界

本记录证明本地 v0.3.0 实现、迁移和验收完成。Cloudflare/GitHub 线上发布仍需在目标发布环境执行，并再次核对公开包的 `config_version=0.3.0`、页面数据状态和回退目标。
