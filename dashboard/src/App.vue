<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppHeader from "./components/AppHeader.vue";
import AiEvaluation from "./components/AiEvaluation.vue";
import StageAxis from "./components/StageAxis.vue";
import CategoryGrid from "./components/CategoryGrid.vue";
import MetricList from "./components/MetricList.vue";
import SharedChart from "./components/SharedChart.vue";
import MetricExplanation from "./components/MetricExplanation.vue";
import { loadDashboardData } from "./composables/useDashboardData";
import type { Analysis, CategoryAssessment, DashboardData, Metric } from "./types";

const data = ref<DashboardData | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const activeCategoryId = ref("valuation");
const activeMetricId = ref("mvrv");
const detailsOpen = ref(false);
const methodOpen = ref(false);

onMounted(async () => {
  try {
    data.value = await loadDashboardData();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "本地数据暂时无法读取。";
  } finally {
    loading.value = false;
  }
});

const analysis = computed<Analysis | null>(() => {
  if (!data.value) return null;
  return data.value.analysis ?? data.value.fallback;
});

const isFallback = computed(() => Boolean(data.value && !data.value.status.today_available && data.value.fallback));
const assessments = computed<CategoryAssessment[]>(() => analysis.value?.categories ?? []);
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
      <div v-if="loading" class="loading-state" role="status">正在读取固定快照…</div>
      <div v-else-if="error" class="fatal-state" role="alert">
        <strong>看板暂时无法读取</strong>
        <span>{{ error }}</span>
      </div>

      <template v-else-if="data">
        <section class="evaluation-shell">
          <AiEvaluation
            :analysis="analysis"
            :fallback="data.fallback"
            :today-available="data.status.today_available"
            :last-success-date="data.status.last_success_date"
            :details-open="detailsOpen"
            @toggle-details="detailsOpen = !detailsOpen"
          />
          <StageAxis :current-stage="analysis?.stage ?? null" />

          <section v-if="analysis && detailsOpen" class="detail-drawer" aria-label="详细分析">
            <article>
              <span class="eyebrow">支持证据</span>
              <p>{{ analysis.detailed.supporting }}</p>
            </article>
            <article>
              <span class="eyebrow">反面或未完成证据</span>
              <p>{{ analysis.detailed.contrary }}</p>
            </article>
            <article>
              <span class="eyebrow">下一阶段确认条件</span>
              <p>{{ analysis.detailed.next_stage }}</p>
            </article>
          </section>
        </section>

        <section class="evidence-board" aria-labelledby="board-title">
          <div class="section-heading">
            <div>
              <span class="eyebrow">分类指标看板 / 16 个固定指标</span>
              <h2 id="board-title">从证据结构进入单项检查</h2>
            </div>
            <p>先看六类状态，再选择一个指标查看共享图表与阈值语义。</p>
          </div>

          <CategoryGrid
            :categories="data.snapshot.categories"
            :assessments="assessments"
            :active-category-id="activeCategoryId"
            @select="selectCategory"
          />

          <div class="workbench">
            <aside class="metric-rail" aria-label="分类指标">
              <div class="rail-heading">
                <div>
                  <span class="eyebrow">当前分类</span>
                  <h3>{{ activeCategory?.name }}</h3>
                </div>
                <span class="rail-count">{{ visibleMetrics.length }} 项</span>
              </div>
              <MetricList
                :metrics="visibleMetrics"
                :active-metric-id="activeMetricId"
                @select="selectMetric"
              />
              <p class="rail-note">核心 / 辅助角色用文字标注；卡片只显示当前档位，不显示距离。</p>
            </aside>

            <div v-if="activeMetric && activeCategory" class="chart-column">
              <SharedChart :metric="activeMetric" :series="data.series" />
              <MetricExplanation :metric="activeMetric" :category="activeCategory" />
            </div>
          </div>
        </section>
      </template>
    </main>

    <footer class="site-footer">
      <div>
        <strong>研究导向的周期证据</strong>
        <span>看板解释当前快照，不宣称识别确切最低点。</span>
      </div>
      <span>仅作公开研究参考 · 不构成交易建议</span>
    </footer>

    <div v-if="methodOpen" class="dialog-backdrop" role="presentation" @click="closeMethod">
      <section class="method-dialog" role="dialog" aria-modal="true" aria-labelledby="method-title">
        <button class="dialog-close" type="button" aria-label="关闭方法说明" @click="methodOpen = false">×</button>
        <span class="eyebrow">方法边界</span>
        <h2 id="method-title">把复杂指标变成可检查的证据结构</h2>
        <p>看板每天使用一份固定的指标快照，先分别读取六类证据状态，再归纳为一个市场阶段。当前值、阈值语义和来源限制始终留在指标区域，方便你自己复核。</p>
        <p>图表仅用于检查指标和 BTC 价格的共同时间范围；它与每日阶段分析分开，刷新页面不会重新生成结论。</p>
        <button class="primary-button" type="button" @click="methodOpen = false">返回看板</button>
      </section>
    </div>
  </div>
</template>
