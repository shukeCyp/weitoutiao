<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useToastStore } from '../stores/toast'

const DEFAULT_PAGE_SIZE = 20
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

const { showToast } = useToastStore()

const items = ref<BenchmarkAccountItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(DEFAULT_PAGE_SIZE)
const loading = ref(false)
const importLoading = ref(false)
const exportLoading = ref(false)
const dialogSubmitting = ref(false)
const selectedIds = ref<number[]>([])
const monitoringIds = ref<number[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

const dialogVisible = ref(false)
const monitorResultVisible = ref(false)
const monitorResult = ref<AccountMonitorResult | null>(null)
const monitorResultUrl = ref('')
const dialogMode = ref<'single' | 'batch'>('single')
const editingId = ref<number | null>(null)
const singleUrl = ref('')
const batchUrls = ref('')

const apiAvailable = computed(() => !!window.pywebview?.api)
const hasItems = computed(() => items.value.length > 0)
const hasSelection = computed(() => selectedIds.value.length > 0)
const isEditing = computed(() => editingId.value !== null)
const allSelected = computed(() => hasItems.value && items.value.every((item) => selectedIds.value.includes(item.id)))
const selectedCount = computed(() => selectedIds.value.length)
const isMonitoring = (id: number): boolean => monitoringIds.value.includes(id)
const rangeText = computed(() => {
  if (!total.value || !items.value.length) {
    return '当前没有数据'
  }

  const start = (currentPage.value - 1) * pageSize.value + 1
  const end = start + items.value.length - 1
  return `显示第 ${start}-${end} 条，共 ${total.value} 条`
})
const dialogTitle = computed(() => {
  if (isEditing.value) {
    return '编辑对标账号'
  }
  return dialogMode.value === 'batch' ? '批量添加对标账号' : '添加对标账号'
})
const monitorArticles = computed(() => monitorResult.value?.articles ?? [])

const getPreviewContent = (content: string | null): string => {
  if (!content) {
    return '-'
  }

  return content.length > 10 ? `${content.slice(0, 10)}...` : content
}

const isValidUrl = (value: string): boolean => {
  try {
    const url = new URL(value.trim())
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

const syncSelection = (): void => {
  const currentIds = new Set(items.value.map((item) => item.id))
  selectedIds.value = selectedIds.value.filter((id) => currentIds.has(id))
}

const closeDialog = (): void => {
  dialogVisible.value = false
  dialogMode.value = 'single'
  editingId.value = null
  singleUrl.value = ''
  batchUrls.value = ''
}

const openCreateDialog = (): void => {
  editingId.value = null
  dialogMode.value = 'single'
  singleUrl.value = ''
  batchUrls.value = ''
  dialogVisible.value = true
}

const closeMonitorResult = (): void => {
  monitorResultVisible.value = false
  monitorResult.value = null
  monitorResultUrl.value = ''
}

const openBatchDialog = (): void => {
  editingId.value = null
  dialogMode.value = 'batch'
  singleUrl.value = ''
  batchUrls.value = ''
  dialogVisible.value = true
}

const openEditDialog = (item: BenchmarkAccountItem): void => {
  editingId.value = item.id
  dialogMode.value = 'single'
  singleUrl.value = item.url
  batchUrls.value = ''
  dialogVisible.value = true
}

const loadAccounts = async (page = currentPage.value): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    items.value = []
    total.value = 0
    totalPages.value = 1
    selectedIds.value = []
    showToast('当前环境不支持读取对标账号。', 'warning')
    return
  }

  loading.value = true

  try {
    const result = await api.list_benchmark_accounts(page, pageSize.value)
    items.value = result.items
    total.value = result.total
    currentPage.value = result.page
    totalPages.value = result.totalPages
    syncSelection()
  } catch {
    showToast('读取对标账号失败，请稍后重试。', 'error')
  } finally {
    loading.value = false
  }
}

const submitSingle = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持保存对标账号。', 'warning')
    return
  }

  const normalizedUrl = singleUrl.value.trim()
  if (!normalizedUrl) {
    showToast('请输入账号链接。', 'warning')
    return
  }

  if (!isValidUrl(normalizedUrl)) {
    showToast('请输入有效的 http/https 链接。', 'error')
    return
  }

  if (editingId.value === null) {
    await api.create_benchmark_account(normalizedUrl)
    showToast('对标账号已新增。', 'success')
    closeDialog()
    await loadAccounts(1)
    return
  }

  await api.update_benchmark_account(editingId.value, normalizedUrl)
  showToast('对标账号已更新。', 'success')
  closeDialog()
  await loadAccounts(currentPage.value)
}

