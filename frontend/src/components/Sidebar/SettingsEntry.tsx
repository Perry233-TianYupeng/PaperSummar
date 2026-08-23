/** 导航栏左下角个人设置入口。 */
import { useAppStore } from '../../store/appStore'
import { Icon } from '../common/Icon'

export function SettingsEntry() {
  const setSettingsOpen = useAppStore((s) => s.setSettingsOpen)
  const settings = useAppStore((s) => s.settings)

  return (
    <button
      className="settings-entry"
      onClick={() => setSettingsOpen(true)}
      title="个人设置"
    >
      <Icon name="user" size={18} />
      <span className="settings-entry-name">{settings?.owner_name || '个人设置'}</span>
    </button>
  )
}
