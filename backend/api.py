from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from models import WatchedStock, StockPrice, TradingDecision, PortfolioSnapshot, AgentOpinion
import portfolio
from data_fetcher import fetcher

router = APIRouter()


# ─── 股票监控管理 ────────────────────────────────────────

@router.post("/stocks")
async def add_stock(stock_code: str, stock_name: str = "", db: Session = Depends(get_db)):
    """添加监控股票"""
    existing = db.query(WatchedStock).filter(WatchedStock.stock_code == stock_code).first()
    if existing:
        raise HTTPException(400, f"股票 {stock_code} 已在监控列表中")

    # 尝试从akshare获取股票名称
    if not stock_name:
        data = fetcher.fetch_realtime(stock_code)
        if data:
            stock_name = data.get('name', '')

    db_stock = WatchedStock(stock_code=stock_code, stock_name=stock_name)
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return {"success": True, "data": {"stock_code": db_stock.stock_code, "stock_name": db_stock.stock_name}}


@router.get("/stocks")
async def get_stocks(db: Session = Depends(get_db)):
    """获取监控股票列表"""
    stocks = db.query(WatchedStock).all()
    result = []
    for s in stocks:
        cached = fetcher.get_cached(s.stock_code)
        result.append({
            "stock_code": s.stock_code,
            "stock_name": s.stock_name,
            "is_active": s.is_active,
            "current_price": cached.get('price') if cached else None,
            "change_percent": cached.get('change_percent') if cached else None,
        })
    return result


@router.delete("/stocks/{stock_code}")
async def delete_stock(stock_code: str, db: Session = Depends(get_db)):
    """删除监控股票"""
    stock = db.query(WatchedStock).filter(WatchedStock.stock_code == stock_code).first()
    if not stock:
        raise HTTPException(404, f"未找到股票 {stock_code}")
    db.delete(stock)
    db.commit()
    return {"success": True}


# ─── 股价数据 ───────────────────────────────────────────

