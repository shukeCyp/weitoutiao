export interface ThemeTokens {
  background: string
  surface: string
  surfaceElevated: string
  border: string
  textPrimary: string
  textSecondary: string
  accent: string
  accentSoft: string
  success: string
  warning: string
  danger: string
  shadow: string
}

export type ThemeName =
  | 'linear-light'
  | 'linear-rose'
  | 'linear-sky'
  | 'linear-sepia'
  | 'linear-mist'
  | 'linear-olive'
  | 'linear-lavender'
  | 'linear-peach'
  | 'linear-aqua'
  | 'linear-sage'

export interface ThemeDefinition {
  name: ThemeName
  label: string
  tokens: ThemeTokens
}

export const THEME_STORAGE_KEY = 'weitoutiao-theme'

export const THEMES: ThemeDefinition[] = [
  {
    name: 'linear-light',
    label: '云境白',
    tokens: {
      background: '#f6f8fc',
      surface: '#ffffff',
      surfaceElevated: '#f1f5ff',
      border: '#dbe2ee',
      textPrimary: '#161b26',
      textSecondary: '#4c5a71',
      accent: '#4f46e5',
      accentSoft: 'rgba(79, 70, 229, 0.14)',
      success: '#16a34a',
      warning: '#d97706',
      danger: '#dc2626',
      shadow: '0 14px 32px rgba(15, 23, 42, 0.12)',
    },
  },
  {
    name: 'linear-rose',
    label: '蔷薇粉',
    tokens: {
      background: '#fff8fb',
      surface: '#ffffff',
      surfaceElevated: '#fff1f6',
      border: '#f3d9e5',
      textPrimary: '#3a1f2f',
      textSecondary: '#8a5a72',
      accent: '#e11d8a',
      accentSoft: 'rgba(225, 29, 138, 0.13)',
      success: '#16a34a',
      warning: '#d97706',
      danger: '#dc2626',
      shadow: '0 14px 30px rgba(90, 39, 66, 0.14)',
    },
  },
  {
    name: 'linear-sky',
    label: '晴空蓝',
    tokens: {
      background: '#f4fbff',
      surface: '#ffffff',
      surfaceElevated: '#ebf7ff',
      border: '#d2e7f4',
      textPrimary: '#102433',
      textSecondary: '#4a6780',
      accent: '#0ea5e9',
      accentSoft: 'rgba(14, 165, 233, 0.14)',
      success: '#16a34a',
      warning: '#d97706',
      danger: '#dc2626',
      shadow: '0 14px 30px rgba(15, 62, 94, 0.12)',
    },
  },
  {
    name: 'linear-sepia',
    label: '暖棕褐',
    tokens: {
      background: '#f7f2e9',
      surface: '#fffaf1',
      surfaceElevated: '#f3eadd',
      border: '#e4d5c0',
      textPrimary: '#3d3125',
      textSecondary: '#796452',
      accent: '#b7791f',
      accentSoft: 'rgba(183, 121, 31, 0.14)',
      success: '#2f855a',
      warning: '#b7791f',
      danger: '#c53030',
      shadow: '0 12px 26px rgba(82, 61, 39, 0.14)',
    },
  },
  {
    name: 'linear-mist',
    label: '薄雾青',
    tokens: {
      background: '#f3f7f6',
      surface: '#fcfefd',
      surfaceElevated: '#eef4f3',
      border: '#d7e4e2',
      textPrimary: '#1f3030',
      textSecondary: '#567171',
      accent: '#0f766e',
      accentSoft: 'rgba(15, 118, 110, 0.13)',
      success: '#15803d',
      warning: '#b45309',
      danger: '#be123c',
      shadow: '0 12px 24px rgba(24, 52, 49, 0.12)',
    },
  },
  {
    name: 'linear-olive',
    label: '橄榄绿',
    tokens: {
      background: '#f6f8ef',
      surface: '#fcfdf7',
      surfaceElevated: '#eef2df',
      border: '#dbe4c1',
      textPrimary: '#2f3a20',
      textSecondary: '#62704b',
      accent: '#6b8e23',
      accentSoft: 'rgba(107, 142, 35, 0.15)',
      success: '#3f8f3f',
      warning: '#b7791f',
      danger: '#c53030',
      shadow: '0 12px 24px rgba(45, 62, 30, 0.12)',
    },
  },
  {
    name: 'linear-lavender',
    label: '薰衣草',
    tokens: {
      background: '#faf7ff',
      surface: '#ffffff',
      surfaceElevated: '#f4efff',
      border: '#e5daf8',
      textPrimary: '#2f2443',
      textSecondary: '#6d5c8d',
      accent: '#8b5cf6',
      accentSoft: 'rgba(139, 92, 246, 0.14)',
      success: '#16a34a',
      warning: '#d97706',
      danger: '#dc2626',
      shadow: '0 14px 30px rgba(70, 49, 120, 0.12)',
    },
  },
  {
    name: 'linear-peach',
    label: '蜜桃橘',
    tokens: {
      background: '#fff8f3',
      surface: '#ffffff',
      surfaceElevated: '#fff1e7',
      border: '#f6ddca',
      textPrimary: '#3b2418',
      textSecondary: '#8b5f4b',
      accent: '#f97316',
      accentSoft: 'rgba(249, 115, 22, 0.14)',
      success: '#16a34a',
      warning: '#d97706',
      danger: '#dc2626',
      shadow: '0 14px 30px rgba(109, 61, 29, 0.12)',
    },
  },
  {
    name: 'linear-aqua',
    label: '海盐青',
    tokens: {
      background: '#f2fbfb',
      surface: '#ffffff',
      surfaceElevated: '#e7f6f6',
      border: '#d0e8e7',
      textPrimary: '#173233',
      textSecondary: '#517476',
      accent: '#14b8a6',
      accentSoft: 'rgba(20, 184, 166, 0.14)',
      success: '#16a34a',
      warning: '#d97706',
      danger: '#dc2626',
      shadow: '0 14px 28px rgba(27, 86, 83, 0.11)',
    },
  },
  {
    name: 'linear-sage',
    label: '鼠尾草',
    tokens: {
      background: '#f5f8f2',
      surface: '#ffffff',
      surfaceElevated: '#edf3e6',
      border: '#d8e2cf',
      textPrimary: '#263222',
      textSecondary: '#627259',
      accent: '#84a98c',
      accentSoft: 'rgba(132, 169, 140, 0.16)',
      success: '#2f855a',
      warning: '#b7791f',
      danger: '#c53030',
      shadow: '0 14px 28px rgba(58, 84, 55, 0.11)',
    },
  },
]

export const DEFAULT_THEME_NAME: ThemeName = 'linear-light'

export const THEME_MAP = new Map(THEMES.map((theme) => [theme.name, theme]))
