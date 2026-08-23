/** 主区资料卡：可滚动编辑全部字段、关闭按钮、右下操作栏、飞入/飞出动画。 */
import { useState } from 'react'
import type { Card } from '../../api/types'
import { useCardsStore } from '../../store/cardsStore'
import { CardField } from './CardField'
import { CardToolbar } from './CardToolbar'
import { Icon } from '../common/Icon'

/** 新建卡片时的默认占位标题（不计入"已填写题目"）。 */
const DEFAULT_TITLE = '新资料卡'

export function CardView() {
  const current = useCardsStore((s) => s.current)
  const close = useCardsStore((s) => s.close)
  if (!current) return null
  // key=current.id：切换卡片时整卡重挂，配合飞入动画并重置编辑草稿
  return <CardViewInner key={current.id} card={current} onClose={close} />
}

function CardViewInner({ card, onClose }: { card: Card; onClose: () => void }) {
  const [draft, setDraft] = useState<Card>(() => ({ ...card }))
  const [leaving, setLeaving] = useState(false)
  const save = useCardsStore((s) => s.save)
  const setError = useCardsStore((s) => s.setError)

  function setField(name: keyof Card, value: string) {
    setDraft((d) => ({ ...d, [name]: value }))
  }

  // AI 功能启用条件：已填写真实题目（非默认占位）且已保存到后端
  // （草稿标题与后端已保存标题一致，即用户点过「保存修改」）。
  const aiEnabled =
    draft.title.trim().length > 0 &&
    draft.title.trim() !== DEFAULT_TITLE &&
    draft.title.trim() === card.title.trim()

  async function handleSave() {
    try {
      await save(draft)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <section
      className={`card-view ${leaving ? 'leaving' : ''}`}
      onAnimationEnd={() => {
        if (leaving) onClose()
      }}
    >
      <header className="card-view-header">
        <div className="card-view-titlebar">
          <Icon name="file" size={18} className="card-view-title-icon" />
          <span className="card-view-title">论文资料卡</span>
        </div>
        <button
          className="card-close-btn"
          onClick={() => setLeaving(true)}
          title="关闭当前资料卡"
        >
          <Icon name="close" size={18} />
        </button>
      </header>

      <div className="card-view-body">
        <CardField
          label="论文题目"
          value={draft.title}
          onChange={(v) => setField('title', v)}
          placeholder="输入论文题目（填写并首次确认保存修改后，启用AI相关功能）"
        />

        <div className="card-field-row">
          <CardField
            label="Arxiv ID"
            value={draft.arxiv_id}
            onChange={(v) => setField('arxiv_id', v)}
            placeholder="如 1706.03762"
          />
          <CardField
            label="代码仓库链接"
            value={draft.code_repo}
            onChange={(v) => setField('code_repo', v)}
            placeholder="https://github.com/..."
          />
        </div>

        <CardField
          label="作者团队人名"
          value={draft.authors}
          onChange={(v) => setField('authors', v)}
          placeholder="作者姓名，逗号分隔"
        />
        <CardField
          label="作者团队信息"
          value={draft.author_team_info}
          onChange={(v) => setField('author_team_info', v)}
          multiline
        />
        <CardField
          label="主要作者研究方向"
          value={draft.research_directions}
          onChange={(v) => setField('research_directions', v)}
          multiline
        />

        <div className="card-field-row">
          <CardField
            label="论文首发时间（Arxiv）"
            value={draft.arxiv_first_published}
            onChange={(v) => setField('arxiv_first_published', v)}
            placeholder="如 2017-06-12"
          />
          <CardField
            label="最终发表期刊/会议"
            value={draft.final_venue}
            onChange={(v) => setField('final_venue', v)}
            placeholder="如 NeurIPS 2017"
          />
        </div>

        <CardField
          label="论文内容"
          value={draft.content}
          onChange={(v) => setField('content', v)}
          multiline
        />
        <CardField
          label="论文创新点"
          value={draft.innovations}
          onChange={(v) => setField('innovations', v)}
          multiline
        />
        <CardField
          label="个人感想"
          value={draft.personal_notes}
          onChange={(v) => setField('personal_notes', v)}
          multiline
          placeholder="记录阅读心得与体会…"
        />
        <CardField
          label="AI 总结"
          value={draft.ai_summary}
          onChange={(v) => setField('ai_summary', v)}
          multiline
          placeholder="点击右下角「AI 总结」自动生成；也可手动填写"
        />
      </div>

      <footer className="card-view-footer">
        <CardToolbar card={draft} aiEnabled={aiEnabled} onSave={handleSave} />
      </footer>
    </section>
  )
}
