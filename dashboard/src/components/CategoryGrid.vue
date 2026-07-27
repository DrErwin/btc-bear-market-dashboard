<script setup lang="ts">
import type { Category, CategoryAssessment } from "../types";

defineProps<{
  categories: Category[];
  assessments: CategoryAssessment[];
  activeCategoryId: string;
}>();

const emit = defineEmits<{
  select: [categoryId: string];
}>();

function assessmentFor(categoryId: string, assessments: CategoryAssessment[]) {
  return assessments.find((assessment) => assessment.id === categoryId);
}
</script>

<template>
  <div class="category-grid" aria-label="六个证据分类">
    <button
      v-for="category in categories"
      :key="category.id"
      type="button"
      class="category-card"
      :class="{ 'is-active': activeCategoryId === category.id }"
      :aria-pressed="activeCategoryId === category.id"
      :aria-label="`${category.name}，${assessmentFor(category.id, assessments)?.status || '状态不可用'}`"
      @click="emit('select', category.id)"
    >
      <span class="category-number">{{ String(categories.indexOf(category) + 1).padStart(2, "0") }}</span>
      <span class="category-short">{{ category.short }}</span>
      <strong
        class="status-tag"
        :class="`status-${assessmentFor(category.id, assessments)?.status || '未确认'}`"
      >{{ assessmentFor(category.id, assessments)?.status || "未确认" }}</strong>
    </button>
  </div>
</template>
