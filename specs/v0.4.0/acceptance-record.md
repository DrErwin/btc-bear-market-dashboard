# v0.4.0 — 验收记录

## 验收入口

主入口是 `python tests/acceptance/run_acceptance.py`。它把“每日完整结果包 → 页面读取同一结果包”作为主验收接缝，并依次执行 Python 契约、前端生产构建和浏览器场景。

## 结果

| 检查 | 结果 |
|---|---|
| `python -m pytest -q` | `73 passed` |
| `cd dashboard; npm run build` | 通过；仅有既有 Vite bundle 大小提示 |
| `python tests/acceptance/run_acceptance.py` | 通过 |
| success 结果包 | 双轴状态、指标阈值、六段解释正确显示 |
| fallback 结果包 | 明确显示当日 AI 失败并保留 v0.4 上次成功解释 |
| no-fallback 结果包 | 明确显示没有可用的上次成功解释 |
| 390px 移动端 | 页面无横向溢出，双轴和详细解释可读 |
| partial／both-axis fixture | 分轴数据不足和双轴数据不足均明确显示，其他事实仍保留 |
| CVDD 状态 | 长期成本锚分类中显示“当前可用”并使用当前可用颜色，不显示验证提示 |
| 键盘操作 | 详细分析按钮可聚焦并用 Enter 展开 |
| 旧 v0.3 字段 | `stage`、`allowed_stages` 和旧单阶段分析被拒绝 |

## 验收边界

- 测试使用固定夹具和 `--mock-ai`，验证的是数据契约、边界和页面行为，不等同于真实远程模型认证。
- 本次验收不代表已部署、已公开发布或已完成第三方数据再分发授权审查。
- 浏览器复核图片位于 `artifacts/review-evidence/v0.4.0/`。
