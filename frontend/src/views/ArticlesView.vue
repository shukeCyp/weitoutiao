<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useToastStore } from '../stores/toast'

const DEFAULT_PAGE_SIZE = 20
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]
const ARTICLE_FILTERS_SETTING_KEY = 'articles.filters'

const { showToast } = useToastStore()

const getDefaultArticleFilters = (): MonitoredArticleFilters => ({
  accountId: null,
  keyword: '',
  startTime: '',
  endTime: '',
  minPlayCount: '',
  minDiggCount: '',
  minCommentCount: '',
  minForwardCount: '',
})

const loading = ref(false)
const page = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const total = ref(0)
const totalPages = ref(1)
const items = ref<MonitoredArticleItem[]>([])
const accountOptions = ref<BenchmarkAccountOption[]>([])
const filters = ref<MonitoredArticleFilters>(getDefaultArticleFilters())
const savedFilters = ref<MonitoredArticleFilters>(getDefaultArticleFilters())

const hasItems = computed(() => items.value.length > 0)
const apiAvailable = computed(() => !!window.pywebview?.api)
const filterDialogVisible = ref(false)
const canDeleteAllArticles = computed(() => apiAvailable.value && !loading.value && hasItems.value)
const normalizedFilters = (): MonitoredArticleFilters => ({
  accountId: filters.value.accountId ? Number(filters.value.accountId) : null,
  keyword: (filters.value.keyword ?? '').trim(),
  startTime: filters.value.startTime || null,
  endTime: filters.value.endTime || null,
  minPlayCount: filters.value.minPlayCount === '' || filters.value.minPlayCount === null ? null : String(filters.value.minPlayCount).trim(),
  minDiggCount: filters.value.minDiggCount === '' || filters.value.minDiggCount === null ? null : String(filters.value.minDiggCount).trim(),
  minCommentCount:
    filters.value.minCommentCount === '' || filters.value.minCommentCount === null ? null : String(filters.value.minCommentCount).trim(),
  minForwardCount:
    filters.value.minForwardCount === '' || filters.value.minForwardCount === null ? null : String(filters.value.minForwardCount).trim(),
})
const activeFilterCount = computed(() => {
  const values = normalizedFilters()
  return [
    values.accountId,
    values.keyword,
    values.startTime,
    values.endTime,
    values.minPlayCount,
    values.minDiggCount,
    values.minCommentCount,
    values.minForwardCount,
  ].filter((value) => value !== null && value !== '').length
})

const applyNormalizedFilters = (value?: Partial<MonitoredArticleFilters> | null): MonitoredArticleFilters => {
  const next = getDefaultArticleFilters()
  if (value) {
    next.accountId = typeof value.accountId === 'number' ? value.accountId : null
    next.keyword = typeof value.keyword === 'string' ? value.keyword.trim() : ''
    next.startTime = typeof value.startTime === 'string' ? value.startTime : ''
    next.endTime = typeof value.endTime === 'string' ? value.endTime : ''
    next.minPlayCount = value.minPlayCount === null || value.minPlayCount === undefined ? '' : String(value.minPlayCount).trim()
    next.minDiggCount = value.minDiggCount === null || value.minDiggCount === undefined ? '' : String(value.minDiggCount).trim()
    next.minCommentCount = value.minCommentCount === null || value.minCommentCount === undefined ? '' : String(value.minCommentCount).trim()
    next.minForwardCount = value.minForwardCount === null || value.minForwardCount === undefined ? '' : String(value.minForwardCount).trim()
  }
  return next
}

const serializeFilters = (value: MonitoredArticleFilters): string => JSON.stringify(value)

const syncSavedFilters = (value: MonitoredArticleFilters): void => {
  savedFilters.value = applyNormalizedFilters(value)
}

const saveCurrentFilters = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    return
  }

  const normalized = normalizedFilters()
  if (serializeFilters(normalized) === serializeFilters(normalizedFiltersFromSaved())) {
    return
  }

  await api.set_setting(ARTICLE_FILTERS_SETTING_KEY, serializeFilters(normalized))
  syncSavedFilters(normalized)
}

const normalizedFiltersFromSaved = (): MonitoredArticleFilters => ({
  accountId: savedFilters.value.accountId ? Number(savedFilters.value.accountId) : null,
  keyword: (savedFilters.value.keyword ?? '').trim(),
  startTime: savedFilters.value.startTime || null,
  endTime: savedFilters.value.endTime || null,
  minPlayCount:
    savedFilters.value.minPlayCount === '' || savedFilters.value.minPlayCount === null ? null : String(savedFilters.value.minPlayCount).trim(),
  minDiggCount:
    savedFilters.value.minDiggCount === '' || savedFilters.value.minDiggCount === null ? null : String(savedFilters.value.minDiggCount).trim(),
  minCommentCount:
    savedFilters.value.minCommentCount === '' || savedFilters.value.minCommentCount === null
      ? null
      : String(savedFilters.value.minCommentCount).trim(),
  minForwardCount:
    savedFilters.value.minForwardCount === '' || savedFilters.value.minForwardCount === null
      ? null
      : String(savedFilters.value.minForwardCount).trim(),
})

const loadSavedFilters = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    filters.value = getDefaultArticleFilters()
    syncSavedFilters(getDefaultArticleFilters())
    return
  }

  try {
    const raw = await api.get_setting(ARTICLE_FILTERS_SETTING_KEY)
    if (!raw) {
      filters.value = getDefaultArticleFilters()
      syncSavedFilters(getDefaultArticleFilters())
      return
    }

    const parsed = JSON.parse(raw) as Partial<MonitoredArticleFilters>
    const normalized = applyNormalizedFilters(parsed)
    filters.value = normalized
    syncSavedFilters(normalized)
  } catch {
    filters.value = getDefaultArticleFilters()
    syncSavedFilters(getDefaultArticleFilters())
  }
}

