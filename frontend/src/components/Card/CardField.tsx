/** 通用字段块：label + textarea/input。 */
import type { ReactNode } from 'react'

interface CardFieldProps {
  label: string
  value: string
  onChange?: (value: string) => void
  /** 多行大文本使用 textarea，自动撑高 */
  multiline?: boolean
  placeholder?: string
  disabled?: boolean
  icon?: ReactNode
}

export function CardField({
  label,
  value,
  onChange,
  multiline,
  placeholder,
  disabled,
  icon,
}: CardFieldProps) {
  return (
    <div className={`card-field ${multiline ? 'multiline' : ''}`}>
      <label className="card-field-label">
        {icon}
        {label}
      </label>
      {multiline ? (
        <textarea
          className="card-field-input"
          rows={3}
          value={value}
          placeholder={placeholder || `填写${label}…`}
          disabled={disabled}
          onChange={(e) => onChange?.(e.target.value)}
        />
      ) : (
        <input
          className="card-field-input"
          type="text"
          value={value}
          placeholder={placeholder || `填写${label}…`}
          disabled={disabled}
          onChange={(e) => onChange?.(e.target.value)}
        />
      )}
    </div>
  )
}
