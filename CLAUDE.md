# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Chinese A-share quantitative trading agent system. DeepSeek AI analyzes real-time stock prices from akshare, makes BUY/SELL/HOLD decisions, and manages a simulated portfolio. The frontend displays price charts, AI decisions, and portfolio value over time.

## Running the Application

```bash
# Quick start
./start.sh

# Or manually:
cd backend && source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm run dev       # Dev server on :3000, proxies /api and /ws to backend
npm run build     # TypeScript check + Vite production build → dist/
npm run lint      # ESLint (typescript-eslint + react-hooks + react-refresh)
npm run preview   # Preview production build
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Dependencies

```bash
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

## Architecture

### Backend (`backend/`)

- **`main.py`** — FastAPI entrypoint. Starts scheduler, manages WebSocket broadcast.
- **`scheduler.py`** — Core loop. Every 30s during A-share trading hours (Mon–Fri 09:30–11:30, 13:00–15:00), 5min otherwise. During trading hours: fetches prices → calls AI → executes trades → updates portfolio → broadcasts. Outside trading hours: only fetches prices and broadcasts, no AI calls. Also skips AI when cash can't buy 1 lot AND no T+1-sellable positions exist.
- **`trading_agent.py`** — DeepSeek API integration. Sends up to 20 recent price records + portfolio state to AI, parses structured JSON response (`action`/`quantity`/`confidence`/`reasoning`). Falls back to rule-based mock decisions if `DEEPSEEK_API_KEY` is unset or API call fails. Mock mode: calculates average `change_percent` over last 5 periods; if < -1.5% → BUY, if > 1.5% → SELL, else HOLD.
- **`data_fetcher.py`** — akshare wrapper. Fetches A-share spot data, normalizes stock codes (6-digit → sz/sh prefix), caches results.
- **`portfolio.py`** — Portfolio management. Tracks cash (initial ¥100,000), positions, avg cost, P&L. Enforces T+1 settlement (stocks bought today cannot be sold today). Records snapshots for the equity curve.
- **`models.py`** — SQLAlchemy ORM: WatchedStock, StockPrice, TradingDecision, Portfolio, Position, PortfolioSnapshot.
- **`database.py`** — SQLite via SQLAlchemy (`backend/trading.db`, auto-created). No external DB server needed.
- **`api.py`** — REST routes: stocks CRUD, price history, decisions, portfolio summary/snapshots/reset.

### Frontend (`frontend/`)

React + TypeScript + Vite + Recharts. Dark theme dashboard with:
- **AccountPanel** — Cash, position value, total assets, P&L, positions table (with sellable quantity respecting T+1)
- **PortfolioChart** — Equity curve (total assets / cash / position value over time)
- **StockList** — Monitored stocks with live prices
- **PriceChart** — Selected stock's price history
- **DecisionList** — AI decision log with action badges
- **AddStockForm** — Add stock by code

WebSocket reconnects automatically every 3 seconds on disconnect.

### Data Flow

1. `scheduler` tick (30s trading / 5min non-trading)
2. `data_fetcher` → akshare → batch fetch all monitored stocks
3. Save `StockPrice` records to SQLite
4. For each stock: call `trading_agent.analyze()` with price history (last 20 records) + portfolio state
5. AI returns `{action, quantity, confidence, reasoning}`
6. `portfolio.execute_buy/sell` validates and executes (enforcing T+1, cash limits, min 100 shares)
7. Save `TradingDecision` record
8. Take `PortfolioSnapshot` for equity curve
9. WebSocket broadcast `{type: "prices"|"decision"|"account"}` to all connected clients

## Configuration

`.env` at project root:
- `DEEPSEEK_API_KEY` — Required for real AI decisions; mock mode without it

## Key Notes

- Stock codes are A-share 6-digit (e.g., "000001" for 平安银行)
- A-share trading rules: minimum 100 shares (1 lot), T+1 settlement (cannot sell stocks bought today), no short selling
- AI system prompt constrains: max 30% of cash per buy, risk control, no intuition-based decisions
- Database is SQLite (`backend/trading.db`), auto-created on first run
- WebSocket endpoint: `ws://host/ws` (single endpoint, all message types multiplexed)
