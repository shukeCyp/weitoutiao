<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useToastStore } from '../stores/toast'

const { showToast } = useToastStore()

const loading = ref(false)
const accountLoading = ref(false)
const accountOptions = ref<BenchmarkAccountOption[]>([])
const selectedAccountIds = ref<number[]>([])
const filterDialogVisible = ref(false)
const resultDialogVisible = ref(false)
const startTime = ref('')
const endTime = ref('')
const minPlayCount = ref('0')
const minDiggCount = ref('0')
const minForwardCount = ref('0')
const result = ref<ArticleMonitoringResult | null>(null)
const apiAvailable = computed(() => !!window.pywebview?.api)

const hasAccounts = computed(() => accountOptions.value.length > 0)
const hasSelection = computed(() => selectedAccountIds.value.length > 0)
const selectedCount = computed(() => selectedAccountIds.value.length)
const allSelected = computed(() => hasAccounts.value && selectedAccountIds.value.length === accountOptions.value.length)
const accountMap = computed(() => new Map(accountOptions.value.map((item) => [item.id, item.url])))
const summaryCards = computed(() => {
  if (!result.value) {
    return []
  }

  return [
    { label: '请求账号数', value: String(result.value.requestedCount) },
    { label: '成功', value: String(result.value.succeededCount), tone: 'success' },
    { label: '告警', value: String(result.value.warningCount), tone: 'warning' },
    { label: '失败', value: String(result.value.failedCount), tone: 'danger' },
  ]
})

const formatSelectedLabel = (id: number): string => accountMap.value.get(id) ?? `账号 ${id}`

const getStatusText = (status: ArticleMonitoringAccountResult['status']): string => {
  if (status === 'success') {
    return '成功'
  }
  if (status === 'warning') {
    return '告警'
  }
  return '失败'
}

const isSelected = (id: number): boolean => selectedAccountIds.value.includes(id)

const toggleAccount = (id: number): void => {
  if (isSelected(id)) {
    selectedAccountIds.value = selectedAccountIds.value.filter((item) => item !== id)
    return
  }

  selectedAccountIds.value = [...selectedAccountIds.value, id]
}

const toggleAllAccounts = (): void => {
  if (allSelected.value) {
    selectedAccountIds.value = []
    return
  }

  selectedAccountIds.value = accountOptions.value.map((item) => item.id)
}

const normalizeTimeValue = (value: string): string | null => {
  const normalized = value.trim()
  return normalized || null
}

const normalizeMetricValue = (value: string): number => {
  const parsed = Number.parseInt(value.trim(), 10)
  if (Number.isNaN(parsed) || parsed < 0) {
    throw new Error('筛选门槛必须是大于等于 0 的整数。')
  }
  return parsed
}

const loadAccounts = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    accountOptions.value = []
    return
  }

  accountLoading.value = true
  try {
    accountOptions.value = await api.list_benchmark_account_options()
    selectedAccountIds.value = selectedAccountIds.value.filter((id) => accountOptions.value.some((item) => item.id === id))
  } catch (error) {
    showToast(error instanceof Error ? error.message : '读取对标账号失败。', 'error')
  } finally {
    accountLoading.value = false
  }
}

const openFilterDialog = (): void => {
  if (!apiAvailable.value) {
    showToast('当前环境不支持执行文章监控。', 'warning')
    return
  }
  if (!hasSelection.value) {
    showToast('请至少选择一个对标账号。', 'warning')
    return
  }
  filterDialogVisible.value = true
}

const closeFilterDialog = (): void => {
  if (loading.value) {
    return
  }
  filterDialogVisible.value = false
}

const closeResultDialog = (): void => {
  resultDialogVisible.value = false
}

