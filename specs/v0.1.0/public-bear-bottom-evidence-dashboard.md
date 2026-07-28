# v0.1.0 — 公开 BTC 熊底证据与市场阶段看板

建议标签：`ready-for-agent`

## Problem Statement

普通用户很难同时理解 16 个 BTC 熊市指标。即使每个指标都有当前值和阈值，用户仍然需要自己判断哪些是核心证据、哪些只是辅助证据、不同类别是否相互支持，以及这些证据共同对应什么市场阶段。

用户需要的不是一个声称可以预测最低价的交易信号，而是一个公开、清晰、可以追溯理由的熊底证据看板：系统每天读取已经筛选和配置好的 16 个指标，由 AI 先归纳各指标分类的证据状态，再从固定的市场阶段中选择当前阶段，并说明支持证据、反面证据和进入下一阶段仍缺少的确认条件。

## Solution

建设一个桌面端优先、手机端可用的公开研究型看板。

页面首先使用一个紧凑的 AI 市场阶段评价区，横向排列当前阶段、一句话摘要和证据一致性。其下使用五阶段横向坐标轴标出当前所处位置，并用三块并列信息分别概括核心支撑、主要阻力和下一阶段条件。用户可以展开查看完整分析，但正常状态下不让 AI 区域占据过多首屏空间。

紧凑 AI 评价区下方是按照六个定义类别组织的 16 个指标看板。每个分类显示由 AI 判断的“未确认 / 部分确认 / 充分确认”状态；每个指标卡片显示名称、核心或辅助角色、当前值、当前进入的阈值档位和简短状态。桌面端使用紧凑分类网格，再以左侧指标列表和右侧公共图表组成检查区域。点击指标后，公共图表切换为“BTC 价格 + 所选指标 + 阈值线”，并同时展示指标含义、分类、角色、阈值解释、数据来源和限制。

AI 每天自动运行一次。它只读取本项目提供的阶段定义、分类状态定义、16 个指标的说明、分类、核心或辅助角色、当前值，以及带有含义说明的多档阈值。AI 不读取历史曲线、近期趋势、新闻或其他外部市场信息。当天分析失败时，页面明确显示“今日 AI 分析不可用”，并可以展示唯一保留的上一份成功结果，但必须标明它属于昨天或上一次分析，不能伪装成当天结论。

## User Stories

