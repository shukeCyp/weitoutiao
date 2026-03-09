<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed, onMounted, ref } from 'vue'

import { useToastStore } from '../stores/toast'
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

const LLM_BASE_URL_KEY = 'llm.base_url'
const LLM_API_KEY_KEY = 'llm.api_key'
const LLM_MODEL_KEY = 'llm.model'
const IMAGE_BASE_URL_KEY = 'image.base_url'
const IMAGE_API_KEY_KEY = 'image.api_key'
const IMAGE_MODEL_KEY = 'image.model'
const AUTOMATION_HEADLESS_KEY = 'automation.headless'
const AUTOMATION_WORKER_COUNT_KEY = 'automation.worker_count'
const REWRITE_WORKER_COUNT_KEY = 'rewrite.worker_count'
const IMAGE_GEN_WORKER_COUNT_KEY = 'image_gen.worker_count'

const themeStore = useThemeStore()
const { currentThemeName } = storeToRefs(themeStore)
const { showToast } = useToastStore()

const monitoring = ref<MonitoringStatus | null>(null)
const activeSection = ref<'basic' | 'theme' | 'logs' | 'database'>('basic')
const llmBaseUrl = ref('')
const llmApiKey = ref('')
const llmModel = ref('')
const imageBaseUrl = ref('')
const imageApiKey = ref('')
const imageModel = ref('')
const automationHeadless = ref('true')
const automationWorkerCount = ref('1')
const rewriteWorkerCount = ref('1')
const imageGenWorkerCount = ref('3')
const isSavingBasicSettings = ref(false)
const llmBaseUrlSaved = ref('')
const llmApiKeySaved = ref('')
const llmModelSaved = ref('')
const imageBaseUrlSaved = ref('')
const imageApiKeySaved = ref('')
const imageModelSaved = ref('')
const automationHeadlessSaved = ref('true')
const automationWorkerCountSaved = ref('1')
const rewriteWorkerCountSaved = ref('1')
const imageGenWorkerCountSaved = ref('3')

const hasUnsavedBasicSettings = computed(() => {
  return (
    llmBaseUrl.value !== llmBaseUrlSaved.value
    || llmApiKey.value !== llmApiKeySaved.value
    || llmModel.value !== llmModelSaved.value
    || imageBaseUrl.value !== imageBaseUrlSaved.value
    || imageApiKey.value !== imageApiKeySaved.value
    || imageModel.value !== imageModelSaved.value
    || automationHeadless.value !== automationHeadlessSaved.value
    || String(automationWorkerCount.value) !== automationWorkerCountSaved.value
    || String(rewriteWorkerCount.value) !== rewriteWorkerCountSaved.value
    || String(imageGenWorkerCount.value) !== imageGenWorkerCountSaved.value
  )
})

const basicSettingsSaveLabel = computed(() => {
  if (isSavingBasicSettings.value) {
    return '保存中...'
  }
  return hasUnsavedBasicSettings.value ? '保存设置' : '已保存'
})

const lightThemes = computed(() => THEMES)
const isPywebviewAvailable = computed(() => !!window.pywebview?.api)
const basicSettingCards = computed(() => [
  {
    title: '大模型服务',
    description: '配置对话模型的 base URL、API Key 与模型名称，AI 实验室和改写能力都会复用这里的设置。',
    accent: 'llm',
  },
  {
    title: '图片服务',
    description: '配置生图模型接入信息，便于在 AI 实验室直接验证图片生成链路。',
    accent: 'image',
  },
  {
    title: '自动化执行',
    description: '控制浏览器自动化的执行方式。文章监控的线程数仍然以这里的设置为准。',
    accent: 'automation',
  },
])

