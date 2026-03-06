import type { ThemeDefinition } from './tokens'

const cssVarName = (key: string) => `--${key.replace(/[A-Z]/g, (char) => `-${char.toLowerCase()}`)}`

export function applyTheme(theme: ThemeDefinition): void {
  const root = document.documentElement
  root.setAttribute('data-theme', theme.name)

  Object.entries(theme.tokens).forEach(([token, value]) => {
    root.style.setProperty(cssVarName(token), value)
  })
}
