/** 卡片状态：列表、当前卡片、CRUD actions。 */
import { create } from 'zustand'
import { api } from '../api/client'
import type { Card, CardSummary, SearchMode } from '../api/types'

function toSummary(card: Card): CardSummary {
  return { id: card.id, title: card.title, updated_at: card.updated_at }
}

/** 解析 URL hash 中的卡片 ID，如 #/cards/card_xxx */
export function cardIdFromHash(hash: string): string | null {
  const m = /^#\/cards\/(card_[0-9_]+[a-f0-9]*)$/.exec(hash.trim())
  return m ? m[1] : null
}

/** 深链同步：打开卡片时写入 hash，关闭时清除，刷新后保持。 */
function syncHash(id: string | null) {
  const current = window.location.hash
  if (id) {
    if (current !== `#/cards/${id}`) window.location.hash = `/cards/${id}`
  } else if (current.startsWith('#/cards/')) {
    // 替换为空 hash，避免残留记录
    window.history.replaceState(null, '', window.location.pathname + window.location.search)
  }
}

interface CardsState {
  cards: CardSummary[]
  searchMeta: { q: string; mode: SearchMode; active: boolean } | null
  activeId: string | null
  current: Card | null
  loadingList: boolean
  saving: boolean
  error: string | null

  fetchList: () => Promise<void>
  search: (q: string, mode: SearchMode) => Promise<void>
  clearSearch: () => Promise<void>
  create: () => Promise<Card | null>
  open: (id: string) => Promise<void>
  close: () => void
  setActiveId: (id: string | null) => void
  save: (card: Card) => Promise<void>
  remove: (id: string) => Promise<void>
  refreshCurrent: () => Promise<void>
  setError: (err: string | null) => void
}

export const useCardsStore = create<CardsState>((set, get) => ({
  cards: [],
  searchMeta: null,
  activeId: null,
  current: null,
  loadingList: false,
  saving: false,
  error: null,

  fetchList: async () => {
    set({ loadingList: true })
    try {
      const cards = await api.get<CardSummary[]>('/cards')
      set({ cards, loadingList: false, error: null })
      // 首次进入自动打开第一张卡
      if (!get().activeId && cards.length > 0) {
        const first = cards[0].id
        set({ activeId: first })
        void get().open(first)
      }
    } catch (e) {
      set({ loadingList: false, error: (e as Error).message })
    }
  },

  search: async (q, mode) => {
    if (!q.trim()) {
      await get().clearSearch()
      return
    }
    set({ loadingList: true })
    try {
      const cards = await api.get<CardSummary[]>(
        `/cards?q=${encodeURIComponent(q)}&mode=${mode}`,
      )
      set({ cards, searchMeta: { q, mode, active: true }, loadingList: false, error: null })
    } catch (e) {
      set({ loadingList: false, error: (e as Error).message })
    }
  },

  clearSearch: async () => {
    set({ searchMeta: null })
    await get().fetchList()
  },

  create: async () => {
    try {
      const card = await api.post<Card>('/cards', {})
      set({ cards: [...get().cards, toSummary(card)], error: null })
      return card
    } catch (e) {
      set({ error: (e as Error).message })
      return null
    }
  },

  open: async (id) => {
    try {
      const card = await api.get<Card>(`/cards/${id}`)
      set({ activeId: id, current: card, error: null })
      syncHash(id)
    } catch (e) {
      set({ error: (e as Error).message })
    }
  },

  close: () => {
    set({ activeId: null, current: null })
    syncHash(null)
  },

  setActiveId: (id) => set({ activeId: id }),

  save: async (card) => {
    set({ saving: true })
    try {
      const saved = await api.put<Card>(`/cards/${card.id}`, card)
      set({
        current: saved,
        saving: false,
        error: null,
        cards: get().cards.map((c) => (c.id === saved.id ? toSummary(saved) : c)),
      })
    } catch (e) {
      set({ saving: false, error: (e as Error).message })
      throw e
    }
  },

  remove: async (id) => {
    try {
      await api.del<{ ok: boolean }>(`/cards/${id}`)
      set({ cards: get().cards.filter((c) => c.id !== id), error: null })
      if (get().activeId === id) get().close()
    } catch (e) {
      set({ error: (e as Error).message })
    }
  },

  refreshCurrent: async () => {
    const id = get().activeId
    if (!id) return
    try {
      const card = await api.get<Card>(`/cards/${id}`)
      set({ current: card, error: null })
    } catch (e) {
      set({ error: (e as Error).message })
    }
  },

  setError: (err) => set({ error: err }),
}))