const runMonitoring = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持执行文章监控。', 'warning')
    return
  }

  const normalizedStartTime = normalizeTimeValue(startTime.value)
  const normalizedEndTime = normalizeTimeValue(endTime.value)

  if (normalizedStartTime && normalizedEndTime && normalizedStartTime > normalizedEndTime) {
    showToast('开始时间不能晚于结束时间。', 'warning')
    return
  }

  let normalizedPlayCount = 0
  let normalizedDiggCount = 0
  let normalizedForwardCount = 0

  try {
    normalizedPlayCount = normalizeMetricValue(minPlayCount.value)
    normalizedDiggCount = normalizeMetricValue(minDiggCount.value)
    normalizedForwardCount = normalizeMetricValue(minForwardCount.value)
  } catch (error) {
    showToast(error instanceof Error ? error.message : '筛选门槛校验失败。', 'warning')
    return
  }

  loading.value = true
  try {
    const response = await api.run_article_monitoring({
      benchmarkAccountIds: [...selectedAccountIds.value],
      startTime: normalizedStartTime,
      endTime: normalizedEndTime,
      minPlayCount: normalizedPlayCount,
      minDiggCount: normalizedDiggCount,
      minForwardCount: normalizedForwardCount,
    })
    result.value = response
    filterDialogVisible.value = false
    resultDialogVisible.value = true

    if (response.failedCount > 0 || response.warningCount > 0) {
      showToast(
        `监控完成：成功 ${response.succeededCount} 个，告警 ${response.warningCount} 个，失败 ${response.failedCount} 个。`,
        response.failedCount > 0 ? 'warning' : 'success',
      )
      return
    }

    showToast(`监控完成，已处理 ${response.requestedCount} 个对标账号。`, 'success')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '执行文章监控失败。', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadAccounts()
})
</script>

