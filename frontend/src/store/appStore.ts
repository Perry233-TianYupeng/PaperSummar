/** 应用级状态：主题、设置弹层、搜索栏。 */
import { create } from 'zustand'
import { api } from '../api/client'
import type { Settings } from '../api/types'

interface AppState {
  theme: 'light' | 'dark'
  settings: Settings | null
  settingsOpen: boolean
  searchExpanded: boolean

  initTheme: () => void
  applyTheme: (theme: 'light' | 'dark') => void
  loadSettings: () => Promise<void>
  saveSettings: (s: Settings) => Promise<void>
  setSettingsOpen: (open: boolean) => void
  setSearchExpanded: (open: boolean) => void
}

export const useAppStore = create<AppState>((set, get) => ({
  theme: 'light',
  settings: null,
  settingsOpen: false,
  searchExpanded: false,

  initTheme: () => {
    // 优先使用 localStorage 快速应用，避免首屏闪烁
    const saved = localStorage.getItem('papersummar-theme') as 'light' | 'dark' | null
    const theme = saved ?? 'light'
    document.documentElement.setAttribute('data-theme', theme)
    set({ theme })
  },

  applyTheme: (theme) => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('papersummar-theme', theme)
    set({ theme })
    // 持久化到后端设置（若 settings 已加载）
    const s = get().settings
    if (s) {
      void api.put<Settings>('/settings', { ...s, theme }).catch(() => undefined)
    }
  },

  loadSettings: async () => {
    try {
      const settings = await api.get<Settings>('/settings')
      set({ settings })
      if (settings.theme) {
        document.documentElement.setAttribute('data-theme', settings.theme)
        localStorage.setItem('papersummar-theme', settings.theme)
        set({ theme: settings.theme })
      }
    } catch {
      /* 设置加载失败不阻塞界面 */
    }
  },

  saveSettings: async (s) => {
    const saved = await api.put<Settings>('/settings', s)
    set({ settings: saved })
    if (saved.theme) {
      document.documentElement.setAttribute('data-theme', saved.theme)
      localStorage.setItem('papersummar-theme', saved.theme)
      set({ theme: saved.theme })
    }
  },

  setSettingsOpen: (open) => set({ settingsOpen: open }),
  setSearchExpanded: (open) => set({ searchExpanded: open }),
}))
