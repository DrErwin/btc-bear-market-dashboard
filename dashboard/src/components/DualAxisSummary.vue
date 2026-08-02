<script setup lang="ts">
import type { BottomingState, PressureState } from "../types";
import { useI18n } from "../i18n";

defineProps<{
  pressureState: PressureState | null;
  bottomingState: BottomingState | null;
}>();

const pressureStates: PressureState[] = ["压力尚未明显", "进入观察", "深度压力", "极端压力", "数据不足"];
const bottomingStates: BottomingState[] = ["未见筑底结构", "筑底线索出现", "筑底证据聚合", "筑底证据较完整", "市场修复中", "已离开底部窗口", "数据不足"];
const { state: stateLabel, t } = useI18n();
</script>

<template>
  <div class="dual-axis-summary" aria-label="Two-axis market state">
    <section class="axis-card pressure-axis-card" aria-labelledby="pressure-axis-title">
      <div class="axis-card-head">
        <span id="pressure-axis-title" class="eyebrow">{{ t("pressureAxis") }}</span>
      </div>
      <ol class="dual-axis-list axis-track-pressure" :aria-label="t('pressureAxis')">
        <li
          v-for="state in pressureStates"
          :key="state"
          :class="{ 'is-current': state === pressureState }"
          :aria-current="state === pressureState ? 'step' : undefined"
        >
          <span class="dual-axis-dot" aria-hidden="true"></span>
          <span class="axis-state-label">{{ stateLabel(state) }}</span>
        </li>
      </ol>
    </section>
    <section class="axis-card bottoming-axis-card" aria-labelledby="bottoming-axis-title">
      <div class="axis-card-head">
        <span id="bottoming-axis-title" class="eyebrow">{{ t("bottomingAxis") }}</span>
      </div>
      <ol class="dual-axis-list axis-track-bottoming" :aria-label="t('bottomingAxis')">
        <li
          v-for="state in bottomingStates"
          :key="state"
          :class="{ 'is-current': state === bottomingState }"
          :aria-current="state === bottomingState ? 'step' : undefined"
        >
          <span class="dual-axis-dot" aria-hidden="true"></span>
          <span class="axis-state-label">{{ stateLabel(state) }}</span>
        </li>
      </ol>
    </section>
  </div>
</template>