const loadAccounts = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    return
  }

  accountOptions.value = await api.list_benchmark_account_options()
}

const loadArticles = async (targetPage = page.value): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    items.value = []
    total.value = 0
    totalPages.value = 1
    showToast('当前环境不支持读取文章列表。', 'warning')
    return
  }

  loading.value = true
  clearSelection()
  try {
    const result = await api.list_monitored_articles(normalizedFilters(), targetPage, pageSize.value)
    items.value = result.items
    total.value = result.total
    page.value = result.page
    totalPages.value = result.totalPages
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读取文章列表失败。', 'error')
  } finally {
    loading.value = false
  }
}

const applyFilters = async (): Promise<void> => {
  try {
    await saveCurrentFilters()
    filterDialogVisible.value = false
    await loadArticles(1)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '保存筛选条件失败。', 'error')
  }
}

const resetFilters = async (): Promise<void> => {
  filters.value = getDefaultArticleFilters()
  try {
    await saveCurrentFilters()
    filterDialogVisible.value = false
    await loadArticles(1)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '重置筛选失败。', 'error')
  }
}

const openFilterDialog = (): void => {
  filterDialogVisible.value = true
}

const closeFilterDialog = (): void => {
  filterDialogVisible.value = false
}

const goToPreviousPage = (): void => {
  if (page.value <= 1 || loading.value) {
    return
  }
  void loadArticles(page.value - 1)
}

const goToNextPage = (): void => {
  if (page.value >= totalPages.value || loading.value) {
    return
  }
  void loadArticles(page.value + 1)
}

const handlePageSizeChange = (): void => {
  void loadArticles(1)
}

const getPreviewContent = (content: string | null): string => {
  if (!content) {
    return '-'
  }
  return content.length > 36 ? `${content.slice(0, 36)}...` : content
}

const formatPlayCount = (value?: number | null): string => {
  if (value === null || value === undefined) {
    return '-'
  }
  if (value < 10000) {
    return String(value)
  }
  return `${(value / 10000).toFixed(2)}W`
}

const openArticle = async (item: MonitoredArticleItem): Promise<void> => {
  const api = window.pywebview?.api
  const targetUrl = item.displayUrl || item.benchmarkAccountUrl
  if (!api || !targetUrl) {
    showToast('当前文章没有可打开的链接。', 'warning')
    return
  }

  const success = await api.open_external_url(targetUrl)
  if (!success) {
    showToast('打开文章失败。', 'error')
  }
}

const REWRITE_TEMPLATE_OPTIONS: Array<{ key: ArticleRewriteTemplateKey; label: string }> = [
  { key: 'international_account_starter', label: '起号版' },
  { key: 'international_stable_hardcore', label: '硬核版' },
  { key: 'international_stable_strategic', label: '战略版' },
]

const rewriteDialogVisible = ref(false)
const rewritingItem = ref<MonitoredArticleItem | null>(null)
const rewriteTemplateKey = ref<ArticleRewriteTemplateKey>('international_account_starter')
const rewritingIds = ref(new Set<number>())

const openRewriteDialog = (item: MonitoredArticleItem): void => {
  rewritingItem.value = item
  rewriteDialogVisible.value = true
}

const closeRewriteDialog = (): void => {
  rewriteDialogVisible.value = false
  rewritingItem.value = null
}

const confirmRewrite = async (): Promise<void> => {
  const api = window.pywebview?.api
  const item = rewritingItem.value
  if (!api || !item) {
    return
  }

  rewriteDialogVisible.value = false
  rewritingIds.value.add(item.id)

  try {
    const result = await api.rewrite_article_full(item.id, rewriteTemplateKey.value)
    const target = items.value.find((a) => a.id === item.id)
    if (target) {
      target.rewrittenTitle = result.rewrittenTitle
      target.rewrittenIntro = result.rewrittenIntro
      target.rewrittenArticle = JSON.stringify(result.rewrittenArticle)
      target.imagePrompts = JSON.stringify(result.imagePrompts)
      target.imagePaths = JSON.stringify(result.imagePaths)
    }
    showToast(`文章改写完成，已生成 ${result.imagePaths.filter(Boolean).length} 张图片。`, 'success')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '文章改写失败。', 'error')
  } finally {
    rewritingIds.value.delete(item.id)
    rewritingItem.value = null
  }
}

const isRewriting = (item: MonitoredArticleItem): boolean => rewritingIds.value.has(item.id)

const isCompleted = (item: MonitoredArticleItem): boolean => {
  if (!item.rewrittenTitle || !item.rewrittenIntro || !item.rewrittenArticle || !item.imagePrompts || !item.imagePaths) return false
  const paths = parseJsonArray(item.imagePaths)
  return paths.length >= 3 && paths.every((p) => !!p)
}

const isPartial = (item: MonitoredArticleItem): boolean => {
  if (isCompleted(item)) return false
  return !!(item.rewrittenTitle || item.rewrittenArticle || item.imagePrompts || item.imagePaths)
}

const isRewritten = (item: MonitoredArticleItem): boolean => isCompleted(item) || isPartial(item)

const viewDialogVisible = ref(false)
const viewingItem = ref<MonitoredArticleItem | null>(null)

const openViewDialog = (item: MonitoredArticleItem): void => {
  viewingItem.value = item
  viewDialogVisible.value = true
}

const closeViewDialog = (): void => {
  viewDialogVisible.value = false
  viewingItem.value = null
}

// ── 多选 ─────────────────────────────────────────────────────────────
const selectedIds = ref(new Set<number>())

const isSelected = (item: MonitoredArticleItem): boolean => selectedIds.value.has(item.id)

