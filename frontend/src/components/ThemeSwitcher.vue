<script setup lang="ts">
import { storeToRefs } from 'pinia'

import { useThemeStore } from '../stores/theme'
import type { ThemeName } from '../themes/tokens'

const themeStore = useThemeStore()
const { themes, currentThemeName } = storeToRefs(themeStore)

const onThemeChange = (event: Event): void => {
  const target = event.target as HTMLSelectElement
  themeStore.setTheme(target.value as ThemeName)
}
</script>

<template>
  <label class="theme-switcher">
    <span class="theme-switcher__label">主题</span>
    <select class="theme-switcher__select" :value="currentThemeName" @change="onThemeChange">
      <option v-for="theme in themes" :key="theme.name" :value="theme.name">
        {{ theme.label }}
      </option>
    </select>
  </label>
</template>

<style scoped>
.theme-switcher {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.theme-switcher__label {
  font-size: 13px;
  color: var(--textSecondary);
}

.theme-switcher__select {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px 12px;
  background: var(--surfaceElevated);
  color: var(--textPrimary);
  outline: none;
}

.theme-switcher__select:focus {
  border-color: var(--accent);
}
</style>
