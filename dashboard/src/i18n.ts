import { computed, ref } from "vue";
import type { Category, Metric } from "./types";

export type Locale = "zh" | "en";

const STORAGE_KEY = "btc-dashboard.locale.v1";
const savedLocale = typeof window === "undefined" ? null : window.localStorage.getItem(STORAGE_KEY);
const locale = ref<Locale>(savedLocale === "en" ? "en" : "zh");

const text = {
  zh: {
    dashboardTitle: "BTC 熊底证据看板", language: "English", dailySnapshot: "每日快照", previousSuccess: "上一份成功分析",
    method: "方法说明", waiting: "等待可用分析", readPacket: "正在读取数据包…", cannotRead: "看板暂时无法读取",
    pressureAxis: "压力轴", bottomingAxis: "筑底过程轴", pressureDepth: "压力深度", bottomingProcess: "熊底过程",
    evidenceConsistency: "证据一致性", savedToday: "今日已保存", noConclusion: "暂无可用结论", fullAnalysis: "查看完整分析", collapseAnalysis: "收起完整分析",
    detail: ["压力判断", "筑底判断", "证据时间线", "相反证据与缺口", "修复与离开窗口", "下一步观察重点"],
    boardEyebrow: "分类指标看板 / 16 个周期指标", boardTitle: "从证据结构进入单项检查", boardText: "先看六类状态，再选择一个指标查看共享图表与阈值语义。",
    currentCategory: "当前分类", itemCount: "项", collapseMetrics: "收起指标列", expandMetrics: "展开指标列",
    railNote: "角色与数据状态分开标注；过期或待验证指标仍保留展示，但不参与当前判断。",
    formula: "指标公式", meaning: "指标含义", usage: "指标使用", source: "指标来源", explanation: "理解这个指标", readingTip: "读图提示",
    categoryRole: "所属分类与角色", currentTier: "当前阈值语义", currentValue: "当前值", evidenceRole: "证据角色",
    insufficient: "部分市场状态数据不足", insufficientText: "压力轴和筑底过程轴分别检查数据；缺失数据没有被当作“没有压力”或反向证据。", waitData: "等待数据恢复",
    aiUnavailable: "今日 AI 分析不可用", fallbackText: "当前展示上一份完整双轴结果，日期为 {date}。", noFallbackText: "目前没有上一份完整双轴结果，页面仅保留指标检查功能。",
    englishUnavailable: "英文 AI 分析暂不可用", englishUnavailableText: "中文分析已生成，但本次英文翻译未成功；市场状态和数据没有改变。",
    footerTitle: "研究导向的周期证据", footerText: "看板解释当前快照，不宣称识别确切最低点。", disclaimer: "仅作公开研究参考 · 不构成交易建议",
    methodEyebrow: "方法边界", methodTitle: "把复杂指标变成可检查的证据结构", methodText1: "看板每天使用一份固定的指标快照，分别读取压力深度和筑底过程两条轴。当前值、阈值语义和来源限制始终留在指标区域，方便你自己复核。", methodText2: "图表仅用于检查指标和 BTC 价格的共同时间范围；它与每日双轴分析分开，刷新页面不会重新生成结论。", returnDashboard: "返回看板",
    current: "当前可用", displayOnly: "仅供展示", validation: "待验证", missing: "缺失", notPart: "不参与当前判断", expired: "已过期 {days} 天", unknownDate: "日期未知",
    expand: "放大", noDate: "无可用日期", linear: "线性", logarithmic: "对数", chartControls: "时间范围与坐标", chartLegend: "图例与曲线开关", btcPrice: "BTC 价格", thresholds: "阈值线", historicalBottoms: "历史熊底", barsUnavailable: "当前时间范围暂无柱状数据，可切换到全量查看", resizeChart: "调整图表高度",
    roles: { "核心锚": "核心锚", "核心复核": "核心复核", "强辅助": "强辅助", "辅助": "辅助" },
    categoryStatus: { "未确认": "未确认", "部分确认": "部分确认", "充分确认": "充分确认" },
  },
  en: {
    dashboardTitle: "BTC Bear-Bottom Evidence Dashboard", language: "中文", dailySnapshot: "Daily snapshot", previousSuccess: "Previous successful analysis",
    method: "Method", waiting: "Awaiting available analysis", readPacket: "Loading data packet…", cannotRead: "Dashboard unavailable",
    pressureAxis: "Pressure axis", bottomingAxis: "Bottoming-process axis", pressureDepth: "Pressure depth", bottomingProcess: "Bottoming process",
    evidenceConsistency: "Evidence consistency", savedToday: "Saved today", noConclusion: "No conclusion available", fullAnalysis: "View full analysis", collapseAnalysis: "Collapse full analysis",
    detail: ["Pressure assessment", "Bottoming assessment", "Evidence timeline", "Contrary evidence and gaps", "Repair and exit window", "What to watch next"],
    boardEyebrow: "Evidence board / 16 cycle indicators", boardTitle: "Inspect one indicator through the evidence structure", boardText: "Read the six category states first, then inspect an indicator, its shared chart, and threshold meaning.",
    currentCategory: "Current category", itemCount: "items", collapseMetrics: "Collapse metric list", expandMetrics: "Show metric list",
    railNote: "Evidence role and data status are shown separately. Stale or unverified indicators remain visible but do not inform the current assessment.",
    formula: "Formula", meaning: "What it means", usage: "How to use it", source: "Source", explanation: "Understand this indicator", readingTip: "Reading guide",
    categoryRole: "Category and role", currentTier: "Current threshold meaning", currentValue: "Current value", evidenceRole: "Evidence role",
    insufficient: "Some market-state data is unavailable", insufficientText: "The pressure and bottoming axes check their data separately. Missing data is not treated as no pressure or as contrary evidence.", waitData: "Waiting for data",
    aiUnavailable: "Today's AI analysis is unavailable", fallbackText: "Showing the previous complete two-axis result from {date}.", noFallbackText: "No previous complete two-axis result is available; indicator review remains available.",
    englishUnavailable: "English AI analysis is unavailable", englishUnavailableText: "The Chinese analysis was generated, but its English translation did not succeed. Market states and data are unchanged.",
    footerTitle: "Research-oriented cycle evidence", footerText: "The dashboard explains the current snapshot; it does not claim to identify an exact market low.", disclaimer: "Public research reference only · Not trading advice",
    methodEyebrow: "Method boundary", methodTitle: "Turn complex indicators into checkable evidence", methodText1: "Each day the dashboard uses one fixed indicator snapshot and reads pressure depth and the bottoming process separately. Current values, threshold meaning, sources, and limits remain on the indicator panel for your own review.", methodText2: "Charts only check the shared time range of an indicator and BTC price. They are separate from the daily two-axis analysis, and refreshing the page does not generate a new conclusion.", returnDashboard: "Back to dashboard",
    current: "Current", displayOnly: "Display only", validation: "Needs validation", missing: "Missing", notPart: "Not used in current assessment", expired: "Stale by {days} days", unknownDate: "Date unknown",
    expand: "Expand", noDate: "No date available", linear: "Linear", logarithmic: "Log", chartControls: "Time range and scale", chartLegend: "Legend and curve toggles", btcPrice: "BTC price", thresholds: "Thresholds", historicalBottoms: "Historical bear bottoms", barsUnavailable: "No bar data in this range; switch to all data to view it", resizeChart: "Resize chart height",
    roles: { "核心锚": "Core anchor", "核心复核": "Core cross-check", "强辅助": "Strong supporting", "辅助": "Supporting" },
    categoryStatus: { "未确认": "Unconfirmed", "部分确认": "Partly confirmed", "充分确认": "Well supported" },
  },
} as const;

