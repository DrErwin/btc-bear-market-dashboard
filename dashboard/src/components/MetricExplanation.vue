<script setup lang="ts">
import type { Category, Metric } from "../types";
import { useI18n } from "../i18n";

const props = defineProps<{
  metric: Metric;
  category: Category;
}>();
const { t, metric: metricCopy } = useI18n();
</script>

<template>
  <section class="metric-explanation" aria-labelledby="explanation-title">
    <div class="explanation-heading">
      <span class="eyebrow">{{ t("readingTip") }} / {{ metric.id }}</span>
      <h3 id="explanation-title">{{ t("explanation") }}</h3>
    </div>
    <div class="explanation-grid">
      <article>
        <span>{{ t("formula") }}</span>
        <p>{{ props.metric.formula }}</p>
      </article>
      <article>
        <span>{{ t("meaning") }}</span>
        <p>{{ metricCopy(props.metric).meaning }}</p>
      </article>
      <article>
        <span>{{ t("usage") }}</span>
        <p>{{ metricCopy(props.metric).usage }}</p>
      </article>
    </div>
    <div class="explanation-source">
      <span>{{ t("source") }}</span>
      <a v-if="metricCopy(props.metric).sourceUrl" :href="metricCopy(props.metric).sourceUrl" target="_blank" rel="noopener noreferrer">{{ metricCopy(props.metric).source }} ↗</a>
      <p v-else>{{ metricCopy(props.metric).source }}</p>
    </div>
  </section>
</template>
