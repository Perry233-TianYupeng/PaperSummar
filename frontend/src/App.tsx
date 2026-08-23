/** 应用根组件：布局组装（侧栏 + 主区 + 任务条 + 设置弹层）。 */
import { useEffect } from 'react'
import { useAppStore } from './store/appStore'
import { useCardsStore, cardIdFromHash } from './store/cardsStore'
import { useTasksStore } from './store/tasksStore'
import { Sidebar } from './components/Sidebar/Sidebar'
import { SearchBar } from './components/Sidebar/SearchBar'
import { CardView } from './components/Card/CardView'
import { EmptyPlaceholder } from './components/Card/EmptyPlaceholder'
import { TaskBar } from './components/Tasks/TaskBar'
import { SettingsModal } from './components/Settings/SettingsModal'

export default function App() {
  const initTheme = useAppStore((s) => s.initTheme)
  const loadSettings = useAppStore((s) => s.loadSettings)
  const fetchList = useCardsStore((s) => s.fetchList)
  const open = useCardsStore((s) => s.open)
  const setActiveId = useCardsStore((s) => s.setActiveId)
  const refreshCurrent = useCardsStore((s) => s.refreshCurrent)
  const setOnSettled = useTasksStore((s) => s.setOnSettled)
  const current = useCardsStore((s) => s.current)

  useEffect(() => {
    initTheme()
    void loadSettings()
    // 深链：若 URL 带 #/cards/<id>，先置空再加载列表，随后按 id 打开
    const deepLinkId = cardIdFromHash(window.location.hash)
    if (deepLinkId) setActiveId(deepLinkId)
    void fetchList().then(() => {
      if (deepLinkId) void open(deepLinkId)
    })
  }, [initTheme, loadSettings, fetchList, setActiveId, open])

  // AI 任务终态后刷新卡片（补全 / 总结会改动卡片内容）
  useEffect(() => {
    setOnSettled((task) => {
      if (task.kind === 'ai_completion' || task.kind === 'ai_summary') {
        void refreshCurrent()
      }
    })
    return () => setOnSettled(null)
  }, [setOnSettled, refreshCurrent])

  return (
    <div className="app">
      <Sidebar />
      <main className="main">
        <div className="topbar">
          <SearchBar />
        </div>
        <div className="content-area">{current ? <CardView /> : <EmptyPlaceholder />}</div>
      </main>
      <TaskBar />
      <SettingsModal />
    </div>
  )
}
