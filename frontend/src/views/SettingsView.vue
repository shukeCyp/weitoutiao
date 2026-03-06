<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { onMounted, ref, computed } from 'vue'

import { useThemeStore } from '../stores/theme'
import { THEMES, type ThemeName } from '../themes/tokens'

interface MonitoringStatus {
  logDir: string
  dbFile: string
  logFiles: number
  logSizeBytes: number
  dbSizeBytes: number
  settingCount: number
}

const themeStore = useThemeStore()
const { currentThemeName } = storeToRefs(themeStore)

const monitoring = ref<MonitoringStatus | null>(null)
const activeSection = ref<'theme' | 'logs' | 'database'>('theme')

const lightThemes = computed(() => THEMES)

const formatBytes = (value: number): string => {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

const refreshMonitoring = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) return
  try {
    monitoring.value = await api.get_monitoring_status()
  } catch {
    monitoring.value = null
  }
}

const selectTheme = (name: ThemeName): void => {
  themeStore.setTheme(name)
}

const openLogsFolder = async (): Promise<void> => {
  await window.pywebview?.api?.open_logs_folder()
}

const openDbFolder = async (): Promise<void> => {
  await window.pywebview?.api?.open_db_folder()
}

const clearLogs = async (): Promise<void> => {
  await window.pywebview?.api?.clear_logs()
  await refreshMonitoring()
}

onMounted(() => {
  void refreshMonitoring()
})
</script>

<template>
  <section class="page-section settings-layout">
    <header class="page-head">
      <h2 class="page-title">设置</h2>
      <p class="page-subtitle">在这里统一管理主题外观、日志和数据库。</p>
    </header>

    <div class="settings-tabs">
      <button
        type="button"
        class="settings-tab"
        :class="{ 'settings-tab--active': activeSection === 'theme' }"
        @click="activeSection = 'theme'"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
        外观主题
      </button>
      <button
        type="button"
        class="settings-tab"
        :class="{ 'settings-tab--active': activeSection === 'logs' }"
        @click="activeSection = 'logs'"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
        日志管理
      </button>
      <button
        type="button"
        class="settings-tab"
        :class="{ 'settings-tab--active': activeSection === 'database' }"
        @click="activeSection = 'database'"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        数据库
      </button>
    </div>

    <div class="page-body settings-body">
      <transition name="section-fade" mode="out-in">
        <!-- Theme Section -->
        <div v-if="activeSection === 'theme'" key="theme" class="settings-panel">
          <div class="theme-panel-intro">
            <h3 class="theme-panel-intro__title">选择主题</h3>
            <p class="theme-panel-intro__text">已移除暗色风格，并补充更多亮色主题。每个主题都以卡片形式展示，点击即可立即应用。</p>
          </div>

          <div class="theme-group">
            <h4 class="theme-group__label">亮色主题</h4>
            <div class="theme-grid">
              <button
                v-for="theme in lightThemes"
                :key="theme.name"
                type="button"
                class="theme-card"
                :class="{ 'theme-card--active': currentThemeName === theme.name }"
                @click="selectTheme(theme.name as ThemeName)"
              >
                <div class="theme-card__preview" :style="{
                  '--preview-bg': theme.tokens.background,
                  '--preview-surface': theme.tokens.surface,
                  '--preview-accent': theme.tokens.accent,
                  '--preview-border': theme.tokens.border,
                  '--preview-text': theme.tokens.textPrimary,
                  '--preview-text2': theme.tokens.textSecondary,
                }">
                  <div class="preview-sidebar">
                    <div class="preview-dot" />
                    <div class="preview-line preview-line--short" />
                    <div class="preview-line" />
                    <div class="preview-line" />
                  </div>
                  <div class="preview-main">
                    <div class="preview-header" />
                    <div class="preview-blocks">
                      <div class="preview-block" />
                      <div class="preview-block" />
                    </div>
                  </div>
                </div>
                <div class="theme-card__info">
                  <div class="theme-card__meta">
                    <span class="theme-card__name">{{ theme.label }}</span>
                    <span class="theme-card__status">{{ currentThemeName === theme.name ? '当前使用' : '点击应用' }}</span>
                  </div>
                  <span class="theme-card__check" v-if="currentThemeName === theme.name">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </span>
                </div>
              </button>
            </div>
          </div>

        </div>

        <!-- Logs Section -->
        <div v-else-if="activeSection === 'logs'" key="logs" class="settings-panel">
          <div class="monitor-grid">
            <article class="monitor-card">
              <div class="monitor-card__icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              </div>
              <div class="monitor-card__body">
                <span class="monitor-card__label">日志目录</span>
                <span class="monitor-card__value monitor-card__value--path">{{ monitoring?.logDir ?? '未知' }}</span>
              </div>
            </article>

            <article class="monitor-card">
              <div class="monitor-card__icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
              </div>
              <div class="monitor-card__body">
                <span class="monitor-card__label">日志文件数</span>
                <span class="monitor-card__value">{{ monitoring?.logFiles ?? 0 }}</span>
              </div>
            </article>

            <article class="monitor-card">
              <div class="monitor-card__icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
              </div>
              <div class="monitor-card__body">
                <span class="monitor-card__label">占用空间</span>
                <span class="monitor-card__value">{{ formatBytes(monitoring?.logSizeBytes ?? 0) }}</span>
              </div>
            </article>
          </div>

          <div class="settings-actions-bar">
            <button type="button" class="action-btn" @click="openLogsFolder">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              打开日志文件夹
            </button>
            <button type="button" class="action-btn action-btn--danger" @click="clearLogs">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              清空日志
            </button>
            <button type="button" class="action-btn" @click="refreshMonitoring">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              刷新状态
            </button>
          </div>
        </div>

        <!-- Database Section -->
        <div v-else-if="activeSection === 'database'" key="database" class="settings-panel">
          <div class="monitor-grid">
            <article class="monitor-card">
              <div class="monitor-card__icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
              </div>
              <div class="monitor-card__body">
                <span class="monitor-card__label">数据库文件</span>
                <span class="monitor-card__value monitor-card__value--path">{{ monitoring?.dbFile ?? '未知' }}</span>
              </div>
            </article>

            <article class="monitor-card">
              <div class="monitor-card__icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
              </div>
              <div class="monitor-card__body">
                <span class="monitor-card__label">数据库大小</span>
                <span class="monitor-card__value">{{ formatBytes(monitoring?.dbSizeBytes ?? 0) }}</span>
              </div>
            </article>

            <article class="monitor-card">
              <div class="monitor-card__icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
              </div>
              <div class="monitor-card__body">
                <span class="monitor-card__label">设置记录数</span>
                <span class="monitor-card__value">{{ monitoring?.settingCount ?? 0 }}</span>
              </div>
            </article>
          </div>

          <div class="settings-actions-bar">
            <button type="button" class="action-btn" @click="openDbFolder">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              打开数据库文件夹
            </button>
            <button type="button" class="action-btn" @click="refreshMonitoring">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              刷新状态
            </button>
          </div>
        </div>
      </transition>
    </div>
  </section>
</template>
