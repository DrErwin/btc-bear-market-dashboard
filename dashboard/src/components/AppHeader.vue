<script setup lang="ts">
defineProps<{
  analysisDate: string | null;
  isFallback: boolean;
}>();

const emit = defineEmits<{
  openMethod: [];
}>();
</script>

<template>
  <header class="topbar">
    <a class="brand-lockup" href="#top" aria-label="回到看板顶部">
      <span class="brand-mark" aria-hidden="true">BΞ</span>
      <span>
        <span class="brand-kicker">CYCLE EVIDENCE / 01</span>
        <span class="brand-name">BTC 熊底证据看板</span>
      </span>
    </a>
    <div class="topbar-meta">
      <span class="data-stamp">
        <span class="status-dot" :class="{ 'is-fallback': isFallback }" aria-hidden="true"></span>
        {{ isFallback ? "上一份成功分析" : "每日快照" }}
      </span>
      <span class="topbar-date">{{ analysisDate || "等待可用分析" }}</span>
      <button class="text-button" type="button" @click="emit('openMethod')">方法说明 <span aria-hidden="true">↗</span></button>
    </div>
  </header>
</template>