const formatBytes = (value: number): string => {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

const isValidUrl = (value: string): boolean => {
  if (!value.trim()) {
    return true
  }

  try {
    new URL(value.trim())
    return true
  } catch {
    return false
  }
}

const syncSavedSettings = (): void => {
  llmBaseUrlSaved.value = llmBaseUrl.value
  llmApiKeySaved.value = llmApiKey.value
  llmModelSaved.value = llmModel.value
  imageBaseUrlSaved.value = imageBaseUrl.value
  imageApiKeySaved.value = imageApiKey.value
  imageModelSaved.value = imageModel.value
  automationHeadlessSaved.value = automationHeadless.value
  automationWorkerCountSaved.value = automationWorkerCount.value
  rewriteWorkerCountSaved.value = rewriteWorkerCount.value
  imageGenWorkerCountSaved.value = imageGenWorkerCount.value
}

const normalizeWorkerCount = (value: string | number): string => {
  const parsed = Number.parseInt(String(value).trim(), 10)
  if (Number.isNaN(parsed) || parsed < 1) {
    throw new Error('浏览器执行线程数量必须大于 0。')
  }

  return String(Math.min(parsed, 16))
}

const normalizeHeadless = (value: string): string => {
  return value === 'false' ? 'false' : 'true'
}

const loadBasicSettings = async (silent = false): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    if (!silent) {
      showToast('当前环境不支持读取基础设置。', 'warning')
    }
    return
  }

  try {
    const [
      savedLlmBaseUrl, savedLlmApiKey, savedLlmModel,
      savedImageBaseUrl, savedImageApiKey, savedImageModel,
      savedAutomationHeadless, savedAutomationWorkerCount,
      savedRewriteWorkerCount, savedImageGenWorkerCount,
    ] =
      await Promise.all([
        api.get_setting(LLM_BASE_URL_KEY),
        api.get_setting(LLM_API_KEY_KEY),
        api.get_setting(LLM_MODEL_KEY),
        api.get_setting(IMAGE_BASE_URL_KEY),
        api.get_setting(IMAGE_API_KEY_KEY),
        api.get_setting(IMAGE_MODEL_KEY),
        api.get_setting(AUTOMATION_HEADLESS_KEY),
        api.get_setting(AUTOMATION_WORKER_COUNT_KEY),
        api.get_setting(REWRITE_WORKER_COUNT_KEY),
        api.get_setting(IMAGE_GEN_WORKER_COUNT_KEY),
      ])

    llmBaseUrl.value = savedLlmBaseUrl ?? ''
    llmApiKey.value = savedLlmApiKey ?? ''
    llmModel.value = savedLlmModel ?? ''
    imageBaseUrl.value = savedImageBaseUrl ?? ''
    imageApiKey.value = savedImageApiKey ?? ''
    imageModel.value = savedImageModel ?? ''
    automationHeadless.value = normalizeHeadless(savedAutomationHeadless ?? 'true')
    automationWorkerCount.value = savedAutomationWorkerCount ?? '1'
    rewriteWorkerCount.value = savedRewriteWorkerCount ?? '1'
    imageGenWorkerCount.value = savedImageGenWorkerCount ?? '3'
    syncSavedSettings()
  } catch {
    showToast('读取基础设置失败，请稍后重试。', 'error')
  }
}

const getSavedValue = (key: string): string => {
  switch (key) {
    case LLM_BASE_URL_KEY:
      return llmBaseUrlSaved.value
    case LLM_API_KEY_KEY:
      return llmApiKeySaved.value
    case LLM_MODEL_KEY:
      return llmModelSaved.value
    case IMAGE_BASE_URL_KEY:
      return imageBaseUrlSaved.value
    case IMAGE_API_KEY_KEY:
      return imageApiKeySaved.value
    case IMAGE_MODEL_KEY:
      return imageModelSaved.value
    case AUTOMATION_HEADLESS_KEY:
      return automationHeadlessSaved.value
    case AUTOMATION_WORKER_COUNT_KEY:
      return automationWorkerCountSaved.value
    case REWRITE_WORKER_COUNT_KEY:
      return rewriteWorkerCountSaved.value
    case IMAGE_GEN_WORKER_COUNT_KEY:
      return imageGenWorkerCountSaved.value
    default:
      return ''
  }
}