const submitBatch = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持批量添加。', 'warning')
    return
  }

  const urls = batchUrls.value
    .split(/\r?\n|,|，/)
    .map((item) => item.trim())
    .filter(Boolean)

  if (!urls.length) {
    showToast('请至少输入一条账号链接。', 'warning')
    return
  }

  const invalidUrl = urls.find((url) => !isValidUrl(url))
  if (invalidUrl) {
    showToast(`链接格式不正确：${invalidUrl}`, 'error')
    return
  }

  await api.import_benchmark_accounts(JSON.stringify(urls))
  showToast(`已提交 ${urls.length} 条账号。`, 'success')
  closeDialog()
  await loadAccounts(1)
}

const submitDialog = async (): Promise<void> => {
  try {
    dialogSubmitting.value = true

    if (dialogMode.value === 'batch' && !isEditing.value) {
      await submitBatch()
      return
    }

    await submitSingle()
  } catch (error) {
    const message = error instanceof Error ? error.message : '保存失败，请稍后重试。'
    showToast(message || '保存失败，请稍后重试。', 'error')
  } finally {
    dialogSubmitting.value = false
  }
}

const toggleAll = (checked: boolean): void => {
  selectedIds.value = checked ? items.value.map((item) => item.id) : []
}

const toggleOne = (id: number, checked: boolean): void => {
  if (checked) {
    if (!selectedIds.value.includes(id)) {
      selectedIds.value = [...selectedIds.value, id]
    }
    return
  }

  selectedIds.value = selectedIds.value.filter((itemId) => itemId !== id)
}

const openAccount = async (url: string): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持打开链接。', 'warning')
    return
  }

  try {
    const success = await api.open_external_url(url)
    if (!success) {
      throw new Error('open failed')
    }
  } catch {
    showToast('打开链接失败，请检查系统浏览器配置。', 'error')
  }
}

const monitorAccount = async (item: BenchmarkAccountItem): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持执行监控。', 'warning')
    return
  }

  const normalizedUrl = item.url.trim()
  if (!normalizedUrl) {
    showToast('该账号缺少可监控的链接。', 'warning')
    return
  }

  if (!isValidUrl(normalizedUrl)) {
    showToast('该账号链接不是有效的 http/https 地址。', 'error')
    return
  }

  if (isMonitoring(item.id)) {
    return
  }

  monitoringIds.value = [...monitoringIds.value, item.id]

  try {
    const result = await api.run_account_monitor({
      url: normalizedUrl,
      benchmarkAccountId: item.id,
      singleCapture: true,
    })

    monitorResult.value = result
    monitorResultUrl.value = normalizedUrl
    monitorResultVisible.value = true

    if (result.warning) {
      showToast(result.warning, 'warning')
      return
    }

    showToast(`监控完成，已保存 ${result.savedCount ?? result.articleCount} 条文章。`, 'success')
  } catch (error) {
    const message = error instanceof Error ? error.message : '监控失败，请稍后重试。'
    showToast(message || '监控失败，请稍后重试。', 'error')
  } finally {
    monitoringIds.value = monitoringIds.value.filter((id) => id !== item.id)
  }
}

const deleteOne = async (item: BenchmarkAccountItem): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持删除。', 'warning')
    return
  }

  if (!window.confirm(`确认删除该对标账号？\n\n${item.url}`)) {
    return
  }

  try {
    const success = await api.delete_benchmark_account(item.id)
    if (!success) {
      throw new Error('delete failed')
    }

    if (editingId.value === item.id) {
      closeDialog()
    }

    showToast('对标账号已删除。', 'success')
    const targetPage = items.value.length === 1 && currentPage.value > 1 ? currentPage.value - 1 : currentPage.value
    await loadAccounts(targetPage)
  } catch {
    showToast('删除失败，请稍后重试。', 'error')
  }
}

const deleteSelected = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持批量删除。', 'warning')
    return
  }

  if (!selectedIds.value.length) {
    showToast('请先选择要删除的账号。', 'warning')
    return
  }

  if (!window.confirm(`确认删除选中的 ${selectedIds.value.length} 个对标账号？`)) {
    return
  }

  try {
    const deletedCount = await api.delete_benchmark_accounts(selectedIds.value)
    if (!deletedCount) {
      throw new Error('delete failed')
    }

    selectedIds.value = []
    showToast(`已删除 ${deletedCount} 个对标账号。`, 'success')

    const remaining = total.value - deletedCount
    const nextTotalPages = remaining > 0 ? Math.ceil(remaining / pageSize.value) : 1
    await loadAccounts(Math.min(currentPage.value, nextTotalPages))
  } catch {
    showToast('批量删除失败，请稍后重试。', 'error')
  }
}

