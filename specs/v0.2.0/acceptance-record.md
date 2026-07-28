# v0.2.0 — 验收记录

> 所有验收于 2026-07-28 跑通；首次真实 AI 自动更新已由 GitHub Actions 完成，并经 Cloudflare 生产地址核验。

## 验收总览

| 验收项 | 命令 | 结果 |
|---|---|---|
| v0.1.0 网页验收回归 | `python tests/acceptance/run_acceptance.py` | **ACCEPTANCE PASS**（success/fallback/no-fallback/responsive/keyboard/受限语言） |
| 数据包契约 + 回退 | `python -m pytest tests/acceptance/test_packet_contract.py -q` | **21 passed** |
| AI 契约 + 输入边界 | `pytest tests/acceptance/test_ai_contract.py tests/acceptance/test_input_boundary.py` | **15 passed** |
| 真实数据 parity | `python scripts/verify_pipeline.py` | **PARITY OK**（16 指标与原型逐位一致） |
| 数据包组装 + 契约往返 | `python scripts/test_packet.py` | **PACKET BUILD + CONTRACT OK** |
| 整包回退（fresh→fallback） | `python services/run_daily.py`（mock-ai，再跑无 key） | published-fresh → published-fallback，archive 生成 |
| 前端构建 | `cd dashboard && npm run build` | vue-tsc 无错，583 模块，built ✓ |

## 需求一验收

- **单一数据包**：前端 `useDashboardData.ts` 只读 `/data/packet.json`（`?fixture=` 仅切换读哪份完整包），契约要求 snapshot/series/bars/analysis/status 齐全。
- **拒绝残缺/不一致**：`test_packet_contract.py` 覆盖缺 snapshot/series/bars/status、metric 数量错、snapshot_date/series 末点/analysis_date 与 data_date 不一致、today_available 与 analysis 在场矛盾。
- **拒绝 AI 不合规**：analysis/fallback 注入“建议买入”“熊底概率为 78%”均被 `validate_packet` 拒绝。
- **整包回退**：`run_daily` 先 `published-fresh`（run_id A），再以无 key 重跑得 `published-fallback`（run_id B）：B 的 `analysis=null`、`fallback` 保留 A 的 stage、`last_success_date` 不变；归档目录生成 `2026-07-27.json`。run-log 两行可追溯。
- **原子发布**：`test_write_atomic_rejects_invalid` 验证无效包不写文件。

## 需求二验收

- SharedChart 双轴主图 + 下方柱状图共用 dataZoom；6 月/1 年/2 年/4 年/全量预设 + 当前可见范围文本。
- `useChartOption.bounds()` 对可见切片重算 y 轴 min/max；缩放后阈值线随主图同步。
- v0.1.0 responsive 流程（390px 不溢出、阶段点完整落视口）继续通过。

## 需求三验收

- bars grid 两个独立系列（HODLer NPC · 30d、≥155d 花费价值占比），各自 label/单位/来源/口径/质量提示（`bars-meta` + tooltip）。
- 柱体仅在低估期（MVRV<1）有值日出现；缺失日不补齐，零分母不写入。
- `verify_pipeline` 显示两 bar 各 766 个低估期日。

## 需求四验收

- **管线**：`verify_pipeline` 用真实 Bitview + OBM 抓取，16 指标 latest_value 与原型 `build_data.py` 逐位匹配（rel=0）。
- **AI 边界**：`test_ai_contract.py` 验证固定词汇表、拒绝禁止措辞与缺失字段；`test_input_boundary.py` 验证 AI 输入只含白名单字段、剥离 series/来源/历史。
- **回退**：`test_provider_no_key_returns_none` / `test_api_key_never_leaks_in_reason` 验证无 key 与失败原因不含密钥。
- **自动纠错**：`test_invalid_ai_wording_is_rewritten_once_before_fallback` 验证首次文案出现禁止词时会完整重写一次，重写仍失败才回退。
- **阈值边界**：`test_input_builder_excludes_neutral_chart_reference_lines` 验证图表中性线不会进入 AI 的触发阈值清单。
- **workflow**：`.github/workflows/daily-update.yml` 每日北京时间 12:00 + 手动触发，密钥仅来自 Secret，`npm run build` 验证后才 commit。
- **日期一致**：`run_daily` 新鲜度检查（`>max-stale-days` 则 skipped），`validate_packet` 强制 analysis_date == data_date。

## 后续 / 边界

- 首次真实运行：GitHub Actions run `30349577265` 成功；生成 `run_id=20260728T100901Z`，`data_date=analysis_date=2026-07-28`，GLM-5.2 输出 `stage=熊市下行期`、`today_available=true`。
- 自动提交 `efaf58f` 触发 Cloudflare Workers Builds 成功；公开 `/data/packet.json` 返回同一 `run_id`，证明数据、AI 结论与线上版本一致。
- `packet-failure.json` / `packet-no-fallback.json` 为固定验收 fixture，不随每日更新改变。
- 历史 packet 归档在 `artifacts/packet-archive/`（最近 7 份，不进 git）。
