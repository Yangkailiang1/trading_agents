# 基于LangChain的股票交易Agent系统

## 系统概述

这是一个基于LangChain和DeepSeek模型的智能股票交易系统，能够：
- 从akshare获取实时股票数据
- 监控股票价格波动，超过阈值时触发AI决策
- 使用DeepSeek模型进行交易决策分析
- 提供Web界面查看实时股价和AI决策

## 已完成功能（第一阶段）

1. **Python环境**：虚拟环境已设置，所有依赖已安装
2. **数据库**：MySQL数据库连接，表结构已创建
3. **数据获取**：使用akshare获取A股实时数据
4. **FastAPI后端**：完整的REST API和WebSocket支持
5. **交易Agent**：DeepSeek集成（支持模拟模式）
6. **监控系统**：价格波动监控框架

## 快速开始

### 1. 启动系统

```bash
# 给启动脚本执行权限
chmod +x start.sh

# 启动系统
./start.sh
```

### 2. 访问系统

- **API文档**: http://localhost:8000/docs
- **实时监控**: http://localhost:8000/test (WebSocket测试页面)
- **健康检查**: http://localhost:8000/health

### 3. 基本API使用示例

#### 添加监控股票
```bash
curl -X POST "http://localhost:8000/api/stocks" \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "000001", "stock_name": "平安银行", "threshold": 2.0}'
```

#### 获取监控股票列表
```bash
curl "http://localhost:8000/api/stocks"
```

#### 获取股票实时数据
```bash
curl "http://localhost:8000/api/stocks/000001/realtime"
```

#### 触发交易决策
```bash
curl -X POST "http://localhost:8000/api/stocks/000001/trigger_decision"
```

## API端点

### 股票监控管理
- `POST /api/stocks` - 添加监控股票
- `GET /api/stocks` - 获取监控股票列表
- `GET /api/stocks/{code}` - 获取单个股票信息
- `PUT /api/stocks/{code}` - 更新股票配置
- `DELETE /api/stocks/{code}` - 删除监控股票

### 股票数据查询
- `GET /api/stocks/{code}/data` - 获取历史数据
- `GET /api/stocks/{code}/realtime` - 获取实时数据

### 交易决策管理
- `GET /api/stocks/{code}/decisions` - 获取决策历史
- `POST /api/stocks/{code}/trigger_decision` - 手动触发决策

### WebSocket实时数据
10;  - `WS /ws/stocks/{code}` - 订阅股票实时数据

## 配置

### 环境变量
编辑 `.env` 文件：
```bash
# 数据库配置
HOST=127.0.0.1
DB_USER=root
MYSQL_PW=your_password
DB_NAME=telco_db
PORT=3306

# DeepSeek API密钥（可选）
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### DeepSeek配置
如需使用真实的DeepSeek模型分析，请：
1. 获取DeepSeek API密钥：https://platform.deepseek.com/
2. 添加到 `.env` 文件：`DEEPSEEK_API_KEY=your_key`
3. 系统将自动使用DeepSeek API进行分析

## 项目结构

```
my_trading_agent/
├── backend/              # 后端代码
│   ├── main.py          # FastAPI应用入口
│   ├── api.py           # API路由定义
│   ├── data_fetcher.py  # 股票数据获取
│   ├── trading_agent.py # 交易决策Agent
│   ├── monitor.py       # 价格监控器
│   ├── database.py      # 数据库连接
│   ├── models.py        # 数据模型
│   ├── schemas.py       # Pydantic模型
│   └── requirements.txt # Python依赖
├── frontend/            # 前端代码（待开发）
├── .env                 # 环境变量配置
├── start.sh             # 启动脚本
└── README.md           # 项目说明
```

## 下一步开发计划

### 第二阶段：核心功能完善
1. 完善交易Agent决策逻辑
2. 优化价格监控算法
3. 添加数据分析和可视化
4. 实现电子邮件/短信通知

### 第三阶段：前端界面开发
1. React + TypeScript前端
2. 实时股票图表
3. 交易决策展示面板
4. 用户配置界面

### 第四阶段：高级功能
1. 多用户支持
2. 多种交易策略
3. 历史回测系统
4. 风险管理模块

## 注意事项

1. **数据源**：使用akshare获取A股数据，可能受网络和API限制
2. **交易决策**：系统提供决策建议，不构成投资建议
3. **实时性**：数据更新间隔可配置，默认30秒
4. **数据库**：需要MySQL服务器运行，配置在`.env`中

## 技术支持

如有问题，请检查：
1. MySQL服务器是否运行
2. 数据库配置是否正确
3. 网络连接是否正常
4. 查看服务器日志获取详细信息