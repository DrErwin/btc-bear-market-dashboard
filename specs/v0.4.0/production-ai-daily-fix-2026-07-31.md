# v0.4.0 生产 AI 日更修复记录（2026-07-31）

> 状态：已修复、已推送、已通过真实 GLM-5.2 日更和线上部署验证。

## 1. 用户影响

网站一度显示 2026-07-28 的 AI 判断。排查确认基础数据、价格和图表已经更新到 2026-07-30，停留在 28 日的是安全回退的上一份 AI 解释，并非浏览器缓存、Cloudflare 缓存或数据抓取整体停止。

系统没有发布未通过校验的 AI 文字，但当时 GitHub Action 仍显示绿色，用户难以区分“完整成功”和“已发布安全回退”。

## 2. 根因

本次问题由三层原因叠加：

1. 2026-07-29 的成功日更包随后被本地 fixture 提交覆盖回 2026-07-28，导致下一次失败只能回退到更旧结论。
2. 生产 Prompt 没有明确列出分类状态只能为“未确认／部分确认／充分确认”，GLM-5.2 使用“修复中／数据不足／部分触发”等近义词后被校验器拒绝。
3. 第一轮修复后，Prompt 虽提供每项阈值事实，但没有把“支持段落可引用的指标”单独展开为醒目的白名单；模型仍把未触发的 MVRV 写入支持文字。

## 3. 实际代码改动

| 模块 | 改动 | 业务作用 |
|---|---|---|
| `services/ai/provider.py` | Prompt 直接复用 `CATEGORY_STATUS_VALUES`；分类状态禁止改写和使用近义词 | 避免模型输出校验器不接受的第四种分类状态 |
| `services/ai/input_builder.py` | 每个指标新增 `support_eligible` | 明确区分“当前可作为支持事实”和“只能作为缺口/待观察”的指标 |
| `services/ai/provider.py` | Prompt 展开支持指标白名单与禁用名单；未触发指标只能进入 `contrary_or_gaps` 或 `next_evidence` | 防止未触发指标被写成当前支持证据 |
| `services/ai/provider.py` | 保持模型为 GLM-5.2，将温度从 `0.2` 调整为 `0` | 降低固定 JSON 和固定词汇任务中的随机偏离 |
| `scripts/automation_health.py` | 新增生产数据日期倒退检查和日更结果健康检查 | 识别旧 fixture 覆盖生产包，并区分完整成功与安全回退 |
| `.github/workflows/packet-regression.yml` | 在拉取请求或 `main` 推送修改生产包时检查 `data_date` | 日期倒退会使 CI 失败并显示原因 |
| `.github/workflows/daily-update.yml` | 提交数据包后检查最后一次 `outcome` | `published-fallback` 或 `skipped` 会把任务标红，不再以绿色掩盖降级 |
| `tests/acceptance/test_ai_contract.py` | 覆盖分类状态词汇、首次请求/重试、支持白名单和禁用名单 | 锁定这次真实 Prompt 缺口 |
| `tests/acceptance/test_v03_ai_boundary.py` | 覆盖 `support_eligible` 和输入边界 | 保证未触发指标不会被标记为支持事实 |
| `tests/acceptance/test_automation_health.py` | 覆盖日期倒退、回退、跳过、完整发布和分轴数据不足 | 锁定自动化健康状态语义 |

这些改动没有引入指标计分、允许状态子集或机器多数票；压力轴和筑底轴仍由 GLM-5.2 在固定词汇内独立判断。

## 4. 提交与真实运行

修复按三个可追溯提交快进推送到 `main`：

- `d1e26ab fix: constrain daily AI category states`
- `8df71cf fix: restrict AI support to triggered evidence`
- `1aa74f9 fix: give AI an explicit support whitelist`

前两次真实运行继续发现语义问题时，系统都发布安全回退包，并由新增健康检查正确标红；没有把错误分析发布成当天结论。

第三次真实任务 [30575192669](https://github.com/DrErwin/btc-bear-market-dashboard/actions/runs/30575192669) 的 GLM-5.2 调用、语义校验、前端构建、数据提交和健康检查全部通过，最终结果为 `published-fresh`。

## 5. 验证结果

- Prompt 与输入边界的针对性回归测试：`32 passed`。
- 前端生产构建：通过；保留原有 Vite 大包提示。
- 真实 GitHub Action：`completed / success`。
- 公开首页：HTTP 200。
- 公开 `/data/packet.json`：HTTP 200。
- 最终线上包：
  - `run_id=20260730T193140Z`
  - `data_date=2026-07-30`
  - `analysis_date=2026-07-30`
  - `today_available=true`
  - `reason=null`

线上双轴结果为“压力尚未明显／筑底线索出现”，一致性为“弱”。这里只记录已发布结果，不扩展为价格、仓位、杠杆或交易建议。

## 6. 后续维护

- 若要真正阻止直接推送绕过检查，需要在 GitHub 分支保护中把 `packet-regression / check` 设为必需检查；仓库内工作流只能在推送后标红。
- 旧验收中仍有一项图表配置哈希绑定到每日变化的生产包，后续应改用固定 fixture，避免正常日更造成与 Prompt 修复无关的基线失败。
- 后续日更必须同时检查 GitHub Action 结论和线上包的 `data_date`、`analysis_date`、`today_available`、`reason`，不能只看任务是否启动。

## 7. 2026-08-03 方向关键词检查暂停

2026-08-02 的日更已成功生成并部署基础数据，但 GLM-5.2 在最多三次生成后仍没有通过全部语义校验。公开包显示 `data_date=2026-08-02`、`analysis_date=2026-08-01`、`today_available=false`，最终错误为 Seller Exhaustion Constant 和 Reserve Risk · 周期的文字被识别成“高于”，而当天触发事实为 `below`。

现有实现会把支持区域的多段文字拼接后，直接搜索“高于、低于、高位、低位、上穿、下穿、升入、跌入”等词。由于失败记录没有保存完整原句，无法排除“并未高于”一类否定语境被误判。经确认，本阶段只暂停这项方向关键词扫描；其他事实、边界和结构检查继续生效，三次生成与失败回退机制保持不变。

具体范围和恢复条件见 [阈值方向关键词检查暂停设计](threshold-direction-keyword-check-pause-2026-08-03.md)。