const updateSavedValue = (key: string, value: string): void => {
  switch (key) {
    case LLM_BASE_URL_KEY:
      llmBaseUrlSaved.value = value
      break
    case LLM_API_KEY_KEY:
      llmApiKeySaved.value = value
      break
    case LLM_MODEL_KEY:
      llmModelSaved.value = value
      break
    case IMAGE_BASE_URL_KEY:
      imageBaseUrlSaved.value = value
      break
    case IMAGE_API_KEY_KEY:
      imageApiKeySaved.value = value
      break
    case IMAGE_MODEL_KEY:
      imageModelSaved.value = value
      break
    case AUTOMATION_HEADLESS_KEY:
      automationHeadlessSaved.value = value
      break
    case AUTOMATION_WORKER_COUNT_KEY:
      automationWorkerCountSaved.value = value
      break
    case REWRITE_WORKER_COUNT_KEY:
      rewriteWorkerCountSaved.value = value
      break
    case IMAGE_GEN_WORKER_COUNT_KEY:
      imageGenWorkerCountSaved.value = value
      break
  }
}

const saveBasicSetting = async (key: string, value: string | number, label: string, options?: { isUrl?: boolean }): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    throw new Error('当前环境不支持保存基础设置。')
  }

  const strValue = String(value)
  let normalizedValue = options?.isUrl ? strValue.trim() : key === LLM_MODEL_KEY || key === IMAGE_MODEL_KEY ? strValue.trim() : strValue

  if (key === AUTOMATION_HEADLESS_KEY) {
    normalizedValue = normalizeHeadless(strValue)
  }

  if (key === AUTOMATION_WORKER_COUNT_KEY || key === REWRITE_WORKER_COUNT_KEY || key === IMAGE_GEN_WORKER_COUNT_KEY) {
    normalizedValue = normalizeWorkerCount(strValue)
  }

  if (options?.isUrl && !isValidUrl(normalizedValue)) {
    throw new Error(`${label} 格式不正确。`)
  }

  if (normalizedValue === getSavedValue(key)) {
    return
  }

  const success = await api.set_setting(key, normalizedValue)
  if (!success) {
    throw new Error(`${label} 保存失败，请稍后重试。`)
  }

  updateSavedValue(key, normalizedValue)

  switch (key) {
    case LLM_BASE_URL_KEY:
      llmBaseUrl.value = normalizedValue
      break
    case LLM_API_KEY_KEY:
      llmApiKey.value = normalizedValue
      break
    case LLM_MODEL_KEY:
      llmModel.value = normalizedValue
      break
    case IMAGE_BASE_URL_KEY:
      imageBaseUrl.value = normalizedValue
      break
    case IMAGE_API_KEY_KEY:
      imageApiKey.value = normalizedValue
      break
    case IMAGE_MODEL_KEY:
      imageModel.value = normalizedValue
      break
    case AUTOMATION_HEADLESS_KEY:
      automationHeadless.value = normalizedValue
      break
    case AUTOMATION_WORKER_COUNT_KEY:
      automationWorkerCount.value = normalizedValue
      break
    case REWRITE_WORKER_COUNT_KEY:
      rewriteWorkerCount.value = normalizedValue
      break
    case IMAGE_GEN_WORKER_COUNT_KEY:
      imageGenWorkerCount.value = normalizedValue
      break
  }
}

const saveAllBasicSettings = async (): Promise<void> => {
  if (!isPywebviewAvailable.value) {
    showToast('当前环境不支持保存基础设置。', 'warning')
    return
  }

  if (!hasUnsavedBasicSettings.value) {
    showToast('基础设置没有变化。', 'warning')
    return
  }

  isSavingBasicSettings.value = true

  try {
    await saveBasicSetting(LLM_BASE_URL_KEY, llmBaseUrl.value, '大语言模型 Base URL', { isUrl: true })
    await saveBasicSetting(LLM_API_KEY_KEY, llmApiKey.value, '大语言模型 API Key')
    await saveBasicSetting(LLM_MODEL_KEY, llmModel.value, '大语言模型 Model')
    await saveBasicSetting(IMAGE_BASE_URL_KEY, imageBaseUrl.value, '生图服务 Base URL', { isUrl: true })
    await saveBasicSetting(IMAGE_API_KEY_KEY, imageApiKey.value, '生图服务 API Key')
    await saveBasicSetting(IMAGE_MODEL_KEY, imageModel.value, '生图服务 Model')
    await saveBasicSetting(AUTOMATION_HEADLESS_KEY, automationHeadless.value, '自动化无头模式')
    await saveBasicSetting(AUTOMATION_WORKER_COUNT_KEY, automationWorkerCount.value, '浏览器执行线程数量')
    await saveBasicSetting(REWRITE_WORKER_COUNT_KEY, rewriteWorkerCount.value, '改写线程数量')
    await saveBasicSetting(IMAGE_GEN_WORKER_COUNT_KEY, imageGenWorkerCount.value, '生图线程数量')
    showToast('基础设置已保存。', 'success')
    await refreshMonitoring()
  } catch (error) {
    showToast(error instanceof Error ? error.message : '基础设置保存失败，请稍后重试。', 'error')
  } finally {
    isSavingBasicSettings.value = false
  }
}

