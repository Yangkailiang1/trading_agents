import type { AccountSummary } from '../types'

interface Props {
  account: AccountSummary | null
  onReset: () => void
}

const fmt = (n: number) => n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export default function AccountPanel({ account, onReset }: Props) {
  if (!account) return <Card title="账户概览">加载中...</Card>

  const pnlColor = account.total_pnl >= 0 ? 'var(--green)' : 'var(--red)'
  const pnlSign = account.total_pnl >= 0 ? '+' : ''

  return (
    <Card title="账户概览">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
        <Metric label="总资产" value={`¥${fmt(account.total_assets)}`} />
        <Metric label="可用现金" value={`¥${fmt(account.cash)}`} />
        <Metric label="持仓市值" value={`¥${fmt(account.position_value)}`} />
        <Metric
          label="总盈亏"
          value={`${pnlSign}¥${fmt(account.total_pnl)}`}
          color={pnlColor}
        />
        <Metric
          label="盈亏比例"
          value={`${pnlSign}${account.total_pnl_percent.toFixed(2)}%`}
          color={pnlColor}
        />
        <Metric label="初始资金" value={`¥${fmt(account.initial_capital)}`} color="var(--text-secondary)" />
      </div>

      {account.positions.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>持仓明细</div>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>股票</th>
                <th style={thStyle}>数量</th>
                <th style={thStyle}>可卖</th>
                <th style={thStyle}>均价</th>
                <th style={thStyle}>现价</th>
                <th style={thStyle}>市值</th>
                <th style={thStyle}>盈亏</th>
              </tr>
            </thead>
            <tbody>
              {account.positions.map(p => (
                <tr key={p.stock_code}>
                  <td style={tdStyle}>{p.stock_name}</td>
                  <td style={tdStyle}>{p.quantity}</td>
                  <td style={{ ...tdStyle, color: p.sellable_quantity > 0 ? 'var(--green)' : 'var(--text-secondary)' }}>{p.sellable_quantity}</td>
                  <td style={tdStyle}>{p.avg_cost.toFixed(2)}</td>
                  <td style={tdStyle}>{p.current_price.toFixed(2)}</td>
                  <td style={tdStyle}>{fmt(p.market_value)}</td>
                  <td style={{ ...tdStyle, color: p.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                    {p.pnl >= 0 ? '+' : ''}{fmt(p.pnl)} ({p.pnl_percent >= 0 ? '+' : ''}{p.pnl_percent.toFixed(2)}%)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <button
        onClick={onReset}
        style={{
          marginTop: 12, padding: '6px 16px', fontSize: 12,
          background: 'var(--red)', color: '#fff', border: 'none',
          borderRadius: 4, cursor: 'pointer', opacity: 0.8,
        }}
      >
        重置账户
      </button>
    </Card>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: 16,
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>{title}</div>
      {children}
    </div>
  )
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: color || 'var(--text-primary)' }}>{value}</div>
    </div>
  )
}

const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: 13 }
const thStyle: React.CSSProperties = { textAlign: 'left', padding: '4px 8px', color: 'var(--text-secondary)', fontWeight: 500, borderBottom: '1px solid var(--border)' }
const tdStyle: React.CSSProperties = { padding: '6px 8px', borderBottom: '1px solid var(--border)' }
