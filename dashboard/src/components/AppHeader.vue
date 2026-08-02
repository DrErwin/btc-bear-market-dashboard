<script setup lang="ts">
import { useI18n } from "../i18n";
defineProps<{
  analysisDate: string | null;
  isFallback: boolean;
}>();

const emit = defineEmits<{
  openMethod: [];
}>();
const { locale, setLocale, t } = useI18n();
</script>

<template>
  <header class="topbar">
    <div class="brand-lockup">
      <a class="brand-link" href="#top" :aria-label="t('dashboardTitle')">
      <span class="brand-mark" aria-hidden="true">BΞ</span>
      <span>
        <span class="brand-kicker">CYCLE EVIDENCE / 01</span>
        <span class="brand-name">{{ t("dashboardTitle") }}</span>
      </span>
      </a>
      <nav class="social-links" aria-label="Social links">
        <a
          class="social-link"
          href="https://x.com/ErwinWu000"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="在 X 查看 ErwinWu000"
          title="X · ErwinWu000"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817-5.963 6.817H1.684l7.73-8.835L1.258 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
          </svg>
        </a>
        <a
          class="social-link"
          href="https://github.com/DrErwin/btc-bear-market-dashboard"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="在 GitHub 查看项目仓库"
          title="GitHub · btc-bear-market-dashboard"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.084-.73.084-.73 1.205.085 1.838 1.237 1.838 1.237 1.07 1.835 2.809 1.305 3.495.998.108-.776.418-1.305.762-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23a11.5 11.5 0 0 1 3.003-.404c1.02.005 2.045.138 3.003.404 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
          </svg>
        </a>
      </nav>
    </div>
    <div class="topbar-meta">
      <button class="language-switch" type="button" :aria-label="t('language')" @click="setLocale(locale === 'zh' ? 'en' : 'zh')">{{ t("language") }}</button>
      <span class="data-stamp">
        <span class="status-dot" :class="{ 'is-fallback': isFallback }" aria-hidden="true"></span>
        {{ isFallback ? t("previousSuccess") : t("dailySnapshot") }}
      </span>
      <span class="topbar-date">{{ analysisDate || t("waiting") }}</span>
      <button class="text-button" type="button" @click="emit('openMethod')">{{ t("method") }} <span aria-hidden="true">↗</span></button>
    </div>
  </header>
</template>
