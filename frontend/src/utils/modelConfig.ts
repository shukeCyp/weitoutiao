const LLM_BASE_URL_KEY = 'llm.base_url'
const LLM_API_KEY_KEY = 'llm.api_key'
const LLM_MODEL_KEY = 'llm.model'
const IMAGE_BASE_URL_KEY = 'image.base_url'
const IMAGE_API_KEY_KEY = 'image.api_key'
const IMAGE_MODEL_KEY = 'image.model'

export interface RuntimeConfig {
  baseUrl: string
  apiKey: string
  model: string
}

export interface ConfigOverrides {
  baseUrl?: string
  apiKey?: string
  model?: string
}

const readSetting = async (key: string): Promise<string> => {
  const api = window.pywebview?.api
  if (!api) {
    throw new Error('pywebview API 不可用，无法读取模型配置。')
  }

  const value = await api.get_setting(key)
  return value?.trim() ?? ''
}

const normalizeBaseUrl = (value: string, label: string): string => {
  const trimmed = value.trim()
  if (!trimmed) {
    throw new Error(`未配置${label} base_url。`)
  }
  return trimmed.replace(/\/+$/, '')
}

const resolveRuntimeConfig = async (
  keys: { baseUrl: string; apiKey: string; model: string },
  overrides: ConfigOverrides,
  label: string,
): Promise<RuntimeConfig> => {
  const [savedBaseUrl, savedApiKey, savedModel] = await Promise.all([
    overrides.baseUrl ? Promise.resolve(overrides.baseUrl.trim()) : readSetting(keys.baseUrl),
    overrides.apiKey ? Promise.resolve(overrides.apiKey) : readSetting(keys.apiKey),
    overrides.model ? Promise.resolve(overrides.model.trim()) : readSetting(keys.model),
  ])

  if (!savedModel) {
    throw new Error(`未配置${label} model。`)
  }

  return {
    baseUrl: normalizeBaseUrl(savedBaseUrl, label),
    apiKey: savedApiKey,
    model: savedModel,
  }
}

export const resolveLlmConfig = async (overrides: ConfigOverrides = {}): Promise<RuntimeConfig> => {
  return resolveRuntimeConfig(
    {
      baseUrl: LLM_BASE_URL_KEY,
      apiKey: LLM_API_KEY_KEY,
      model: LLM_MODEL_KEY,
    },
    overrides,
    '大模型',
  )
}

export const resolveImageConfig = async (overrides: ConfigOverrides = {}): Promise<RuntimeConfig> => {
  return resolveRuntimeConfig(
    {
      baseUrl: IMAGE_BASE_URL_KEY,
      apiKey: IMAGE_API_KEY_KEY,
      model: IMAGE_MODEL_KEY,
    },
    overrides,
    '生图',
  )
}
