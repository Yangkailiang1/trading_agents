"""
资金管理模块
管理现金、持仓、总资产的计算和持久化
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, date

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Portfolio, Position, PortfolioSnapshot

logger = logging.getLogger(__name__)

INITIAL_CASH = 100000.0


def get_portfolio(db: Session) -> Portfolio:
    """获取当前投资组合，如果没有则初始化"""
    p = db.query(Portfolio).first()
    if not p:
        p = Portfolio(cash=INITIAL_CASH, total_assets=INITIAL_CASH)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def get_positions(db: Session) -> List[Position]:
    """获取所有持仓"""
    return db.query(Position).all()


def get_position(db: Session, stock_code: str) -> Optional[Position]:
    """获取单只股票的持仓"""
    return db.query(Position).filter(Position.stock_code == stock_code).first()


def execute_buy(
    db: Session, stock_code: str, stock_name: str,
    quantity: int, price: float
) -> Dict:
    """执行买入操作"""
    cost = quantity * price
    p = get_portfolio(db)

    if p.cash < cost:
        return {"success": False, "message": f"现金不足: 需要{cost:.2f}, 可用{p.cash:.2f}"}

    # 扣减现金
    p.cash -= cost

    # 更新持仓
    pos = get_position(db, stock_code)
    today = date.today()
    if pos:
        total_cost = pos.avg_cost * pos.quantity + cost
        pos.quantity += quantity
        pos.avg_cost = total_cost / pos.quantity
        pos.stock_name = stock_name
        pos.buy_date = today  # T+1: 追加买入也更新为当天，当天全部不可卖
        pos.updated_at = datetime.now()
    else:
        pos = Position(
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            avg_cost=price,
            buy_date=today,
        )
        db.add(pos)

    db.commit()
    db.refresh(p)
    logger.info(f"买入 {stock_code} {quantity}股 @ {price:.2f}, 剩余现金 {p.cash:.2f}")
    return {"success": True, "message": f"买入{stock_name} {quantity}股@{price:.2f}"}


def execute_sell(
    db: Session, stock_code: str,
    quantity: int, price: float
) -> Dict:
    """执行卖出操作，遵循T+1规则"""
    pos = get_position(db, stock_code)
    if not pos or pos.quantity < quantity:
        avail = pos.quantity if pos else 0
        return {"success": False, "message": f"持仓不足: 欲卖{quantity}股, 可用{avail}股"}

    # T+1: 当天买入的股票不可卖出
    today = date.today()
    if pos.buy_date and pos.buy_date >= today:
        return {"success": False, "message": f"T+1限制: {stock_code} 今日买入不可卖出"}

    revenue = quantity * price

    # 增加现金
    p = get_portfolio(db)
    p.cash += revenue

    # 减少持仓
    pos.quantity -= quantity
    pos.updated_at = datetime.now()
    if pos.quantity == 0:
        db.delete(pos)

    db.commit()
    db.refresh(p)
    logger.info(f"卖出 {stock_code} {quantity}股 @ {price:.2f}, 现金 {p.cash:.2f}")
    return {"success": True, "message": f"卖出{pos.stock_name} {quantity}股@{price:.2f}"}


def calc_total_assets(db: Session, latest_prices: Dict[str, float]) -> float:
    """计算总资产 = 现金 + 所有持仓市值"""
    p = get_portfolio(db)
    positions = get_positions(db)
    position_value = 0.0
    for pos in positions:
        market_price = latest_prices.get(pos.stock_code, pos.avg_cost)
        position_value += pos.quantity * market_price
    return p.cash + position_value


def update_portfolio_total(db: Session, total_assets: float):
    """更新投资组合的总资产"""
    p = get_portfolio(db)
    p.total_assets = total_assets
    db.commit()


def take_snapshot(db: Session, latest_prices: Dict[str, float]):
    """记录资金快照，用于绘制资金曲线"""
    p = get_portfolio(db)
    positions = get_positions(db)
    position_value = 0.0
    for pos in positions:
        market_price = latest_prices.get(pos.stock_code, pos.avg_cost)
        position_value += pos.quantity * market_price

    snapshot = PortfolioSnapshot(
        cash=p.cash,
        position_value=position_value,
        total_assets=p.cash + position_value,
    )
    db.add(snapshot)
    db.commit()


def get_account_summary(db: Session, latest_prices: Dict[str, float]) -> Dict:
    """获取账户摘要"""
    p = get_portfolio(db)
    positions = get_positions(db)

    position_list = []
    position_value = 0.0
    for pos in positions:
        market_price = latest_prices.get(pos.stock_code, pos.avg_cost)
        market_val = pos.quantity * market_price
        pnl = (market_price - pos.avg_cost) * pos.quantity
        pnl_pct = ((market_price - pos.avg_cost) / pos.avg_cost * 100) if pos.avg_cost > 0 else 0
        # T+1: 当天买入的不可卖出
        sellable_qty = pos.quantity if (not pos.buy_date or pos.buy_date < date.today()) else 0

        position_list.append({
            "stock_code": pos.stock_code,
            "stock_name": pos.stock_name,
            "quantity": pos.quantity,
            "sellable_quantity": sellable_qty,
            "avg_cost": round(pos.avg_cost, 2),
            "current_price": round(market_price, 2),
            "market_value": round(market_val, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
        })
        position_value += market_val

    total = p.cash + position_value
    return {
        "cash": round(p.cash, 2),
        "position_value": round(position_value, 2),
        "total_assets": round(total, 2),
        "initial_capital": INITIAL_CASH,
        "total_pnl": round(total - INITIAL_CASH, 2),
        "total_pnl_percent": round((total - INITIAL_CASH) / INITIAL_CASH * 100, 2),
        "positions": position_list,
    }
