import { Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart } from 'recharts'
import type { PricePoint } from '../types'

interface Props {
  data: PricePoint[]
  stockCode: string | null
}

function formatChartTime(timestamp: string, allTimestamps: string[]): string {
  const d = new Date(timestamp)
  const dates = new Set(allTimestamps.map(t => new Date(t).toDateString()))
  if (dates.size > 1) {
    return `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

export default function PriceChart({ data, stockCode }: Props) {
  const allTimestamps = data.map(p => p.timestamp)
  const chartData = data.map(p => ({
    time: formatChartTime(p.timestamp, allTimestamps),
    price: p.price,
    high: p.high,
    low: p.low,
  }))

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: 16,
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
        股价走势 {stockCode ? `· ${stockCode}` : ''}
      </div>
      {chartData.length < 2 ? (
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 40, fontSize: 13 }}>
          {stockCode ? '等待数据积累...' : '请先选择一只股票'}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#448aff" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#448aff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2e3f" />
            <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#9aa0b0' }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11, fill: '#9aa0b0' }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ background: '#1e2235', border: '1px solid #2a2e3f', borderRadius: 6, fontSize: 12 }}
              labelStyle={{ color: '#9aa0b0' }}
            />
            <Area type="monotone" dataKey="price" stroke="#448aff" strokeWidth={2} fill="url(#priceGrad)" dot={false} name="价格" />
            <Line type="monotone" dataKey="high" stroke="#ff9100" strokeWidth={1} dot={false} strokeDasharray="3 3" name="最高" />
            <Line type="monotone" dataKey="low" stroke="#00c853" strokeWidth={1} dot={false} strokeDasharray="3 3" name="最低" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