<template>
  <section class="page-section page-section--full article-monitoring-layout">
    <header class="page-head article-monitoring-head">
      <div>
        <h2 class="page-title">文章监控</h2>
        <p class="page-subtitle">先选择账号，再点击执行监控，在弹窗里设置时间范围与数据门槛，完成后查看结果明细。</p>
      </div>

      <div class="article-monitoring-head__actions">
        <button type="button" class="action-btn" :disabled="!apiAvailable || accountLoading" @click="loadAccounts">
          {{ accountLoading ? '刷新中...' : '刷新账号' }}
        </button>
        <button type="button" class="action-btn" :disabled="!apiAvailable || loading || !hasAccounts" @click="toggleAllAccounts">
          {{ allSelected ? '清空选择' : '全选账号' }}
        </button>
        <button type="button" class="action-btn" :disabled="!apiAvailable || loading || !hasSelection" @click="openFilterDialog">
          {{ loading ? '监控中...' : '执行监控' }}
        </button>
      </div>
    </header>

    <div class="page-body article-monitoring-body">
      <section class="article-monitoring-panel">
        <div class="article-monitoring-panel__head">
          <div>
            <h3 class="article-monitoring-panel__title">监控范围</h3>
            <p class="article-monitoring-panel__text">支持单账号或多账号并发执行。点击执行监控后再填写本次抓取条件。</p>
          </div>
          <span class="article-monitoring-selection">已选 {{ selectedCount }} / {{ accountOptions.length }}</span>
        </div>

        <div v-if="accountLoading" class="benchmark-empty-state article-monitoring-empty">正在加载对标账号...</div>
        <div v-else-if="!hasAccounts" class="benchmark-empty-state article-monitoring-empty">
          暂无可用对标账号，请先到“对标账号”页面添加账号。
        </div>
        <div v-else class="article-monitoring-account-grid">
          <button
            v-for="account in accountOptions"
            :key="account.id"
            type="button"
            class="article-monitoring-account"
            :class="{ 'article-monitoring-account--selected': isSelected(account.id) }"
            @click="toggleAccount(account.id)"
          >
            <span class="article-monitoring-account__check">{{ isSelected(account.id) ? '✓' : '' }}</span>
            <span class="article-monitoring-account__meta">
              <span class="article-monitoring-account__id">ID {{ account.id }}</span>
              <span class="article-monitoring-account__url">{{ account.url }}</span>
            </span>
          </button>
        </div>
      </section>
    </div>

    <Teleport to="body">
      <div v-if="filterDialogVisible" class="benchmark-dialog-mask" @click.self="closeFilterDialog">
        <div class="benchmark-dialog benchmark-dialog--article-filter">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">设置监控条件</h3>
              <p class="benchmark-dialog__text">本次执行可按时间范围、播放量、点赞量和转发量过滤文章。</p>
            </div>
            <button type="button" class="benchmark-dialog__close" :disabled="loading" @click="closeFilterDialog">×</button>
          </div>

          <div class="benchmark-dialog__body articles-filter-dialog-shell">
            <section class="articles-filter-group">
              <div class="articles-filter-group__head">
                <h4 class="articles-filter-group__title">已选账号</h4>
                <p class="articles-filter-group__text">本次将并发处理 {{ selectedCount }} 个对标账号。</p>
              </div>
              <div class="article-monitoring-selected-list">
                <span v-for="accountId in selectedAccountIds" :key="accountId" class="article-monitoring-selected-pill">
                  {{ formatSelectedLabel(accountId) }}
                </span>
              </div>
            </section>

            <section class="articles-filter-group">
              <div class="articles-filter-group__head">
                <h4 class="articles-filter-group__title">时间范围</h4>
                <p class="articles-filter-group__text">只抓取落在这段时间范围内的文章；留空表示不限制。</p>
              </div>
              <div class="articles-filter-dialog">
                <label class="articles-filter">
                  <span>开始时间</span>
                  <input v-model="startTime" type="datetime-local" class="basic-settings-input" />
                </label>
                <label class="articles-filter">
                  <span>结束时间</span>
                  <input v-model="endTime" type="datetime-local" class="basic-settings-input" />
                </label>
              </div>
            </section>

            <section class="articles-filter-group">
              <div class="articles-filter-group__head">
                <h4 class="articles-filter-group__title">数据门槛</h4>
                <p class="articles-filter-group__text">仅保留满足最低播放量、点赞量和转发量的文章，0 表示不限制。</p>
              </div>
              <div class="articles-filter-dialog articles-filter-dialog--metrics article-monitoring-metrics-grid">
                <label class="articles-filter">
                  <span>最低播放量</span>
                  <input v-model="minPlayCount" type="number" min="0" class="basic-settings-input" />
                </label>
                <label class="articles-filter">
                  <span>最低点赞量</span>
                  <input v-model="minDiggCount" type="number" min="0" class="basic-settings-input" />
                </label>
                <label class="articles-filter">
                  <span>最低转发量</span>
                  <input v-model="minForwardCount" type="number" min="0" class="basic-settings-input" />
                </label>
              </div>
            </section>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" :disabled="loading" @click="closeFilterDialog">取消</button>
            <button type="button" class="action-btn" :disabled="loading" @click="runMonitoring">
              {{ loading ? '监控中...' : '开始执行' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="resultDialogVisible && result" class="benchmark-dialog-mask" @click.self="closeResultDialog">
        <div class="benchmark-dialog benchmark-dialog--monitor-result">
          <div class="benchmark-dialog__head">
            <div>
              <h3 class="benchmark-dialog__title">监控结果</h3>
              <p class="benchmark-dialog__text">每个账号独立创建监控记录，允许部分失败，其余账号继续落库。</p>
            </div>
            <button type="button" class="benchmark-dialog__close" @click="closeResultDialog">×</button>
          </div>

          <div class="benchmark-dialog__body article-monitoring-result-dialog">
            <div class="article-monitoring-summary">
              <article
                v-for="card in summaryCards"
                :key="card.label"
                class="article-monitoring-summary__card"
                :class="card.tone ? `article-monitoring-summary__card--${card.tone}` : ''"
              >
                <span class="article-monitoring-summary__label">{{ card.label }}</span>
                <strong class="article-monitoring-summary__value">{{ card.value }}</strong>
              </article>
            </div>

            <div class="benchmark-table-wrap article-monitoring-results-wrap">
              <table class="benchmark-table article-monitoring-results-table">
                <thead>
                  <tr>
                    <th>对标账号</th>
                    <th>状态</th>
                    <th>采集数</th>
                    <th>过滤后</th>
                    <th>入库数</th>
                    <th>MonitorRun</th>
                    <th>结果说明</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in result.results" :key="item.benchmarkAccountId">
                    <td>
                      <div class="article-monitoring-result-account">
                        <strong>{{ formatSelectedLabel(item.benchmarkAccountId) }}</strong>
                        <span>ID {{ item.benchmarkAccountId }}</span>
                      </div>
                    </td>
                    <td>
                      <span class="article-monitoring-status" :class="`article-monitoring-status--${item.status}`">
                        {{ getStatusText(item.status) }}
                      </span>
                    </td>
                    <td>{{ item.captureCount }}</td>
                    <td>{{ item.filteredArticleCount }}</td>
                    <td>{{ item.savedCount }}</td>
                    <td>{{ item.monitorRunId ?? '-' }}</td>
                    <td class="article-monitoring-results-table__message">
                      {{ item.error || item.warning || `${item.articles.length} 条文章返回前端` }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="benchmark-dialog__actions">
            <button type="button" class="action-btn" @click="closeResultDialog">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>
