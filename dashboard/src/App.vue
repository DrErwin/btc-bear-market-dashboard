<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppHeader from "./components/AppHeader.vue";
import AiEvaluation from "./components/AiEvaluation.vue";
import DualAxisSummary from "./components/DualAxisSummary.vue";
import CategoryGrid from "./components/CategoryGrid.vue";
import MetricList from "./components/MetricList.vue";
import SharedChart from "./components/SharedChart.vue";
import MetricExplanation from "./components/MetricExplanation.vue";
import { loadDashboardData } from "./composables/useDashboardData";
import type { Analysis, CategoryAssessment, DashboardData, Metric } from "./types";
import { useI18n } from "./i18n";

const data = ref<DashboardData | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const activeCategoryId = ref("valuation");
const activeMetricId = ref("mvrv");
const detailsOpen = ref(false);
const methodOpen = ref(false);
const railCollapsed = ref(false);
const { locale, t, detail, category, metric: metricCopy, state } = useI18n();

onMounted(async () => {
  try {
    data.value = await loadDashboardData();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "本地数据暂时无法读取。";
  } finally {
    loading.value = false;
  }
});

const chineseAnalysis = computed<Analysis | null>(() => {
  if (!data.value) return null;
  return data.value.analysis ?? data.value.fallback;
});
const analysis = computed<Analysis | null>(() => {
  if (!data.value || locale.value !== "en") return chineseAnalysis.value;
  return data.value.analysis
    ? data.value.analysisEn ?? data.value.analysis
    : data.value.fallbackEn ?? data.value.fallback;
});
const englishAnalysisUnavailable = computed(() => Boolean(
  locale.value === "en" && (data.value?.analysis ? !data.value.analysisEn : data.value?.fallback ? !data.value.fallbackEn : false),
));

const isFallback = computed(() => Boolean(data.value && !data.value.status.today_available && data.value.fallback));
const assessments = computed<CategoryAssessment[]>(() => analysis.value?.categories ?? []);
const detailSections = computed(() => {
  const current = analysis.value;
  if (!current) return [];
  const detailed = current.detailed ?? {};
  const quality = data.value?.evidenceBrief?.data_quality;
  const qualityText = quality
    ? locale.value === "en"
      ? `Data status: ${data.value?.status.data_insufficient ? "some axis inputs are unavailable" : "both axes have usable inputs"}. Metric cards and the timeline show remaining gaps.`
      : `数据状态：${data.value?.status.data_insufficient ? "部分轴暂时不足" : "两条轴均有可用输入"}。缺口由指标卡和时间线继续说明。`
    : undefined;
  const sections: Array<{ id: string; label: string; text: string | undefined }> = [
    { id: "pressure_reason", label: detail(0), text: detailed.pressure_reason },
    { id: "bottoming_reason", label: detail(1), text: detailed.bottoming_reason },
    { id: "evidence_timeline", label: detail(2), text: detailed.evidence_timeline },
    { id: "contrary_or_gaps", label: detail(3), text: detailed.contrary_or_gaps ?? qualityText },
    { id: "repair_exit", label: detail(4), text: detailed.repair_exit },
    { id: "next_evidence", label: detail(5), text: detailed.next_evidence },
  ];
  return sections.filter((section): section is { id: string; label: string; text: string } => Boolean(section.text?.trim()));
});
const activeCategory = computed(() => data.value?.snapshot.categories.find((category) => category.id === activeCategoryId.value) ?? data.value?.snapshot.categories[0]);
const activeMetric = computed<Metric | null>(() => {
  if (!data.value) return null;
  return data.value.snapshot.metrics.find((metric) => metric.id === activeMetricId.value) ?? data.value.snapshot.metrics[0] ?? null;
});
const visibleMetrics = computed(() => data.value?.snapshot.metrics.filter((metric) => metric.category === activeCategoryId.value) ?? []);

function selectCategory(categoryId: string) {
  activeCategoryId.value = categoryId;
  const firstMetric = data.value?.snapshot.metrics.find((metric) => metric.category === categoryId);
  if (firstMetric) activeMetricId.value = firstMetric.id;
}

function selectMetric(metricId: string) {
  const metric = data.value?.snapshot.metrics.find((candidate) => candidate.id === metricId);
  if (!metric) return;
  activeMetricId.value = metric.id;
  activeCategoryId.value = metric.category;
}

function closeMethod(event: MouseEvent) {
  if (event.target === event.currentTarget) methodOpen.value = false;
}
</script>