const reloadBasicSettings = (): void => {
  void loadBasicSettings()
  showToast('已重新加载基础设置。', 'warning')
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
  void loadBasicSettings(true)
})
</script>

<template>
  <section class="page-section settings-layout">
    <header class="page-head">
      <h2 class="page-title">设置</h2>
      <p class="page-subtitle">在这里统一管理模型服务、自动化执行、主题外观、日志和数据库。</p>
    </header>

    <div class="settings-tabs">
      <button type="button" class="settings-tab" :class="{ 'settings-tab--active': activeSection === 'basic' }" @click="activeSection = 'basic'">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7H14.5a3.5 3.5 0 0 1 0 7H6"/></svg>
        基础设置
      </button>
      <button type="button" class="settings-tab" :class="{ 'settings-tab--active': activeSection === 'theme' }" @click="activeSection = 'theme'">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
        外观主题
      </button>
      <button type="button" class="settings-tab" :class="{ 'settings-tab--active': activeSection === 'logs' }" @click="activeSection = 'logs'">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
        日志管理
      </button>
      <button type="button" class="settings-tab" :class="{ 'settings-tab--active': activeSection === 'database' }" @click="activeSection = 'database'">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        数据库
      </button>
    </div>

    <div class="page-body settings-body">
      <transition name="section-fade" mode="out-in">
        <div v-if="activeSection === 'basic'" key="basic" class="settings-panel">
          <section class="settings-basic-hero">
            <div>
              <p class="settings-basic-hero__eyebrow">BASE SETTINGS</p>
              <h3 class="settings-basic-hero__title">把核心能力分成三组来管理</h3>
              <p class="settings-basic-hero__text">监控筛选门槛已从设置页移到文章监控执行弹窗。本页仅保留真正需要长期保存的全局配置。</p>
            </div>
            <div class="settings-basic-hero__meta">
              <span class="settings-basic-hero__badge">手动保存</span>
              <span class="settings-basic-hero__badge">本地设置数据库</span>
            </div>
          </section>

          <div class="settings-basic-overview">
            <article v-for="card in basicSettingCards" :key="card.title" class="settings-basic-overview__card" :data-accent="card.accent">
              <strong class="settings-basic-overview__title">{{ card.title }}</strong>
              <p class="settings-basic-overview__text">{{ card.description }}</p>
            </article>
          </div>

          <div class="basic-settings-grid">
            <section class="basic-settings-group basic-settings-group--feature">
              <div class="basic-settings-group__head">
                <h4 class="basic-settings-group__title">大模型服务</h4>
                <p class="basic-settings-group__text">标题改写、文章改写和通用对话测试都复用这里的配置。</p>
              </div>

              <div class="basic-settings-fields">
                <label class="basic-settings-field basic-settings-field--wide">
                  <span class="basic-settings-field__label">Base URL</span>
                  <input
                    v-model="llmBaseUrl"
                    type="text"
                    class="basic-settings-input"
                    placeholder="https://api.example.com/v1"
                  />
                </label>

                <label class="basic-settings-field">
                  <span class="basic-settings-field__label">API Key</span>
                  <input
                    v-model="llmApiKey"
                    type="password"
                    class="basic-settings-input"
                    placeholder="请输入大语言模型 API Key"
                  />
                </label>

                <label class="basic-settings-field">
                  <span class="basic-settings-field__label">Model</span>
                  <input
                    v-model="llmModel"
                    type="text"
                    class="basic-settings-input"
                    placeholder="gpt-4.1 / claude-opus-4-6"
                  />
                </label>
              </div>
            </section>

            <section class="basic-settings-group basic-settings-group--feature">
              <div class="basic-settings-group__head">
                <h4 class="basic-settings-group__title">图片服务</h4>
                <p class="basic-settings-group__text">用于 AI 实验室的图片生成测试。通过 chat/completions 接口以 SSE 流方式返回 base64 图片，格式与大模型服务一致，Base URL 填到 <code>/v1</code> 结尾即可。</p>
              </div>

              <div class="basic-settings-fields">
                <label class="basic-settings-field basic-settings-field--wide">
                  <span class="basic-settings-field__label">Base URL</span>
                  <input
                    v-model="imageBaseUrl"
                    type="text"
                    class="basic-settings-input"
                    placeholder="https://api.example.com/v1"
                  />
                </label>

                <label class="basic-settings-field">
                  <span class="basic-settings-field__label">API Key</span>
                  <input
                    v-model="imageApiKey"
                    type="password"
                    class="basic-settings-input"
                    placeholder="请输入生图服务 API Key"
                  />
                </label>

                <label class="basic-settings-field">
                  <span class="basic-settings-field__label">Model</span>
                  <input
                    v-model="imageModel"
                    type="text"
                    class="basic-settings-input"
                    placeholder="gpt-image-1 / flux-dev"
                  />
                </label>
              </div>
            </section>

            <section class="basic-settings-group basic-settings-group--feature">
              <div class="basic-settings-group__head">
                <h4 class="basic-settings-group__title">自动化执行</h4>
                <p class="basic-settings-group__text">控制 Playwright 的无头模式和并发线程数，文章监控仍会按这里的线程数并发运行。</p>
              </div>

              <div class="basic-settings-fields basic-settings-fields--compact">
                <label class="basic-settings-field">
                  <span class="basic-settings-field__label">是否无头</span>
                  <select
                    v-model="automationHeadless"
                    class="basic-settings-input"
                  >
                    <option value="true">是</option>
                    <option value="false">否</option>
                  </select>
                </label>

                <label class="basic-settings-field">
                  <span class="basic-settings-field__label">浏览器执行线程数量</span>
                  <input
                    v-model="automationWorkerCount"
                    type="number"
                    min="1"
                    max="16"
                    class="basic-settings-input"
                    placeholder="1"
                  />
                </label>
              </div>
            </section>

            <section class="basic-settings-group basic-settings-group--feature">
              <div class="basic-settings-group__head">
                <h4 class="basic-settings-group__title">内容改写</h4>
                <p class="basic-settings-group__text">控制文章改写和生图的并发线程数，改写线程池和生图线程池相互独立。</p>
              </div>

              <div class="basic-settings-fields basic-settings-fields--compact">
                <label class="basic-settings-field">
                  <span class="basic-settings-field__label">改写线程数量</span>
                  <input
                    v-model="rewriteWorkerCount"
                    type="number"
                    min="1"
                    max="16"
                    class="basic-settings-input"
                    placeholder="1"
                  />
                </label>

                <label class="basic-settings-field">
                  <span class="basic-settings-field__label">生图线程数量</span>
                  <input
                    v-model="imageGenWorkerCount"
                    type="number"
                    min="1"
                    max="16"
                    class="basic-settings-input"
                    placeholder="3"
                  />
                </label>
              </div>
            </section>
          </div>

          <div class="basic-settings-actions">
            <div class="basic-settings-hint">
              <span class="basic-settings-hint__text">基础设置改为手动保存。文章监控的播放量、点赞量、转发量条件已改为执行时配置。</span>
            </div>
            <div class="basic-settings-toolbar">
              <button type="button" class="action-btn" :disabled="isSavingBasicSettings" @click="saveAllBasicSettings">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                {{ basicSettingsSaveLabel }}
              </button>
              <button type="button" class="action-btn" :disabled="!isPywebviewAvailable || isSavingBasicSettings" @click="reloadBasicSettings">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                重新加载
              </button>
            </div>
          </div>
        </div>

        <div v-else-if="activeSection === 'theme'" key="theme" class="settings-panel">
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
