import { useState } from 'react'

interface Props {
  onAdd: (code: string, name: string) => void
}

export default function AddStockForm({ onAdd }: Props) {
  const [code, setCode] = useState('')
  const [name, setName] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = code.trim()
    if (!trimmed) return
    onAdd(trimmed, name.trim())
    setCode('')
    setName('')
  }

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 8, padding: 16, display: 'flex', gap: 8, alignItems: 'flex-end',
      }}
    >
      <div style={{ flex: 1 }}>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
          股票代码
        </label>
        <input
          value={code}
          onChange={e => setCode(e.target.value)}
          placeholder="如 000001"
          style={inputStyle}
        />
      </div>
      <div style={{ flex: 1 }}>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
          股票名称（可选）
        </label>
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="如 平安银行"
          style={inputStyle}
        />
      </div>
      <button type="submit" style={{
        padding: '8px 20px', background: 'var(--blue)', color: '#fff',
        border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13, fontWeight: 600,
      }}>
        添加监控
      </button>
    </form>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', fontSize: 13,
  background: 'var(--bg-primary)', color: 'var(--text-primary)',
  border: '1px solid var(--border)', borderRadius: 4, outline: 'none',
}
