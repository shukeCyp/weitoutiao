import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { applyTheme } from '../themes/applyTheme'
import {
  DEFAULT_THEME_NAME,
  THEME_MAP,
  THEME_STORAGE_KEY,
  THEMES,
  type ThemeDefinition,
  type ThemeName,
} from '../themes/tokens'

const THEME_SETTING_KEY = 'theme.name'
const THEME_BACKEND_RETRY_COUNT = 10
const THEME_BACKEND_RETRY_DELAY_MS = 300

const isValidTheme = (value: string | null): value is ThemeName => {
  return !!value && THEME_MAP.has(value as ThemeName)
}

const sleep = (ms: number): Promise<void> => new Promise((resolve) => window.setTimeout(resolve, ms))

const getBackendTheme = async (): Promise<ThemeName | null> => {
  const api = window.pywebview?.api
  if (!api) {
    return null
  }

  try {
    const value = await api.get_setting(THEME_SETTING_KEY)
    return isValidTheme(value) ? value : null
  } catch {
    return null
  }
}

const getBackendThemeWithRetry = async (): Promise<ThemeName | null> => {
  for (let index = 0; index < THEME_BACKEND_RETRY_COUNT; index += 1) {
    const theme = await getBackendTheme()
    if (theme) {
      return theme
    }
    if (window.pywebview?.api) {
      break
    }
    await sleep(THEME_BACKEND_RETRY_DELAY_MS)
  }
  return null
}

const setBackendTheme = async (themeName: ThemeName): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    return
  }

  try {
    await api.set_setting(THEME_SETTING_KEY, themeName)
  } catch {
    // noop
  }
}

const applyThemeByName = (themeName: ThemeName): void => {
  const theme = THEME_MAP.get(themeName) ?? THEME_MAP.get(DEFAULT_THEME_NAME)!
  applyTheme(theme)
}

export const useThemeStore = defineStore('theme', () => {
  const initialThemeName = (() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    return isValidTheme(saved) ? saved : DEFAULT_THEME_NAME
  })()

  const currentThemeName = ref<ThemeName>(initialThemeName)

  const currentTheme = computed<ThemeDefinition>(() => {
    return THEME_MAP.get(currentThemeName.value) ?? THEME_MAP.get(DEFAULT_THEME_NAME)!
  })

  const setTheme = (name: ThemeName): void => {
    const nextTheme = THEME_MAP.get(name)
    if (!nextTheme) {
      return
    }

    currentThemeName.value = nextTheme.name
    applyTheme(nextTheme)
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme.name)
    void setBackendTheme(nextTheme.name)
  }

  const initialize = async (): Promise<void> => {
    applyThemeByName(currentThemeName.value)

    const backendTheme = await getBackendThemeWithRetry()
    if (backendTheme && backendTheme !== currentThemeName.value) {
      currentThemeName.value = backendTheme
      applyThemeByName(backendTheme)
      localStorage.setItem(THEME_STORAGE_KEY, backendTheme)
      return
    }

    localStorage.setItem(THEME_STORAGE_KEY, currentThemeName.value)
    if (window.pywebview?.api) {
      void setBackendTheme(currentThemeName.value)
    }
  }

  return {
    themes: THEMES,
    currentThemeName,
    currentTheme,
    initialize,
    setTheme,
  }
})
