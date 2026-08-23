/** 左侧纵向导航栏：新建按钮 + 论文列表 + 左下设置入口。 */
import { useCardsStore } from '../../store/cardsStore'
import { CardNavItem } from './CardNavItem'
import { NewCardButton } from './NewCardButton'
import { SettingsEntry } from './SettingsEntry'

export function Sidebar() {
  const cards = useCardsStore((s) => s.cards)
  const loading = useCardsStore((s) => s.loadingList)
  const searchMeta = useCardsStore((s) => s.searchMeta)

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <NewCardButton />
      </div>

      <div className="sidebar-list">
        {searchMeta?.active && (
          <div className="sidebar-hint">检索结果（{searchMeta.mode}：{searchMeta.q}）</div>
        )}
        {loading && <div className="sidebar-loading">加载中…</div>}
        {!loading && cards.length === 0 && (
          <div className="sidebar-empty">
            {searchMeta?.active ? '未找到匹配的资料卡' : '暂无资料卡，点击左上角「+新建资料卡」开始'}
          </div>
        )}
        {cards.map((card) => (
          <CardNavItem key={card.id} card={card} />
        ))}
      </div>

      <div className="sidebar-footer">
        <SettingsEntry />
      </div>
    </aside>
  )
}
