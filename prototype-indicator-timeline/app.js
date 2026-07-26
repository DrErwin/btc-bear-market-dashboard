/* PROTOTYPE — source-backed indicator validation workbench. All editable state uses browser-local storage. */

const VARIANTS = [
  { key: "A", name: "逐项验证台" },
  { key: "B", name: "指标目录" },
  { key: "C", name: "验证进度" },
];

const COLORS = {
  price: "#e9edf1",
  metric: "#ffb000",
  secondary: ["#35d0ba", "#ff6b4a", "#8fa7ff", "#d69cff"],
  reference: "#ff7043",
  bottom: "#c9d2db",
  entry: "#ff3b30",
};

const LTH_STH_DISTRIBUTION_COLORS = {
  lth_profit: "#3f63d8",
  sth_profit: "#9ab3f4",
  sth_loss: "#f2a4ad",
  lth_loss: "#ec6468",
};

const app = document.querySelector("#app");
const variantLabel = document.querySelector("#variant-label");
const ANALYSIS_STORAGE_KEY = "btc-indicator-validation-analysis-v1";
const VALIDATION_STORAGE_KEY = "btc-indicator-validation-state-v2";
let timelineData;
let selectedMetricId;
let chartInstances = [];
let priceScale = "log";
let indicatorScale = "linear";
let rangePreset = "all";
let showPrice = true;
const referencesByMetric = {};
const directionByMetric = {};
const verdictByMetric = {};
const lineModeByMetric = {};
const analysisByMetric = {};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getVariant() {
  const value = new URLSearchParams(window.location.search).get("variant")?.toUpperCase();
  return VARIANTS.some((item) => item.key === value) ? value : "A";
}

function setVariant(key) {
  const url = new URL(window.location.href);
  url.searchParams.set("variant", key);
  history.replaceState({}, "", url);
  renderVariant(key);
}

function cycleVariant(direction) {
  const current = VARIANTS.findIndex((item) => item.key === getVariant());
  setVariant(VARIANTS[(current + direction + VARIANTS.length) % VARIANTS.length].key);
}

function disposeCharts() {
  chartInstances.forEach((chart) => {
    if (chart && !chart.isDisposed()) chart.dispose();
  });
  chartInstances = [];
}

function initChart(element) {
  const chart = echarts.init(element, null, { renderer: "canvas" });
  chartInstances.push(chart);
  return chart;
}

function metricById(id) {
  return timelineData.metrics.find((item) => item.id === id);
}

function currentMetric() {
  return metricById(selectedMetricId) || timelineData.metrics[0];
}

function formatValue(value, unit) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  if (unit === "percent") return `${(number * 100).toFixed(Math.abs(number) < 0.001 ? 4 : 2)}%`;
  if (unit === "btc") return `${number.toLocaleString("en-US", { maximumFractionDigits: 0 })} BTC`;
  if (unit === "small") return number.toExponential(4);
  if (unit === "zscore") return `${number.toFixed(2)}σ`;
  if (unit === "usd") return `$${number.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  if (Math.abs(number) < 0.001 && number !== 0) return number.toExponential(4);
  return number.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

function formatError(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(3)}%` : "—";
}

function verdictLabel(value) {
  return { unreviewed: "未验证", valid: "有效", watch: "待观察", invalid: "无效" }[value] || value;
}

function verdictClass(value) {
  return `verdict-${value || "unreviewed"}`;
}

function availableLineModes(metric) {
  const modes = [...(metric.line_modes || [])];
  if (metric.id === "lth_sth_normalized_net_realized_pnl" && !modes.includes("distribution")) modes.push("distribution");
  return modes;
}

function loadAnalysisNotes() {
  try {
    const stored = JSON.parse(localStorage.getItem(ANALYSIS_STORAGE_KEY) || "{}");
    return stored && typeof stored === "object" ? stored : {};
  } catch {
    return {};
  }
}

function loadValidationState() {
  try {
    const stored = JSON.parse(localStorage.getItem(VALIDATION_STORAGE_KEY) || "{}");
    return stored && typeof stored === "object" ? stored : {};
  } catch {
    return {};
  }
}

function validationStatePayload() {
  const metrics = {};
  timelineData.metrics.forEach((metric) => {
    metrics[metric.id] = {
      references: referencesByMetric[metric.id],
      direction: directionByMetric[metric.id],
      verdict: verdictByMetric[metric.id],
      lineMode: lineModeByMetric[metric.id],
      analysis: analysisByMetric[metric.id],
    };
  });
  return {
    version: 2,
    ui: { selectedMetricId, priceScale, indicatorScale, rangePreset, showPrice },
    metrics,
  };
}

function saveValidationState() {
  const state = validationStatePayload();
  try {
    localStorage.setItem(VALIDATION_STORAGE_KEY, JSON.stringify(state));
    localStorage.setItem(ANALYSIS_STORAGE_KEY, JSON.stringify(analysisByMetric));
    return true;
  } catch {
    return false;
  }
}