const triggerImport = (): void => {
  fileInput.value?.click()
}

const handleImportFile = async (event: Event): Promise<void> => {
  const api = window.pywebview?.api
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!api) {
    showToast('当前环境不支持导入。', 'warning')
    input.value = ''
    return
  }

  if (!file) {
    return
  }

  importLoading.value = true

  try {
    const payload = await file.text()
    const result = await api.import_benchmark_accounts(payload)
    showToast(`导入完成：新增 ${result.created} 条，更新 ${result.updated} 条，跳过 ${result.skipped} 条。`, 'success')
    await loadAccounts(1)
  } catch (error) {
    const message = error instanceof Error ? error.message : '导入失败，请检查 JSON 内容。'
    showToast(message || '导入失败，请检查 JSON 内容。', 'error')
  } finally {
    importLoading.value = false
    input.value = ''
  }
}

const downloadText = (filename: string, content: string): void => {
  const blob = new Blob([content], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

const exportAccounts = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持导出。', 'warning')
    return
  }

  exportLoading.value = true

  try {
    const result = await api.export_benchmark_accounts()
    const content = JSON.stringify(result, null, 2)
    const stamp = new Date().toISOString().replace(/[:.]/g, '-')
    downloadText(`benchmark-accounts-${stamp}.json`, content)
    showToast(`已导出 ${result.length} 条对标账号。`, 'success')
  } catch {
    showToast('导出失败，请稍后重试。', 'error')
  } finally {
    exportLoading.value = false
  }
}

const goToPreviousPage = (): void => {
  if (currentPage.value <= 1 || loading.value) {
    return
  }

  void loadAccounts(currentPage.value - 1)
}

const goToNextPage = (): void => {
  if (currentPage.value >= totalPages.value || loading.value) {
    return
  }

  void loadAccounts(currentPage.value + 1)
}

const handlePageSizeChange = (): void => {
  currentPage.value = 1
  void loadAccounts(1)
}

onMounted(() => {
  void loadAccounts(1)
})
</script>

