"""
交易决策Agent - 接入DeepSeek
定时接收股价数据，输出BUY/SELL/HOLD决策
"""
import os
import json
import logging
import httpx
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingAgent:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.client: Optional[httpx.AsyncClient] = None
        self.use_mock = not bool(self.api_key)

        if self.use_mock:
            logger.warning("未配置DEEPSEEK_API_KEY，将使用模拟决策")

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self.client

    async def analyze(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        price_history: List[Dict],
        cash: float,
        position_qty: int,
        position_avg_cost: float,
    ) -> Dict:
        """
        分析股票并输出交易决策。

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            current_price: 当前价格
            price_history: 最近价格列表 [{"price": float, "timestamp": str}, ...]
            cash: 当前可用现金
            position_qty: 当前持仓数量
            position_avg_cost: 持仓均价（0表示无持仓）

        Returns:
            {"action": "BUY"/"SELL"/"HOLD", "quantity": int, "confidence": float, "reasoning": str}
        """
        if self.use_mock:
            return self._mock_decision(current_price, price_history, cash, position_qty, position_avg_cost)

        prompt = self._build_prompt(
            stock_code, stock_name, current_price, price_history,
            cash, position_qty, position_avg_cost
        )

        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 600,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(content, current_price, cash, position_qty)
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {e}")
            return self._mock_decision(current_price, price_history, cash, position_qty, position_avg_cost)

    def _build_prompt(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        price_history: List[Dict],
        cash: float,
        position_qty: int,
        position_avg_cost: float,
    ) -> str:
        # 格式化最近价格走势
        history_str = ""
        for h in price_history[-20:]:
            history_str += f"  {h.get('timestamp', '')}  价格: {h.get('price', 0):.2f}  涨跌幅: {h.get('change_percent', 0):.2f}%\n"

        position_desc = "无持仓" if position_qty == 0 else (
            f"持有 {position_qty} 股，均价 {position_avg_cost:.2f}，"
            f"浮动盈亏 {((current_price - position_avg_cost) / position_avg_cost * 100):.2f}%"
        )

        return f"""## 当前任务
请分析以下股票数据并给出交易决策。

## 股票信息
- 代码: {stock_code}
- 名称: {stock_name}
- 当前价格: {current_price:.2f}

## 最近价格走势
{history_str if history_str else "  暂无历史数据"}

## 账户状态
- 可用现金: {cash:.2f}
- 持仓: {position_desc}

## 交易规则
1. A股最低买入100股（1手），卖出也必须是100的整数倍
2. 不能透支（现金不足则无法买入）
3. 不能卖空（持仓不足则无法卖出）
4. 买入时需预留少量资金余量

请以JSON返回决策，格式如下：
```json
{{"action": "BUY或SELL或HOLD", "quantity": 买卖数量(整数, HOLD时为0), "confidence": 0.0到1.0, "reasoning": "简短理由"}}
```"""

    def _parse_response(self, content: str, current_price: float, cash: float, position_qty: int) -> Dict:
        """解析AI返回的JSON"""
        try:
            # 提取JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                d = json.loads(json_match.group())
            else:
                raise ValueError("未找到JSON")

            action = d.get("action", "HOLD").upper()
            if action not in ("BUY", "SELL", "HOLD"):
                action = "HOLD"
            quantity = max(0, int(d.get("quantity", 0)))
            confidence = max(0.0, min(1.0, float(d.get("confidence", 0.5))))
            reasoning = d.get("reasoning", "")

            # 校验数量合法性
            if action == "BUY":
                max_afford = int(cash / current_price / 100) * 100
                quantity = min(quantity, max_afford)
                if quantity < 100:
                    action = "HOLD"
                    quantity = 0
                    reasoning = "资金不足以买入1手，改为持有观望"
            elif action == "SELL":
                quantity = min(quantity, position_qty)
                if quantity <= 0:
                    action = "HOLD"
                    quantity = 0
                    reasoning = "无持仓可卖出，改为持有观望"

            return {
                "action": action,
                "quantity": quantity,
                "confidence": round(confidence, 2),
                "reasoning": reasoning,
            }
        except Exception as e:
            logger.warning(f"解析AI响应失败: {e}, 原始内容: {content[:200]}")
            return {"action": "HOLD", "quantity": 0, "confidence": 0.3, "reasoning": "AI响应解析失败，保守持有"}

    def _mock_decision(
        self, current_price: float, price_history: List[Dict],
        cash: float, position_qty: int, position_avg_cost: float
    ) -> Dict:
        """模拟决策：基于简单规则"""
        if len(price_history) < 3:
            return {"action": "HOLD", "quantity": 0, "confidence": 0.3, "reasoning": "数据不足，暂时观望"}

        recent = [h.get("change_percent", 0) for h in price_history[-5:]]
        avg_change = sum(recent) / len(recent) if recent else 0

        if avg_change < -1.5 and cash >= current_price * 100:
            qty = int(cash / current_price / 100) * 100
            qty = max(100, min(qty, 500))  # 模拟最多买5手
            return {"action": "BUY", "quantity": qty, "confidence": 0.6, "reasoning": f"近期平均跌幅{avg_change:.2f}%，模拟买入"}
        elif avg_change > 1.5 and position_qty > 0:
            qty = min(position_qty, 100)
            return {"action": "SELL", "quantity": qty, "confidence": 0.6, "reasoning": f"近期平均涨幅{avg_change:.2f}%，模拟卖出"}
        else:
            return {"action": "HOLD", "quantity": 0, "confidence": 0.5, "reasoning": f"近期走势平稳(均值{avg_change:.2f}%)，继续持有"}


SYSTEM_PROMPT = """你是一个专业的A股量化交易AI助手。你的职责是根据股价走势和账户状态做出理性的交易决策。

核心原则：
1. 严格控制风险，不要全仓操作
2. 单次买入不超过总资金的30%
3. 设置合理的止损止盈
4. 优先保护本金安全
5. 基于数据做决策，不要凭直觉

你必须严格按照JSON格式返回决策结果。"""


# 全局实例
agent = TradingAgent()
