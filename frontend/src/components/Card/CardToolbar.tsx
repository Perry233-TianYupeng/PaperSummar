/** 卡片右下角操作栏：保存修改 / AI 总结 / AI 信息补全 / AI 生成 md 文件。 */
import { useState } from 'react'
import { api } from '../../api/client'
import type { Card, Task } from '../../api/types'
import { useCardsStore } from '../../store/cardsStore'
import { useTasksStore } from '../../store/tasksStore'
import { Icon } from '../common/Icon'
import { Spinner } from '../common/Spinner'

interface CardToolbarProps {
  card: Card
  /** AI 功能是否启用：已填写真实题目且已保存到后端 */
  aiEnabled: boolean
  onSave: () => Promise<void>
}

async function triggerAI(endpoint: string, cardId: string): Promise<void> {
  const task = await api.post<Task>(endpoint, { card_id: cardId })
  useTasksStore.getState().startTask(task)
}

export function CardToolbar({ card, aiEnabled, onSave }: CardToolbarProps) {
  const saving = useCardsStore((s) => s.saving)
  const [busy, setBusy] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  async function run(kind: 'completion' | 'summary' | 'md-export') {
    if (busy) return
    setBusy(kind)
    setErr(null)
    try {
      await triggerAI(`/ai/${kind}`, card.id)
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="card-toolbar">
      <div className="card-toolbar-actions">
        <button className="btn btn-primary" onClick={() => void onSave()} disabled={saving}>
          {saving ? <Spinner size={14} /> : <Icon name="save" size={16} />}
          <span>{saving ? '保存中…' : '保存修改'}</span>
        </button>

        <button
          className="btn"
          disabled={!aiEnabled || busy !== null}
          title={aiEnabled ? 'AI 对论文内容生成一段总结，写入「AI 总结」字段' : '请先填写论文题目并保存修改'}
          onClick={() => void run('summary')}
        >
          {busy === 'summary' ? <Spinner size={14} /> : <Icon name="sparkles" size={16} />}
          <span>AI 总结</span>
        </button>

        <button
          className="btn"
          disabled={!aiEnabled || busy !== null}
          title={
            aiEnabled
              ? '联网搜索并补全未填写的信息（已填内容不会被修改）'
              : '请先填写论文题目并保存修改'
          }
          onClick={() => void run('completion')}
        >
          {busy === 'completion' ? <Spinner size={14} /> : <Icon name="search" size={16} />}
          <span>AI 信息补全</span>
        </button>

        <button
          className="btn"
          disabled={!aiEnabled || busy !== null}
          title={aiEnabled ? '按卡片内容生成 Markdown 文件（首行标注卡片 ID）' : '请先填写论文题目并保存修改'}
          onClick={() => void run('md-export')}
        >
          {busy === 'md-export' ? <Spinner size={14} /> : <Icon name="file" size={16} />}
          <span>AI 生成 md 文件</span>
        </button>
      </div>

      {err && <div className="card-toolbar-error">{err}</div>}
      {!aiEnabled && <div className="card-toolbar-hint">填写论文题目并首次确认保存修改后，启用 AI 相关功能</div>}
    </div>
  )
}
