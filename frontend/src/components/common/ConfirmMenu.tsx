/** 两段式确认弹层：首次显示提示，再次点击确认触发。 */
import { useEffect, useRef, useState } from 'react'

interface ConfirmMenuProps {
  title: string
  confirmText: string
  danger?: boolean
  onConfirm: () => void
  onClose: () => void
}

export function ConfirmMenu({ title, confirmText, danger, onConfirm, onClose }: ConfirmMenuProps) {
  const [armed, setArmed] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  return (
    <div className="confirm-menu" ref={ref}>
      <div className="confirm-menu-title">{title}</div>
      {!armed ? (
        <button className="btn btn-danger" onClick={() => setArmed(true)}>
          {confirmText}
        </button>
      ) : (
        <div className="confirm-menu-armed">
          <span className="confirm-hint">再次点击确认{danger ? '，此操作不可撤销' : ''}</span>
          <div className="confirm-actions">
            <button className="btn" onClick={() => setArmed(false)}>
              取消
            </button>
            <button className="btn btn-danger" onClick={onConfirm} autoFocus>
              确认删除
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
