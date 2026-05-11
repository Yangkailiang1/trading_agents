# A股多智能体量化交易系统

基于 DeepSeek AI 的多智能体辩论交易决策系统。5个AI智能体从不同视角分析股票，通过辩论达成最终交易决策，前端实时展示辩论过程和投资组合。

## 系统架构

### 多智能体辩论决策

```
┌─────────────────────────────────────────────┐
│              阶段1：并行分析（4个API调用）       │
│                                               │
│  🐂 多头分析师    🐻 空头分析师                 │
│  寻找买入机会     发现风险信号                  │
│                                               │
│  📋 基本面分析师  🛡️ 风控经理                   │
│  财务+资金面分析  仓位+止损控制                 │
└──────────────┬──────────────────────────────┘
               │ 4份意见汇总
               ▼
┌─────────────────────────┐
│  阶段2：主席裁决（1个API调用）│
│  ⚖️ 决策主席              │
│  - 置信度加权投票          │
│  - 风控否决权优先          │
│  - 输出最终 BUY/SELL/HOLD │
└─────────────────────────┘
```

| 智能体 | 角色 | 数据来源 |
|--------|------|----------|
| 多头分析师 | 看多视角，寻找买入机会 | 价格走势 + 基本面简要 |
| 空头分析师 | 看空视角，发现风险信号 | 价格走势 + 基本面简要 |
| 基本面分析师 | 客观分析公司财务和资金面 | 价格走势 + **完整基本面数据** |
| 风控经理 | 仓位管理、止损止盈 | 价格走势 + 账户状态 |
| 决策主席 | 综合裁决，加权投票 | 4位分析师意见 |

### 基本面数据（akshare）

基本面分析师通过 akshare 获取以下数据（无需额外 API key）：

- **公司基本信息**：行业、市值、股本（`stock_individual_info_em`）
- **财务摘要**：净利润、营收、ROE、EPS、资产负债率等，最近2期（`stock_financial_abstract_ths`）
- **资金流向**：主力/超大单/大单净流入，近5日（`stock_individual_fund_flow`）
- **综合评分**：东方财富综合评分趋势（`stock_comment_detail_zhpj_lspf_em`）

## 快速开始

### 1. 安装依赖

```bash
# 后端
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 前端
cd frontend && npm install
```

### 2. 配置

在项目根目录创建 `.env` 文件：

```bash
# DeepSeek API密钥（可选，不配置则使用模拟决策）
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 3. 启动

```bash
# 快速启动（后端 + 前端构建）
./start.sh

# 或分别启动：
# 后端
cd backend && source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 前端（开发模式，支持热更新）
cd frontend && npm run dev
```

### 4. 访问

- **前端界面**: http://localhost:3000（开发模式）或 http://localhost:8000（生产模式）
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 前端界面

React + TypeScript + Vite + Recharts 暗色主题仪表盘：

- **AccountPanel** — 账户概览：现金、持仓市值、总资产、盈亏、持仓表格（含 T+1 可卖数量）
- **PortfolioChart** — 资产曲线：总资产/现金/持仓市值随时间变化
- **StockList** — 监控股票列表，实时价格
- **PriceChart** — 选中股票的价格历史图表
- **DecisionList** — AI 决策记录，含投票条和各智能体意见标签
- **DebatePanel** — 多智能体辩论详情，可展开查看每个智能体的意见和主席裁决

## API 端点

### 股票管理
- `POST /api/stocks` — 添加监控股票
- `GET /api/stocks` — 获取监控列表
- `DELETE /api/stocks/{code}` — 删除监控股票

### 行情数据
- `GET /api/stocks/{code}/prices` — 价格历史
- `GET /api/stocks/{code}/realtime` — 实时行情

### 交易决策
- `GET /api/decisions` — 决策历史（含各智能体意见）

### 多智能体辩论
- `GET /api/debates` — 辩论历史列表
- `GET /api/debates/{debate_id}` — 单次辩论详情

### 资金与持仓
- `GET /api/portfolio` — 账户摘要
- `POST /api/portfolio/reset` — 重置账户
- `GET /api/portfolio/snapshots` — 资产快照曲线

### WebSocket
- `WS /ws` — 实时推送（prices / decision / account）

## 数据流

```
1. scheduler tick（交易时间30s / 非交易时间5min）
2. data_fetcher → akshare → 批量获取实时价格
3. 保存 StockPrice 到 SQLite
4. multi_agent.debate() → 获取基本面数据 → 4个分析师并行分析 → 主席裁决
5. portfolio.execute_buy/sell() → 执行交易（T+1、最低100股）
6. 保存 TradingDecision + AgentOpinion 到数据库
7. WebSocket 广播到前端
```

## 交易规则

- A股最低买入100股（1手），卖出必须是100的整数倍
- T+1 结算：今天买入的股票今天不能卖出
- 禁止透支和卖空
- 单次买入不超过可用现金的30%
- 单只股票持仓不超过总资产40%
- 可用现金不低于总资产20%
- 亏损超8%触发止损，盈利超20%部分止盈

## 项目结构

```
my_trading_agent/
├── backend/
│   ├── main.py                # FastAPI 入口，WebSocket 广播
│   ├── api.py                 # REST API 路由
│   ├── scheduler.py           # 定时调度器（交易/非交易时间）
│   ├── multi_agent.py         # 多智能体辩论系统（5个Agent）
│   ├── fundamental_fetcher.py # 基本面数据获取（akshare）
│   ├── trading_agent.py       # 单智能体（已弃用，保留兼容）
│   ├── portfolio.py           # 投资组合管理（买卖执行、T+1）
│   ├── data_fetcher.py        # 行情数据获取（akshare）
│   ├── models.py              # SQLAlchemy ORM 模型
│   ├── database.py            # SQLite 数据库 + 迁移
│   └── requirements.txt       # Python 依赖
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # 主布局
│   │   ├── types.ts           # TypeScript 类型定义
│   │   ├── components/
│   │   │   ├── AccountPanel.tsx
│   │   │   ├── PortfolioChart.tsx
│   │   │   ├── StockList.tsx
│   │   │   ├── PriceChart.tsx
│   │   │   ├── DecisionList.tsx    # 决策列表（含投票条）
│   │   │   ├── DebatePanel.tsx     # 辩论详情面板
│   │   │   ├── AddStockForm.tsx
│   │   │   └── Header.tsx
│   │   └── hooks/
│   │       └── useWebSocket.ts
│   └── ...config files
├── .env                       # 环境变量
├── start.sh                   # 启动脚本
├── CLAUDE.md                  # Claude Code 指引
└── README.md
```

## 成本说明

- **真实 AI 模式**：每只股票每 tick 调用 5 次 DeepSeek API（4个分析师并行 + 1个主席串行）
- **Mock 模式**：零 API 调用，各智能体使用规则逻辑模拟
- 未配置 `DEEPSEEK_API_KEY` 时自动进入 Mock 模式

## 免责声明

本系统仅供学习和研究用途，交易决策由 AI 生成，**不构成任何投资建议**。股市有风险，投资需谨慎。
