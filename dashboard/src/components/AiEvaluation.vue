<script setup lang="ts">
import type { Analysis } from "../types";
import { useI18n } from "../i18n";

const props = defineProps<{
  analysis: Analysis | null;
  fallback: Analysis | null;
  todayAvailable: boolean;
  lastSuccessDate: string | null;
  detailsOpen: boolean;
  dataInsufficient?: boolean;
  englishUnavailable?: boolean;
}>();

const emit = defineEmits<{ toggleDetails: [] }>();
const { t, detail, state } = useI18n();

function statusLabel() {
  if (props.todayAvailable) return t("savedToday");
  if (props.fallback) return `回退至 ${props.fallback.analysis_date}`;
  return t("noConclusion");
}
</script>

<template>
  <section class="evaluation" aria-labelledby="evaluation-title">
    <div v-if="dataInsufficient" class="availability-banner" role="status">
      <span class="availability-icon" aria-hidden="true">!</span>
      <div>
        <strong>{{ t("insufficient") }}</strong>
        <span>{{ t("insufficientText") }}</span>
      </div>
      <span class="availability-note">{{ t("waitData") }}</span>
    </div>

    <div v-else-if="!todayAvailable" class="availability-banner" :class="{ 'has-fallback': fallback }" role="status">
      <span class="availability-icon" aria-hidden="true">!</span>
      <div>
        <strong>{{ t("aiUnavailable") }}</strong>
        <span v-if="fallback">{{ t("fallbackText", { date: fallback.analysis_date }) }}</span>
        <span v-else>{{ t("noFallbackText") }}</span>
      </div>
      <span class="availability-note">{{ statusLabel() }}</span>
    </div>

    <template v-if="analysis">
      <div v-if="englishUnavailable" class="availability-banner" role="status">
        <span class="availability-icon" aria-hidden="true">!</span>
        <div><strong>{{ t("englishUnavailable") }}</strong><span>{{ t("englishUnavailableText") }}</span></div>
      </div>
      <div class="evaluation-head dual-state-head">
        <div class="state-hero pressure-hero">
          <span class="eyebrow">{{ t("pressureDepth") }}</span>
          <h1 id="evaluation-title">{{ state(analysis.pressure_state) }}</h1>
        </div>
        <div class="state-hero bottoming-hero">
          <span class="eyebrow">{{ t("bottomingProcess") }}</span>
          <h1>{{ state(analysis.bottoming_state) }}</h1>
        </div>
        <div class="evaluation-copy">
          <p class="evaluation-summary">{{ analysis.summary }}</p>
        </div>
        <div class="consistency-pill" :data-level="analysis.consistency ?? '数据不足'">
          <span>{{ t("evidenceConsistency") }}</span>
          <strong>{{ state(analysis.consistency) }}</strong>
          <small>{{ statusLabel() }}</small>
        </div>
      </div>

      <div class="summary-blocks" aria-label="AI two-axis summary">
        <article class="summary-block summary-support">
          <span class="summary-index">01 / {{ t("pressureAxis") }}</span>
          <h2>{{ analysis.compact.pressure.title }}</h2>
          <p>{{ analysis.compact.pressure.text }}</p>
        </article>
        <article class="summary-block summary-obstacle">
          <span class="summary-index">02 / {{ t("bottomingProcess") }}</span>
          <h2>{{ analysis.compact.bottoming.title }}</h2>
          <p>{{ analysis.compact.bottoming.text }}</p>
        </article>
        <article class="summary-block summary-next">
          <span class="summary-index">03 / {{ detail(2) }}</span>
          <h2>{{ analysis.compact.change.title }}</h2>
          <p>{{ analysis.compact.change.text }}</p>
        </article>
      </div>

      <button class="detail-toggle" type="button" :aria-expanded="detailsOpen" @click="emit('toggleDetails')">
        <span>{{ detailsOpen ? t("collapseAnalysis") : t("fullAnalysis") }}</span>
        <span class="detail-toggle-arrow" aria-hidden="true">↓</span>
      </button>
    </template>
  </section>
</template>
