<script setup lang="ts">
import type { Analysis } from "../types";

const props = defineProps<{
  analysis: Analysis | null;
  fallback: Analysis | null;
  todayAvailable: boolean;
  lastSuccessDate: string | null;
  detailsOpen: boolean;
}>();

const emit = defineEmits<{
  toggleDetails: [];
}>();

function statusLabel() {
  if (props.todayAvailable) return "今日已保存";
  if (props.fallback) return `回退至 ${props.fallback.analysis_date}`;
  return "暂无可用结论";
}
</script>

<template>
  <section class="evaluation" aria-labelledby="evaluation-title">
    <div v-if="!todayAvailable" class="availability-banner" :class="{ 'has-fallback': fallback }" role="status">
      <span class="availability-icon" aria-hidden="true">!</span>
      <div>
        <strong>今日 AI 分析不可用</strong>
        <span v-if="fallback">当前展示上一份成功结果，日期为 {{ fallback.analysis_date }}。</span>
        <span v-else>目前没有上一份成功结果，页面仅保留指标检查功能。</span>
      </div>
      <span class="availability-note">{{ statusLabel() }}</span>
    </div>

    <template v-if="analysis">
      <div class="evaluation-head">
        <div class="stage-hero">
          <span class="eyebrow">当前市场阶段</span>
          <h1 id="evaluation-title">{{ analysis.stage }}</h1>
        </div>
        <p class="evaluation-summary">{{ analysis.summary }}</p>
        <div class="consistency-pill" :data-level="analysis.consistency">
          <span>证据一致性</span>
          <strong>{{ analysis.consistency }}</strong>
          <small>{{ statusLabel() }}</small>
        </div>
      </div>

      <div class="summary-blocks" aria-label="AI 摘要">
        <article class="summary-block summary-support">
          <span class="summary-index">01 / 核心支撑</span>
          <h2>{{ analysis.compact.support.title }}</h2>
          <p>{{ analysis.compact.support.text }}</p>
        </article>
        <article class="summary-block summary-obstacle">
          <span class="summary-index">02 / 主要阻力</span>
          <h2>{{ analysis.compact.obstacle.title }}</h2>
          <p>{{ analysis.compact.obstacle.text }}</p>
        </article>
        <article class="summary-block summary-next">
          <span class="summary-index">03 / 下一阶段条件</span>
          <h2>{{ analysis.compact.next.title }}</h2>
          <p>{{ analysis.compact.next.text }}</p>
        </article>
      </div>

      <button class="detail-toggle" type="button" :aria-expanded="detailsOpen" @click="emit('toggleDetails')">
        <span>{{ detailsOpen ? "收起完整分析" : "查看完整分析" }}</span>
        <span class="detail-toggle-arrow" aria-hidden="true">↓</span>
      </button>
    </template>
  </section>
</template>
