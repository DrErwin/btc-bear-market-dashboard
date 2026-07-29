<script setup lang="ts">
import type { Analysis } from "../types";

const props = defineProps<{
  analysis: Analysis | null;
  fallback: Analysis | null;
  todayAvailable: boolean;
  lastSuccessDate: string | null;
  detailsOpen: boolean;
  dataInsufficient?: boolean;
}>();

const emit = defineEmits<{ toggleDetails: [] }>();

function statusLabel() {
  if (props.todayAvailable) return "今日已保存";
  if (props.fallback) return `回退至 ${props.fallback.analysis_date}`;
  return "暂无可用结论";
}
</script>

<template>
  <section class="evaluation" aria-labelledby="evaluation-title">
    <div v-if="dataInsufficient" class="availability-banner" role="status">
      <span class="availability-icon" aria-hidden="true">!</span>
      <div>
        <strong>部分市场状态数据不足</strong>
        <span>压力轴和筑底过程轴分别检查数据；缺失数据没有被当作“没有压力”或反向证据。</span>
      </div>
      <span class="availability-note">等待数据恢复</span>
    </div>

    <div v-else-if="!todayAvailable" class="availability-banner" :class="{ 'has-fallback': fallback }" role="status">
      <span class="availability-icon" aria-hidden="true">!</span>
      <div>
        <strong>今日 AI 分析不可用</strong>
        <span v-if="fallback">当前展示上一份完整双轴结果，日期为 {{ fallback.analysis_date }}。</span>
        <span v-else>目前没有上一份完整双轴结果，页面仅保留指标检查功能。</span>
      </div>
      <span class="availability-note">{{ statusLabel() }}</span>
    </div>

    <template v-if="analysis">
      <div class="evaluation-head dual-state-head">
        <div class="state-hero pressure-hero">
          <span class="eyebrow">压力深度</span>
          <h1 id="evaluation-title">{{ analysis.pressure_state }}</h1>
        </div>
        <div class="state-hero bottoming-hero">
          <span class="eyebrow">熊底过程</span>
          <h1>{{ analysis.bottoming_state }}</h1>
        </div>
        <div class="evaluation-copy">
          <p class="evaluation-summary">{{ analysis.summary }}</p>
        </div>
        <div class="consistency-pill" :data-level="analysis.consistency ?? '数据不足'">
          <span>证据一致性</span>
          <strong>{{ analysis.consistency ?? "—" }}</strong>
          <small>{{ statusLabel() }}</small>
        </div>
      </div>

      <div class="summary-blocks" aria-label="AI 双轴摘要">
        <article class="summary-block summary-support">
          <span class="summary-index">01 / 压力轴</span>
          <h2>{{ analysis.compact.pressure.title }}</h2>
          <p>{{ analysis.compact.pressure.text }}</p>
        </article>
        <article class="summary-block summary-obstacle">
          <span class="summary-index">02 / 筑底过程</span>
          <h2>{{ analysis.compact.bottoming.title }}</h2>
          <p>{{ analysis.compact.bottoming.text }}</p>
        </article>
        <article class="summary-block summary-next">
          <span class="summary-index">03 / 近三日变化</span>
          <h2>{{ analysis.compact.change.title }}</h2>
          <p>{{ analysis.compact.change.text }}</p>
        </article>
      </div>

      <button class="detail-toggle" type="button" :aria-expanded="detailsOpen" @click="emit('toggleDetails')">
        <span>{{ detailsOpen ? "收起完整分析" : "查看完整分析" }}</span>
        <span class="detail-toggle-arrow" aria-hidden="true">↓</span>
      </button>
    </template>
  </section>
</template>
