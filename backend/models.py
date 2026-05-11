from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, Date, Index, ForeignKey
from database import Base


class WatchedStock(Base):
    """监控的股票"""
    __tablename__ = "watched_stocks"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False, unique=True)
    stock_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (Index('idx_stock_code', 'stock_code'),)


class StockPrice(Base):
    """股价历史记录"""
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False)
    price = Column(Float, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    prev_close = Column(Float)
    volume = Column(Integer)
    change = Column(Float)
    change_percent = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_price_stock_code', 'stock_code'),
        Index('idx_price_timestamp', 'timestamp'),
    )


class TradingDecision(Base):
    """AI交易决策记录"""
    __tablename__ = "trading_decisions"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100))
    action = Column(String(10), nullable=False)  # BUY / SELL / HOLD
    quantity = Column(Integer, default=0)
    price = Column(Float, default=0)
    confidence = Column(Float, default=0)
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    debate_id = Column(String(50), nullable=True)  # 关联多智能体辩论ID

    __table_args__ = (
        Index('idx_decision_stock_code', 'stock_code'),
        Index('idx_decision_created_at', 'created_at'),
    )


class AgentOpinion(Base):
    """多智能体辩论中每个智能体的意见"""
    __tablename__ = "agent_opinions"

    id = Column(Integer, primary_key=True, index=True)
    debate_id = Column(String(50), nullable=False)  # 辩论ID，同一次辩论的所有意见共享
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100))
    agent_name = Column(String(20), nullable=False)  # bull / bear / tech / risk / moderator
    agent_role = Column(String(50), nullable=False)  # 角色中文名
    action = Column(String(10), nullable=False)  # BUY / SELL / HOLD
    quantity = Column(Integer, default=0)
    confidence = Column(Float, default=0)
    reasoning = Column(Text)
    is_final = Column(Boolean, default=False)  # 是否是最终裁决
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_opinion_debate_id', 'debate_id'),
        Index('idx_opinion_stock_code', 'stock_code'),
        Index('idx_opinion_created_at', 'created_at'),
    )


class Portfolio(Base):
    """投资组合：单条记录代表一次快照"""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    cash = Column(Float, default=100000.0)
    total_assets = Column(Float, default=100000.0)
    created_at = Column(DateTime, default=datetime.now)


class Position(Base):
    """持仓"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False, unique=True)
    stock_name = Column(String(100))
    quantity = Column(Integer, default=0)
    avg_cost = Column(Float, default=0)  # 持仓均价
    buy_date = Column(Date, default=None)  # 首次买入日期，用于T+1判断
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PortfolioSnapshot(Base):
    """资金变动历史快照，用于绘制资金曲线"""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    cash = Column(Float)
    position_value = Column(Float)
    total_assets = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (Index('idx_snapshot_timestamp', 'timestamp'),)
