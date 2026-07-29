# v0.4.0 — 双轴市场状态实施规格

> 建议标签：`ready-for-agent`
>
> 状态：产品设计与主要验收接缝已确认；已发布为 [GitHub Issue #2](https://github.com/DrErwin/btc-bear-market-dashboard/issues/2) 并添加 `ready-for-agent` 标签。本文用于指导实施，不代表运行代码已经升级。

## Problem Statement

当前看板把“市场压力有多深”和“熊底证据形成到什么程度”压缩成一条五阶段路线。这会造成三个问题。

第一，不同指标本来就观察不同市场现象，也会在不同时间进入观察、深度压力或极端压力档。把它们强行排成一个阶段，容易让用户误以为所有指标必须同步。

第二，熊底通常是一段会反复的过程，而不是某一天出现的精确时刻。当前单日快照和单向阶段轴难以表达证据逐步出现、短暂修复、重新下探、修复失败或离开底部窗口。

第三，当前机器会先根据详细规则生成 AI 可以选择的阶段范围。这样虽然限制了 AI，但也让 AI 越来越像一个规则结果的文案改写器，无法真正综合不同职责、不同时间和相互矛盾的证据。

用户已经通过人工回看历史熊市，为许多指标校准了观察、深度压力和极端压力三档阈值。这些阈值是重要研究成果，不能因为页面改名或状态模型升级而改变触发结果。当前实现又会从中文显示名称推断档位，因此直接改名可能改变判断、颜色和 AI 输入。

产品需要在保留人工阈值成果的同时，把公开结论改成真正的市场状态说明：一条轴描述当前压力深度，另一条轴描述近期筑底过程；机器保证事实和边界，AI 在固定框架内完成定性综合判断。

## Solution

看板改为同时显示两条可以独立变化、可以回退的市场状态：

- 压力轴回答“当前市场承受多深的压力”；
- 筑底轴回答“近期熊底证据已经形成到什么程度”。

AI 从两套固定词汇中各选择一个状态，并给出证据一致性、综合摘要、与前三个自然日的比较、状态变化原因和六部分详细解释。页面不再把两条轴重新压缩成第三个总体阶段，也不再使用单向五阶段进度条。

机器继续负责数据新鲜度、数值与阈值比较、稳定的人工校准档位、指标职责、相关性、证据时间线、前三天上下文和事实校验。机器只判断某条轴是否具备足够数据，不使用计分表、指标数量或固定组合公式预先决定市场状态。

人工校准档位使用稳定身份，不再依赖中文显示名称。观察、深度压力和极端压力的数值、方向、顺序和历史校准含义保持不变；“定投、抄底、大力抄底”等行动对应关系只保留在内部校准来源中，不进入公开结果包和 AI 判断。

系统继续每天发布一份完整结果包。指标事实、时间线、AI 双轴结论、回退状态和页面展示必须属于同一次运行。主要验收从固定历史场景出发，经过完整每日判断形成结果包，再由页面读取同一结果包验证最终行为。

## User Stories

1. As a 公开访问者, I want to immediately see the current pressure state, so that I can understand how deeply the market is under stress.
2. As a 公开访问者, I want to immediately see the current bottoming state, so that I can understand whether bottom evidence is absent, forming, relatively complete, repairing, or already outside the bottom window.
3. As a 公开访问者, I want the two states displayed together, so that I do not mistake deep pressure for complete bottom evidence.
4. As a 公开访问者, I want the pressure state to use fixed wording, so that daily conclusions remain comparable.
5. As a 公开访问者, I want the bottoming state to use fixed wording, so that the process remains understandable across different market combinations.
6. As a 公开访问者, I want both states to be allowed to strengthen, weaken, or reverse, so that the page reflects a real market process rather than a one-way progress bar.
7. As a 公开访问者, I do not want the two states compressed into a third overall stage, so that distinct market questions remain distinct.
8. As a 公开访问者, I want to see evidence consistency as weak, medium, or strong, so that I understand whether independent evidence groups broadly agree.
9. As a 公开访问者, I do not want evidence consistency described as a probability, so that I am not misled by false precision.
10. As a 公开访问者, I want each axis to be able to show data insufficiency independently, so that missing bottoming history does not hide a still-reliable pressure conclusion.
11. As a 公开访问者, I want the page to show overall data insufficiency when neither axis can be judged, so that missing data is not presented as a market opinion.
12. As a 公开访问者, I do not want a consistency label when both axes lack enough data, so that absence of evidence is not confused with conflicting evidence.
13. As a 公开访问者, I want one plain-language summary of the two states, so that I can understand the main conclusion without reading every metric.
14. As a 公开访问者, I want to know whether either state changed relative to the previous three natural days, so that I can recognize a meaningful change in the evidence structure.
15. As a 公开访问者, I want a one-line reason whenever a state changes, so that the change is traceable to new, stronger, weaker, missing, or repairing evidence.
16. As a 公开访问者, I do not want previous-day states to mechanically outvote today’s facts, so that an important new event can change the conclusion immediately.
17. As a 公开访问者, I want unchanged states to remain understandable in context, so that continuity is not mistaken for a failed daily update.
18. As a 公开访问者, I want to expand a detailed explanation, so that I can inspect the reasoning only when I need it.
19. As a 公开访问者, I want the detailed explanation to state why the current pressure level was selected, so that I can understand why it is not shallower or deeper.
20. As a 公开访问者, I want the detailed explanation to state why the current bottoming state was selected, so that I can see which types of bottom evidence have or have not formed.
21. As a 公开访问者, I want the detailed explanation to summarize the evidence timeline, so that I can distinguish newly appearing, persistent, recurring, weakening, and disappearing evidence.
22. As a 公开访问者, I want the detailed explanation to include contrary evidence and data gaps, so that the conclusion is not selectively argued.
23. As a 公开访问者, I want the detailed explanation to distinguish temporary pressure relief from sustained repair, so that a short rebound is not called a completed recovery.
24. As a 公开访问者, I want the detailed explanation to state what market evidence should be watched next, so that I understand the unresolved questions without receiving an action recommendation.
25. As a 公开访问者, I want metric cards and charts to retain exact values, dates, thresholds, and directions, so that I can verify the AI explanation.
26. As a 公开访问者, I want each metric’s current artificial calibration tier to remain visible, so that the historical threshold framework is preserved.
27. As a 公开访问者, I want each tier to include a metric-specific factual meaning, so that “deep pressure” explains what is happening in that metric.
28. As a 公开访问者, I want data freshness and unavailable reasons to remain visible, so that stale or pending evidence is not mistaken for current evidence.
29. As a 公开访问者, I want indicators to remain grouped by evidence category, so that I can see which part of the market each fact comes from.
30. As a 公开访问者, I want the AI explanation to mention representative evidence rather than repeat all 16 metrics, so that the conclusion stays readable.
31. As a 公开访问者, I want correlated indicators to be described as confirmation rather than multiple independent votes, so that evidence strength is not exaggerated.
32. As a 公开访问者, I want repair and exit judgments to use changes in the existing indicators, so that the product does not quietly introduce an unreviewed indicator set.
33. As a 公开访问者, I want the page to clearly label a previous successful result when today’s analysis fails, so that an old conclusion is never presented as current.
34. As a 公开访问者, I want the metric dashboard to remain available when today’s AI analysis fails, so that factual evidence is still inspectable.
35. As a 公开访问者, I do not want to see “定投、抄底、大力抄底,” buy or sell instructions, entry prices, position sizes, leverage, or bottom probabilities, so that the page remains a public research product.
36. As a 手机访问者, I want both axes, the summary, and the change reason to remain readable in one column, so that the conclusion works on a small screen.
37. As a 键盘用户, I want the new conclusion and detail controls to remain keyboard operable, so that the migration does not reduce accessibility.
38. As a 公开访问者, I want state meaning to be communicated with text as well as color, so that color alone is never required.
39. As a 看板维护者, I want every threshold to have a stable calibration-tier identity, so that changing a label cannot change the trigger result.
40. As a 看板维护者, I want observation, deep-pressure, and extreme-pressure values and directions preserved exactly, so that the upgrade does not silently recalibrate history.
41. As a 看板维护者, I want the private action provenance of each tier kept outside the public packet, so that historical research context does not become public advice.
42. As a 看板维护者, I want each indicator to have one primary judgment responsibility, so that AI understands what question the metric mainly helps answer.
43. As a 看板维护者, I want every indicator to retain its evidence category and correlation family, so that related indicators are not treated as independent evidence.
44. As a 看板维护者, I want stale, missing, display-only, and validation-pending metrics explicitly marked, so that AI cannot use them as current support.
45. As a 看板维护者, I want the machine to calculate current value-versus-threshold facts, so that AI does not perform unverified arithmetic.
46. As a 看板维护者, I want the machine to summarize tier entry, exit, duration, recurrence, strengthening, weakening, and reversal, so that AI can reason about a process without receiving full curves.
47. As a 看板维护者, I want the evidence lookback range selected through historical validation, so that the system neither forgets an active bottom process too early nor carries obsolete evidence indefinitely.
48. As a 看板维护者, I want the lookback range stored as versioned configuration, so that later changes are reviewable and do not alter numeric tier thresholds.
49. As a 看板维护者, I want exactly the previous three natural days represented in AI context, so that missing calendar days are visible rather than silently skipped.
50. As a 看板维护者, I want missing previous days explicitly marked, so that AI does not invent continuity.
51. As a 看板维护者, I want a carried-forward fallback excluded from being counted as a new daily state, so that one old conclusion is not repeated as several days of evidence.
52. As a 看板维护者, I want old single-stage results treated as incompatible history rather than guessed into two axes, so that migration does not fabricate prior states.
53. As a 看板维护者, I want machine data-readiness checks to operate separately for pressure and bottoming, so that one missing evidence type does not block the other axis.
54. As a 看板维护者, I want data-readiness checks limited to coverage, freshness, and timeline completeness, so that they do not become hidden market-stage rules.
55. As a 看板维护者, I want AI to choose from the full fixed vocabulary for every data-ready axis, so that the machine does not precompute an allowed stage range.
56. As a 看板维护者, I want AI to weigh supporting, contrary, missing, and repairing evidence, so that its contribution is qualitative synthesis rather than metric counting.
57. As a 看板维护者, I want malformed AI output rejected before publication, so that the public packet always follows the new contract.
58. As a 看板维护者, I want AI claims checked against actual values, threshold directions, dates, eligibility, and timeline facts, so that fluent but false explanations cannot be published.
59. As a 看板维护者, I want any trading advice, probability language, or internal rule-engine terminology rejected, so that the product boundary remains enforceable.
60. As a 看板维护者, I want the AI response to contain all six detailed explanation sections, so that important reasoning responsibilities cannot be silently omitted.
61. As a 看板维护者, I want today’s snapshot, timeline, three-day context, AI conclusion, fallback status, and page data to share one run identity, so that users never see a mixed-date result.
62. As a 看板维护者, I want the packet, evidence brief, AI response, and configuration versions clearly identified, so that old and new contracts are not mixed.
63. As a 看板维护者, I want the first v0.4 release to start with a valid v0.4 fallback or a clear unavailable state, so that an old five-stage conclusion is not silently shown as a dual-axis result.
64. As a 看板维护者, I want existing charts, indicator inventory, and data sources preserved unless the new contract requires a display adaptation, so that the release remains focused on market-state judgment.
65. As a 产品审阅者, I want one highest-level acceptance flow from fixed evidence through the daily result packet to the rendered page, so that the complete feature is verified as one product behavior.
66. As a 产品审阅者, I want the main acceptance flow to run offline with deterministic fixtures, so that normal verification does not depend on network access or paid AI calls.
67. As a 产品审阅者, I want the fixed scenarios to cover deep pressure without complete bottom evidence, so that the two axes are proven independent.
68. As a 产品审阅者, I want the fixed scenarios to cover evidence appearing on different dates, so that the system is proven to understand a process rather than same-day triggers.
69. As a 产品审阅者, I want the fixed scenarios to cover reversal, repair failure, sustained repair, and leaving the bottom window, so that the state model is proven reversible.
70. As a 产品审阅者, I want the fixed scenarios to cover independent data insufficiency, so that each axis fails safely.
71. As a 产品审阅者, I want the fixed scenarios to cover label-only changes, so that tier identity, trigger results, colors, and AI facts remain unchanged.
72. As a 产品审阅者, I want invalid AI fixtures to reference wrong directions, stale data, and ineligible metrics, so that semantic validation is tested rather than only JSON structure.
73. As a 产品审阅者, I want the previous-three-day context tested without majority voting, so that continuity cannot become a hidden transition rule.
74. As a 产品审阅者, I want desktop, mobile, keyboard, success, partial-data, fallback, and no-fallback states covered by the same acceptance entry point, so that trust-sensitive states are release requirements.
75. As a 产品审阅者, I want real-model evaluation recorded separately from deterministic acceptance, so that a mock response is never reported as proof that AI judgment quality is acceptable.

## Implementation Decisions

### Product vocabulary and conclusion model

- The pressure axis uses exactly:
  - 压力尚未明显;
  - 进入观察;
  - 深度压力;
  - 极端压力;
  - 数据不足.
- The bottoming axis uses exactly:
  - 未见筑底结构;
  - 筑底线索出现;
  - 筑底证据聚合;
  - 筑底证据较完整;
  - 市场修复中;
  - 已离开底部窗口;
  - 数据不足.
- Evidence consistency uses exactly 弱、中等、强. It is not a probability or a third market axis.
- Both axes describe the current evidence structure. They may move forward, move backward, or remain unchanged.
- No combined overall-stage field is generated for public use.
- When both axes are data insufficient, consistency is absent rather than set to weak.
- When only one axis is data insufficient, the other axis remains publishable. Consistency is shown only when enough valid evidence remains to compare directions.

### Daily analysis contract

- The new analysis contract contains:
  - analysis date;
  - pressure state;
  - bottoming state;
  - nullable evidence consistency;
  - one combined plain-language summary;
  - a comparison with the previous three natural days;
  - separate indicators of whether the pressure state and bottoming state changed;
  - a one-line change reason when either state changed;
  - six required detailed explanation sections;
  - evidence-category assessments used by the existing evidence board.
- The six detailed sections are:
  - pressure-state reasoning;
  - bottoming-state reasoning;
  - evidence timeline;
  - contrary evidence and data gaps;
  - repair and bottom-window exit judgment;
  - next evidence to watch.
- The comparison with the previous three days is always present when at least one compatible previous result exists. The change reason is required only when at least one axis actually changes.
- Category assessments may continue to summarize the existing evidence groups for navigation, but they do not calculate, limit, or vote on either market-state axis.
- The analysis contract replaces the old single-stage and allowed-stage fields. Old stage names are not aliases for new states.

### Stable calibration tiers

- Each configured threshold carries a stable calibration-tier identity independent of display text.
- Stable identities cover no active tier, observation, deep pressure, and extreme pressure. Unavailable data is represented as data quality, not as a pressure tier.
- Each metric exposes its current stable tier identity, public display label, metric-specific factual meaning, numeric threshold, direction, and data date.
- Page color and emphasis use the stable tier identity rather than searching Chinese labels.
- Numeric threshold values, directions, order, and current artificial calibration meanings are migrated without recalibration.
- Internal provenance may record that the three tiers were historically associated with different research actions. That provenance is excluded from the public packet, AI input, AI output, logs intended for public review, and page copy.

### Evidence metadata and responsibilities

- Every indicator retains one evidence category and receives:
  - one primary judgment responsibility;
  - one correlation family;
  - its existing importance or evidence role;
  - current eligibility and freshness status.
- An indicator may contribute secondary explanation through its reverse movement, but it cannot be represented as multiple independent pieces of evidence on the same date.
- Highly related indicators remain individually visible for factual inspection while being summarized as one evidence family for AI weighting.
- The machine supplies correlation and responsibility facts. It does not convert them into a score or a fixed stage result.
- The initial 16-indicator responsibility mapping is the mapping approved in the product design and is versioned with the evidence configuration.

### Evidence timeline

- A deterministic timeline builder converts historical metric observations into bounded factual summaries.
- Each eligible metric summary includes:
  - current calibration tier;
  - first entry date in the current recent episode;
  - latest entry or exit date;
  - current duration;
  - recurrence within the configured range;
  - recent strengthening, weakening, exit, or reversal;
  - data date, freshness, and unavailable reason.
- Correlated metrics also receive a family-level summary so AI can see confirmation without interpreting the number of metrics as independent votes.
- Timeline extraction compares actual values against versioned thresholds and directions. It does not infer a market state.
- AI receives event summaries, not complete historical curves or unrestricted raw daily history.
- The historical lookback length is a versioned configuration selected before production activation by comparing candidate ranges across historical bear-market cases.
- The selected range must cover complete bottom processes in the validation cases without allowing clearly expired episodes to continue supporting today’s state.
- Changing the lookback length requires a recorded validation update but never changes the user’s numeric calibration thresholds.

### Per-axis data readiness

- The machine produces separate readiness results for pressure and bottoming.
- Readiness may consider only required data coverage, evidence-family coverage, freshness, and availability of the timeline needed for that axis.
- Readiness does not use the number of triggered tiers, a weighted score, or a desired market state.
- A non-ready axis is forced to 数据不足 and receives explicit missing-data reasons.
- A ready axis is presented to AI with the full fixed vocabulary. The machine does not generate a smaller allowed-state subset.

### Previous-three-day context

- AI context represents the previous three natural calendar days, not merely the previous three stored records.
- Each day includes both axes, evidence consistency, one main reason, result date, and whether the record is a current successful result, missing day, or older fallback.
- Missing calendar days remain explicit gaps and are not filled with the nearest available result.
- A carried-forward fallback is not counted as a newly judged day.
- Pre-v0.4 single-stage analyses are not converted into guessed dual-axis history. They appear as incompatible or unavailable context during migration.
- The three-day context is descriptive only. No majority vote, consecutive-day promotion rule, cooling-off rule, or automatic state ceiling is derived from it.

### AI input and judgment boundary

- AI receives:
  - fixed definitions of both state vocabularies and evidence consistency;
  - per-axis data readiness and missing reasons;
  - current metric facts and stable calibration tiers;
  - metric responsibilities, evidence categories, roles, correlation families, eligibility, dates, and freshness;
  - bounded metric and evidence-family timeline summaries;
  - supporting, contrary, unavailable, and repair-related facts;
  - previous-three-day context.
- AI does not receive:
  - private action provenance;
  - an allowed-state subset;
  - a machine-computed overall state;
  - metric scores or weighted totals;
  - unrestricted full historical curves;
  - news, sentiment, price forecasts, or unapproved external evidence.
- AI independently selects the pressure state, bottoming state, and applicable consistency label within the fixed vocabularies.
- AI must explain why the selected state fits better than nearby alternatives without claiming that a fixed metric formula forced the answer.
- AI must use evidence categories and correlation information qualitatively. It may describe confirmation but may not count correlated indicators as separate votes.

### Validation and safety

- Structural validation enforces required fields, fixed vocabularies, nullable consistency rules, six detailed sections, dates, and category completeness.
- Semantic validation compares AI claims with the supplied factual input, including:
  - actual current values;
  - threshold direction and triggered tier;
  - data date and freshness;
  - eligibility status;
  - entry, exit, duration, and reversal facts;
  - previous-day states and whether a change actually occurred.
- Semantic validation rejects references to missing, stale, display-only, or validation-pending metrics as current support.
- Semantic validation rejects invented metric values, incorrect threshold directions, fabricated timeline events, incorrect state-change claims, and correlated metrics presented as independent votes.
- Product-safety validation rejects trading actions, target prices, position or leverage advice, bottom probabilities, and internal rule-engine terminology.
- Validation checks factual consistency and product boundaries. It does not reintroduce a hidden formula that decides which qualitative state AI must choose.

### Complete packet, fallback, and migration

- The daily process continues to publish one complete packet containing snapshot, chart series, bars, evidence brief, timeline context, analysis or fallback, and status.
- A successful v0.4 analysis and its evidence input share the same run identity and data date.
- If today’s AI call or validation fails, the page may show the most recent complete successful v0.4 analysis as fallback with its original analysis date.
- A v0.3 single-stage analysis is never silently treated as a v0.4 dual-axis fallback.
- If no valid v0.4 fallback exists, the page shows today’s analysis as unavailable while retaining the factual indicator dashboard.
- Packet schema, evidence-brief contract, AI response contract, and evidence configuration are all versioned for v0.4 compatibility.
- The configuration version changes because stable tier identities, responsibilities, correlation families, and timeline settings are part of the judgment contract even though numeric thresholds remain unchanged.

### Public page

- The old five-stage progress axis is replaced by a dual-state conclusion area.
- The first view shows:
  - pressure state;
  - bottoming state;
  - applicable evidence consistency;
  - one combined summary;
  - comparison with the previous three days;
  - a one-line reason when a state changes.
- Detailed analysis is collapsed by default and expands into the six approved sections.
- The page does not generate a combined overall stage.
- Existing evidence categories, 16 indicator cards, shared charts, exact values, threshold lines, sources, limitations, and freshness information remain available.
- Metric tier color and text are driven by the stable tier identity.
- The new conclusion remains readable at representative desktop and mobile sizes and preserves keyboard operation and text alternatives to color.
- Internal terms such as allowed stages, stage ceilings, voting, core-anchor rules, and private action provenance are not rendered.

### Delivery sequence

1. **Contract and fixture foundation**
   - Freeze the v0.4 state vocabularies, analysis shape, evidence-brief shape, stable tier identities, version relationships, and representative success, partial-data, fallback, and invalid fixtures.
   - Update the unified acceptance expectations before changing runtime judgment.
   - Exit condition: the new contract and fixtures express all approved states and fail against the old single-stage implementation for the intended reasons.

2. **Calibration-tier and evidence-metadata migration**
   - Add stable tier identities, metric responsibilities, correlation families, and public/private provenance separation.
   - Migrate all 16 indicators without changing numeric thresholds or directions.
   - Replace label-based color and severity inference.
   - Exit condition: label-only changes cannot alter tier identity, threshold result, page color, evidence facts, or AI input.

3. **Timeline, lookback validation, and three-day context**
   - Build deterministic timeline summaries and family summaries.
   - Compare candidate historical ranges across the approved bear-market cases and record the selected configuration.
   - Build exact three-natural-day context with missing-day and fallback handling.
   - Exit condition: timeline facts, reversals, recurrence, expiration, missing days, and old-contract migration behavior pass fixed scenarios.

4. **AI contract, input, validation, and daily packet**
   - Replace the old single-stage prompt and allowed-stage flow with the dual-axis judgment framework.
   - Implement per-axis readiness, the new output contract, six explanation sections, state-change comparison, semantic validation, and v0.4 fallback behavior.
   - Exit condition: the complete daily process produces a valid v0.4 packet for deterministic success and data-insufficient scenarios and rejects invalid AI fixtures.

5. **Public-page migration**
   - Replace the single stage and progress axis with the dual-state conclusion.
   - Add previous-three-day comparison, change reason, and six-section detail display.
   - Preserve the evidence board and charts while switching tier styling to stable identities.
   - Exit condition: the page reads one v0.4 packet and correctly renders success, independent data insufficiency, fallback, no-fallback, desktop, mobile, and keyboard scenarios.

6. **Integrated acceptance and release readiness**
   - Run the single highest-level acceptance flow across the complete packet and rendered page.
   - Run the fixed real-model scenario review separately and record factual and qualitative results.
   - Update repository guidance, version maps, acceptance evidence, and release notes so old allowed-stage instructions no longer describe v0.4 behavior.
   - Exit condition: deterministic acceptance passes, real-model review is explicitly recorded, no unrelated threshold or indicator changes are included, and production deployment remains a separately approved action.

## Testing Decisions

- The one primary acceptance seam is the daily complete packet consumed by the public page.
- The highest-level test starts from fixed historical evidence and previous-day context, executes the daily judgment path with a controlled AI response, validates the complete packet, opens the page using that same packet, and asserts public behavior.
- Lower-level tests are allowed to locate failures and protect calculations, but they are not separate definitions of product completion.
- Good tests assert external behavior and stable contracts. They do not depend on private helper names, internal call order, exact prompt wording, DOM structure, or styling implementation.
- Existing prior art is reused:
  - one unified acceptance entry point;
  - offline packet fixtures;
  - deterministic mock-AI responses;
  - packet-contract validation;
  - AI structural and semantic validation;
  - browser checks for success, fallback, no-fallback, responsive layout, keyboard use, and restricted language.
- The main successful fixture must prove:
  - both states are visible and belong to fixed vocabularies;
  - no combined stage or five-stage progress axis is rendered;
  - consistency, summary, three-day comparison, and applicable change reason are visible;
  - all six detailed sections expand and collapse;
  - the evidence board and all retained indicators remain usable;
  - the page content matches the packet.
- Independent data-insufficiency fixtures must prove:
  - pressure can be available while bottoming is data insufficient;
  - bottoming can be available while pressure is data insufficient when the supplied evidence supports that case;
  - both axes can be data insufficient;
  - consistency is absent when both axes are insufficient;
  - missing reasons are explained without invented conclusions.
- Timeline fixtures must prove:
  - evidence can enter different tiers on different dates;
  - a current episode start and duration are correct;
  - repeated entry and exit are represented as recurrence;
  - weakening and reversal respect each metric’s threshold direction;
  - expired evidence no longer supports the current timeline;
  - correlated-family summaries do not turn several metrics into several independent votes.
- Previous-three-day fixtures must prove:
  - exactly three natural dates are represented;
  - missing dates remain missing;
  - fallbacks are not duplicated as new daily judgments;
  - pre-v0.4 history is not guessed into dual axes;
  - today may change immediately despite three identical previous states;
  - today does not change merely because two of three previous states agree.
- Stable-tier migration tests must compare actual values, directions, tier identities, display labels, colors, and AI facts before and after a label-only change.
- Semantic rejection fixtures must include:
  - an AI claim that reverses a threshold direction;
  - an AI claim that cites an untriggered tier;
  - an AI claim that uses stale, missing, display-only, or validation-pending evidence as current support;
  - an invented entry, exit, duration, recurrence, or reversal;
  - an incorrect statement that a state changed;
  - correlated indicators presented as independent votes;
  - missing one of the six detailed sections;
  - trading advice, probability, price, position, leverage, or private action language.
- The approved product scenarios must cover:
  1. one extreme metric with insufficient independent confirmation;
  2. deep pressure without meaningful bottoming structure;
  3. independent bottoming evidence appearing on different dates;
  4. temporary relief followed by renewed pressure;
  5. repair failure returning to the bottom window;
  6. sustained repair moving to 市场修复中;
  7. sustained repair supporting 已离开底部窗口;
  8. pressure ready but bottoming timeline insufficient;
  9. important new facts overriding three days of unchanged context;
  10. unchanged facts resisting a three-day majority effect;
  11. display-text changes leaving tier behavior unchanged;
  12. invalid AI references being rejected.
- Browser acceptance must cover representative desktop and 390-pixel mobile layouts, no page-level horizontal overflow, keyboard operation, visible text labels, and success/failure screenshots.
- Restricted-language checks apply to all user-visible AI conclusion fields and must reject public action guidance without rejecting factual metric descriptions of selling, losses, or capitulation.
- The deterministic acceptance path runs without public network access, production data fetches, paid AI calls, or real credentials.
- A separate real-model evaluation runs the same fixed scenario family through the actual provider before release. It reviews:
  - whether both states are reasonable given the supplied facts;
  - whether support, counterevidence, gaps, timeline, repair, and next evidence are explained;
  - whether actual values and directions are cited correctly;
  - whether the model avoids metric counting and rule-engine language;
  - whether state changes are explained against the real previous-day context.
- Passing mock acceptance does not count as passing the real-model evaluation. Both results are recorded separately.
- Existing chart behavior unrelated to stable tier styling is regression-tested but not redesigned by this feature.

## Out of Scope

- Recalibrating any observation, deep-pressure, or extreme-pressure numeric threshold.
- Adding, removing, or replacing indicators.
- Introducing new data providers or external market information.
- Predicting the exact lowest price or exact bottom date.
- Publishing bottom probabilities, confidence percentages, price targets, buy or sell actions, entry timing, position sizes, or leverage guidance.
- Showing “定投、抄底、大力抄底” in public output or AI context.
- Building a score, weighted index, metric-count vote, fixed state-combination table, or machine-generated allowed-state range.
- Sending complete unrestricted historical curves to AI.
- Turning the previous three days into a majority vote, minimum-duration gate, or mandatory transition order.
- Creating a third combined overall stage.
- Building a public threshold editor, administration page, user account, personalization, alert, notification, or intraday analysis feature.
- Building a public browser for historical AI judgments.
- Reworking chart interaction, chart reference lines, or indicator data formulas except where stable tier identity must replace label-based behavior.
- Treating pre-v0.4 stages as automatically convertible to the new axes.
- Claiming production deployment, live-model quality, or data-redistribution approval based only on local deterministic acceptance.
- Deploying v0.4 to production without a separate user approval after implementation and release-readiness review.

## Further Notes

- The user confirmed on 2026-07-29 that the daily complete packet consumed by the page is the single primary acceptance seam.
- This specification supersedes the v0.3 single-stage and allowed-stage behavior only after v0.4 is implemented, accepted, and released. Until then, current runtime behavior remains unchanged.
- The historical lookback length is intentionally a validation output rather than a subjective product guess. Implementation cannot mark the timeline phase complete until the selected range and evidence are recorded.
- Existing repository guidance that says AI must select from machine-generated allowed stages must be updated as part of the v0.4 release-readiness phase, not silently ignored during implementation.
- The repository currently contains unrelated local changes. Implementation must keep v0.4 commits focused and avoid absorbing unrelated chart, data, research, or generated-artifact changes.
- The issue-ready implementation should preserve the existing successful principle: AI explains the conclusion, while metric cards and charts prove the factual basis.