function exportValidationState() {
  saveValidationState();
  const payload = {
    schema: "btc-indicator-validation-config",
    exportedAt: new Date().toISOString(),
    dataset: {
      generatedAt: timelineData.generated_at,
      priceLatest: timelineData.price_quality.end,
      metricCount: timelineData.metrics.length,
    },
    ...validationStatePayload(),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `btc-indicator-config-${payload.exportedAt.slice(0, 10)}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function validReferences(value, fallback) {
  if (!Array.isArray(value) || !value.length) return fallback;
  const references = value
    .map((item) => ({ value: Number(item?.value), label: String(item?.label || "参考线") }))
    .filter((item) => Number.isFinite(item.value));
  return references.length ? references : fallback;
}

function initialiseState() {
  const savedAnalysis = loadAnalysisNotes();
  const savedState = loadValidationState();
  timelineData.metrics.forEach((metric) => {
    const stored = savedState.metrics?.[metric.id] || {};
    const defaults = metric.default_references.map((item) => ({ ...item }));
    referencesByMetric[metric.id] = validReferences(stored.references, defaults);
    directionByMetric[metric.id] = ["below", "above"].includes(stored.direction) ? stored.direction : metric.default_direction;
    verdictByMetric[metric.id] = ["unreviewed", "valid", "watch", "invalid"].includes(stored.verdict) ? stored.verdict : "unreviewed";
    const allowedModes = availableLineModes(metric).length ? availableLineModes(metric) : [metric.default_line_mode || "all"];
    lineModeByMetric[metric.id] = allowedModes.includes(stored.lineMode) ? stored.lineMode : (metric.default_line_mode || "all");
    analysisByMetric[metric.id] = typeof stored.analysis === "string"
      ? stored.analysis
      : (typeof savedAnalysis[metric.id] === "string" ? savedAnalysis[metric.id] : "");
  });
  const ui = savedState.ui || {};
  selectedMetricId = metricById(ui.selectedMetricId)?.id || timelineData.metrics[0].id;
  priceScale = ["linear", "log"].includes(ui.priceScale) ? ui.priceScale : "log";
  indicatorScale = ["linear", "log"].includes(ui.indicatorScale) ? ui.indicatorScale : "linear";
  rangePreset = ["4", "8", "all"].includes(ui.rangePreset) ? ui.rangePreset : "all";
  showPrice = typeof ui.showPrice === "boolean" ? ui.showPrice : true;
  saveValidationState();
}

function rangeStartValue() {
  if (rangePreset === "all") return undefined;
  const last = new Date(`${timelineData.price_quality.end}T00:00:00Z`);
  const years = Number(rangePreset);
  last.setUTCFullYear(last.getUTCFullYear() - years);
  return last.toISOString().slice(0, 10);
}

function thresholdEntries(metric) {
  const references = referencesByMetric[metric.id] || [];
  const threshold = Number(references[0]?.value);
  if (!Number.isFinite(threshold)) return [];
  const direction = directionByMetric[metric.id] || "below";
  const priceMap = new Map(timelineData.price.map(([day, value]) => [day, value]));
  const output = [];
  let previousTriggered = false;
  let lastMarkerTime = -Infinity;
  metric.lines[0].series.forEach(([day, value]) => {
    const triggered = direction === "above" ? value >= threshold : value <= threshold;
    const dayTime = new Date(`${day}T00:00:00Z`).getTime();
    if (triggered && !previousTriggered && priceMap.has(day) && dayTime - lastMarkerTime >= 30 * 86400000) {
      output.push({ value: [day, priceMap.get(day)], metricValue: value });
      lastMarkerTime = dayTime;
    }
    previousTriggered = triggered;
  });
  return output;
}

function thresholdStats(metric) {
  const references = referencesByMetric[metric.id] || [];
  const threshold = Number(references[0]?.value);
  if (!Number.isFinite(threshold)) return { days: 0, episodes: 0, share: 0, hits: 0 };
  const direction = directionByMetric[metric.id] || "below";
  const isTriggered = (value) => direction === "above" ? value >= threshold : value <= threshold;
  let days = 0;
  let episodes = 0;
  let previous = false;
  metric.lines[0].series.forEach(([, value]) => {
    const active = isTriggered(value);
    if (active) days += 1;
    if (active && !previous) episodes += 1;
    previous = active;
  });
  const hits = timelineData.bottoms.filter((bottom) => {
    const center = new Date(`${bottom.date}T00:00:00Z`).getTime();
    return metric.lines[0].series.some(([day, value]) => (
      Math.abs(new Date(`${day}T00:00:00Z`).getTime() - center) <= 180 * 86400000 && isTriggered(value)
    ));
  }).length;
  return { days, episodes, share: days / metric.lines[0].series.length, hits };
}

function axisLabelFormatter(unit) {
  return (value) => {
    if (unit === "percent") return `${(value * 100).toFixed(Math.abs(value) < 0.01 ? 1 : 0)}%`;
    if (unit === "small") return Number(value).toExponential(1);
    if (unit === "btc") return `${Math.round(value / 1000)}k`;
    return Number(value).toLocaleString("en-US", { maximumFractionDigits: 2, notation: "compact" });
  };
}

function lthSthDistributionLines(metric) {
  const definitions = [
    ["lth_profit", "LTH 已实现利润占比"],
    ["sth_profit", "STH 已实现利润占比"],
    ["sth_loss", "STH 已实现亏损占比"],
    ["lth_loss", "LTH 已实现亏损占比"],
  ];
  const sourceLines = Object.fromEntries(definitions.map(([id]) => [id, metric.lines.find((line) => line.id === id)]));
  const dates = sourceLines.lth_profit?.series.map(([day]) => day) || [];
  const valueMaps = Object.fromEntries(definitions.map(([id]) => [id, new Map((sourceLines[id]?.series || []).map(([day, value]) => [day, Math.abs(Number(value))]))]));
  const smoothedValues = Object.fromEntries(definitions.map(([id]) => {
    const values = dates.map((day) => valueMaps[id].get(day) || 0);
    const smoothed = [];
    let rollingSum = 0;
    values.forEach((value, index) => {
      rollingSum += value;
      if (index >= 30) rollingSum -= values[index - 30];
      smoothed.push(rollingSum / Math.min(index + 1, 30));
    });
    return [id, smoothed];
  }));
  const totals = dates.map((_, index) => definitions.reduce((sum, [id]) => sum + smoothedValues[id][index], 0));
  return definitions.map(([id, label]) => ({
    id: `${id}_share`,
    label,
    axis: "indicator",
    mode: "distribution",
    color: LTH_STH_DISTRIBUTION_COLORS[id],
    series: dates.map((day, index) => [day, totals[index] > 0 ? smoothedValues[id][index] / totals[index] : 0]),
  }));
}

function visibleMetricLines(metric) {
  const mode = lineModeByMetric[metric.id] || metric.default_line_mode || "all";
  if (metric.id === "lth_sth_normalized_net_realized_pnl" && mode === "distribution") return lthSthDistributionLines(metric);
  return metric.lines.filter((line) => !line.mode || mode === "all" || line.mode === mode);
}

function indicatorBounds(metric, startDate, endDate) {
  if (lineModeByMetric[metric.id] === "distribution") return { min: 0, max: 1 };
  const values = visibleMetricLines(metric)
    .filter((line) => line.axis === "indicator")
    .flatMap((line) => line.series
      .filter(([day]) => (!startDate || day >= startDate) && (!endDate || day <= endDate))
      .map(([, value]) => Number(value)))
    .filter((value) => Number.isFinite(value) && (indicatorScale !== "log" || value > 0))
    .sort((a, b) => a - b);
  if (!values.length) return {};
  const pick = (probability) => values[Math.min(values.length - 1, Math.max(0, Math.round((values.length - 1) * probability)))];
  let minimum = pick(0.02);
  let maximum = pick(0.98);
  (referencesByMetric[metric.id] || []).forEach((item) => {
    const value = Number(item.value);
    if (Number.isFinite(value) && (indicatorScale !== "log" || value > 0)) {
      minimum = Math.min(minimum, value);
      maximum = Math.max(maximum, value);
    }
  });
  if (indicatorScale === "log") return { min: minimum * 0.88, max: maximum * 1.12 };
  const span = maximum - minimum || Math.max(Math.abs(maximum), 1) * 0.1;
  return { min: minimum - span * 0.08, max: maximum + span * 0.08 };
}

function buildChartOption(metric) {
  if (indicatorScale === "log" && !metric.indicator_log_available) indicatorScale = "linear";
  const distributionMode = lineModeByMetric[metric.id] === "distribution";
  const references = referencesByMetric[metric.id] || [];
  const startValue = rangeStartValue();
  const bounds = indicatorBounds(metric, startValue, timelineData.price_quality.end);
  const entries = thresholdEntries(metric);
  const priceSeries = {
    name: "BTC Price",
    type: "line",
    yAxisIndex: 0,
    data: showPrice ? timelineData.price : [],
    showSymbol: false,
    animation: false,
    lineStyle: { color: COLORS.price, width: 1.35, opacity: 0.9 },
    emphasis: { disabled: true },
    markLine: {
      silent: true,
      symbol: ["none", "none"],
      label: { formatter: "{b}", color: "#8e9aa5", fontSize: 9 },
      lineStyle: { color: "rgba(201,210,219,.28)", type: "dashed", width: 1 },
      data: timelineData.bottoms.map((item) => ({ name: item.label, xAxis: item.date })),
    },
  };
  const visibleLines = visibleMetricLines(metric);
  const indicatorSeries = visibleLines.map((line, index) => ({
    name: line.label,
    type: "line",
    stack: distributionMode ? "lth-sth-realized-flow" : undefined,
    yAxisIndex: line.axis === "price" ? 0 : 1,
    data: line.series,
    showSymbol: false,
    connectNulls: false,
    animation: false,
    areaStyle: distributionMode ? { color: line.color, opacity: 0.94 } : undefined,
    lineStyle: {
      color: distributionMode ? line.color : (index === 0 ? COLORS.metric : COLORS.secondary[(index - 1) % COLORS.secondary.length]),
      width: distributionMode ? 0.5 : (index === 0 ? 1.8 : 1.35),
      opacity: distributionMode ? 0.7 : 0.95,
    },
    itemStyle: { color: distributionMode ? line.color : (index === 0 ? COLORS.metric : COLORS.secondary[(index - 1) % COLORS.secondary.length]) },
    emphasis: { focus: "series" },
  }));
  const entrySeries = {
    name: "阈值进入（30日冷却显示）",
    type: "scatter",
    yAxisIndex: 0,
    data: distributionMode ? [] : entries,
    symbol: "triangle",
    symbolRotate: 180,
    symbolSize: 9,
    itemStyle: { color: COLORS.entry, borderColor: "#fff", borderWidth: 0.7 },
    tooltip: {
      formatter: (params) => `${params.value[0]}<br/>首次进入：${formatValue(params.data.metricValue, metric.unit)}<br/>BTC ${formatValue(params.value[1], "usd")}`,
    },
    z: 8,
  };
  const referenceSeries = (!distributionMode && references.length) ? {
    name: "参考线",
    type: "line",
    yAxisIndex: 1,
    data: [],
    showSymbol: false,
    animation: false,
    silent: true,
    tooltip: { show: false },
    z: 5,
    markLine: {
      silent: true,
      symbol: ["none", "none"],
      label: { formatter: (params) => params.name, color: "#ffd0c4", fontSize: 10, position: "insideEndTop" },
      lineStyle: { color: COLORS.reference, type: "dashed", width: 1.2 },
      data: references.filter((item) => Number.isFinite(Number(item.value))).map((item) => ({
        name: item.label || "参考线",
        yAxis: Number(item.value),
      })),
    },
  } : null;
  return {
    animation: false,
    color: [COLORS.price, COLORS.metric, ...COLORS.secondary],
    legend: { top: 4, left: 12, type: "scroll", textStyle: { color: "#aeb6bd", fontSize: 10 } },
    grid: { left: 84, right: 86, top: 50, bottom: 76 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", label: { backgroundColor: "#2a3137" } },
      backgroundColor: "rgba(15,18,20,.95)",
      borderColor: "#404a52",
      textStyle: { color: "#eef2f5", fontSize: 11 },
      formatter: (params) => {
        const rows = params.filter((item) => item.seriesName !== "阈值进入（30日冷却显示）").map((item) => {
          const isPrice = item.seriesName === "BTC Price" || metric.lines.find((line) => line.label === item.seriesName)?.axis === "price";
          return `${item.marker}${escapeHtml(item.seriesName)}　<b>${formatValue(item.value[1], isPrice ? "usd" : metric.unit)}</b>`;
        });
        return `<strong>${params[0]?.axisValueLabel || ""}</strong><br/>${rows.join("<br/>")}`;
      },
    },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: "#46515a" } },
      axisLabel: { color: "#7f8a93", hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: priceScale === "log" ? "log" : "value",
        position: distributionMode ? "right" : "left",
        name: `BTC USD · ${priceScale === "log" ? "LOG" : "LINEAR"}`,
        nameTextStyle: { color: "#8f9aa3", fontSize: 10 },
        min: priceScale === "log" ? undefined : "dataMin",
        scale: true,
        axisLine: { show: true, lineStyle: { color: "#65727c" } },
        axisLabel: { color: "#9aa4ac", formatter: axisLabelFormatter("usd") },
        splitLine: { lineStyle: { color: "rgba(255,255,255,.055)" } },
      },
      {
        type: indicatorScale === "log" ? "log" : "value",
        position: distributionMode ? "left" : "right",
        name: distributionMode ? "30日均值已实现盈亏构成 · 100%" : `${metric.label} · ${indicatorScale === "log" ? "LOG" : "LINEAR"}`,
        nameTextStyle: { color: "#d7a743", fontSize: 10 },
        scale: true,
        ...bounds,
        axisLine: { show: true, lineStyle: { color: "#b48223" } },
        axisLabel: { color: "#d7a743", formatter: axisLabelFormatter(metric.unit) },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: "inside", filterMode: "filter", startValue },
      {
        type: "slider", filterMode: "filter", startValue, bottom: 20, height: 25,
        borderColor: "#3a444c", fillerColor: "rgba(255,176,0,.12)", handleStyle: { color: "#ffb000" },
        textStyle: { color: "#7f8a93" },
      },
    ],
    series: [priceSeries, ...indicatorSeries, entrySeries, referenceSeries].filter(Boolean),
  };
}

function renderFocusChart(metric) {
  const element = document.querySelector("#focus-chart");
  if (!element) return;
  disposeCharts();
  const chart = initChart(element);
  chart.setOption(buildChartOption(metric), true);
  chart.on("datazoom", (event) => {
    const zoom = event.batch?.[0] || event;
    const startPercent = Number.isFinite(Number(zoom.start)) ? Number(zoom.start) : 0;
    const endPercent = Number.isFinite(Number(zoom.end)) ? Number(zoom.end) : 100;
    const dates = metric.lines[0].series;
    const startIndex = Math.max(0, Math.floor((dates.length - 1) * startPercent / 100));
    const endIndex = Math.min(dates.length - 1, Math.ceil((dates.length - 1) * endPercent / 100));
    const visibleBounds = indicatorBounds(metric, dates[startIndex]?.[0], dates[endIndex]?.[0]);
    chart.setOption({ yAxis: [{}, visibleBounds] }, { lazyUpdate: true });
  });
}

function metricNavHtml(metric) {
  const index = timelineData.metrics.findIndex((item) => item.id === metric.id);
  return `<div class="metric-nav-head">
    <span>${index + 1} / ${timelineData.metrics.length}</span>
    <div><button type="button" data-metric-step="-1">← 上一个</button><button type="button" data-metric-step="1">下一个 →</button></div>
  </div>
  <div class="metric-list">${timelineData.metrics.map((item, itemIndex) => `
    <button type="button" class="metric-button ${item.id === metric.id ? "active" : ""}" data-metric-id="${item.id}">
      <small>${String(itemIndex + 1).padStart(2, "0")} · ${escapeHtml(item.method)}</small>
      <strong>${escapeHtml(item.label)}</strong>
      <i class="${verdictClass(verdictByMetric[item.id])}">${verdictLabel(verdictByMetric[item.id])}</i>
    </button>`).join("")}</div>`;
}

function scaleButton(axis, value, label, disabled = false) {
  const current = axis === "price" ? priceScale : indicatorScale;
  return `<button type="button" data-axis="${axis}" data-scale="${value}" class="${current === value ? "active" : ""}" ${disabled ? "disabled" : ""}>${label}</button>`;
}

function referenceEditorHtml(metric) {
  const references = referencesByMetric[metric.id];
  return `<div class="reference-editor">
    <div class="reference-title"><div><strong>参考线</strong><span>第一条同时生成价格图上的“首次进入”标记</span></div><button type="button" data-reference-add>＋ 添加</button></div>
    ${references.map((item, index) => `<div class="reference-row">
      <b>${index === 0 ? "触发" : index + 1}</b>
      <input type="number" step="any" value="${Number(item.value)}" data-reference-value="${index}" aria-label="参考线数值" />
      <input type="text" value="${escapeHtml(item.label)}" data-reference-label="${index}" aria-label="参考线名称" />
      <button type="button" data-reference-remove="${index}" ${references.length === 1 ? "disabled" : ""}>×</button>
    </div>`).join("")}
    <div class="reference-actions">
      <label>触发方向<select data-direction><option value="below" ${directionByMetric[metric.id] === "below" ? "selected" : ""}>低于参考线</option><option value="above" ${directionByMetric[metric.id] === "above" ? "selected" : ""}>高于参考线</option></select></label>
      <button type="button" data-reference-reset>恢复默认值</button>
    </div>
  </div>`;
}

function methodCheckHtml(metric) {
  const check = metric.reproduction_check;
  if (!check || !check.overlap_rows) return `<span>该项使用公开成品线或无同公式成品对照</span>`;
  return `<span>同日核对 ${check.overlap_rows.toLocaleString("en-US")} 行</span>
    <strong>中位相对差 ${formatError(check.median_relative_error)}</strong>
    <span>P95 ${formatError(check.p95_relative_error)}</span>`;
}

function thresholdStatsHtml(metric) {
  const stats = thresholdStats(metric);
  return `<div class="stat"><span>触发日占比</span><strong>${(stats.share * 100).toFixed(1)}%</strong></div>
    <div class="stat"><span>独立进入次数</span><strong>${stats.episodes}</strong></div>
    <div class="stat"><span>熊底 ±180日命中</span><strong>${stats.hits} / ${timelineData.bottoms.length}</strong></div>
    <div class="stat"><span>当前值</span><strong>${formatValue(metric.latest_value, metric.unit)}</strong></div>`;
}

function analysisEditorHtml(metric) {
  const note = analysisByMetric[metric.id] || "";
  return `<section class="analysis-card">
    <div class="analysis-title">
      <div><strong>我的分析说明</strong><span>每个指标独立记录；保存空间取决于当前浏览器和当前地址</span></div>
      <span class="analysis-save-state" data-analysis-save-state>已保存</span>
    </div>
    <textarea data-analysis-note aria-label="${escapeHtml(metric.label)}分析说明" placeholder="记录你对信号含义、历史表现、误判区间和是否采用该指标的判断……">${escapeHtml(note)}</textarea>
    <div class="analysis-meta"><span>切换指标或刷新页面不会丢失</span><span><b data-analysis-count>${note.length}</b> 字</span></div>
  </section>`;
}

function refreshThresholdVisual(metric) {
  const stats = document.querySelector(".threshold-stats");
  if (stats) stats.innerHTML = thresholdStatsHtml(metric);
  renderFocusChart(metric);
}

function renderWorkbench() {
  saveValidationState();
  const metric = currentMetric();
  const index = timelineData.metrics.findIndex((item) => item.id === metric.id);
  app.innerHTML = `<main class="workbench">
    <header class="topbar">
      <div><div class="prototype-badge">PROTOTYPE / INDICATOR VALIDATION</div><h1>BTC 指标验证台</h1></div>
      <div class="topbar-actions">
        <div class="freshness"><span>数据生成</span><strong>${timelineData.generated_at.slice(0, 10)}</strong><span>BTC最新</span><strong>${timelineData.price_quality.end}</strong></div>
        <button type="button" class="export-config-button" data-export-config>↓ 导出配置 JSON</button>
      </div>
    </header>
    <div class="workbench-grid">
      <aside class="metric-rail">${metricNavHtml(metric)}</aside>
      <section class="validation-stage">
        <div class="metric-heading">
          <div><span class="sequence">INDICATOR ${String(index + 1).padStart(2, "0")}</span><h2>${escapeHtml(metric.label)}</h2><p>${escapeHtml(metric.description)}</p></div>
          <div class="verdict-control" aria-label="人工验证结论">
            ${["valid", "watch", "invalid"].map((value) => `<button type="button" data-verdict="${value}" class="${verdictByMetric[metric.id] === value ? "active" : ""} ${verdictClass(value)}">${verdictLabel(value)}</button>`).join("")}
          </div>
        </div>
        <div class="chart-controls">
          <div class="control-group"><span>BTC坐标</span>${scaleButton("price", "linear", "普通")}${scaleButton("price", "log", "对数")}</div>
          <div class="control-group"><span>指标坐标</span>${scaleButton("indicator", "linear", "普通")}${scaleButton("indicator", "log", "对数", !metric.indicator_log_available)}</div>
          <div class="control-group"><span>区间</span>${["4", "8", "all"].map((value) => `<button type="button" data-range="${value}" class="${rangePreset === value ? "active" : ""}">${value === "all" ? "全部" : `${value}年`}</button>`).join("")}</div>
          ${availableLineModes(metric).length > 1 ? `<div class="control-group line-mode-control"><span>LTH/STH</span>${availableLineModes(metric).map((mode) => `<button type="button" data-line-mode="${mode}" class="${lineModeByMetric[metric.id] === mode ? "active" : ""}">${mode === "net" ? "净盈亏" : mode === "split" ? "盈亏拆分" : "100%分布"}</button>`).join("")}</div>` : ""}
          ${lineModeByMetric[metric.id] === "distribution" ? `<small class="distribution-note">30日均值 · 全链150日 cohort · 非交易所流入口径</small>` : ""}
          <small class="auto-axis-note">纵轴随可见时间自动调整</small>
          <label class="price-toggle"><input type="checkbox" data-show-price ${showPrice ? "checked" : ""}/>显示BTC价格</label>
        </div>
        <div id="focus-chart" role="img" aria-label="BTC价格与${escapeHtml(metric.label)}叠加时间轴"></div>
        <div class="threshold-stats">${thresholdStatsHtml(metric)}</div>
        <div class="details-grid">
          <section class="method-card"><span>计算方法</span><h3>${escapeHtml(metric.formula)}</h3><p>${escapeHtml(metric.source)} · ${escapeHtml(metric.method)}</p>${metric.caveat ? `<em>${escapeHtml(metric.caveat)}</em>` : ""}<div class="check-strip">${methodCheckHtml(metric)}</div></section>
          <section>${referenceEditorHtml(metric)}</section>
        </div>
        ${analysisEditorHtml(metric)}
        <div class="memory-note"><strong>持续保存请固定使用：</strong>运行 <code>python .\prototype-indicator-timeline\serve.py</code> 后，从 <code>http://127.0.0.1:8123</code> 打开。直接双击 <code>index.html</code>（file://）、使用 localhost、改端口或换浏览器配置都会形成不同或不稳定的保存空间。所有编辑均自动保存在当前浏览器：参考线、触发方向、验证结论、显示设置和分析说明。全样本分位线含前视信息，只用于肉眼探索。</div>
      </section>
    </div>
  </main>`;
  bindWorkbench(metric);
  renderFocusChart(metric);
}

function bindWorkbench(metric) {
  document.querySelector("[data-export-config]")?.addEventListener("click", (event) => {
    const button = event.currentTarget;
    exportValidationState();
    button.textContent = "✓ 已导出";
    setTimeout(() => { button.textContent = "↓ 导出配置 JSON"; }, 1200);
  });
  document.querySelectorAll("[data-metric-id]").forEach((button) => button.addEventListener("click", () => {
    selectedMetricId = button.dataset.metricId;
    indicatorScale = "linear";
    renderWorkbench();
  }));
  document.querySelectorAll("[data-metric-step]").forEach((button) => button.addEventListener("click", () => {
    const current = timelineData.metrics.findIndex((item) => item.id === selectedMetricId);
    const next = (current + Number(button.dataset.metricStep) + timelineData.metrics.length) % timelineData.metrics.length;
    selectedMetricId = timelineData.metrics[next].id;
    indicatorScale = "linear";
    renderWorkbench();
  }));
  document.querySelectorAll("[data-axis][data-scale]").forEach((button) => button.addEventListener("click", () => {
    if (button.disabled) return;
    if (button.dataset.axis === "price") priceScale = button.dataset.scale;
    else indicatorScale = button.dataset.scale;
    renderWorkbench();
  }));
  document.querySelectorAll("[data-range]").forEach((button) => button.addEventListener("click", () => {
    rangePreset = button.dataset.range;
    renderWorkbench();
  }));
  document.querySelectorAll("[data-line-mode]").forEach((button) => button.addEventListener("click", () => {
    lineModeByMetric[metric.id] = button.dataset.lineMode;
    renderWorkbench();
  }));
  document.querySelector("[data-show-price]")?.addEventListener("change", (event) => {
    showPrice = event.target.checked;
    renderWorkbench();
  });
  document.querySelectorAll("[data-verdict]").forEach((button) => button.addEventListener("click", () => {
    verdictByMetric[metric.id] = button.dataset.verdict;
    renderWorkbench();
  }));
  document.querySelectorAll("[data-reference-value]").forEach((input) => input.addEventListener("input", () => {
    const value = Number(input.value);
    if (Number.isFinite(value)) referencesByMetric[metric.id][Number(input.dataset.referenceValue)].value = value;
    saveValidationState();
    refreshThresholdVisual(metric);
  }));
  document.querySelectorAll("[data-reference-label]").forEach((input) => input.addEventListener("input", () => {
    referencesByMetric[metric.id][Number(input.dataset.referenceLabel)].label = input.value || "参考线";
    saveValidationState();
    refreshThresholdVisual(metric);
  }));
  document.querySelectorAll("[data-reference-remove]").forEach((button) => button.addEventListener("click", () => {
    if (referencesByMetric[metric.id].length > 1) referencesByMetric[metric.id].splice(Number(button.dataset.referenceRemove), 1);
    renderWorkbench();
  }));
  document.querySelector("[data-reference-add]")?.addEventListener("click", () => {
    referencesByMetric[metric.id].push({ value: metric.latest_value, label: "自定义参考线" });
    renderWorkbench();
  });
  document.querySelector("[data-reference-reset]")?.addEventListener("click", () => {
    referencesByMetric[metric.id] = metric.default_references.map((item) => ({ ...item }));
    directionByMetric[metric.id] = metric.default_direction;
    renderWorkbench();
  });
  document.querySelector("[data-direction]")?.addEventListener("change", (event) => {
    directionByMetric[metric.id] = event.target.value;
    renderWorkbench();
  });
  document.querySelector("[data-analysis-note]")?.addEventListener("input", (event) => {
    analysisByMetric[metric.id] = event.target.value;
    const saved = saveValidationState();
    const count = document.querySelector("[data-analysis-count]");
    const state = document.querySelector("[data-analysis-save-state]");
    if (count) count.textContent = String(event.target.value.length);
    if (state) {
      state.textContent = saved ? "已保存" : "保存失败";
      state.classList.toggle("save-error", !saved);
    }
  });
}

function renderCatalog() {
  saveValidationState();
  app.innerHTML = `<main class="catalog-view">
    <header class="catalog-head"><div class="prototype-badge">FLAT INVENTORY / NO FAMILIES</div><h1>19个可实现指标，逐个看。</h1><p>点击任意指标进入叠加验证台。目录只说明数据与公式，不预设谁应该进入最终系统。</p></header>
    <section class="catalog-grid">${timelineData.metrics.map((metric, index) => `
      <article class="catalog-card" data-open-metric="${metric.id}">
        <div class="catalog-index">${String(index + 1).padStart(2, "0")}</div>
        <div class="catalog-status ${verdictClass(verdictByMetric[metric.id])}">${verdictLabel(verdictByMetric[metric.id])}</div>
        <h2>${escapeHtml(metric.label)}</h2><p>${escapeHtml(metric.description)}</p>
        <dl><div><dt>方法</dt><dd>${escapeHtml(metric.method)}</dd></div><div><dt>覆盖</dt><dd>${metric.quality.start} → ${metric.quality.end}</dd></div><div><dt>默认主线</dt><dd>${escapeHtml(metric.default_references[0]?.label || "—")} · ${formatValue(metric.default_references[0]?.value, metric.unit)}</dd></div></dl>
        <button type="button">进入验证 →</button>
      </article>`).join("")}</section>
  </main>`;
  document.querySelectorAll("[data-open-metric]").forEach((card) => card.addEventListener("click", () => {
    selectedMetricId = card.dataset.openMetric;
    setVariant("A");
  }));
}

function renderReviewBoard() {
  saveValidationState();
  const counts = ["valid", "watch", "invalid", "unreviewed"].reduce((result, key) => {
    result[key] = Object.values(verdictByMetric).filter((value) => value === key).length;
    return result;
  }, {});
  app.innerHTML = `<main class="review-view">
    <header class="review-head"><div><div class="prototype-badge">LOCALLY SAVED REVIEW BOARD</div><h1>验证进度</h1></div><div class="review-counts"><span>有效 <b>${counts.valid}</b></span><span>待观察 <b>${counts.watch}</b></span><span>无效 <b>${counts.invalid}</b></span><span>未验证 <b>${counts.unreviewed}</b></span></div></header>
    <div class="review-table-wrap"><table class="review-table"><thead><tr><th>#</th><th>指标</th><th>计算方式</th><th>数据覆盖</th><th>复算核对</th><th>参考线</th><th>人工结论</th><th></th></tr></thead><tbody>
      ${timelineData.metrics.map((metric, index) => `<tr><td>${String(index + 1).padStart(2, "0")}</td><td><strong>${escapeHtml(metric.label)}</strong><small>${escapeHtml(metric.source)}</small></td><td>${escapeHtml(metric.method)}</td><td>${metric.quality.start}<br/>${metric.quality.end}</td><td>${metric.reproduction_check?.median_relative_error != null ? `中位差 ${formatError(metric.reproduction_check.median_relative_error)}` : "—"}</td><td>${referencesByMetric[metric.id].map((item) => formatValue(item.value, metric.unit)).join(" / ")}</td><td><i class="${verdictClass(verdictByMetric[metric.id])}">${verdictLabel(verdictByMetric[metric.id])}</i></td><td><button type="button" data-review-metric="${metric.id}">验证</button></td></tr>`).join("")}
    </tbody></table></div><p class="review-footnote">验证结论、参考线和分析说明会自动保存。请固定通过 serve.py 的 http://127.0.0.1:8123 地址使用；file://、localhost、不同端口或浏览器配置不会共享保存空间。</p>
  </main>`;
  document.querySelectorAll("[data-review-metric]").forEach((button) => button.addEventListener("click", () => {
    selectedMetricId = button.dataset.reviewMetric;
    setVariant("A");
  }));
}

function renderVariant(key) {
  disposeCharts();
  const variant = VARIANTS.find((item) => item.key === key) || VARIANTS[0];
  variantLabel.textContent = `${variant.key} — ${variant.name}`;
  if (key === "B") renderCatalog();
  else if (key === "C") renderReviewBoard();
  else renderWorkbench();
  window.scrollTo({ top: 0, behavior: "instant" });
}

document.querySelectorAll("#prototype-switcher button").forEach((button) => {
  button.addEventListener("click", () => cycleVariant(button.dataset.direction === "next" ? 1 : -1));
});

window.addEventListener("keydown", (event) => {
  if (event.target.matches("input, textarea, select, [contenteditable='true']")) return;
  if (event.key === "ArrowLeft") cycleVariant(-1);
  if (event.key === "ArrowRight") cycleVariant(1);
});

window.addEventListener("resize", () => chartInstances.forEach((chart) => chart.resize()));

try {
  if (!window.__TIMELINE_DATA__) throw new Error("timeline-data.js 没有生成，请运行 build_data.py");
  timelineData = window.__TIMELINE_DATA__;
  initialiseState();
  renderVariant(getVariant());
} catch (error) {
  app.innerHTML = `<main class="error-screen"><div><div class="prototype-badge">PROTOTYPE FAILED</div><h1>指标数据没有展开</h1><pre>${escapeHtml(error.stack || error)}</pre><p>运行：python prototype-indicator-timeline\\serve.py --refresh</p></div></main>`;
}
