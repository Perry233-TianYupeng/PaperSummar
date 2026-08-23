/** 导航栏单项：题目截断+"…"，右上角「…」删除菜单。 */
import { useState } from 'react'
import { useCardsStore } from '../../store/cardsStore'
import type { CardSummary } from '../../api/types'
import { Icon } from '../common/Icon'
import { ConfirmMenu } from '../common/ConfirmMenu'

const MAX_TITLE = 16

function truncate(title: string): string {
  if (title.length <= MAX_TITLE) return title
  return title.slice(0, MAX_TITLE) + '…'
}

export function CardNavItem({ card }: { card: CardSummary }) {
  const activeId = useCardsStore((s) => s.activeId)
  const open = useCardsStore((s) => s.open)
  const remove = useCardsStore((s) => s.remove)
  const [menuOpen, setMenuOpen] = useState(false)
  const active = activeId === card.id

  return (
    <div className={`nav-item ${active ? 'active' : ''}`} onClick={() => void open(card.id)}>
      <div className="nav-item-main">
        <span className="nav-item-title" title={card.title}>
          {truncate(card.title)}
        </span>
        <span className="nav-item-meta">
          {card.updated_at ? new Date(card.updated_at).toLocaleDateString() : ''}
        </span>
      </div>
      <button
        className="nav-item-menu-btn"
        title="更多操作"
        onClick={(e) => {
          e.stopPropagation()
          setMenuOpen((v) => !v)
        }}
      >
        <Icon name="dots" size={16} />
      </button>
      {menuOpen && (
        <div className="nav-item-menu" onClick={(e) => e.stopPropagation()}>
          <ConfirmMenu
            title="删除该资料卡"
            confirmText="删除该资料卡"
            danger
            onClose={() => setMenuOpen(false)}
            onConfirm={() => {
              void remove(card.id)
              setMenuOpen(false)
            }}
          />
        </div>
      )}
    </div>
  )
}
