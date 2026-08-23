/** 导航栏左上角「+新建资料卡」按钮。 */
import { useCardsStore } from '../../store/cardsStore'
import { Icon } from '../common/Icon'

export function NewCardButton() {
  const create = useCardsStore((s) => s.create)
  const open = useCardsStore((s) => s.open)

  async function handleClick() {
    const card = await create()
    if (card) await open(card.id)
  }

  return (
    <button className="new-card-btn" onClick={handleClick} title="新建资料卡">
      <Icon name="plus" size={18} />
      <span>新建资料卡</span>
    </button>
  )
}