const toggleSelect = (item: MonitoredArticleItem): void => {
  if (selectedIds.value.has(item.id)) {
    selectedIds.value.delete(item.id)
  } else {
    selectedIds.value.add(item.id)
  }
}

const allSelected = computed((): boolean => hasItems.value && items.value.every((i) => selectedIds.value.has(i.id)))
const someSelected = computed((): boolean => selectedIds.value.size > 0)

const toggleSelectAll = (): void => {
  if (allSelected.value) {
    items.value.forEach((i) => selectedIds.value.delete(i.id))
  } else {
    items.value.forEach((i) => selectedIds.value.add(i.id))
  }
}

// 翻页/刷新后清空选择
const clearSelection = (): void => {
  selectedIds.value.clear()
}

// ── 全局批量改写 ───────────────────────────────────────────────────────
const globalBatchRewriteDialogVisible = ref(false)
const globalBatchRewriteTemplateKey = ref<ArticleRewriteTemplateKey>('international_account_starter')
const globalBatchRewriteScope = ref<'incomplete' | 'all'>('incomplete')

interface GlobalBatchRewriteState {
  running: boolean
  total: number
  done: number
  succeeded: number
  failed: number
  currentTitle: string
}

const globalBatchRewriteState = ref<GlobalBatchRewriteState>({
  running: false, total: 0, done: 0, succeeded: 0, failed: 0, currentTitle: '',
})

const openGlobalBatchRewriteDialog = (): void => {
  if (globalBatchRewriteState.value.running) return
  globalBatchRewriteDialogVisible.value = true
}

const closeGlobalBatchRewriteDialog = (): void => {
  globalBatchRewriteDialogVisible.value = false
}

const confirmGlobalBatchRewrite = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api || globalBatchRewriteState.value.running) return

  globalBatchRewriteDialogVisible.value = false

  const skipRewritten = globalBatchRewriteScope.value === 'incomplete'
  const ids = await api.list_article_ids_for_batch(normalizedFilters(), skipRewritten)
  if (!ids.length) {
    showToast('没有符合条件的文章需要改写。', 'warning')
    return
  }

  // 读取改写线程数设置
  const workerCountRaw = await api.get_setting('rewrite.worker_count')
  const concurrency = Math.max(1, Math.min(parseInt(workerCountRaw ?? '1') || 1, 16))

  globalBatchRewriteState.value = { running: true, total: ids.length, done: 0, succeeded: 0, failed: 0, currentTitle: '' }

  // 并发 worker 池：同时跑 concurrency 个请求，一个完成后立即取下一个
  const queue = [...ids]

  const worker = async (): Promise<void> => {
    while (queue.length > 0) {
      const id = queue.shift()!
      rewritingIds.value.add(id)
      const currentItem = items.value.find((a) => a.id === id)
      globalBatchRewriteState.value.currentTitle =
        currentItem?.content?.slice(0, 20) || `ID ${id}`

      try {
        const result = await api.rewrite_article_full(id, globalBatchRewriteTemplateKey.value)
        const target = items.value.find((a) => a.id === id)
        if (target) {
          target.rewrittenTitle = result.rewrittenTitle
          target.rewrittenIntro = result.rewrittenIntro
          target.rewrittenArticle = JSON.stringify(result.rewrittenArticle)
          target.imagePrompts = JSON.stringify(result.imagePrompts)
          target.imagePaths = JSON.stringify(result.imagePaths)
        }
        globalBatchRewriteState.value.succeeded++
      } catch {
        globalBatchRewriteState.value.failed++
      } finally {
        rewritingIds.value.delete(id)
        globalBatchRewriteState.value.done++
      }
    }
  }

  // 启动 concurrency 个并发 worker，全部完成后结束
  await Promise.all(Array.from({ length: concurrency }, worker))

  const s = globalBatchRewriteState.value
  globalBatchRewriteState.value.running = false
  globalBatchRewriteState.value.currentTitle = ''
  showToast(
    s.failed === 0
      ? `批量改写完成，共 ${s.succeeded} 篇。`
      : `批量改写完成，成功 ${s.succeeded} 篇，失败 ${s.failed} 篇。`,
    s.failed === 0 ? 'success' : 'warning',
  )
}

// ── 全局批量下载 ───────────────────────────────────────────────────────
interface GlobalBatchDownloadState {
  running: boolean
  succeeded: number
  failed: number
  skipped: number
  folder: string
}

const globalBatchDownloadState = ref<GlobalBatchDownloadState>({
  running: false, succeeded: 0, failed: 0, skipped: 0, folder: '',
})

const startGlobalBatchDownload = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api || globalBatchDownloadState.value.running) return

  const ids = await api.list_completed_article_ids(normalizedFilters())
  if (!ids.length) {
    showToast('没有已完成改写的文章可以下载。', 'warning')
    return
  }

  globalBatchDownloadState.value = { running: true, succeeded: 0, failed: 0, skipped: 0, folder: '' }

  try {
    const result = await api.batch_download_articles_docx(ids)
    if (result.status === 'success') {
      globalBatchDownloadState.value = {
        running: false,
        succeeded: result.succeeded ?? 0,
        failed: result.failed ?? 0,
        skipped: result.skipped ?? 0,
        folder: result.folder ?? '',
      }
      const msg = `批量下载完成：成功 ${result.succeeded} 篇${result.skipped ? `，跳过 ${result.skipped} 篇` : ''}${result.failed ? `，失败 ${result.failed} 篇` : ''}。`
      showToast(msg, (result.failed ?? 0) > 0 ? 'warning' : 'success')
    } else if (result.status === 'cancel') {
      globalBatchDownloadState.value.running = false
    } else {
      globalBatchDownloadState.value.running = false
      showToast(result.message || '批量下载失败。', 'error')
    }
  } catch (error) {
    globalBatchDownloadState.value.running = false
    showToast(error instanceof Error ? error.message : '批量下载失败。', 'error')
  }
}

