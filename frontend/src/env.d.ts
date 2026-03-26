/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

interface BenchmarkAccountItem {
  id: number
  url: string
  createdAt: string
  updatedAt: string
  lastMonitoredAt?: string | null
}

interface BenchmarkAccountOption {
  id: number
  url: string
}

interface BenchmarkAccountListResult {
  items: BenchmarkAccountItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

interface BenchmarkAccountImportResult {
  created: number
  updated: number
  skipped: number
  total: number
}

interface AccountMonitorPayload {
  url: string
  benchmarkAccountId?: number
  startTime?: string | null
  endTime?: string | null
  singleCapture?: boolean
}

interface AccountMonitorArticle {
  id: string | null
  groupId: string | null
  itemId: string | null
  cellType: string | null
  title: string | null
  content: string | null
  publishTime: string | null
  source: string | null
  mediaName: string | null
  displayUrl: string | null
  playCount?: number | null
  diggCount?: number | null
  commentCount?: number | null
  forwardCount?: number | null
  buryCount?: number | null
  raw: Record<string, unknown>
}

interface AccountMonitorTypeSummary {
  topLevelType: string | null
  itemCount: number
  topLevelKeys?: string[]
  dataType?: string | null
  sampleItemKeys?: string[]
}

interface AccountMonitorResult {
  url: string
  matchedRequestUrl: string | null
  rawText: string | null
  json: Record<string, unknown> | unknown[] | null
  startTime: string | null
  endTime: string | null
  captureCount: number
  typeSummary: AccountMonitorTypeSummary
  articleCount: number
  filteredArticleCount: number
  savedCount?: number
  articles: AccountMonitorArticle[]
  warning?: string | null
}

interface MonitoredArticleItem {
  id: number
  benchmarkAccountId: number
  benchmarkAccountUrl: string
  itemId: string | null
  groupId: string | null
  cellType: string | null
  content: string | null
  publishTime: string | null
  source: string | null
  mediaName: string | null
  displayUrl: string | null
  playCount?: number | null
  diggCount?: number | null
  commentCount?: number | null
  forwardCount?: number | null
  buryCount?: number | null
  updatedAt: string
  raw: Record<string, unknown>
  rewrittenTitle: string | null
  rewrittenIntro: string | null
  rewrittenArticle: string | null
  imagePrompts: string | null
  imagePaths: string | null
}

interface RewriteArticleFullResult {
  rewrittenTitle: string
  rewrittenIntro: string
  rewrittenArticle: string[]
  imagePrompts: string[]
  imagePaths: (string | null)[]
}

interface MonitoredArticleFilters {
  accountId?: number | null
  keyword?: string | null
  startTime?: string | null
  endTime?: string | null
  minPlayCount?: string | number | null
  minDiggCount?: string | number | null
  minCommentCount?: string | number | null
  minForwardCount?: string | number | null
}

interface MonitoredArticleListResult {
  items: MonitoredArticleItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

interface ArticleMonitoringPayload {
  benchmarkAccountIds: number[]
  startTime?: string | null
  endTime?: string | null
  minPlayCount?: number | null
  minDiggCount?: number | null
  minForwardCount?: number | null
}

type ArticleRewriteTemplateKey =
  | 'international_account_starter'
  | 'international_stable_hardcore'
  | 'international_stable_strategic'

interface ArticleMonitoringAccountResult {
  benchmarkAccountId: number
  benchmarkAccountUrl: string
  status: 'success' | 'warning' | 'failed'
  savedCount: number
  articleCount: number
  filteredArticleCount: number
  captureCount: number
  warning?: string | null
  error?: string | null
  monitorRunId?: number | null
  articles: AccountMonitorArticle[]
}

interface ArticleMonitoringResult {
  requestedCount: number
  succeededCount: number
  failedCount: number
  warningCount: number
  results: ArticleMonitoringAccountResult[]
}

interface DownloadRewrittenArticleResult {
  status: 'success' | 'cancel' | 'error'
  path?: string
  message?: string
}

interface DownloadArticleDocxResult {
  status: 'success' | 'cancel' | 'error'
  path?: string
  message?: string
}

interface BatchDownloadArticlesDocxResult {
  status: 'success' | 'cancel' | 'error'
  folder?: string
  succeeded?: number
  failed?: number
  skipped?: number
  errors?: string[]
  message?: string
}

interface StartOriginalExportResult {
  status: 'started' | 'cancel' | 'error'
  folder?: string
  total?: number
  message?: string
}

interface OriginalExportProgress {
  running: boolean
  total: number
  done: number
  succeeded: number
  failed: number
  skipped: number
  currentArticle: string
  folder: string
  message?: string
  errors?: string[]
}

interface PywebviewApi {
  ping(): Promise<string>
  get_setting(key: string): Promise<string | null>
  set_setting(key: string, value: string): Promise<boolean>
  get_monitoring_status(): Promise<{
    logDir: string
    dbFile: string
    logFiles: number
    logSizeBytes: number
    dbSizeBytes: number
    settingCount: number
    benchmarkAccountCount: number
    monitorRunCount: number
    monitoredArticleCount: number
  }>
  list_benchmark_accounts(page: number, pageSize: number): Promise<BenchmarkAccountListResult>
  list_benchmark_account_options(): Promise<BenchmarkAccountOption[]>
  create_benchmark_account(url: string): Promise<BenchmarkAccountItem>
  update_benchmark_account(id: number, url: string): Promise<BenchmarkAccountItem>
  delete_benchmark_account(id: number): Promise<boolean>
  delete_benchmark_accounts(ids: number[]): Promise<number>
  import_benchmark_accounts(payload: string): Promise<BenchmarkAccountImportResult>
  export_benchmark_accounts(): Promise<BenchmarkAccountItem[]>
  run_account_monitor(payload: AccountMonitorPayload): Promise<AccountMonitorResult>
  run_article_monitoring(payload: ArticleMonitoringPayload): Promise<ArticleMonitoringResult>
  list_monitored_articles(filters: MonitoredArticleFilters, page: number, pageSize: number): Promise<MonitoredArticleListResult>
  list_article_ids_for_batch(filters: MonitoredArticleFilters, skipRewritten: boolean): Promise<number[]>
  list_completed_article_ids(filters: MonitoredArticleFilters): Promise<number[]>
  soft_delete_all_monitored_articles(): Promise<number>
  delete_monitored_article(id: number): Promise<boolean>
  rewrite_title(title: string): Promise<string>
  rewrite_article(content: string, templateKey: ArticleRewriteTemplateKey): Promise<string>
  rewrite_article_full(articleId: number, templateKey: ArticleRewriteTemplateKey): Promise<RewriteArticleFullResult>
  download_rewritten_article(content: string): Promise<DownloadRewrittenArticleResult>
  download_article_docx(articleId: number): Promise<DownloadArticleDocxResult>
  batch_download_articles_docx(articleIds: number[]): Promise<BatchDownloadArticlesDocxResult>
  start_batch_export_original_articles(filters: MonitoredArticleFilters): Promise<StartOriginalExportResult>
  get_original_export_progress(): Promise<OriginalExportProgress>
  open_external_url(url: string): Promise<boolean>
  open_folder(path: string): Promise<boolean>
  open_logs_folder(): Promise<boolean>
  open_db_folder(): Promise<boolean>
  clear_logs(): Promise<boolean>
}

interface Window {
  pywebview?: {
    api: PywebviewApi
  }
}