1. As a 公开访问者, I want to immediately see the current market stage, so that I can understand the dashboard conclusion without first reading 16 indicators.
2. As a 公开访问者, I want to see a one-sentence summary beside the stage on desktop and below it on mobile, so that I can quickly understand the main reason for the conclusion.
3. As a 公开访问者, I want to see three compact summaries for core support, the main obstacle, and the next-stage condition, so that I can grasp the most important evidence without opening the full analysis.
4. As a 公开访问者, I want to expand the detailed AI analysis, so that I can inspect the reasoning when I need more depth.
5. As a 公开访问者, I want the market stage to use one of the fixed stage names, so that the wording remains stable from day to day.
6. As a 公开访问者, I want to see whether evidence consistency is weak, medium, or strong, so that I understand how aligned the evidence categories are.
7. As a 公开访问者, I do not want to see an artificial probability such as “78% bottom probability,” so that I am not misled by false precision.
8. As a 公开访问者, I want the analysis to identify the evidence categories supporting the conclusion, so that I know which parts of the market are providing evidence.
9. As a 公开访问者, I want the analysis to name representative indicators, so that I can connect the conclusion to visible dashboard content.
10. As a 公开访问者, I want the analysis to distinguish core evidence from supporting evidence, so that many correlated supporting indicators do not appear stronger than independent core evidence.
11. As a 公开访问者, I want the analysis to include contrary or incomplete evidence, so that the conclusion does not look selectively argued.
12. As a 公开访问者, I want to see what confirmation is still needed for the next stage, so that I understand why the current conclusion has not been upgraded.
13. As a 公开访问者, I do not want the AI narrative to repeat every current value and threshold, so that the explanation remains readable.
14. As a 公开访问者, I want exact current values and threshold positions to remain visible on metric cards and charts, so that I can verify the AI explanation myself.
15. As a 公开访问者, I want indicators grouped by their six definition categories, so that I can understand the evidence structure rather than see an unrelated list.
16. As a 公开访问者, I want each category to show “未确认 / 部分确认 / 充分确认,” so that I can see how the overall stage was assembled.
17. As a 公开访问者, I want core indicators to be visually distinguishable from supporting indicators, so that their roles are clear.
18. As a 公开访问者, I want every metric card to show the current threshold tier, so that multiple thresholds are understandable as different evidence levels.
19. As a 公开访问者, I do not want a “distance to next tier” figure, so that the cards stay focused on the current evidence state.
20. As a 公开访问者, I want to click any metric card and update one shared large chart, so that I can inspect metrics without navigating among 16 separate charts.
21. As a 公开访问者, I want the selected metric card to remain visibly selected, so that I always know what the shared chart is displaying.
22. As a 公开访问者, I want the shared chart to display BTC price, the selected metric, and its configured threshold lines, so that I can compare market price with the evidence signal.
23. As a 公开访问者, I want the selected metric’s meaning next to the chart, so that I can understand it without leaving the page.
24. As a 公开访问者, I want to see the selected metric’s category and core/supporting role, so that I can place it within the evidence model.
25. As a 公开访问者, I want every threshold to have a plain-language label and meaning, so that the threshold values are not unexplained numbers.
26. As a 公开访问者, I want to see the metric’s data source and limitations, so that I can judge what the evidence does and does not prove.
27. As a 公开访问者, I want the page to use plain Chinese explanations, so that I do not need specialist knowledge to understand the main framework.
28. As a 手机访问者, I want the conclusion and analysis to remain readable in a single-column layout, so that I can use the dashboard on a small screen.
29. As a 手机访问者, I want the large chart to remain usable through a simplified or full-screen presentation, so that desktop interactions are not required.
30. As a 公开访问者, I want color to be accompanied by text labels, so that evidence status is not communicated by color alone.
31. As a 键盘用户, I want metric cards and analysis controls to be operable without a mouse, so that the dashboard remains accessible.
32. As a 公开访问者, I want a professional research-dashboard visual style, so that the product does not resemble a high-pressure short-term trading terminal.
33. As a 公开访问者, I do not want flashing alerts, “抄底” buttons, or buy/sell calls, so that the product boundary remains evidence interpretation.
34. As a 公开访问者, I want the page to state that it is not trading advice, so that the product promise is explicit.
35. As a 公开访问者, I want the same daily indicator snapshot to show the same saved analysis throughout the day, so that refreshing the page does not produce a different conclusion.
36. As a 公开访问者, I want the page to clearly report when today’s AI analysis is unavailable, so that a technical failure is not mistaken for a market conclusion.
37. As a 公开访问者, I want any fallback conclusion to be labeled as yesterday’s or the previous analysis, so that stale information is never presented as current.
38. As a 看板维护者, I want one automatic AI analysis run per day, so that the public dashboard updates without manual work.
39. As a 看板维护者, I want the public dashboard to be read-only, so that every visitor sees the same indicator and threshold framework.
40. As a 看板维护者, I want threshold changes to remain under private administrative control, so that public users cannot alter the market conclusion.
41. As a 看板维护者, I want the AI to receive only the approved 16-indicator snapshot and definitions, so that it cannot quietly introduce external evidence.
42. As a 看板维护者, I want malformed or incomplete AI output to be rejected, so that invalid analysis is not published.
43. As a 看板维护者, I want only the latest successful result retained for fallback, so that the product can recover from a daily failure without creating a user-facing history feature.
44. As a 产品审阅者, I want to reproduce the complete page from a fixed indicator fixture and controlled AI response, so that the agreed behavior can be verified automatically.
45. As a 产品审阅者, I want the same verification entry point to cover desktop and mobile layouts, so that responsiveness is part of acceptance rather than a later visual check.
46. As a 产品审阅者, I want failure and fallback states included in automated verification, so that the most trust-sensitive behavior is not left to manual testing.
47. As a 公开访问者, I want to see all five market stages on one horizontal progress axis with the current stage highlighted, so that I can understand the current position within the complete bear-market evidence sequence.
48. As a 公开访问者, I want the AI evaluation area to remain compact enough for the indicator dashboard to begin within the first desktop viewport, so that the main evidence is not pushed below excessive empty space.
49. As a 公开访问者, I want detailed analysis collapsed by default in the normal state, so that the indicator dashboard is not pushed down by information I have not requested.

