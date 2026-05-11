import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import type { StockInfo, Decision, AccountSummary, PortfolioSnapshot, PricePoint, RealtimeData, WSMessage, AgentOpinion } from './types'
import Header from './components/Header'
import AccountPanel from './components/AccountPanel'
import PortfolioChart from './components/PortfolioChart'
import StockList from './components/StockList'
import PriceChart from './components/PriceChart'
import DecisionList from './components/DecisionList'
import DebatePanel from './components/DebatePanel'
import AddStockForm from './components/AddStockForm'

const API = '/api'

export default function App() {
  const [stocks, setStocks] = useState<StockInfo[]>([])
  const [selectedStock, setSelectedStock] = useState<string | null>(null)
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [account, setAccount] = useState<AccountSummary | null>(null)
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([])
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([])
  const [realtimePrices, setRealtimePrices] = useState<Record<string, RealtimeData>>({})

  // Fetch initial data
  const fetchAll = useCallback(async () => {
    try {
      const [stocksRes, decisionsRes, portfolioRes, snapshotsRes] = await Promise.all([
        fetch(`${API}/stocks`),
        fetch(`${API}/decisions?limit=50`),
        fetch(`${API}/portfolio`),
        fetch(`${API}/portfolio/snapshots?hours=24`),
      ])
      setStocks(await stocksRes.json())
      setDecisions(await decisionsRes.json())
      setAccount(await portfolioRes.json())
      setSnapshots(await snapshotsRes.json())
    } catch (e) {
      console.error('Failed to fetch data', e)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  // Fetch price history when selected stock changes
  useEffect(() => {
    if (!selectedStock) return
    fetch(`${API}/stocks/${selectedStock}/prices?hours=24`)
      .then(r => r.json())
      .then(setPriceHistory)
      .catch(console.error)
  }, [selectedStock])

  // WebSocket for real-time updates
  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.type === 'prices') {
      setRealtimePrices(msg.data)
      // Update stock list with new prices
      setStocks(prev => prev.map(s => {
        const rd = msg.data[s.stock_code]
        if (rd) return { ...s, current_price: rd.price, change_percent: rd.change_percent }
        return s
      }))
      // Auto-select first stock if none selected
      setSelectedStock(prev => prev || Object.keys(msg.data)[0] || null)
      // Refresh price history for selected stock
      if (selectedStock && msg.data[selectedStock]) {
        fetch(`${API}/stocks/${selectedStock}/prices?hours=24`)
          .then(r => r.json())
          .then(setPriceHistory)
          .catch(console.error)
      }
    } else if (msg.type === 'decision') {
      // 将辩论意见附加到决策数据中
      const decisionWithOpinions: Decision = {
        stock_code: msg.data.stock_code,
        stock_name: msg.data.stock_name,
        action: msg.data.action,
        quantity: msg.data.quantity,
        price: msg.data.price,
        confidence: msg.data.confidence,
        reasoning: msg.data.reasoning,
        timestamp: msg.data.timestamp,
        debate_id: msg.data.debate_id,
        opinions: msg.data.opinions as AgentOpinion[] | undefined,
      }
      setDecisions(prev => [decisionWithOpinions, ...prev.slice(0, 49)])
    } else if (msg.type === 'account') {
      setAccount(msg.data)
      // Refresh snapshots
      fetch(`${API}/portfolio/snapshots?hours=24`)
        .then(r => r.json())
        .then(setSnapshots)
        .catch(console.error)
    }
  }, [selectedStock])

  useWebSocket(handleWSMessage)

  const addStock = async (code: string, name: string) => {
    const res = await fetch(`${API}/stocks?stock_code=${code}&stock_name=${encodeURIComponent(name)}`, { method: 'POST' })
    if (res.ok) {
      await fetchAll()
      setSelectedStock(code)
    }
  }

  const removeStock = async (code: string) => {
    await fetch(`${API}/stocks/${code}`, { method: 'DELETE' })
    await fetchAll()
    if (selectedStock === code) setSelectedStock(null)
  }

  const resetPortfolio = async () => {
    await fetch(`${API}/portfolio/reset`, { method: 'POST' })
    await fetchAll()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, padding: '0 24px 24px' }}>
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <AccountPanel account={account} onReset={resetPortfolio} />
          <PortfolioChart snapshots={snapshots} />
        </div>
        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <AddStockForm onAdd={addStock} />
          <StockList
            stocks={stocks}
            realtime={realtimePrices}
            selected={selectedStock}
            onSelect={setSelectedStock}
            onRemove={removeStock}
          />
        </div>
      </div>
      {/* Full width bottom section */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, padding: '0 24px 24px' }}>
        <PriceChart data={priceHistory} stockCode={selectedStock} />
        <DecisionList decisions={decisions} />
        <DebatePanel decisions={decisions} />
      </div>
    </div>
  )
}
