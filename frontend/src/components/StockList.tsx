import type { StockInfo, RealtimeData } from '../types'

interface Props {
  stocks: StockInfo[]
  realtime: Record<string, RealtimeData>
  selected: string | null
  onSelect: (code: string) => void
  onRemove: (code: string) => void
}

export default function StockList({ stocks, realtime, selected, onSelect, onRemove }: Props) {
  if (stocks.length === 0) {
    return (
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 8, padding: 40, textAlign: 'center',
        color: 'var(--text-secondary)', fontSize: 13,
      }}>
        暂无监控股票，请在上方添加
      </div>
    )
  }

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: 16,
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
        监控股票
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {stocks.map(s => {
          const rd = realtime[s.stock_code]
          const price = rd?.price ?? s.current_price
          const change = rd?.change_percent ?? s.change_percent
          const isSelected = selected === s.stock_code
          const color = change != null ? (change >= 0 ? 'var(--green)' : 'var(--red)') : 'var(--text-secondary)'

          return (
            <div
              key={s.stock_code}
              onClick={() => onSelect(s.stock_code)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '10px 12px', borderRadius: 6, cursor: 'pointer',
                background: isSelected ? 'rgba(68, 138, 255, 0.1)' : 'transparent',
                border: isSelected ? '1px solid var(--blue)' : '1px solid transparent',
                transition: 'all 0.15s',
              }}
            >
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{s.stock_name || s.stock_code}</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{s.stock_code}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 16, fontWeight: 700, color }}>
                  {price != null ? price.toFixed(2) : '--'}
                </div>
                {change != null && (
                  <div style={{ fontSize: 12, color }}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                  </div>
                )}
              </div>
              <button
                onClick={e => { e.stopPropagation(); onRemove(s.stock_code) }}
                style={{
                  marginLeft: 8, padding: '2px 8px', fontSize: 11,
                  background: 'transparent', color: 'var(--red)', border: '1px solid var(--red)',
                  borderRadius: 3, cursor: 'pointer', opacity: 0.6,
                }}
              >
                删除
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