@router.get("/stocks/{stock_code}/prices")
async def get_stock_prices(
    stock_code: str,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """获取股价历史"""
    since = datetime.now() - timedelta(hours=hours)
    rows = db.query(StockPrice).filter(
        StockPrice.stock_code == stock_code,
        StockPrice.timestamp >= since,
    ).order_by(StockPrice.timestamp.asc()).limit(limit).all()

    return [{
        "price": r.price,
        "open": r.open,
        "high": r.high,
        "low": r.low,
        "prev_close": r.prev_close,
        "volume": r.volume,
        "change": r.change,
        "change_percent": r.change_percent,
        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
    } for r in rows]


@router.get("/stocks/{stock_code}/realtime")
async def get_realtime(stock_code: str):
    """获取实时股价"""
    data = fetcher.fetch_realtime(stock_code)
    if not data:
        raise HTTPException(404, f"未找到股票 {stock_code} 的实时数据")
    return data


# ─── 交易决策 ───────────────────────────────────────────

@router.get("/decisions")
async def get_decisions(
    stock_code: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取交易决策历史"""
    q = db.query(TradingDecision)
    if stock_code:
        q = q.filter(TradingDecision.stock_code == stock_code)
    rows = q.order_by(TradingDecision.created_at.desc()).limit(limit).all()

    result = []
    for r in rows:
        item = {
            "stock_code": r.stock_code,
            "stock_name": r.stock_name,
            "action": r.action,
            "quantity": r.quantity,
            "price": r.price,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
            "debate_id": r.debate_id,
        }

        # 如果有辩论ID，附带各智能体意见
        if r.debate_id:
            opinions = db.query(AgentOpinion).filter(
                AgentOpinion.debate_id == r.debate_id,
                AgentOpinion.is_final == False,
            ).all()
            item["opinions"] = [{
                "agent_name": o.agent_name,
                "role_cn": o.agent_role,
                "action": o.action,
                "quantity": o.quantity,
                "confidence": o.confidence,
                "reasoning": o.reasoning,
            } for o in opinions]

        result.append(item)

    return result


# ─── 资金与持仓 ─────────────────────────────────────────

@router.get("/portfolio")
async def get_portfolio_summary(db: Session = Depends(get_db)):
    """获取账户摘要"""
    latest_prices = fetcher.get_all_cached_prices()
    return portfolio.get_account_summary(db, latest_prices)


@router.post("/portfolio/reset")
async def reset_portfolio(db: Session = Depends(get_db)):
    """重置账户到初始状态"""
    from models import Portfolio, Position
    db.query(Position).delete()
    p = db.query(Portfolio).first()
    if p:
        p.cash = 100000.0
        p.total_assets = 100000.0
    else:
        p = Portfolio(cash=100000.0, total_assets=100000.0)
        db.add(p)
    db.commit()
    return {"success": True, "message": "账户已重置"}


@router.get("/portfolio/snapshots")
async def get_portfolio_snapshots(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """获取资金变动历史"""
    since = datetime.now() - timedelta(hours=hours)
    rows = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.timestamp >= since,
    ).order_by(PortfolioSnapshot.timestamp.asc()).limit(limit).all()

    return [{
        "cash": r.cash,
        "position_value": r.position_value,
        "total_assets": r.total_assets,
        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
    } for r in rows]


# ─── 多智能体辩论 ─────────────────────────────────────────

@router.get("/debates")
async def get_debates(
    stock_code: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取辩论历史列表（按debate_id分组）"""
    # 获取最近的辩论ID列表
    q = db.query(AgentOpinion.debate_id).filter(AgentOpinion.debate_id != "no_debate")
    if stock_code:
        q = q.filter(AgentOpinion.stock_code == stock_code)
    q = q.group_by(AgentOpinion.debate_id).order_by(
        db.query(AgentOpinion.created_at).filter(
            AgentOpinion.debate_id == AgentOpinion.debate_id
        ).order_by(AgentOpinion.created_at.desc()).limit(1).as_scalar().desc()
    )
    debate_ids = [row[0] for row in q.limit(limit).all()]

    result = []
    for did in debate_ids:
        opinions = db.query(AgentOpinion).filter(
            AgentOpinion.debate_id == did
        ).order_by(AgentOpinion.is_final.asc(), AgentOpinion.created_at.asc()).all()

        if not opinions:
            continue

        first = opinions[0]
        final_op = next((o for o in opinions if o.is_final), None)
        analyst_opinions = [o for o in opinions if not o.is_final]

        result.append({
            "debate_id": did,
            "stock_code": first.stock_code,
            "stock_name": first.stock_name,
            "final_decision": {
                "action": final_op.action,
                "quantity": final_op.quantity,
                "confidence": final_op.confidence,
                "reasoning": final_op.reasoning,
            } if final_op else None,
            "opinions": [{
                "agent_name": o.agent_name,
                "agent_role": o.agent_role,
                "action": o.action,
                "quantity": o.quantity,
                "confidence": o.confidence,
                "reasoning": o.reasoning,
            } for o in analyst_opinions],
            "timestamp": first.created_at.isoformat() if first.created_at else None,
        })

    return result


@router.get("/debates/{debate_id}")
async def get_debate_detail(debate_id: str, db: Session = Depends(get_db)):
    """获取单次辩论详情"""
    opinions = db.query(AgentOpinion).filter(
        AgentOpinion.debate_id == debate_id
    ).order_by(AgentOpinion.is_final.asc(), AgentOpinion.created_at.asc()).all()

    if not opinions:
        raise HTTPException(404, f"未找到辩论 {debate_id}")

    first = opinions[0]
    final_op = next((o for o in opinions if o.is_final), None)
    analyst_opinions = [o for o in opinions if not o.is_final]

    return {
        "debate_id": debate_id,
        "stock_code": first.stock_code,
        "stock_name": first.stock_name,
        "final_decision": {
            "action": final_op.action,
            "quantity": final_op.quantity,
            "confidence": final_op.confidence,
            "reasoning": final_op.reasoning,
        } if final_op else None,
        "opinions": [{
            "agent_name": o.agent_name,
            "agent_role": o.agent_role,
            "action": o.action,
            "quantity": o.quantity,
            "confidence": o.confidence,
            "reasoning": o.reasoning,
        } for o in analyst_opinions],
        "timestamp": first.created_at.isoformat() if first.created_at else None,
    }
