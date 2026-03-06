/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
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
  }>
  open_logs_folder(): Promise<boolean>
  open_db_folder(): Promise<boolean>
  clear_logs(): Promise<boolean>
}

interface Window {
  pywebview?: {
    api: PywebviewApi
  }
}