## Implementation Decisions

- The product is a public “BTC 熊底证据与市场阶段看板.” It is not a bottom-price predictor, buy/sell signal, position-sizing tool, or personalized financial adviser.
- The selected normal-state layout is the compact hybrid direction validated in the wireframe:
  1. compact AI market-stage evaluation;
  2. five-stage horizontal progress axis;
  3. three summary blocks for core support, main obstacle, and next-stage condition;
  4. expandable detailed analysis;
  5. compact six-category indicator dashboard;
  6. left-side selected-category metric list and right-side shared chart;
  7. compact selected-metric explanation and public disclaimer.
- The AI evaluation header places the current stage, one-sentence summary, and evidence-consistency label in one horizontal desktop row. Evidence consistency must not occupy a separate full-width row on desktop.
- The five fixed market stages appear together on a horizontal progress axis. Earlier stages are visually completed, the current stage is explicitly highlighted, and later stages remain visible but inactive.
- The horizontal stage axis communicates sequence and current position only. It must not imply a numeric probability or a guaranteed forward progression.
- The normal-state AI evaluation area stays visually compact. On a representative desktop viewport, the beginning of the six-category indicator dashboard must be visible without scrolling.
- The three AI summary blocks display:
  - core supporting categories and representative core indicators;
  - the most important contrary or incomplete evidence;
  - the evidence condition required before moving to the next stage.
- Detailed supporting evidence, contrary evidence, and next-stage confirmation conditions remain available through one expand/collapse control.
- The fixed market-stage vocabulary is:
  - 尚未进入熊底观察期;
  - 熊市下行期;
  - 深度压力期;
  - 筑底证据积累期;
  - 熊底证据充分期;
  - 数据不足, which is a system judgment rather than a market phase.
- The fixed category-status vocabulary is:
  - 未确认;
  - 部分确认;
  - 充分确认.
- The fixed evidence-consistency vocabulary is:
  - 弱;
  - 中等;
  - 强.
- The AI makes both levels of judgment in one daily analysis: it first selects a status for each category and then selects the overall market stage.
- AI judgment is constrained to the fixed stage and category-status vocabularies. It cannot invent a sixth market phase or a fourth category status.
- The AI input contains only:
  - market-stage definitions;
  - category-status definitions;
  - metric name and plain-language meaning;
  - definition category;
  - core or supporting role;
  - current metric value;
  - every configured threshold, its direction, and its plain-language meaning.
- The AI does not receive chart series, historical values, recent trend summaries, threshold-duration fields, news, sentiment, price forecasts, or external market research.
- The system treats the provided 16-metric snapshot as the authoritative current input. This release does not ask the AI to reconcile differing source dates.
- The AI output must be structured and validated before publication. It contains:
  - selected overall market stage;
  - evidence-consistency level;
  - one-sentence summary;
  - one compact core-support summary;
  - one compact main-obstacle summary;
  - one compact next-stage-condition summary;
  - six category assessments;
  - supporting evidence explanation;
  - contrary or incomplete evidence explanation;
  - confirmation conditions for the next stage.
