<script setup lang="ts">
import type { Category, CategoryAssessment } from "../types";
import { useI18n } from "../i18n";

defineProps<{
  categories: Category[];
  assessments: CategoryAssessment[];
  activeCategoryId: string;
}>();

const emit = defineEmits<{
  select: [categoryId: string];
}>();
const { category: categoryName, categoryStatus } = useI18n();

function assessmentFor(categoryId: string, assessments: CategoryAssessment[]) {
  return assessments.find((assessment) => assessment.id === categoryId);
}
</script>

<template>
  <div class="category-grid" aria-label="Evidence categories">
    <button
      v-for="category in categories"
      :key="category.id"
      type="button"
      class="category-card"
      :class="{ 'is-active': activeCategoryId === category.id }"
      :aria-pressed="activeCategoryId === category.id"
      :aria-label="`${categoryName(category)} · ${categoryStatus(assessmentFor(category.id, assessments)?.status || '未确认')}`"
      @click="emit('select', category.id)"
    >
      <span class="category-number">{{ String(categories.indexOf(category) + 1).padStart(2, "0") }}</span>
      <span class="category-short">{{ categoryName(category) }}</span>
      <strong
        class="status-tag"
        :class="`status-${assessmentFor(category.id, assessments)?.status || '未确认'}`"
      >{{ categoryStatus(assessmentFor(category.id, assessments)?.status || "未确认") }}</strong>
    </button>
  </div>
</template>
