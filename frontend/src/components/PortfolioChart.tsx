import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import type { PortfolioSnapshot } from '../types'

interface Props {
  snapshots: PortfolioSnapshot[]
}

function formatChartTime(timestamp: string, allTimestamps: string[]): string {
  const d = new Date(timestamp)
  const dates = new Set(allTimestamps.map(t => new Date(t).toDateString()))
  if (dates.size > 1) {
    return `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

export default function PortfolioChart({ snapshots }: Props) {
  const allTimestamps = snapshots.map(s => s.timestamp)
  const data = snapshots.map(s => ({
    time: formatChartTime(s.timestamp, allTimestamps),
    total: s.total_assets,
    cash: s.cash,
    position: s.position_value,
  }))

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: 16,
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
        资金变动曲线
      </div>
      {data.length < 2 ? (
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 40, fontSize: 13 }}>
          等待数据积累...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2e3f" />
            <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#9aa0b0' }} />
            <YAxis tick={{ fontSize: 11, fill: '#9aa0b0' }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ background: '#1e2235', border: '1px solid #2a2e3f', borderRadius: 6, fontSize: 12 }}
              labelStyle={{ color: '#9aa0b0' }}
            />
            <Line type="monotone" dataKey="total" stroke="#448aff" strokeWidth={2} dot={false} name="总资产" />
            <Line type="monotone" dataKey="cash" stroke="#ffd600" strokeWidth={1.5} dot={false} name="现金" strokeDasharray="4 2" />
            <Line type="monotone" dataKey="position" stroke="#00c853" strokeWidth={1.5} dot={false} name="持仓市值" strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
