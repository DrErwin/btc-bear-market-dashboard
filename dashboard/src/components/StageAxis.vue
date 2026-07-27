<script setup lang="ts">
import type { Stage } from "../types";

const props = defineProps<{
  currentStage: Stage | null;
}>();

const stages: Stage[] = [
  "尚未进入熊底观察期",
  "熊市下行期",
  "深度压力期",
  "筑底证据积累期",
  "熊底证据充分期",
];

const currentIndex = () =>
  props.currentStage ? stages.indexOf(props.currentStage) : -1;
</script>

<template>
  <div class="stage-axis-wrap" aria-label="五阶段市场证据轴">
    <div class="axis-line" aria-hidden="true">
      <span class="axis-line-fill" :style="{ width: currentIndex() >= 0 ? `${(currentIndex() / 4) * 100}%` : '0%' }"></span>
    </div>
    <ol class="stage-axis">
      <li
        v-for="(stage, index) in stages"
        :key="stage"
        class="stage-stop"
        :class="{ 'is-past': currentIndex() > index, 'is-current': currentIndex() === index }"
        :aria-current="currentIndex() === index ? 'step' : undefined"
      >
        <span class="axis-point">{{ String(index + 1).padStart(2, "0") }}</span>
        <span class="axis-stage">{{ stage }}</span>
        <span class="axis-state">{{ currentIndex() === index ? "当前" : currentIndex() > index ? "已通过" : "待观察" }}</span>
      </li>
    </ol>
  </div>
</template>
