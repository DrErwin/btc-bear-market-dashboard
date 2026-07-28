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
    <div v-if="dataInsufficient" class="availability-banner" role="status">
      <span class="availability-icon" aria-hidden="true">!</span>
      <div>
        <strong>当前数据不足</strong>
        <span>关键锚数据没有同时通过新鲜度检查，系统没有调用 AI，也没有把缺失数据当作未触发。</span>
      </div>
      <span class="availability-note">等待数据恢复</span>
    </div>

    <div v-else-if="!todayAvailable" class="availability-banner" :class="{ 'has-fallback': fallback }" role="status">
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
        <div class="evaluation-copy">
          <p class="evaluation-summary">{{ analysis.summary }}</p>
          <p v-if="analysis.pressure_summary?.trim()" class="pressure-summary">
            <span class="pressure-summary-label">阶段内部压力</span>
            <span>{{ analysis.pressure_summary }}</span>
          </p>
        </div>
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
