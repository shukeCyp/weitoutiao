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

const isValidTheme = (value: string | null): value is ThemeName => {
  return !!value && THEME_MAP.has(value as ThemeName)
}

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

export const useThemeStore = defineStore('theme', () => {
  const currentThemeName = ref<ThemeName>(DEFAULT_THEME_NAME)

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
    applyTheme(THEME_MAP.get(DEFAULT_THEME_NAME)!)

    const backendTheme = await getBackendTheme()
    if (backendTheme) {
      currentThemeName.value = backendTheme
      applyTheme(THEME_MAP.get(backendTheme)!)
      localStorage.setItem(THEME_STORAGE_KEY, backendTheme)
      return
    }

    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (isValidTheme(saved)) {
      currentThemeName.value = saved
      applyTheme(THEME_MAP.get(saved)!)
      return
    }

    setTheme(DEFAULT_THEME_NAME)
  }

  return {
    themes: THEMES,
    currentThemeName,
    currentTheme,
    initialize,
    setTheme,
  }
})