const categories: Record<string, { zh: string; en: string }> = {
  valuation: { zh: "估值与成本", en: "Valuation and cost" }, supply: { zh: "供应盈亏", en: "Supply profit and loss" },
  capital: { zh: "链上资本流", en: "On-chain capital flow" }, holders: { zh: "持有者行为", en: "Holder behaviour" },
  miners: { zh: "矿工压力", en: "Miner pressure" }, anchors: { zh: "长期成本锚", en: "Long-term cost anchors" },
};

const states: Record<string, { zh: string; en: string }> = {
  "压力尚未明显": { zh: "压力尚未明显", en: "Pressure not yet broad" }, "进入观察": { zh: "进入观察", en: "Watch zone" }, "深度压力": { zh: "深度压力", en: "Deep pressure" }, "极端压力": { zh: "极端压力", en: "Extreme pressure" },
  "未见筑底结构": { zh: "未见筑底结构", en: "No bottoming structure" }, "筑底线索出现": { zh: "筑底线索出现", en: "Bottoming clues emerging" }, "筑底证据聚合": { zh: "筑底证据聚合", en: "Bottoming evidence converging" }, "筑底证据较完整": { zh: "筑底证据较完整", en: "Bottoming evidence more complete" }, "市场修复中": { zh: "市场修复中", en: "Market repairing" }, "已离开底部窗口": { zh: "已离开底部窗口", en: "Past the bottoming window" }, "数据不足": { zh: "数据不足", en: "Insufficient data" }, "弱": { zh: "弱", en: "Low" }, "中等": { zh: "中等", en: "Medium" }, "强": { zh: "强", en: "High" },
};

