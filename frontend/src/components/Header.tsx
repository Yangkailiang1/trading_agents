import { useState, useEffect } from 'react'

export default function Header() {
  const [marketOpen, setMarketOpen] = useState<boolean | null>(null)

  useEffect(() => {
    const check = () => {
      fetch('/health')
        .then(r => r.json())
        .then(data => setMarketOpen(data.market_open))
        .catch(() => {})
    }
    check()
    const timer = setInterval(check, 30000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header style={{
      padding: '16px 24px',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      background: 'var(--bg-secondary)',
    }}>
      <span style={{ fontSize: 24 }}>📈</span>
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>量化交易Agent</h1>
      <span style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 8 }}>
        DeepSeek AI 驱动 · A股实时监控
      </span>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
        {marketOpen !== null && (
          <>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: marketOpen ? 'var(--green)' : 'var(--red)',
              display: 'inline-block',
              boxShadow: marketOpen ? '0 0 6px var(--green)' : '0 0 6px var(--red)',
            }} />
            <span style={{
              fontSize: 13,
              color: marketOpen ? 'var(--green)' : 'var(--red)',
              fontWeight: 500,
            }}>
              {marketOpen ? '交易中' : '已休市'}
            </span>
            {!marketOpen && (
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                （AI决策暂停）
              </span>
            )}
          </>
        )}
      </div>
    </header>
  )
}