<template>
  <div id="top" class="app-frame">
    <AppHeader
      :analysis-date="analysis?.analysis_date ?? null"
      :is-fallback="isFallback"
      @open-method="methodOpen = true"
    />

    <main>
      <div v-if="loading" class="loading-state" role="status">{{ t("readPacket") }}</div>
      <div v-else-if="error" class="fatal-state" role="alert">
        <strong>{{ t("cannotRead") }}</strong>
        <span>{{ error }}</span>
      </div>

      <template v-else-if="data">
        <section class="evaluation-shell">
          <AiEvaluation
            :analysis="analysis"
            :fallback="data.fallback"
            :today-available="data.status.today_available"
            :last-success-date="data.status.last_success_date"
            :data-insufficient="data.status.data_insufficient"
            :english-unavailable="englishAnalysisUnavailable"
            :details-open="detailsOpen"
            @toggle-details="detailsOpen = !detailsOpen"
          />
          <DualAxisSummary
            :pressure-state="analysis?.pressure_state ?? null"
            :bottoming-state="analysis?.bottoming_state ?? null"
          />

          <section v-if="analysis && detailsOpen && detailSections.length" class="detail-drawer" aria-label="Detailed analysis">
            <article v-for="section in detailSections" :key="section.id">
              <span class="eyebrow">{{ section.label }}</span>
              <p>{{ section.text }}</p>
            </article>
          </section>
        </section>

        <section class="evidence-board" aria-labelledby="board-title">
          <div class="section-heading">
            <div>
              <span class="eyebrow">{{ t("boardEyebrow") }}</span>
              <h2 id="board-title">{{ t("boardTitle") }}</h2>
            </div>
            <p>{{ t("boardText") }}</p>
          </div>

          <CategoryGrid
            :categories="data.snapshot.categories"
            :assessments="assessments"
            :active-category-id="activeCategoryId"
            @select="selectCategory"
          />

          <div class="workbench" :class="{ 'is-rail-collapsed': railCollapsed }">
            <nav v-if="railCollapsed" class="metric-tabs-compact" aria-label="Metric selection">
              <button
                v-for="metric in visibleMetrics"
                :key="metric.id"
                type="button"
                class="metric-tab"
                :class="{ 'is-active': metric.id === activeMetricId }"
                :aria-pressed="metric.id === activeMetricId"
                @click="selectMetric(metric.id)"
              >
                {{ metricCopy(metric).label }}
              </button>
              <button type="button" class="rail-expand-btn" @click="railCollapsed = false">{{ t("expandMetrics") }}</button>
            </nav>

            <aside v-show="!railCollapsed" class="metric-rail" aria-label="Category metrics">
              <div class="rail-heading">
                <div>
                  <span class="eyebrow">{{ t("currentCategory") }}</span>
                  <h3 v-if="activeCategory">{{ category(activeCategory) }}</h3>
                </div>
                <div class="rail-heading-actions">
                  <span class="rail-count">{{ visibleMetrics.length }} {{ t("itemCount") }}</span>
                  <button class="rail-collapse-btn" type="button" @click="railCollapsed = true">{{ t("collapseMetrics") }}</button>
                </div>
              </div>
              <MetricList
                :metrics="visibleMetrics"
                :active-metric-id="activeMetricId"
                @select="selectMetric"
              />
              <p class="rail-note">{{ t("railNote") }}</p>
            </aside>

            <div v-if="activeMetric && activeCategory" class="chart-column">
              <SharedChart :metric="activeMetric" :series="data.series" :bars="data.bars" :bottoms="data.bottoms" />
              <MetricExplanation :metric="activeMetric" :category="activeCategory" />
            </div>
          </div>
        </section>
      </template>
    </main>

    <footer class="site-footer">
      <div>
        <strong>{{ t("footerTitle") }}</strong>
        <span>{{ t("footerText") }}</span>
      </div>
      <span>{{ t("disclaimer") }}</span>
    </footer>

    <div v-if="methodOpen" class="dialog-backdrop" role="presentation" @click="closeMethod">
      <section class="method-dialog" role="dialog" aria-modal="true" aria-labelledby="method-title">
        <button class="dialog-close" type="button" aria-label="Close method dialog" @click="methodOpen = false">×</button>
        <span class="eyebrow">{{ t("methodEyebrow") }}</span>
        <h2 id="method-title">{{ t("methodTitle") }}</h2>
        <p>{{ t("methodText1") }}</p>
        <p>{{ t("methodText2") }}</p>
        <button class="primary-button" type="button" @click="methodOpen = false">{{ t("returnDashboard") }}</button>
      </section>
    </div>
  </div>
</template>

<style scoped>
.rail-heading-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
