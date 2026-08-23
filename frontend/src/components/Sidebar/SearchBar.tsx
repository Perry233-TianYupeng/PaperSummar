/** 右上角搜索栏：默认收起仅显示 🔍，展开后可选择题目/作者/内容搜索。 */
import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../../store/appStore'
import { useCardsStore } from '../../store/cardsStore'
import type { SearchMode } from '../../api/types'
import { Icon } from '../common/Icon'

const MODES: { value: SearchMode; label: string }[] = [
  { value: 'title', label: '题目' },
  { value: 'author', label: '作者' },
  { value: 'content', label: '内容' },
]

export function SearchBar() {
  const expanded = useAppStore((s) => s.searchExpanded)
  const setExpanded = useAppStore((s) => s.setSearchExpanded)
  const search = useCardsStore((s) => s.search)
  const clearSearch = useCardsStore((s) => s.clearSearch)
  const searchMeta = useCardsStore((s) => s.searchMeta)

  const [q, setQ] = useState('')
  const [mode, setMode] = useState<SearchMode>('title')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (expanded) inputRef.current?.focus()
  }, [expanded])

  useEffect(() => {
    if (!expanded) return
    const timer = window.setTimeout(() => {
      void search(q, mode)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [q, mode, expanded, search])

  if (!expanded) {
    return (
      <button className="search-btn-collapsed" onClick={() => setExpanded(true)} title="搜索">
        <Icon name="search" size={18} />
        <span>搜索</span>
      </button>
    )
  }

  return (
    <div className="search-bar">
      <div className="search-input-wrap">
        <Icon name="search" size={16} />
        <input
          ref={inputRef}
          className="search-input"
          placeholder="输入关键词检索论文…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setExpanded(false)
              setQ('')
              void clearSearch()
            }
          }}
        />
        {q && (
          <button
            className="search-clear"
            onClick={() => {
              setQ('')
              void clearSearch()
            }}
            title="清除搜索"
          >
            <Icon name="close" size={14} />
          </button>
        )}
      </div>
      <div className="search-modes" role="radiogroup" aria-label="搜索方式">
        {MODES.map((m) => (
          <button
            key={m.value}
            className={`search-mode ${mode === m.value ? 'active' : ''}`}
            onClick={() => setMode(m.value)}
          >
            {m.label}
          </button>
        ))}
      </div>
      <button
        className="search-close"
        onClick={() => {
          setExpanded(false)
          setQ('')
          void clearSearch()
        }}
        title="关闭搜索"
      >
        <Icon name="close" size={16} />
      </button>
      {searchMeta?.active && (
        <div className="search-result-meta">
          搜索结果（{searchMeta.q}）
          <button onClick={() => void clearSearch()}>清除</button>
        </div>
      )}
    </div>
  )
}