<template>
  <section class="page-section benchmark-layout">
    <header class="page-head benchmark-page-head">
      <div>
        <h2 class="page-title">对标账号</h2>
        <p class="page-subtitle">表格查看对标账号，支持新增、批量添加、导入导出、批量删除和分页。</p>
      </div>

      <div class="benchmark-toolbar benchmark-toolbar--top">
        <button type="button" class="action-btn" :disabled="!apiAvailable" @click="openCreateDialog">
          添加
        </button>
        <button type="button" class="action-btn" :disabled="importLoading || !apiAvailable" @click="triggerImport">
          导入
        </button>
        <button type="button" class="action-btn" :disabled="exportLoading || !apiAvailable" @click="exportAccounts">
          {{ exportLoading ? '导出中...' : '导出' }}
        </button>
        <input
          ref="fileInput"
          type="file"
          accept="application/json,.json"
          class="benchmark-hidden-input"
          @change="handleImportFile"
        />
      </div>
    </header>

    <div class="page-body benchmark-body">
      <div class="benchmark-selection-bar">
        <button type="button" class="action-btn action-btn--danger" :disabled="!hasSelection || !apiAvailable" @click="deleteSelected">
          批量删除
        </button>
      </div>

      <div class="benchmark-table-wrap">
        <table class="benchmark-table">
          <thead>
            <tr>
              <th class="benchmark-table__check">
                <input :checked="allSelected" type="checkbox" @change="toggleAll(($event.target as HTMLInputElement).checked)" />
              </th>
              <th>ID</th>
              <th>URL</th>
              <th class="benchmark-table__actions">操作</th>
            </tr>
          </thead>
          <tbody v-if="hasItems && !loading">
            <tr v-for="item in items" :key="item.id">
              <td class="benchmark-table__check">
                <input
                  :checked="selectedIds.includes(item.id)"
                  type="checkbox"
                  @change="toggleOne(item.id, ($event.target as HTMLInputElement).checked)"
                />
              </td>
              <td class="benchmark-table__id">{{ item.id }}</td>
              <td>
                <div class="benchmark-url-cell">
                  <span class="benchmark-url-cell__text">{{ item.url }}</span>
                </div>
              </td>
              <td>
                <div class="benchmark-actions">
                  <button type="button" class="action-btn" @click="openAccount(item.url)">打开</button>
                  <button
                    type="button"
                    class="action-btn"
                    :disabled="isMonitoring(item.id) || !apiAvailable"
                    @click="monitorAccount(item)"
                  >
                    {{ isMonitoring(item.id) ? '监控中...' : '监控' }}
                  </button>
                  <button type="button" class="action-btn" @click="openEditDialog(item)">编辑</button>
                  <button type="button" class="action-btn action-btn--danger" @click="deleteOne(item)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="loading" class="benchmark-empty-state">正在加载对标账号列表...</div>
        <div v-else-if="!hasItems" class="benchmark-empty-state">暂无对标账号，点击右上角添加或导入。</div>
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
          <span class="benchmark-pagination__info">第 {{ currentPage }} / {{ totalPages }} 页</span>
        </div>

        <div class="benchmark-pagination__actions">
          <button type="button" class="action-btn" :disabled="currentPage <= 1 || loading" @click="goToPreviousPage">
            上一页
          </button>
          <button type="button" class="action-btn" :disabled="currentPage >= totalPages || loading" @click="goToNextPage">
            下一页
          </button>
        </div>
      </footer>
    </div>

    <Teleport to="body">
      <div v-if="dialogVisible" class="benchmark-dialog-mask" @click.self="closeDialog">
        <div class="benchmark-dialog">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">{{ dialogTitle }}</h3>
              <p class="benchmark-dialog__text">
                {{ isEditing ? '修改当前账号链接。' : dialogMode === 'batch' ? '支持换行或逗号分隔批量添加。' : '添加一条新的对标账号链接。' }}
              </p>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="closeDialog">×</button>
          </div>

          <div v-if="!isEditing" class="benchmark-dialog__tabs">
            <button
              type="button"
              class="benchmark-dialog__tab"
              :class="{ 'benchmark-dialog__tab--active': dialogMode === 'single' }"
              @click="dialogMode = 'single'"
            >
              单个添加
            </button>
            <button
              type="button"
              class="benchmark-dialog__tab"
              :class="{ 'benchmark-dialog__tab--active': dialogMode === 'batch' }"
              @click="dialogMode = 'batch'"
            >
              批量添加
            </button>
          </div>

          <div class="benchmark-dialog__body">
            <label v-if="dialogMode === 'single' || isEditing" class="benchmark-dialog__field">
              <span class="benchmark-dialog__label">账号链接</span>
              <input
                v-model="singleUrl"
                type="text"
                class="basic-settings-input"
                placeholder="https://example.com/account"
                @keyup.enter="submitDialog"
              />
            </label>

            <label v-else class="benchmark-dialog__field">
              <span class="benchmark-dialog__label">批量链接</span>
              <textarea
                v-model="batchUrls"
                class="benchmark-dialog__textarea"
                placeholder="https://example.com/a&#10;https://example.com/b"
              />
            </label>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" @click="dialogMode === 'batch' && !isEditing ? openBatchDialog() : openCreateDialog()" v-if="!isEditing">
              重置
            </button>
            <button type="button" class="action-btn" @click="closeDialog">取消</button>
            <button type="button" class="action-btn" :disabled="dialogSubmitting || !apiAvailable" @click="submitDialog">
              {{ dialogSubmitting ? '提交中...' : isEditing ? '保存' : dialogMode === 'batch' ? '批量添加' : '添加' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="monitorResultVisible" class="benchmark-dialog-mask" @click.self="closeMonitorResult">
        <div class="benchmark-dialog benchmark-dialog--monitor-result">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">监控结果</h3>
              <p class="benchmark-dialog__text">{{ monitorResultUrl }}</p>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="closeMonitorResult">×</button>
          </div>

          <div class="benchmark-dialog__body">
            <div class="benchmark-dialog__field benchmark-dialog__field--stretch">
              <div v-if="monitorArticles.length" class="benchmark-table-wrap benchmark-table-wrap--dialog">
                <table class="benchmark-table benchmark-table--dialog">
                  <thead>
                    <tr>
                      <th>发布时间</th>
                      <th>内容</th>
                      <th>播放量</th>
                      <th>点赞量</th>
                      <th>转发量</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="article in monitorArticles" :key="article.itemId ?? article.groupId ?? article.id ?? JSON.stringify(article.raw)">
                      <td>{{ article.publishTime || '-' }}</td>
                      <td>{{ getPreviewContent(article.content) }}</td>
                      <td>{{ article.playCount ?? '-' }}</td>
                      <td>{{ article.diggCount ?? '-' }}</td>
                      <td>{{ article.forwardCount ?? '-' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="benchmark-empty-state">本次没有返回可展示的文章。</div>
            </div>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" @click="closeMonitorResult">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>
