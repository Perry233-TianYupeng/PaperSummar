/** 与后端 API 契约对应的 TypeScript 类型。 */

export interface Card {
  id: string
  title: string
  arxiv_id: string
  authors: string
  author_team_info: string
  research_directions: string
  arxiv_first_published: string
  final_venue: string
  content: string
  innovations: string
  code_repo: string
  personal_notes: string
  ai_summary: string
  created_at: string
  updated_at: string
}

/** 导航栏列表项（摘要，无大文本字段）。 */
export interface CardSummary {
  id: string
  title: string
  updated_at: string
}

export interface Settings {
  owner_name: string
  api_key: string // 返回时是掩码
  base_url: string
  model: string
  theme: 'light' | 'dark'
  data_dir: string
}

export type TaskKind = 'ai_completion' | 'ai_summary' | 'md_export'
export type TaskStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface Task {
  task_id: string
  kind: TaskKind
  card_id: string
  status: TaskStatus
  progress: number // 0..1
  stage: string
  message: string
  result: Record<string, unknown> | null
  error: string | null
  created_at: string
  finished_at: string
}

export type SearchMode = 'title' | 'author' | 'content'
