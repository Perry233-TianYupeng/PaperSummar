/** 右下角悬浮任务条：显示 AI 任务进度；成功/失败给出反馈。 */
import { useState } from 'react'
import type { Task } from '../../api/types'
import { useTasksStore } from '../../store/tasksStore'
import { Icon } from '../common/Icon'

const KIND_LABEL: Record<string, string> = {
  ai_completion: 'AI 信息补全',
  ai_summary: 'AI 总结',
  md_export: 'AI 生成 md 文件',
}

const STAGE_LABEL: Record<string, string> = {
  arxiv: '查询 arXiv',
  web: '联网搜索',
  llm: 'LLM 生成',
  merge: '合并写入',
  export: '生成 Markdown',
  done: '完成',
}

function percent(task: Task): number {
  return Math.round((task.progress || 0) * 100)
}

function TaskCard({ task }: { task: Task }) {
  const [showError, setShowError] = useState(false)
  const running = task.status === 'running' || task.status === 'queued'
  const succeeded = task.status === 'succeeded'
  const failed = task.status === 'failed'

  const stageText = STAGE_LABEL[task.stage] || task.stage
  const mdPath = task.kind === 'md_export' && succeeded ? (task.result?.path as string) : null

  return (
    <div className={`task-card ${task.status}`}>
      <div className="task-row">
        <span className={`task-status-icon ${task.status}`}>
          {running ? <span className="spinner" style={{ width: 14, height: 14 }} /> : null}
          {succeeded ? <Icon name="check" size={16} /> : null}
          {failed ? <Icon name="alert" size={16} /> : null}
        </span>
        <span className="task-title">{KIND_LABEL[task.kind] || task.kind}</span>
        <span className="task-stage">{stageText}</span>
        <span className="task-percent">{percent(task)}%</span>
      </div>

      {running && (
        <div className="task-progress">
          <div className="task-progress-bar" style={{ width: `${percent(task)}%` }} />
        </div>
      )}
      {task.message && <div className="task-message">{task.message}</div>}

      {succeeded && mdPath && (
        <div className="task-result">
          已导出：<code>{mdPath}</code>
        </div>
      )}

      {failed && (
        <div className="task-error-wrap">
          <button className="task-error-toggle" onClick={() => setShowError((v) => !v)}>
            {showError ? '收起错误' : '展开错误'}
          </button>
          {showError && <div className="task-error">{task.error}</div>}
          <div className="task-error-log-hint">错误已写入 data/logs/tasks.log</div>
        </div>
      )}
    </div>
  )
}

export function TaskBar() {
  const tasks = useTasksStore((s) => s.tasks)
  const activeIds = useTasksStore((s) => s.activeIds)
  const clearFinished = useTasksStore((s) => s.clearFinished)
  const list = Object.values(tasks)

  if (list.length === 0) return null

  return (
    <div className="task-bar">
      <div className="task-bar-header">
        <span>任务</span>
        {activeIds.length === 0 && (
          <button className="task-bar-clear" onClick={clearFinished}>
            清除
          </button>
        )}
      </div>
      {list.map((t) => (
        <TaskCard key={t.task_id} task={t} />
      ))}
    </div>
  )
}