type IndicatorCopy = { label: string; meaning: string; usage: string; source: string; sourceUrl: string };
const indicatorCopy: Record<string, { zh: IndicatorCopy; en: IndicatorCopy }> = {
  mvrv: {
    zh: { label: "MVRV", meaning: "比较全网市值和币上次移动时形成的整体成本。接近或低于 1 时，更多持有人接近或处于账面亏损。", usage: "用它看投资者成本压力是否变广；它不能单独证明市场已经见底。", source: "Glassnode · MVRV Ratio", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/mvrv-ratio" },
    en: { label: "MVRV", meaning: "Compares the market's total value with the aggregate cost when coins last moved. Near or below 1, more holders are near or below their cost basis.", usage: "Use it to judge whether investor cost pressure is broad. It cannot prove a bottom on its own.", source: "Glassnode · MVRV Ratio", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/mvrv-ratio" },
  },
  aviv: {
    zh: { label: "AVIV", meaning: "补充观察真正活跃的币相对其成本处在什么位置。较低值通常表示活跃投资者的成本压力更大。", usage: "把它作为 MVRV 的交叉核对，不把两者当成两份独立结论。", source: "ARK × Glassnode · Cointime Economics", sourceUrl: "https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARK%20Invest%20x%20Glassnode_White%20Paper_Cointime%20Economics_Final.pdf" },
    en: { label: "AVIV", meaning: "Adds a view of where actively circulating coins sit relative to their cost basis. Lower values usually mean more cost pressure for active investors.", usage: "Use it to cross-check MVRV, not as a second independent verdict.", source: "ARK × Glassnode · Cointime Economics", sourceUrl: "https://research.ark-invest.com/hubfs/1_Download_Files_ARK-Invest/White_Papers/ARK%20Invest%20x%20Glassnode_White%20Paper_Cointime%20Economics_Final.pdf" },
  },
  "sth-mvrv": {
    zh: { label: "STH-MVRV 战术价位", meaning: "观察最近约五个月买入者平均处于盈利、亏损还是接近回本。数值越低，近期买入者压力通常越大。", usage: "用于查看短期持有者压力是否缓解；要结合实际花费和资本流证据。", source: "Glassnode · STH-MVRV", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/sth-mvrv" },
    en: { label: "STH-MVRV tactical level", meaning: "Shows whether coins acquired in roughly the past five months are, on average, in profit, loss, or near break-even. Lower values usually mean more pressure on recent buyers.", usage: "Use it to see whether short-term holder pressure is easing; pair it with spending and capital-flow evidence.", source: "Glassnode · STH-MVRV", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/mvrv/sth-mvrv" },
  },
  psip: {
    zh: { label: "PSIP（盈利供应占比）", meaning: "显示每 100 枚 BTC 中有多少枚当前价格高于上次移动时的价格。数值下降表示处于浮亏的币变多。", usage: "用来理解账面压力覆盖面；它不说明这些币一定会卖。", source: "Glassnode · Percent Supply in Profit", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/percent-supply-in-profit" },
    en: { label: "PSIP (supply in profit)", meaning: "Shows how many of every 100 BTC are worth more than when they last moved. A lower value means more coins are underwater.", usage: "Use it to understand the breadth of unrealised stress; it does not say those coins will be sold.", source: "Glassnode · Percent Supply in Profit", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/percent-supply-in-profit" },
  },
  sipl: {
    zh: { label: "SIPL（盈利／亏损供应）", meaning: "直接比较赚钱的币和亏钱的币哪一边更多。差额为负时，亏损供应更多。", usage: "它帮助理解供应盈亏构成，但与 PSIP 是同一现象的两面，不应重复计数。", source: "Glassnode · Profit/Loss Supply", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/profit-loss-supply" },
    en: { label: "SIPL (profit/loss supply)", meaning: "Directly compares whether profitable or loss-making coins are more numerous. A negative gap means loss-making supply is larger.", usage: "It describes supply composition, but is the other side of PSIP rather than independent evidence.", source: "Glassnode · Profit/Loss Supply", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/profit-loss-supply/profit-loss-supply" },
  },
  rup: {
    zh: { label: "Relative Unrealized Profit", meaning: "衡量全网尚未卖出、但账面已经盈利的金额占市场价值的比例。较高值表示可兑现的账面利润更充足。", usage: "它描述潜在获利了结背景，不代表卖出已经发生。", source: "Glassnode · Unrealized Profit", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-profit" },
    en: { label: "Relative Unrealized Profit", meaning: "Measures the share of market value that is unrealised profit. Higher values mean more paper profit is available to realise.", usage: "It describes a potential profit-taking backdrop, not selling that has already happened.", source: "Glassnode · Unrealized Profit", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-profit" },
  },
  "rul-z": {
    zh: { label: "RUL · 4 年 z-score", meaning: "把全网尚未卖出的账面亏损与过去四年通常水平比较。数值越高，表示亏损压力相对历史更突出。", usage: "它是深度压力背景，不能单独证明筑底完成。", source: "Glassnode · Unrealized Loss", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-loss" },
    en: { label: "RUL · 4-year z-score", meaning: "Compares unrealised network losses with their usual level over the past four years. Higher values mean loss pressure is more unusual versus that history.", usage: "It is context for deep pressure, not proof that bottoming is complete.", source: "Glassnode · Unrealized Loss", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/unrealized-loss" },
  },
  "rc-npc": {
    zh: { label: "Realized Cap Relative NPC · 30d", meaning: "观察最近一个月，真实换手后留在链上的资金账本是在增加还是减少。", usage: "由负转正或持续改善可作为修复背景，但不能只凭它宣布走出压力。", source: "Glassnode · Realized Capitalization", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/realized-capitalization" },
    en: { label: "Realized Cap Relative NPC · 30d", meaning: "Shows whether the on-chain capital ledger created by genuine coin movement expanded or contracted over the past month.", usage: "A turn positive or sustained improvement can support a repair narrative, but cannot establish it alone.", source: "Glassnode · Realized Capitalization", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/realized-capitalization" },
  },
  asopr: {
    zh: { label: "aSOPR", meaning: "看当天真正换手的币，平均是赚着卖、亏着卖还是接近回本。低于 1 表示实现亏损较多。", usage: "持续低于 1 可说明投降压力仍值得关注；单日波动不能单独下结论。", source: "Glassnode · aSOPR", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/asopr-adjusted-sopr" },
    en: { label: "aSOPR", meaning: "Shows whether coins actually spent today were sold at an average profit, loss, or near break-even. Below 1 means more realised losses.", usage: "Sustained readings below 1 can indicate ongoing capitulation pressure; one day cannot settle the question.", source: "Glassnode · aSOPR", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/asopr-adjusted-sopr" },
  },
  hodler: {
    zh: { label: "HODLer NPC · 30d", meaning: "观察长期不动的币，这个月是在变多，还是被拿出来卖了。低估期中负值代表长期不动供应减少。", usage: "把它当作投降或承接的背景；数据仅供展示时不能参与当前状态。", source: "Glassnode · Quantifying Bitcoin HODLer Supply", sourceUrl: "https://research.glassnode.com/quantifying-bitcoin-hodler-supply/" },
    en: { label: "HODLer NPC · 30d", meaning: "Shows whether long-held, inactive supply rose over the month or was brought back into circulation. In undervaluation periods, negative values mean less inactive supply.", usage: "Treat it as capitulation or absorption context; when display-only, it does not inform the current state.", source: "Glassnode · Quantifying Bitcoin HODLer Supply", sourceUrl: "https://research.glassnode.com/quantifying-bitcoin-hodler-supply/" },
  },
  spent155: {
    zh: { label: "≥155d 花费价值占比", meaning: "显示当天花费价值里有多少来自放了至少五个月的老币。低估期中升高表示老币活动增多。", usage: "需和 aSOPR 等实际盈亏证据一起看；它不直接等于亏损卖出。", source: "Open Bitcoin Metrics · spent value", sourceUrl: "https://github.com/diegorllanos/open-bitcoin-metrics/tree/main/metrics/obm_spent_value_ge155d_btc_daily" },
    en: { label: "≥155d spent-value share", meaning: "Shows how much of today's spent value came from coins held at least five months. In undervaluation periods, a rise means more old-coin activity.", usage: "Read it with realised-profit/loss evidence such as aSOPR; it does not directly mean loss selling.", source: "Open Bitcoin Metrics · spent value", sourceUrl: "https://github.com/diegorllanos/open-bitcoin-metrics/tree/main/metrics/obm_spent_value_ge155d_btc_daily" },
  },
  seller: {
    zh: { label: "Seller Exhaustion Constant", meaning: "同时观察盈利供应偏低和价格波动收缩，寻找卖方压力可能被消化的线索。", usage: "低值只是一条线索，必须和实际亏损、矿工压力等不同维度交叉阅读。", source: "Glassnode · Indicators", sourceUrl: "https://docs.glassnode.com/basic-api/endpoints/indicators" },
    en: { label: "Seller Exhaustion Constant", meaning: "Combines low profitable supply with contracting price volatility to look for clues that seller pressure may be exhausting.", usage: "A low value is only a clue; cross-check it against realised loss and miner pressure.", source: "Glassnode · Indicators", sourceUrl: "https://docs.glassnode.com/basic-api/endpoints/indicators" },
  },
  puell: {
    zh: { label: "Puell Multiple", meaning: "比较矿工今天新挖币收入和过去一年平均收入。数值越低，矿工收入压力通常越大。", usage: "用来判断压力是否也发生在矿工一侧；减半会机械影响收入，不能单独定位底部。", source: "Glassnode · Puell Multiple", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-issuance/puell-multiple" },
    en: { label: "Puell Multiple", meaning: "Compares miners' daily new-coin revenue with its one-year average. Lower values usually mean more miner income pressure.", usage: "Use it to see whether stress also reaches miners. Halvings mechanically affect issuance, so it cannot locate a bottom alone.", source: "Glassnode · Puell Multiple", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-issuance/puell-multiple" },
  },
  thermo: {
    zh: { label: "Thermocap Multiple · 周期 z", meaning: "把市场总估值放到矿工长期累计获得的报酬背景中，观察当前周期相对自身偏冷还是偏热。", usage: "这是矿工压力背景补充，不是矿工当天利润率。", source: "Glassnode · Thermocap background", sourceUrl: "https://research.glassnode.com/the-week-on-chain-week-38-2021/" },
    en: { label: "Thermocap Multiple · cycle z", meaning: "Places total market value against miners' accumulated long-term rewards to show whether this cycle is relatively cool or hot versus itself.", usage: "It supplements miner-pressure context; it is not a daily miner profitability measure.", source: "Glassnode · Thermocap background", sourceUrl: "https://research.glassnode.com/the-week-on-chain-week-38-2021/" },
  },
  cvdd: {
    zh: { label: "CVDD 接近程度", meaning: "把老币长期未动的时间价值计入一条长期参考线。数字越大，当前价格越靠近这条参考线。", usage: "它只说明接近长期参考区，不能预测价格一定会在这里停止下跌。", source: "Willy Woo · CVDD", sourceUrl: "https://woobull.com/experiments-on-cumulative-destruction/" },
    en: { label: "CVDD proximity", meaning: "Builds a long-term reference line from the time value of old coins that remained unspent. A larger number means price is closer to that line.", usage: "It only shows proximity to a long-term reference area; it cannot predict where a decline will stop.", source: "Willy Woo · CVDD", sourceUrl: "https://woobull.com/experiments-on-cumulative-destruction/" },
  },
  reserve: {
    zh: { label: "Reserve Risk · 周期", meaning: "比较现在价格带来的卖出诱因，与长期持有人坚持不卖累积的信念。较低周期 z 表示相对过去四年更低。", usage: "用作长期压力或承接背景，必须与其他维度共同解释。", source: "Glassnode · Reserve Risk", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-days-destroyed/reserve-risk" },
    en: { label: "Reserve Risk · cycle", meaning: "Compares the current incentive to sell with the conviction accumulated by long-term holders who did not sell. A lower cycle z is lower relative to the past four years.", usage: "Use it as long-term pressure or absorption context and interpret it with other dimensions.", source: "Glassnode · Reserve Risk", sourceUrl: "https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-days-destroyed/reserve-risk" },
  },
};

function interpolate(value: string, values: Record<string, string | number> = {}) {
  return value.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? ""));
}

type StringTextKey = {
  [Key in keyof typeof text.zh]: typeof text.zh[Key] extends string ? Key : never;
}[keyof typeof text.zh];

export function useI18n() {
  const copy = computed(() => text[locale.value]);
  function setLocale(next: Locale) {
    locale.value = next;
    try { window.localStorage.setItem(STORAGE_KEY, next); } catch { /* storage is optional */ }
  }
  function t(key: StringTextKey, values?: Record<string, string | number>) {
    return interpolate(copy.value[key] as string, values);
  }
  function detail(index: number) { return copy.value.detail[index] ?? ""; }
  function state(value: string | null | undefined) { return value ? (states[value]?.[locale.value] ?? value) : "—"; }
  function category(value: Category) { return categories[value.id]?.[locale.value] ?? value.name; }
  function metric(metric: Metric) { return indicatorCopy[metric.id]?.[locale.value] ?? { label: metric.label, meaning: metric.description, usage: metric.caveat, source: metric.source, sourceUrl: "" }; }
  function role(value: string) { return copy.value.roles[value as keyof typeof copy.value.roles] ?? value; }
  function categoryStatus(value: string) { return copy.value.categoryStatus[value as keyof typeof copy.value.categoryStatus] ?? value; }
  return { locale, setLocale, copy, t, detail, state, category, metric, role, categoryStatus };
}