- AI reasoning names relevant categories and representative indicators and distinguishes core from supporting evidence. The prose does not need to repeat exact current values.
- AI reasoning cannot contain buy/sell instructions, entry prices, position sizes, leverage advice, or numeric bottom probabilities.
- Thresholds are multi-tiered where required. Every threshold has a semantic label and explanation; raw threshold numbers alone are insufficient.
- The current validated inventory contains 16 indicators across six definition categories:
  - 市场估值与成本基础: MVRV and AVIV as core indicators; STH-MVRV tactical price as supporting evidence.
  - 未实现盈亏与供应盈亏结构: PSIP, SIPL, Relative Unrealized Profit, and RUL four-year z-score as supporting evidence.
  - 已实现盈亏与链上资本流: Realized Cap Relative NPC 30d and aSOPR as supporting evidence.
  - 持有者行为与投降: HODLer Net Position Change 30d and ≥155d spent-value share as core indicators; Seller Exhaustion Constant as supporting evidence.
  - 矿工经济压力与矿工成本: Puell Multiple as a core indicator; cycle-normalized Thermocap Multiple z-score as supporting evidence.
  - 长期成本锚与持币信念: CVDD proximity and cycle-normalized Reserve Risk z-score as supporting evidence.
- Five core labels represent three independent core judgment dimensions:
  - market valuation and cost basis;
  - holder behavior and capitulation;
  - miner economic pressure.
- Indicators within the same core dimension can confirm one another but do not become separate independent votes. Supporting indicators can strengthen, weaken, or explain a core conclusion but cannot automatically replace missing core evidence.
- Each category header displays its AI-selected status. The indicator cards beneath it retain their own factual threshold state.
- The six category headers use a compact responsive grid. They provide category name and category status without repeating long analytical copy that already appears in the AI evaluation.
- Each metric card displays:
  - metric name;
  - core or supporting role;
  - current value;
  - current threshold tier;
  - a short factual status label.
- Metric cards do not display distance to the next threshold.
- One shared chart is used for all 16 indicators. Selecting a metric updates the chart and its explanation area; it does not create an inline chart for every card.
- The shared chart displays BTC price, the selected indicator, and the indicator’s configured threshold lines.
- The selected metric explanation contains its meaning, category, role, threshold semantics, data source, and known limitations.
- On desktop, the selected-category metric list sits beside the shared chart. The chart and metric explanation are vertically compact enough to preserve the dashboard’s overview-first character.
- The public dashboard and thresholds are read-only. Private administration or configuration is a separate concern and is not placed in the public interface.
- The AI analysis runs automatically once per day. Reopening or refreshing the page on the same day reuses the saved result rather than calling the model again.
- The product does not expose a daily judgment-history browser.
- The system may retain one previous successful analysis only as operational fallback. When today’s run fails, the page states that today’s analysis is unavailable and labels the fallback with its actual previous date.
- A successful current-day analysis replaces the previous public conclusion while maintaining only the minimal fallback needed for the next failed run.
- The visual direction is a professional research dashboard: calm dark surfaces are acceptable; gray, blue, and orange can express evidence strength; text labels must accompany color.
- The design avoids flashing alerts, aggressive red/green trading semantics, countdown pressure, and “buy the bottom” calls to action.
- The layout is desktop-first and mobile-readable. Mobile uses a single-column information order and a simplified or full-screen chart experience.
- On mobile, all five stage points and labels remain visible across the available page width without creating page-level horizontal overflow. The AI summary blocks stack vertically before the category dashboard.
- The first release is Chinese-language and uses plain explanations suitable for non-specialist public users.

## Testing Decisions

- The preferred verification seam is one highest-level public-dashboard acceptance flow. It starts from a fixed 16-indicator daily snapshot and a deterministic mock AI result, then verifies the external behavior visible to a user.
- The implementation must provide one machine-executable verification entry point that can run without public-network access, paid API calls, real AI credentials, or production data.
- Pass criteria for the main successful-state fixture:
  - the fixed overall stage is displayed at the top;
  - all five fixed stages appear on one horizontal progress axis and exactly one stage is marked current;
  - the evidence-consistency label and one-sentence summary are visible;
  - the three compact summary blocks for core support, main obstacle, and next-stage condition are rendered;
  - detailed analysis expands and collapses;
  - at a representative 1440 × 900 desktop viewport, the top edge of the six-category indicator dashboard is visible without scrolling;
  - all six category states are visible;
  - all 16 retained indicators appear under the correct categories;
  - core and supporting roles are distinguishable by text;
  - selecting each indicator updates the single shared chart and explanation;
  - the chart contains BTC price, selected metric data, and configured threshold lines;
  - no probability, buy/sell, entry-price, position-size, or leverage language is rendered.
