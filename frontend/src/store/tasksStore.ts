/** 任务状态：轮询 /api/tasks/{id}，维护活跃任务与历史。 */
import { create } from 'zustand'
import { api } from '../api/client'
import type { Task } from '../api/types'

const POLL_INTERVAL = 1000

interface TasksState {
  tasks: Record<string, Task>
  activeIds: string[]
  /** 任务进入终态后的回调（如刷新卡片、提示导出路径） */
  onSettled: ((task: Task) => void) | null
  setOnSettled: (cb: ((task: Task) => void) | null) => void
  startTask: (task: Task) => void
  tick: (taskId: string) => Promise<void>
  clearFinished: () => void
}

export const useTasksStore = create<TasksState>((set, get) => ({
  tasks: {},
  activeIds: [],
  onSettled: null,
  setOnSettled: (cb) => set({ onSettled: cb }),

  startTask: (task) => {
    set((st) => ({
      tasks: { ...st.tasks, [task.task_id]: task },
      activeIds: st.activeIds.includes(task.task_id) ? st.activeIds : [...st.activeIds, task.task_id],
    }))
    void get().tick(task.task_id)
  },

  tick: async (taskId) => {
    let latest: Task | null = null
    try {
      latest = await api.get<Task>(`/tasks/${taskId}`)
    } catch {
      // 任务可能随后端重启失效 → 标记失败
      const t = get().tasks[taskId]
      if (t) {
        const failed: Task = { ...t, status: 'failed', error: '任务已失效（后端可能重启），请重试' }
        set((st) => ({
          tasks: { ...st.tasks, [taskId]: failed },
          activeIds: st.activeIds.filter((id) => id !== taskId),
        }))
        get().onSettled?.(failed)
      }
      return
    }

    if (latest.status === 'running' || latest.status === 'queued') {
      set((st) => ({ tasks: { ...st.tasks, [taskId]: latest as Task } }))
      window.setTimeout(() => void get().tick(taskId), POLL_INTERVAL)
    } else {
      // 终态
      set((st) => ({
        tasks: { ...st.tasks, [taskId]: latest as Task },
        activeIds: st.activeIds.filter((id) => id !== taskId),
      }))
      get().onSettled?.(latest as Task)
    }
  },

  clearFinished: () => {
    set((st) => {
      const tasks = { ...st.tasks }
      for (const id of Object.keys(tasks)) {
        const s = tasks[id].status
        if (s === 'succeeded' || s === 'failed') delete tasks[id]
      }
      return { tasks }
    })
  },
}))