// ── 状态 Dialog ────────────────────────────────────────────────────────
const statusDialogVisible = ref(false)

const hasAnyBatchTask = computed(() =>
  globalBatchRewriteState.value.running ||
  globalBatchRewriteState.value.done > 0 ||
  globalBatchDownloadState.value.running ||
  globalBatchDownloadState.value.succeeded > 0 ||
  globalBatchDownloadState.value.failed > 0,
)

// ── 选框批量改写（保留，基于复选框）──────────────────────────────────
const batchRewriteDialogVisible = ref(false)
const batchRewriteTemplateKey = ref<ArticleRewriteTemplateKey>('international_account_starter')
const batchRewriting = ref(false)
const batchRewriteProgress = ref({ done: 0, total: 0 })

const openBatchRewriteDialog = (): void => {
  if (!someSelected.value) return
  batchRewriteDialogVisible.value = true
}

const closeBatchRewriteDialog = (): void => {
  batchRewriteDialogVisible.value = false
}

const confirmBatchRewrite = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api || batchRewriting.value) return

  const ids = Array.from(selectedIds.value)
  batchRewriteDialogVisible.value = false
  batchRewriting.value = true
  batchRewriteProgress.value = { done: 0, total: ids.length }

  let succeeded = 0
  let failed = 0

  for (const id of ids) {
    rewritingIds.value.add(id)
    try {
      const result = await api.rewrite_article_full(id, batchRewriteTemplateKey.value)
      const target = items.value.find((a) => a.id === id)
      if (target) {
        target.rewrittenTitle = result.rewrittenTitle
        target.rewrittenIntro = result.rewrittenIntro
        target.rewrittenArticle = JSON.stringify(result.rewrittenArticle)
        target.imagePrompts = JSON.stringify(result.imagePrompts)
        target.imagePaths = JSON.stringify(result.imagePaths)
      }
      succeeded++
    } catch {
      failed++
    } finally {
      rewritingIds.value.delete(id)
      batchRewriteProgress.value.done++
    }
  }

  batchRewriting.value = false
  if (failed === 0) {
    showToast(`批量改写完成，共 ${succeeded} 篇。`, 'success')
  } else {
    showToast(`批量改写完成，成功 ${succeeded} 篇，失败 ${failed} 篇。`, 'warning')
  }
}

// ── 选框批量下载（保留，基于复选框）──────────────────────────────────
const batchDownloading = ref(false)

const batchDownloadDocx = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api || batchDownloading.value) return

  const ids = Array.from(selectedIds.value)
  if (!ids.length) return

  batchDownloading.value = true
  try {
    const result = await api.batch_download_articles_docx(ids)
    if (result.status === 'success') {
      const msg = `批量下载完成：成功 ${result.succeeded} 篇${result.skipped ? `，跳过 ${result.skipped} 篇（未完成）` : ''}${result.failed ? `，失败 ${result.failed} 篇` : ''}。`
      showToast(msg, result.failed ? 'warning' : 'success')
    } else if (result.status === 'error') {
      showToast(result.message || '批量下载失败。', 'error')
    }
  } catch (error) {
    showToast(error instanceof Error ? error.message : '批量下载失败。', 'error')
  } finally {
    batchDownloading.value = false
  }
}

// ── 单篇下载 ──────────────────────────────────────────────────────────
const downloadingIds = ref(new Set<number>())

const downloadArticleDocx = async (item: MonitoredArticleItem): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) return

  downloadingIds.value.add(item.id)
  try {
    const result = await api.download_article_docx(item.id)
    if (result.status === 'success') {
      showToast('Word 文档已保存。', 'success')
    } else if (result.status === 'error') {
      showToast(result.message || '下载失败。', 'error')
    }
  } catch (error) {
    showToast(error instanceof Error ? error.message : '下载失败。', 'error')
  } finally {
    downloadingIds.value.delete(item.id)
  }
}

const isDownloading = (item: MonitoredArticleItem): boolean => downloadingIds.value.has(item.id)

const parseJsonArray = (raw: string | null): string[] => {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === 'string' && v) : []
  } catch {
    return []
  }
}

const viewArticleSections = computed(() => parseJsonArray(viewingItem.value?.rewrittenArticle ?? null))
const viewImagePrompts = computed(() => parseJsonArray(viewingItem.value?.imagePrompts ?? null))
const viewImagePaths = computed(() =>
  parseJsonArray(viewingItem.value?.imagePaths ?? null).map((p) => (p ? `file://${p}` : null)).filter(Boolean) as string[],
)

const reloadAfterDeletion = async (deletedCount: number): Promise<void> => {
  const remaining = Math.max(0, total.value - deletedCount)
  const nextTotalPages = remaining > 0 ? Math.ceil(remaining / pageSize.value) : 1
  await loadArticles(Math.min(page.value, nextTotalPages))
}

const removeAllArticles = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持全部删除文章。', 'warning')
    return
  }

  if (!window.confirm(`确认全部删除当前文章库中的 ${total.value} 篇文章吗？\n\n该操作会执行软删除，数据不会物理移除，但列表将不再显示。`)) {
    return
  }

  try {
    const deletedCount = await api.soft_delete_all_monitored_articles()
    if (!deletedCount) {
      showToast('当前没有可删除的文章。', 'warning')
      await loadArticles(1)
      return
    }
    showToast(`已删除 ${deletedCount} 篇文章。`, 'success')
    await reloadAfterDeletion(deletedCount)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '全部删除文章失败。', 'error')
  }
}