- Pass criteria for the daily failure fixture:
  - the page states that today’s AI analysis is unavailable;
  - the previous successful result is shown only when available;
  - the previous result is labeled with its actual prior date;
  - the 16-indicator dashboard remains usable;
  - a missing previous result produces a clear unavailable state rather than invented analysis.
- Pass criteria for the AI-response contract:
  - only approved market stages, category states, and evidence-consistency values are accepted;
  - all six category assessments are required;
  - supporting evidence, contrary evidence, and next-stage confirmation conditions are required;
  - unknown indicator names, missing required sections, or forbidden trading-advice fields reject the result and activate failure handling.
- Pass criteria for the input boundary:
  - the generated AI request contains the agreed definitions, roles, current values, and thresholds;
  - it contains no historical series, trend fields, news, external research, or user portfolio information.
- Pass criteria for responsive behavior:
  - the complete conclusion and analysis remain readable at a representative desktop viewport;
  - the same information remains available in a representative mobile viewport without horizontal page overflow;
  - all five stage points remain visible at a representative 390-pixel-wide mobile viewport;
  - metric selection and detailed-analysis controls remain operable by keyboard;
  - status meaning is available in text and is not dependent on color alone.
- Tests assert public behavior and stable contracts rather than internal function names, DOM structure, styling implementation, or private module boundaries.
- Existing indicator-generation and validation artifacts are treated as source definitions and fixtures, not as the production interface. Prototype-only behavior must not become a required dependency of the public dashboard.
- A separate live-AI smoke check may be provided for maintainers, but it is not the deterministic acceptance gate and must never be required for routine local verification.
- Review evidence should include the verification command result plus desktop and mobile screenshots of the successful state and the daily-failure fallback state.

## Out of Scope

- Buy or sell recommendations.
- Entry-price recommendations.
- Position-sizing or portfolio-allocation advice.
- Leverage recommendations.
- Personalized financial advice.
- Numeric “bottom probability” or confidence percentages.
- AI access to historical chart series or recent-trend calculations.
- AI access to news, social sentiment, macroeconomic feeds, or external web search.
- Adding indicators beyond the confirmed 16-indicator inventory.
- Allowing AI to modify metric definitions, categories, roles, or thresholds.
- Public editing of thresholds or metric settings.
- A public administration interface.
- User accounts, saved preferences, or personalized dashboards.
- A browsable archive of previous daily AI judgments.
- Historical backtesting of the AI’s stage choices as part of this feature.
- Alerts through email, mobile push, messaging applications, or browser notifications.
- Intraday or on-demand AI analysis for every page refresh.
- Displaying distance to the next threshold tier.
- Automatic reconciliation of different source dates or freshness levels.
- Claiming that an indicator, threshold combination, or AI stage identifies the exact BTC cycle bottom.

## Further Notes

- “市场阶段” is a constrained interpretation of the current 16-indicator threshold configuration. Because the AI does not receive historical trends, the stage describes the evidence pattern in the current snapshot rather than a measured price trajectory.
- “数据不足” remains available when the supplied snapshot or AI response cannot support a valid judgment. Missing evidence must not be silently converted into a negative vote.
- The public explanation should state that the dashboard provides research-oriented cycle evidence and is not trading advice.
- The previous-result fallback is operational resilience, not a history feature. The interface must make the result date obvious whenever fallback is active.
- Current metric names, category assignments, and core/supporting roles come from the validated 16-indicator inventory. Threshold values remain controlled configuration and are intentionally not frozen inside this product specification.
- The selected wireframe verdict is: use the compact hybrid layout that combines the conclusion-and-chart hierarchy of the first dashboard direction with the stage-oriented AI evaluation of the evidence-map direction. The final refinement removes the separate full-width evidence-consistency row and compresses the normal AI section so the indicator dashboard begins within the first desktop viewport.
- The repository currently contains prototype and validation artifacts rather than a production application. Implementation should preserve validated metric semantics while treating the public dashboard as a new product surface.
