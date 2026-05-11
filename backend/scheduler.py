"""
定时调度器
按间隔获取股价 → 保存到DB → 发给AI决策 → 执行交易 → 更新资金 → 广播前端

A股交易时间：周一至周五
  上午 09:30 - 11:30
  下午 13:00 - 15:00
非交易时间仅获取股价做展示，不调用AI以节省token
"""
import asyncio
import logging
from datetime import datetime, time, date
from typing import Dict, Optional, Callable, Awaitable

from database import SessionLocal
from models import WatchedStock, StockPrice, TradingDecision, AgentOpinion
from data_fetcher import fetcher
from multi_agent import multi_agent
import portfolio

logger = logging.getLogger(__name__)


def is_trading_hours() -> bool:
    """判断当前是否在A股交易时间段内"""
    now = datetime.now()
    # 周末不交易
    if now.weekday() >= 5:
        return False
    t = now.time()
    # 上午 09:30 - 11:30
    if time(9, 30) <= t <= time(11, 30):
        return True
    # 下午 13:00 - 15:00
    if time(13, 0) <= t <= time(15, 0):
        return True
    return False


class TradingScheduler:
    def __init__(self, interval_seconds: int = 30):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self._broadcast_callback: Optional[Callable[[dict], Awaitable[None]]] = None
        self._last_trading_state: Optional[bool] = None  # 追踪状态变化，用于打日志

    def set_broadcast(self, callback: Callable[[dict], Awaitable[None]]):
        """设置WebSocket广播回调"""
        self._broadcast_callback = callback

    async def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"调度器启动，间隔 {self.interval_seconds}秒")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("调度器已停止")

    async def _loop(self):
        while self.is_running:
            try:
                in_trading = is_trading_hours()

                # 状态变化时打日志
                if in_trading != self._last_trading_state:
                    if in_trading:
                        logger.info("进入交易时间段，启动AI决策")
                    else:
                        logger.info("离开交易时间段，暂停AI决策（仅获取股价）")
                    self._last_trading_state = in_trading

                await self._tick(in_trading)
            except Exception as e:
                logger.error(f"调度循环异常: {e}", exc_info=True)

            # 交易时间用短间隔，非交易时间用5分钟长间隔（省资源）
            sleep_seconds = self.interval_seconds if in_trading else 300
            await asyncio.sleep(sleep_seconds)

    async def _tick(self, in_trading: bool):
        """一次完整的调度周期"""
        db = SessionLocal()
        try:
            # 1. 获取所有监控中的股票代码
            stocks = db.query(WatchedStock).filter(WatchedStock.is_active == True).all()
            if not stocks:
                return

            codes = [s.stock_code for s in stocks]

            # 2. 批量获取实时数据
            realtime_data = fetcher.fetch_batch(codes)
            if not realtime_data:
                return

            # 3. 保存股价到数据库
            for stock_code, data in realtime_data.items():
                price_record = StockPrice(
                    stock_code=stock_code,
                    price=data['price'],
                    open=data.get('open', 0),
                    high=data.get('high', 0),
                    low=data.get('low', 0),
                    prev_close=data.get('prev_close', 0),
                    volume=data.get('volume', 0),
                    change=data.get('change', 0),
                    change_percent=data.get('change_percent', 0),
                )
                db.add(price_record)
            db.commit()

            # 4. 非交易时间：只获取股价和广播，跳过AI决策
            if not in_trading:
                latest_prices = fetcher.get_all_cached_prices()
                summary = portfolio.get_account_summary(db, latest_prices)
                await self._broadcast({"type": "account", "data": summary})
                await self._broadcast({"type": "prices", "data": realtime_data})
                return

            # 5. 交易时间：判断是否需要调用AI
            latest_prices = fetcher.get_all_cached_prices()
            pf = get_portfolio(db)

            # 检查是否有可操作空间：现金不足买1手 且 没有T+1可卖持仓 → 跳过AI
            positions = portfolio.get_positions(db)
            today = date.today()
            has_sellable = any(
                pos.buy_date and pos.buy_date < today
                for pos in positions if pos.quantity > 0
            )
            min_price = min((stock_data['price'] for stock_data in realtime_data.values() if stock_data.get('price', 0) > 0), default=0)
            can_buy = pf.cash >= min_price * 100 if min_price > 0 else False
            skip_ai = not can_buy and not has_sellable

            if skip_ai:
                logger.info("现金不足买入且无T+1可卖持仓，跳过AI决策")

            for stock in stocks:
                stock_code = stock.stock_code
                stock_data = realtime_data.get(stock_code)
                if not stock_data:
                    continue

                pos = portfolio.get_position(db, stock_code)
                pos_qty = pos.quantity if pos else 0
                pos_avg = pos.avg_cost if pos else 0

                if skip_ai:
                    # 跳过AI，直接生成HOLD决策
                    debate_result = {
                        "debate_id": None,
                        "stock_code": stock_code,
                        "stock_name": stock_data.get('name', ''),
                        "opinions": [],
                        "final_decision": {
                            "action": "HOLD",
                            "quantity": 0,
                            "confidence": 0.1,
                            "reasoning": "现金不足买入且无T+1可卖持仓，无需AI分析",
                        },
                    }
                else:
                    # 获取最近价格历史
                    price_history = db.query(StockPrice).filter(
                        StockPrice.stock_code == stock_code
                    ).order_by(StockPrice.timestamp.desc()).limit(20).all()

                    history_dicts = [
                        {
                            "price": hp.price,
                            "change_percent": hp.change_percent,
                            "timestamp": hp.timestamp.isoformat() if hp.timestamp else "",
                        }
                        for hp in reversed(price_history)
                    ]

                    # 多智能体辩论
                    debate_result = await multi_agent.debate(
                        stock_code=stock_code,
                        stock_name=stock_data.get('name', ''),
                        current_price=stock_data['price'],
                        price_history=history_dicts,
                        cash=pf.cash,
                        position_qty=pos_qty,
                        position_avg_cost=pos_avg,
                    )

                decision = debate_result["final_decision"]

                # 6. 执行交易
                executed = False
                if decision['action'] == 'BUY' and decision.get('quantity', 0) > 0:
                    result = portfolio.execute_buy(
                        db, stock_code, stock_data.get('name', ''),
                        decision['quantity'], stock_data['price']
                    )
                    executed = result['success']
                elif decision['action'] == 'SELL' and decision.get('quantity', 0) > 0:
                    result = portfolio.execute_sell(
                        db, stock_code, decision['quantity'], stock_data['price']
                    )
                    executed = result['success']

                # 7. 保存决策记录
                debate_id = debate_result.get("debate_id")
                db_decision = TradingDecision(
                    stock_code=stock_code,
                    stock_name=stock_data.get('name', ''),
                    action=decision['action'],
                    quantity=decision.get('quantity', 0),
                    price=stock_data['price'],
                    confidence=decision.get('confidence', 0),
                    reasoning=decision.get('reasoning', ''),
                    debate_id=debate_id,
                )
                db.add(db_decision)

                # 保存各智能体意见
                for opinion in debate_result.get("opinions", []):
                    db_opinion = AgentOpinion(
                        debate_id=debate_id or "no_debate",
                        stock_code=stock_code,
                        stock_name=stock_data.get('name', ''),
                        agent_name=opinion.get("agent_name", ""),
                        agent_role=opinion.get("role_cn", ""),
                        action=opinion.get("action", "HOLD"),
                        quantity=opinion.get("quantity", 0),
                        confidence=opinion.get("confidence", 0),
                        reasoning=opinion.get("reasoning", ""),
                        is_final=False,
                    )
                    db.add(db_opinion)

                # 保存最终裁决意见
                if debate_id:
                    db_final_opinion = AgentOpinion(
                        debate_id=debate_id,
                        stock_code=stock_code,
                        stock_name=stock_data.get('name', ''),
                        agent_name=decision.get("agent_name", "moderator"),
                        agent_role=decision.get("role_cn", "决策主席"),
                        action=decision['action'],
                        quantity=decision.get('quantity', 0),
                        confidence=decision.get('confidence', 0),
                        reasoning=decision.get('reasoning', ''),
                        is_final=True,
                    )
                    db.add(db_final_opinion)

                db.commit()

                # 广播决策事件（包含辩论详情）
                await self._broadcast({
                    "type": "decision",
                    "data": {
                        "stock_code": stock_code,
                        "stock_name": stock_data.get('name', ''),
                        "action": decision['action'],
                        "quantity": decision.get('quantity', 0),
                        "price": stock_data['price'],
                        "confidence": decision.get('confidence', 0),
                        "reasoning": decision.get('reasoning', ''),
                        "executed": executed,
                        "debate_id": debate_id,
                        "opinions": debate_result.get("opinions", []),
                        "timestamp": datetime.now().isoformat(),
                    }
                })

            # 8. 更新总资产 & 记录快照
            latest_prices = fetcher.get_all_cached_prices()
            total = portfolio.calc_total_assets(db, latest_prices)
            portfolio.update_portfolio_total(db, total)
            portfolio.take_snapshot(db, latest_prices)

            # 9. 广播账户和价格更新
            summary = portfolio.get_account_summary(db, latest_prices)
            await self._broadcast({
                "type": "account",
                "data": summary,
            })
            await self._broadcast({
                "type": "prices",
                "data": realtime_data,
            })

        except Exception as e:
            db.rollback()
            logger.error(f"调度tick异常: {e}", exc_info=True)
        finally:
            db.close()

    async def _broadcast(self, message: dict):
        """广播消息到前端"""
        if self._broadcast_callback:
            try:
                await self._broadcast_callback(message)
            except Exception as e:
                logger.error(f"广播失败: {e}")


def get_portfolio(db):
    """获取Portfolio记录"""
    return portfolio.get_portfolio(db)


# 全局调度器实例
scheduler = TradingScheduler()
