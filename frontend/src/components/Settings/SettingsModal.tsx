/** 个人设置弹层：名称 / API key / base_url / model / 保存路径 / 主题。 */
import { useEffect, useState } from 'react'
import type { Settings } from '../../api/types'
import { useAppStore } from '../../store/appStore'
import { Icon } from '../common/Icon'
import { Spinner } from '../common/Spinner'

export function SettingsModal() {
  const open = useAppStore((s) => s.settingsOpen)
  const setOpen = useAppStore((s) => s.setSettingsOpen)
  const loadSettings = useAppStore((s) => s.loadSettings)
  const saveSettings = useAppStore((s) => s.saveSettings)
  const applyTheme = useAppStore((s) => s.applyTheme)

  const [form, setForm] = useState<Settings | null>(null)
  const [keyInput, setKeyInput] = useState('') // 重新输入才更新 key
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      void loadSettings().then(() => setForm(useAppStore.getState().settings))
    }
  }, [open, loadSettings])

  if (!open || !form) return null

  function update(name: keyof Settings, value: string) {
    setForm((f) => (f ? ({ ...f, [name]: value } as Settings) : f))
    if (name === 'theme' && (value === 'light' || value === 'dark')) {
      applyTheme(value) // 主题即时生效
    }
  }

  async function handleSave() {
    setSaving(true)
    setErr(null)
    setMsg(null)
    try {
      const payload: Settings = { ...(form as Settings) }
      if (keyInput.trim()) payload.api_key = keyInput.trim() // 有输入才更新 key
      await saveSettings(payload)
      setKeyInput('')
      setMsg('设置已保存')
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={() => setOpen(false)}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span>个人设置</span>
          <button className="modal-close" onClick={() => setOpen(false)}>
            <Icon name="close" size={18} />
          </button>
        </div>

        <div className="modal-body">
          <label className="form-label">
            个人名称
            <input
              className="form-input"
              value={form.owner_name}
              onChange={(e) => update('owner_name', e.target.value)}
              placeholder="你的名字或昵称"
            />
          </label>

          <label className="form-label">
            API Key（OpenAI 格式）
            <input
              className="form-input"
              type="password"
              value={keyInput}
              placeholder={form.api_key ? `已配置：${form.api_key}` : 'sk-...'}
              onChange={(e) => setKeyInput(e.target.value)}
              autoComplete="off"
            />
          </label>

          <label className="form-label">
            Base URL（OpenAI 兼容接口地址）
            <input
              className="form-input"
              value={form.base_url}
              onChange={(e) => update('base_url', e.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </label>

          <label className="form-label">
            模型名称
            <input
              className="form-input"
              value={form.model}
              onChange={(e) => update('model', e.target.value)}
              placeholder="gpt-4o-mini"
            />
          </label>

          <label className="form-label">
            论文资料与 AI 输出的本地保存路径
            <input
              className="form-input"
              value={form.data_dir}
              onChange={(e) => update('data_dir', e.target.value)}
              placeholder="留空使用默认 data/ 目录"
            />
            <span className="form-hint">
              支持相对路径（以项目根目录为基准，如 <code>data</code>）或绝对路径。
              使用相对路径时，移动 / 剪切整个项目文件夹后数据会跟随，不会丢失。
            </span>
          </label>

          <div className="form-label">
            主题配色
            <div className="theme-options">
              <button
                className={`theme-option ${form.theme === 'light' ? 'active' : ''}`}
                onClick={() => update('theme', 'light')}
              >
                <Icon name="sun" size={16} /> 浅色
              </button>
              <button
                className={`theme-option ${form.theme === 'dark' ? 'active' : ''}`}
                onClick={() => update('theme', 'dark')}
              >
                <Icon name="moon" size={16} /> 深色
              </button>
            </div>
          </div>

          {msg && <div className="form-msg ok">{msg}</div>}
          {err && <div className="form-msg err">{err}</div>}
        </div>

        <div className="modal-footer">
          <button className="btn" onClick={() => setOpen(false)}>
            取消
          </button>
          <button className="btn btn-primary" onClick={() => void handleSave()} disabled={saving}>
            {saving ? <Spinner size={14} /> : null}
            {saving ? '保存中…' : '保存设置'}
          </button>
        </div>
      </div>
    </div>
  )
}
