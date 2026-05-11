import type { Decision, AgentOpinion } from '../types'

interface Props {
  decisions: Decision[]
}

const actionColors: Record<string, string> = {
  BUY: 'var(--green)',
  SELL: 'var(--red)',
  HOLD: 'var(--yellow)',
}

const actionLabels: Record<string, string> = {
  BUY: '买入',
  SELL: '卖出',
  HOLD: '持有',
}

const AGENT_COLORS: Record<string, string> = {
  bull: '#4CAF50',
  bear: '#F44336',
  fundamental: '#2196F3',
  risk: '#FF9800',
}

function MiniVoteBar({ opinions }: { opinions: AgentOpinion[] }) {
  const analyst = opinions.filter(o => o.agent_name !== 'moderator')
  if (analyst.length === 0) return null
  const total = analyst.length
  const buyW = analyst.filter(o => o.action === 'BUY').length / total * 100
  const sellW = analyst.filter(o => o.action === 'SELL').length / total * 100
  const holdW = analyst.filter(o => o.action === 'HOLD').length / total * 100

  return (
    <div style={{ display: 'flex', height: 3, borderRadius: 2, overflow: 'hidden', marginTop: 6 }}>
      {buyW > 0 && <div style={{ width: `${buyW}%`, background: '#4CAF50' }} />}
      {holdW > 0 && <div style={{ width: `${holdW}%`, background: '#FFC107' }} />}
      {sellW > 0 && <div style={{ width: `${sellW}%`, background: '#F44336' }} />}
    </div>
  )
}

function OpinionBadges({ opinions }: { opinions: AgentOpinion[] }) {
  const analyst = opinions.filter(o => o.agent_name !== 'moderator')
  if (analyst.length === 0) return null

  return (
    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' as const }}>
      {analyst.map((op, i) => {
        const color = AGENT_COLORS[op.agent_name] || '#666'
        return (
          <span key={i} style={{
            fontSize: 10, padding: '1px 5px', borderRadius: 2,
            background: `${color}18`, color: color,
            border: `1px solid ${color}33`,
            display: 'inline-flex', alignItems: 'center', gap: 2,
          }}>
            {op.action === 'BUY' ? '↑' : op.action === 'SELL' ? '↓' : '→'}
            {op.agent_name}
          </span>
        )
      })}
    </div>
  )
}

export default function DecisionList({ decisions }: Props) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: 16, maxHeight: 320, overflowY: 'auto',
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
        AI 决策记录
      </div>
      {decisions.length === 0 ? (
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 20, fontSize: 13 }}>
          暂无决策记录
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {decisions.map((d, i) => (
            <div
              key={`${d.timestamp}-${i}`}
              style={{
                padding: '10px 12px', borderRadius: 6,
                background: 'var(--bg-secondary)', border: '1px solid var(--border)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{
                  padding: '2px 10px', borderRadius: 3, fontSize: 12, fontWeight: 700,
                  color: actionColors[d.action] || 'var(--text-secondary)',
                  background: `${actionColors[d.action] || '#666'}22`,
                  border: `1px solid ${actionColors[d.action] || '#666'}44`,
                }}>
                  {actionLabels[d.action] || d.action}
                </span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>
                  {d.stock_name || d.stock_code}
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {d.quantity > 0 ? `${d.quantity}股 ` : ''}@ ¥{d.price.toFixed(2)}
                </span>
                <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-secondary)' }}>
                  信心 {((d.confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
              {/* 投票条 */}
              {d.opinions && d.opinions.length > 0 && (
                <>
                  <MiniVoteBar opinions={d.opinions} />
                  <OpinionBadges opinions={d.opinions} />
                </>
              )}
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, marginTop: 4 }}>
                {d.reasoning}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4, opacity: 0.6 }}>
                {d.timestamp ? new Date(d.timestamp).toLocaleString('zh-CN') : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
