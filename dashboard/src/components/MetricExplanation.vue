<script setup lang="ts">
import type { Category, Metric } from "../types";

defineProps<{
  metric: Metric;
  category: Category;
}>();
</script>

<template>
  <section class="metric-explanation" aria-labelledby="explanation-title">
    <div class="explanation-heading">
      <span class="eyebrow">读图提示 / {{ metric.id }}</span>
      <h3 id="explanation-title">理解这个指标</h3>
    </div>
    <div class="explanation-grid">
      <article>
        <span>指标含义</span>
        <p>{{ metric.description }}</p>
      </article>
      <article>
        <span>所属分类与角色</span>
        <p>{{ category.name }} · <strong>{{ metric.role }}</strong>证据</p>
      </article>
      <article>
        <span>当前阈值语义</span>
        <p>{{ metric.tier_label }}：{{ metric.tier_meaning }}</p>
      </article>
      <article>
        <span>来源与限制</span>
        <p>{{ metric.source }}。{{ metric.caveat }}</p>
      </article>
    </div>
  </section>
</template>