const removeArticle = async (item: MonitoredArticleItem): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持删除文章。', 'warning')
    return
  }

  const confirmed = window.confirm('确定删除这篇文章吗？')
  if (!confirmed) {
    return
  }

  try {
    const success = await api.delete_monitored_article(item.id)
    if (!success) {
      throw new Error('delete failed')
    }
    showToast('文章已删除。', 'success')
    await reloadAfterDeletion(1)
  } catch {
    showToast('删除文章失败。', 'error')
  }
}

onMounted(() => {
  void (async () => {
    await loadSavedFilters()
    await loadAccounts()
    await loadArticles(1)
  })()
})
</script>

<template>
  <section class="page-section articles-layout articles-layout--wide">
    <header class="page-head articles-head">
      <div>
        <h2 class="page-title">文章列表</h2>
        <p class="page-subtitle">查看已保存到数据库的微头条文章，并按账号、关键词、时间和数据指标筛选。</p>
      </div>

      <div class="articles-head__actions">
        <!-- 全局批量按钮（始终显示） -->
        <button
          type="button"
          class="action-btn"
          :class="{ 'action-btn--active': hasAnyBatchTask }"
          @click="statusDialogVisible = true"
        >状态</button>
        <button
          type="button"
          class="action-btn"
          :disabled="globalBatchRewriteState.running || !apiAvailable"
          @click="openGlobalBatchRewriteDialog"
        >{{ globalBatchRewriteState.running ? `改写中 ${globalBatchRewriteState.done}/${globalBatchRewriteState.total}` : '批量改写' }}</button>
        <button
          type="button"
          class="action-btn"
          :disabled="globalBatchDownloadState.running || !apiAvailable"
          @click="startGlobalBatchDownload"
        >{{ globalBatchDownloadState.running ? '下载中...' : '批量下载' }}</button>

        <!-- 选框批量（仅选中时显示） -->
        <template v-if="someSelected">
          <span class="articles-selection-count">已选 {{ selectedIds.size }} 篇</span>
          <button
            type="button"
            class="action-btn"
            :disabled="batchRewriting || !apiAvailable"
            @click="openBatchRewriteDialog"
          >{{ batchRewriting ? `改写中 ${batchRewriteProgress.done}/${batchRewriteProgress.total}` : '选框改写' }}</button>
          <button
            type="button"
            class="action-btn"
            :disabled="batchDownloading || !apiAvailable"
            @click="batchDownloadDocx"
          >{{ batchDownloading ? '下载中...' : '选框下载' }}</button>
        </template>

        <button type="button" class="action-btn action-btn--danger" :disabled="!canDeleteAllArticles" @click="removeAllArticles">
          全部删除
        </button>
        <button type="button" class="action-btn" :disabled="!apiAvailable || loading" @click="openFilterDialog">
          筛选
          <span v-if="activeFilterCount" class="articles-filter-count">{{ activeFilterCount }}</span>
        </button>
      </div>
    </header>

    <div class="page-body articles-body">
      <div class="benchmark-table-wrap articles-table-wrap">
        <table class="benchmark-table articles-table">
          <thead>
            <tr>
              <th class="articles-table__check">
                <input type="checkbox" :checked="allSelected" :indeterminate="someSelected && !allSelected" @change="toggleSelectAll" />
              </th>
              <th>ID</th>
              <th>发布时间</th>
              <th>内容</th>
              <th>播放量</th>
              <th>点赞量</th>
              <th>转发量</th>
              <th>改写状态</th>
              <th class="articles-table__actions">操作</th>
            </tr>
          </thead>
          <tbody v-if="hasItems && !loading">
            <tr v-for="item in items" :key="item.id" :class="{ 'articles-row--selected': isSelected(item) }">
              <td class="articles-table__check">
                <input type="checkbox" :checked="isSelected(item)" @change="toggleSelect(item)" />
              </td>
              <td>{{ item.itemId || item.groupId || item.id || '-' }}</td>
              <td>{{ item.publishTime || '-' }}</td>
              <td class="articles-table__content" :title="item.content || '-'">{{ getPreviewContent(item.content) }}</td>
              <td>{{ formatPlayCount(item.playCount) }}</td>
              <td>{{ item.diggCount ?? '-' }}</td>
              <td>{{ item.forwardCount ?? '-' }}</td>
              <td>
                <span v-if="isRewriting(item)" class="rewrite-badge rewrite-badge--pending">改写中...</span>
                <span v-else-if="isCompleted(item)" class="rewrite-badge rewrite-badge--done">已完成</span>
                <span v-else-if="isPartial(item)" class="rewrite-badge rewrite-badge--partial">未完成</span>
                <span v-else class="rewrite-badge rewrite-badge--none">未改写</span>
              </td>
              <td class="articles-table__actions">
                <div class="benchmark-actions benchmark-actions--compact">
                  <button type="button" class="action-btn" @click="openArticle(item)">打开</button>
                  <button
                    type="button"
                    class="action-btn"
                    :disabled="isRewriting(item) || !apiAvailable"
                    @click="openRewriteDialog(item)"
                  >{{ isPartial(item) ? '继续' : '改写' }}</button>
                  <button
                    v-if="isRewritten(item)"
                    type="button"
                    class="action-btn action-btn--accent"
                    @click="openViewDialog(item)"
                  >查看</button>
                  <button
                    v-if="isCompleted(item)"
                    type="button"
                    class="action-btn"
                    :disabled="isDownloading(item) || !apiAvailable"
                    @click="downloadArticleDocx(item)"
                  >{{ isDownloading(item) ? '下载中...' : '下载' }}</button>
                  <button type="button" class="action-btn action-btn--danger" @click="removeArticle(item)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="loading" class="benchmark-empty-state">正在加载文章列表...</div>
        <div v-else-if="!hasItems" class="benchmark-empty-state">暂无文章数据，请先在对标账号页执行监控。</div>
      </div>

      <footer class="benchmark-pagination">
        <div class="benchmark-pagination__left">
          <label class="benchmark-page-size">
            <span>每页</span>
            <select v-model="pageSize" class="benchmark-page-size__select" @change="handlePageSizeChange">
              <option v-for="size in PAGE_SIZE_OPTIONS" :key="size" :value="size">{{ size }}</option>
            </select>
            <span>条</span>
          </label>
          <span class="benchmark-pagination__info">第 {{ page }} / {{ totalPages }} 页，共 {{ total }} 条</span>
        </div>

        <div class="benchmark-pagination__actions">
          <button type="button" class="action-btn" :disabled="page <= 1 || loading" @click="goToPreviousPage">上一页</button>
          <button type="button" class="action-btn" :disabled="page >= totalPages || loading" @click="goToNextPage">下一页</button>
        </div>
      </footer>
    </div>

    <Teleport to="body">
      <!-- 全局批量改写 Dialog -->
      <div v-if="globalBatchRewriteDialogVisible" class="benchmark-dialog-mask" @click.self="closeGlobalBatchRewriteDialog">
        <div class="benchmark-dialog benchmark-dialog--rewrite">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">批量改写</h3>
              <p class="benchmark-dialog__text">根据当前筛选条件，对文章库中的文章批量进行改写。</p>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="closeGlobalBatchRewriteDialog">×</button>
          </div>

          <div class="benchmark-dialog__body">
            <label class="articles-filter">
              <span>改写模板</span>
              <select v-model="globalBatchRewriteTemplateKey" class="benchmark-page-size__select">
                <option v-for="option in REWRITE_TEMPLATE_OPTIONS" :key="option.key" :value="option.key">
                  {{ option.label }}
                </option>
              </select>
            </label>
            <label class="articles-filter" style="margin-top: 12px;">
              <span>改写范围</span>
              <select v-model="globalBatchRewriteScope" class="benchmark-page-size__select">
                <option value="incomplete">只改写未改写的文章</option>
                <option value="all">全部覆盖改写（包含已改写）</option>
              </select>
            </label>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" @click="closeGlobalBatchRewriteDialog">取消</button>
            <button type="button" class="action-btn" @click="confirmGlobalBatchRewrite">开始批量改写</button>
          </div>
        </div>
      </div>

      <!-- 状态 Dialog -->
      <div v-if="statusDialogVisible" class="benchmark-dialog-mask" @click.self="statusDialogVisible = false">
        <div class="benchmark-dialog benchmark-dialog--status">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">批量任务状态</h3>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="statusDialogVisible = false">×</button>
          </div>

          <div class="benchmark-dialog__body">
            <div v-if="!hasAnyBatchTask" class="status-empty">暂无正在进行的批量任务</div>
            <template v-else>
              <!-- 改写进度 -->
              <div class="status-section">
                <h4 class="status-section__title">批量改写</h4>
                <template v-if="globalBatchRewriteState.done > 0 || globalBatchRewriteState.running">
                  <p class="status-section__row">
                    <span>进度：</span>
                    <span>{{ globalBatchRewriteState.done }} / {{ globalBatchRewriteState.total }} 篇</span>
                    <span v-if="globalBatchRewriteState.running" class="status-badge status-badge--running">进行中</span>
                    <span v-else class="status-badge status-badge--done">已完成</span>
                  </p>
                  <p class="status-section__row">
                    <span>成功：{{ globalBatchRewriteState.succeeded }} 篇</span>
                    <span v-if="globalBatchRewriteState.failed > 0" style="color: var(--danger, #e74c3c); margin-left: 12px;">失败：{{ globalBatchRewriteState.failed }} 篇</span>
                  </p>
                  <p v-if="globalBatchRewriteState.running && globalBatchRewriteState.currentTitle" class="status-section__row status-section__row--current">
                    当前：{{ globalBatchRewriteState.currentTitle }}
                  </p>
                </template>
                <p v-else class="status-section__empty">暂无改写任务</p>
              </div>

              <!-- 下载进度 -->
              <div class="status-section" style="margin-top: 16px;">
                <h4 class="status-section__title">批量下载</h4>
                <template v-if="globalBatchDownloadState.running || globalBatchDownloadState.succeeded > 0 || globalBatchDownloadState.failed > 0">
                  <p v-if="globalBatchDownloadState.running" class="status-section__row">
                    <span>保存中...</span>
                    <span class="status-badge status-badge--running">进行中</span>
                  </p>
                  <p v-else class="status-section__row">
                    <span>完成 {{ globalBatchDownloadState.succeeded }} 篇</span>
                    <span v-if="globalBatchDownloadState.skipped > 0" style="margin-left: 12px;">跳过 {{ globalBatchDownloadState.skipped }} 篇</span>
                    <span v-if="globalBatchDownloadState.failed > 0" style="color: var(--danger, #e74c3c); margin-left: 12px;">失败 {{ globalBatchDownloadState.failed }} 篇</span>
                    <span class="status-badge status-badge--done" style="margin-left: 12px;">已完成</span>
                  </p>
                  <p v-if="globalBatchDownloadState.folder" class="status-section__row" style="font-size: 12px; color: #888; word-break: break-all;">
                    路径：{{ globalBatchDownloadState.folder }}
                  </p>
                </template>
                <p v-else class="status-section__empty">暂无下载任务</p>
              </div>
            </template>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" @click="statusDialogVisible = false">关闭</button>
          </div>
        </div>
      </div>

      <!-- 选框批量改写 Dialog -->
      <div v-if="batchRewriteDialogVisible" class="benchmark-dialog-mask" @click.self="closeBatchRewriteDialog">
        <div class="benchmark-dialog benchmark-dialog--rewrite">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">批量改写（已选）</h3>
              <p class="benchmark-dialog__text">将对已选 {{ selectedIds.size }} 篇文章依次进行改写，改写过程中请勿关闭窗口。</p>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="closeBatchRewriteDialog">×</button>
          </div>

          <div class="benchmark-dialog__body">
            <label class="articles-filter">
              <span>改写模板</span>
              <select v-model="batchRewriteTemplateKey" class="benchmark-page-size__select">
                <option v-for="option in REWRITE_TEMPLATE_OPTIONS" :key="option.key" :value="option.key">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" @click="closeBatchRewriteDialog">取消</button>
            <button type="button" class="action-btn" @click="confirmBatchRewrite">开始批量改写</button>
          </div>
        </div>
      </div>

      <div v-if="rewriteDialogVisible" class="benchmark-dialog-mask" @click.self="closeRewriteDialog">
        <div class="benchmark-dialog benchmark-dialog--rewrite">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">改写文章</h3>
              <p class="benchmark-dialog__text">选择改写模板后开始改写。改写完成将自动生成配图并保存结果。</p>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="closeRewriteDialog">×</button>
          </div>

          <div class="benchmark-dialog__body">
            <label class="articles-filter">
              <span>改写模板</span>
              <select v-model="rewriteTemplateKey" class="benchmark-page-size__select">
                <option v-for="option in REWRITE_TEMPLATE_OPTIONS" :key="option.key" :value="option.key">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" @click="closeRewriteDialog">取消</button>
            <button type="button" class="action-btn" @click="confirmRewrite">开始改写</button>
          </div>
        </div>
      </div>

      <div v-if="viewDialogVisible" class="benchmark-dialog-mask" @click.self="closeViewDialog">
        <div class="benchmark-dialog rewrite-view-dialog">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">改写结果查看</h3>
              <p class="benchmark-dialog__text rewrite-view-dialog__subtitle">{{ viewingItem?.rewrittenTitle || '-' }}</p>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="closeViewDialog">×</button>
          </div>

          <div class="benchmark-dialog__body rewrite-view-dialog__body">
            <section class="rewrite-view-section">
              <h4 class="rewrite-view-section__title">改写标题</h4>
              <p class="rewrite-view-section__content rewrite-view-section__content--title">{{ viewingItem?.rewrittenTitle || '-' }}</p>
            </section>

            <section v-if="viewingItem?.rewrittenIntro" class="rewrite-view-section">
              <h4 class="rewrite-view-section__title">导语</h4>
              <p class="rewrite-view-section__content">{{ viewingItem.rewrittenIntro }}</p>
            </section>

            <section class="rewrite-view-section">
              <h4 class="rewrite-view-section__title">改写正文</h4>
              <div v-if="viewArticleSections.length" class="rewrite-view-article">
                <div
                  v-for="(section, idx) in viewArticleSections"
                  :key="idx"
                  class="rewrite-view-article__block"
                >
                  <span class="rewrite-view-article__label">{{ String(idx + 1).padStart(2, '0') }}</span>
                  <p class="rewrite-view-article__text">{{ section }}</p>
                </div>
              </div>
              <p v-else class="rewrite-view-empty">暂无正文内容。</p>
            </section>

            <section class="rewrite-view-section">
              <h4 class="rewrite-view-section__title">图片提示词</h4>
              <div v-if="viewImagePrompts.length" class="rewrite-view-prompts">
                <div
                  v-for="(prompt, idx) in viewImagePrompts"
                  :key="idx"
                  class="rewrite-view-prompt"
                >
                  <span class="rewrite-view-prompt__index">{{ idx + 1 }}</span>
                  <p class="rewrite-view-prompt__text">{{ prompt }}</p>
                </div>
              </div>
              <p v-else class="rewrite-view-empty">暂无图片提示词。</p>
            </section>

            <section class="rewrite-view-section">
              <h4 class="rewrite-view-section__title">生成图片</h4>
              <div v-if="viewImagePaths.length" class="rewrite-view-images">
                <div
                  v-for="(src, idx) in viewImagePaths"
                  :key="idx"
                  class="rewrite-view-image-wrap"
                >
                  <img :src="src" :alt="`配图 ${idx + 1}`" class="rewrite-view-image" @error="(e) => (e.target as HTMLImageElement).style.display='none'" />
                  <p class="rewrite-view-image__caption">配图 {{ idx + 1 }}</p>
                </div>
              </div>
              <p v-else class="rewrite-view-empty">暂无生成图片。</p>
            </section>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" @click="closeViewDialog">关闭</button>
          </div>
        </div>
      </div>

      <div v-if="filterDialogVisible" class="benchmark-dialog-mask" @click.self="closeFilterDialog">
        <div class="benchmark-dialog benchmark-dialog--article-filter">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">筛选文章</h3>
              <p class="benchmark-dialog__text">按账号、时间、关键词和指标快速定位已保存文章。应用后会保存为下次默认筛选条件。</p>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="closeFilterDialog">×</button>
          </div>

          <div class="benchmark-dialog__body articles-filter-dialog-shell">
            <section class="articles-filter-group">
              <div class="articles-filter-group__head">
                <h4 class="articles-filter-group__title">基础筛选</h4>
                <p class="articles-filter-group__text">先缩小账号和关键词范围。</p>
              </div>
              <div class="articles-filter-dialog articles-filter-dialog--basic">
                <label class="articles-filter">
                  <span>对标账号</span>
                  <select v-model="filters.accountId" class="benchmark-page-size__select">
                    <option :value="null">全部账号</option>
                    <option v-for="account in accountOptions" :key="account.id" :value="account.id">{{ account.url }}</option>
                  </select>
                </label>

                <label class="articles-filter">
                  <span>关键词</span>
                  <input v-model="filters.keyword" type="text" class="basic-settings-input" placeholder="按正文搜索" />
                </label>
              </div>
            </section>

            <section class="articles-filter-group">
              <div class="articles-filter-group__head">
                <h4 class="articles-filter-group__title">时间范围</h4>
                <p class="articles-filter-group__text">可按发布时间筛选本次要查看的数据区间。</p>
              </div>
              <div class="articles-filter-dialog">
                <label class="articles-filter">
                  <span>开始时间</span>
                  <input v-model="filters.startTime" type="datetime-local" class="basic-settings-input" />
                </label>

                <label class="articles-filter">
                  <span>结束时间</span>
                  <input v-model="filters.endTime" type="datetime-local" class="basic-settings-input" />
                </label>
              </div>
            </section>

            <section class="articles-filter-group">
              <div class="articles-filter-group__head">
                <h4 class="articles-filter-group__title">数据门槛</h4>
                <p class="articles-filter-group__text">按关键指标快速过滤低价值文章。</p>
              </div>
              <div class="articles-filter-dialog articles-filter-dialog--metrics">
                <label class="articles-filter">
                  <span>最低播放量</span>
                  <input v-model="filters.minPlayCount" type="number" min="0" class="basic-settings-input" />
                </label>

                <label class="articles-filter">
                  <span>最低点赞量</span>
                  <input v-model="filters.minDiggCount" type="number" min="0" class="basic-settings-input" />
                </label>

                <label class="articles-filter">
                  <span>最低评论量</span>
                  <input v-model="filters.minCommentCount" type="number" min="0" class="basic-settings-input" />
                </label>

                <label class="articles-filter">
                  <span>最低转发量</span>
                  <input v-model="filters.minForwardCount" type="number" min="0" class="basic-settings-input" />
                </label>
              </div>
            </section>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" :disabled="loading" @click="resetFilters">重置</button>
            <button type="button" class="action-btn" @click="closeFilterDialog">取消</button>
            <button type="button" class="action-btn" :disabled="!apiAvailable || loading" @click="applyFilters">应用筛选</button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.rewrite-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.rewrite-badge--done {
  background: var(--color-success, #16a34a);
  color: #fff;
}

.rewrite-badge--pending {
  background: var(--color-warning, #d97706);
  color: #fff;
}

.rewrite-badge--partial {
  background: var(--color-warning, #d97706);
  color: #fff;
}

.rewrite-badge--none {
  background: var(--color-border, #e5e7eb);
  color: var(--color-text-secondary, #6b7280);
}

/* ── 查看结果 dialog ────────────────────────────── */
.rewrite-view-dialog {
  width: min(760px, 94vw);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
}

.rewrite-view-dialog__subtitle {
  font-weight: 600;
  color: var(--color-text-primary, #111);
  margin-top: 4px;
  font-size: 14px;
  max-width: 560px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rewrite-view-dialog__body {
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 20px 24px;
}

.rewrite-view-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rewrite-view-section__title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-secondary, #6b7280);
  border-bottom: 1px solid var(--color-border, #e5e7eb);
  padding-bottom: 6px;
}

.rewrite-view-section__content--title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary, #111);
  line-height: 1.5;
}

.rewrite-view-article {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rewrite-view-article__block {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.rewrite-view-article__label {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--color-accent, #2563eb);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  margin-top: 2px;
}

.rewrite-view-article__text {
  flex: 1;
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-primary, #111);
  white-space: pre-wrap;
  word-break: break-word;
}

.rewrite-view-prompts {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rewrite-view-prompt {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: var(--color-surface, #f9fafb);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 8px;
  padding: 10px 12px;
}

.rewrite-view-prompt__index {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-secondary, #6b7280);
  min-width: 16px;
}

.rewrite-view-prompt__text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text-primary, #111);
  word-break: break-word;
}

.rewrite-view-images {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.rewrite-view-image-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
}

.rewrite-view-image {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--color-border, #e5e7eb);
  background: var(--color-surface, #f9fafb);
}

.rewrite-view-image__caption {
  font-size: 12px;
  color: var(--color-text-secondary, #6b7280);
}

.rewrite-view-empty {
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
  font-style: italic;
}

.action-btn--accent {
  background: var(--color-accent, #2563eb);
  color: #fff;
  border-color: var(--color-accent, #2563eb);
}

.action-btn--accent:hover:not(:disabled) {
  opacity: 0.88;
}

/* ── 复选框列 ────────────────────────────────────── */
.articles-table__check {
  width: 36px;
  text-align: center;
  padding: 0 4px;
}

.articles-table__check input[type='checkbox'] {
  cursor: pointer;
  width: 15px;
  height: 15px;
}

.articles-row--selected td {
  background: var(--color-accent-light, #eff6ff);
}

/* ── 批量操作工具栏 ──────────────────────────────── */
.articles-selection-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent, #2563eb);
  padding: 0 4px;
  white-space: nowrap;
}

/* ── 全局批量按钮激活态 ──────────────────────────── */
.action-btn--active {
  background: var(--color-accent, #2563eb);
  color: #fff;
  border-color: var(--color-accent, #2563eb);
}

/* ── 状态 Dialog ─────────────────────────────────── */
.benchmark-dialog--status {
  width: min(480px, 92vw);
}

.status-empty {
  text-align: center;
  color: var(--color-text-secondary, #6b7280);
  padding: 24px 0;
  font-size: 14px;
}

.status-section__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #111);
  margin: 0 0 8px;
}

.status-section__row {
  font-size: 13px;
  color: var(--color-text-secondary, #555);
  margin: 4px 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.status-section__row--current {
  font-style: italic;
  color: var(--color-accent, #2563eb);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-section__empty {
  font-size: 13px;
  color: var(--color-text-secondary, #9ca3af);
}

.status-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.status-badge--running {
  background: #fef3c7;
  color: #92400e;
}

.status-badge--done {
  background: #d1fae5;
  color: #065f46;
}
</style>

