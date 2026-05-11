import { useState } from 'react'
import type { AgentOpinion, Decision } from '../types'

interface Props {
  decisions: Decision[]
}

const AGENT_META: Record<string, { label: string; color: string; icon: string }> = {
  bull: { label: '多头分析师', color: '#4CAF50', icon: '🐂' },
  bear: { label: '空头分析师', color: '#F44336', icon: '🐻' },
  tech: { label: '技术分析师', color: '#2196F3', icon: '📊' },
  risk: { label: '风控经理', color: '#FF9800', icon: '🛡️' },
  moderator: { label: '决策主席', color: '#9C27B0', icon: '⚖️' },
}

const ACTION_META: Record<string, { label: string; color: string }> = {
  BUY: { label: '买入', color: 'var(--green)' },
  SELL: { label: '卖出', color: 'var(--red)' },
  HOLD: { label: '持有', color: 'var(--yellow)' },
}

function OpinionCard({ opinion, isFinal }: { opinion: AgentOpinion; isFinal?: boolean }) {
  const meta = AGENT_META[opinion.agent_name] || { label: opinion.agent_name, color: '#666', icon: '🤖' }
  const actionMeta = ACTION_META[opinion.action] || { label: opinion.action, color: '#666' }
  const displayName = opinion.role_cn || opinion.agent_role || meta.label

  return (
    <div style={{
      padding: '10px 12px',
      borderRadius: 6,
      background: isFinal ? 'rgba(156, 39, 176, 0.08)' : 'var(--bg-secondary)',
      border: isFinal ? '1px solid rgba(156, 39, 176, 0.3)' : '1px solid var(--border)',
      position: 'relative',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 16 }}>{meta.icon}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: meta.color }}>
          {displayName}
        </span>
        {isFinal && (
          <span style={{
            fontSize: 10, padding: '1px 6px', borderRadius: 3,
            background: 'rgba(156, 39, 176, 0.15)', color: '#9C27B0',
            fontWeight: 700, border: '1px solid rgba(156, 39, 176, 0.3)',
          }}>
            最终裁决
          </span>
        )}
        <span style={{
          padding: '2px 8px', borderRadius: 3, fontSize: 11, fontWeight: 700,
          color: actionMeta.color,
          background: `${actionMeta.color}22`,
          border: `1px solid ${actionMeta.color}44`,
          marginLeft: 'auto',
        }}>
          {actionMeta.label}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
        {opinion.quantity > 0 && <span>数量: {opinion.quantity}股</span>}
        <span>置信度: {(opinion.confidence * 100).toFixed(0)}%</span>
        <div style={{
          flex: 1, height: 4, borderRadius: 2,
          background: 'var(--border)', overflow: 'hidden',
        }}>
          <div style={{
            width: `${opinion.confidence * 100}%`, height: '100%',
            borderRadius: 2, background: meta.color,
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6, lineHeight: 1.5 }}>
        {opinion.reasoning}
      </div>
    </div>
  )
}

function VoteBar({ opinions }: { opinions: AgentOpinion[] }) {
  const analystOpinions = opinions.filter(o => o.agent_name !== 'moderator')
  const total = analystOpinions.length || 1
  const buyCount = analystOpinions.filter(o => o.action === 'BUY').length
  const sellCount = analystOpinions.filter(o => o.action === 'SELL').length
  const holdCount = analystOpinions.filter(o => o.action === 'HOLD').length

  return (
    <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 8 }}>
      {buyCount > 0 && (
        <div style={{ width: `${(buyCount / total) * 100}%`, background: '#4CAF50', transition: 'width 0.3s' }} />
      )}
      {holdCount > 0 && (
        <div style={{ width: `${(holdCount / total) * 100}%`, background: '#FFC107', transition: 'width 0.3s' }} />
      )}
      {sellCount > 0 && (
        <div style={{ width: `${(sellCount / total) * 100}%`, background: '#F44336', transition: 'width 0.3s' }} />
      )}
    </div>
  )
}

export default function DebatePanel({ decisions }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // 只显示有辩论数据的决策
  const debateDecisions = decisions.filter(d => d.opinions && d.opinions.length > 0)

  if (debateDecisions.length === 0) {
    return (
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 8, padding: 16,
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
          多智能体辩论
        </div>
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 20, fontSize: 13 }}>
          暂无辩论记录
        </div>
      </div>
    )
  }

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: 16, maxHeight: 500, overflowY: 'auto',
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
        多智能体辩论
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {debateDecisions.map((d, i) => {
          const key = `${d.timestamp}-${i}`
          const isExpanded = expandedId === key
          const opinions = d.opinions || []
          const finalOpinion: AgentOpinion = {
            agent_name: 'moderator',
            role_cn: '决策主席',
            action: d.action,
            quantity: d.quantity,
            confidence: d.confidence,
            reasoning: d.reasoning,
          }

          return (
            <div key={key} style={{
              borderRadius: 6,
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              overflow: 'hidden',
            }}>
              {/* 折叠头部 */}
              <div
                onClick={() => setExpandedId(isExpanded ? null : key)}
                style={{
                  padding: '10px 12px', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}
              >
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 70 }}>
                  {d.timestamp ? new Date(d.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}
                </span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>
                  {d.stock_name || d.stock_code}
                </span>
                <VoteBar opinions={opinions} />
                <span style={{
                  padding: '2px 8px', borderRadius: 3, fontSize: 11, fontWeight: 700,
                  color: ACTION_META[d.action]?.color || '#666',
                  background: `${ACTION_META[d.action]?.color || '#666'}22`,
                  border: `1px solid ${ACTION_META[d.action]?.color || '#666'}44`,
                }}>
                  {ACTION_META[d.action]?.label || d.action}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  {isExpanded ? '▲' : '▼'}
                </span>
              </div>

              {/* 展开详情 */}
              {isExpanded && (
                <div style={{ padding: '0 12px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {/* 分隔线 */}
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4, fontWeight: 600 }}>
                    阶段一：分析师各自意见
                  </div>
                  {opinions
                    .filter(o => o.agent_name !== 'moderator')
                    .map((op, j) => (
                      <OpinionCard key={j} opinion={op} />
                    ))}
                  {/* 主席裁决 */}
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4, marginBottom: 4, fontWeight: 600 }}>
                    阶段二：主席裁决
                  </div>
                  <OpinionCard opinion={finalOpinion} isFinal />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
