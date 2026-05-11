"""
多智能体辩论交易决策系统

架构：5个智能体，2阶段决策
- 阶段1（并行）：多头、空头、技术、风控 4个分析师各自独立分析
- 阶段2（串行）：主席汇总所有意见，做出最终裁决

每个智能体有独立的System Prompt和分析视角，
最终决策由主席综合各方意见、置信度和推理逻辑后做出。
"""
import os
import json
import re
import uuid
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


# ─── 智能体角色定义 ─────────────────────────────────────────

class AgentRole(str, Enum):
    BULL = "bull"          # 多头分析师
    BEAR = "bear"          # 空头分析师
    TECH = "tech"          # 技术分析师
    RISK = "risk"          # 风控经理
    MODERATOR = "moderator"  # 决策主席


AGENT_CONFIG = {
    AgentRole.BULL: {
        "name": "bull",
        "role_cn": "多头分析师",
        "icon": "🐂",
        "color": "#4CAF50",
        "system_prompt": """你是「多头分析师」，你的职责是寻找买入机会。

你的分析视角：
1. 关注利好信号：低估值反弹、政策利好、行业景气、资金流入
2. 倾向于发现上涨潜力，寻找被低估的买入时机
3. 分析价格下跌是否为抄底机会
4. 关注支撑位、底部形态、止跌企稳信号
5. 从乐观角度解读市场信息

注意：
- 你不是盲目看多，而是基于数据寻找合理的买入理由
- 如果数据确实不支持买入，你应该给出HOLD而非强行BUY
- 你需要给出具体的买入数量建议（A股最低100股）
- 单次买入不超过可用现金的30%""",
    },
    AgentRole.BEAR: {
        "name": "bear",
        "role_cn": "空头分析师",
        "icon": "🐻",
        "color": "#F44336",
        "system_prompt": """你是「空头分析师」，你的职责是发现风险和卖出信号。

你的分析视角：
1. 关注利空信号：高位滞涨、放量下跌、趋势破位、资金流出
2. 倾向于发现下跌风险，寻找合理的卖出时机
3. 分析价格上涨是否为诱多陷阱
4. 关注压力位、顶部形态、见顶信号
5. 从风险角度解读市场信息

注意：
- 你不是盲目看空，而是基于数据寻找合理的风险点
- 如果数据确实没有风险信号，你应该给出HOLD而非强行SELL
- 如果有持仓且发现风险，你需要给出具体的卖出数量建议
- 保护本金安全是你的首要原则""",
    },
    AgentRole.TECH: {
        "name": "tech",
        "role_cn": "技术分析师",
        "icon": "📊",
        "color": "#2196F3",
        "system_prompt": """你是「技术分析师」，你的职责是基于纯技术面进行客观分析。

你的分析视角：
1. 价格形态：趋势方向、支撑压力位、K线组合形态
2. 量价关系：成交量变化与价格走势的配合
3. 动量指标：涨跌幅变化速率、连续涨跌天数
4. 均线系统：短期均线与长期均线的关系（用价格数据近似判断）
5. 波动率：近期价格波动幅度

注意：
- 你必须客观中立，不偏向多头或空头
- 只基于技术数据给出分析结论
- 如果技术面不明确，给出HOLD
- 你的分析应该包含关键的技术位说明""",
    },
    AgentRole.RISK: {
        "name": "risk",
        "role_cn": "风控经理",
        "icon": "🛡️",
        "color": "#FF9800",
        "system_prompt": """你是「风控经理」，你的职责是评估交易风险并控制仓位。

你的分析视角：
1. 仓位风险：当前持仓占比是否过高，是否需要减仓
2. 止损止盈：持仓是否触及止损/止盈线
3. 资金管理：可用现金是否充足，是否需要保留现金
4. 集中度风险：单只股票仓位是否过重
5. 波动率风险：近期波动是否加大，是否需要降低仓位

风控规则：
- 单只股票持仓不超过总资产的40%
- 可用现金不低于总资产的20%
- 亏损超过8%建议止损
- 盈利超过20%建议部分止盈
- 新买入不超过可用现金的30%

注意：
- 你不直接判断涨跌方向，而是评估交易的风险收益比
- 即使方向正确，如果仓位过重你也应该建议减仓
- 即使方向不明，如果仓位很轻你也可以允许少量建仓""",
    },
    AgentRole.MODERATOR: {
        "name": "moderator",
        "role_cn": "决策主席",
        "icon": "⚖️",
        "color": "#9C27B0",
        "system_prompt": """你是「决策主席」，你的职责是汇总所有分析师的意见，做出最终交易决策。

你将收到以下信息：
1. 多头分析师的意见（看多视角）
2. 空头分析师的意见（看空视角）
3. 技术分析师的意见（中性技术面）
4. 风控经理的意见（风险控制）

你的裁决原则：
1. 综合考虑所有分析师的意见和置信度
2. 当多头和空头意见对立时，技术分析师和风控经理的意见更具参考价值
3. 置信度更高的意见权重更大
4. 风控经理的减仓/止损建议具有一票否决权（如果风控明确要求止损，必须执行）
5. 如果没有明确方向，默认HOLD
6. 最终决策必须是理性的、基于多数意见的

裁决流程：
- 统计各方意见的BUY/SELL/HOLD分布
- 考虑各方置信度进行加权
- 风控否决权优先
- 给出最终决策和理由

你必须严格按照JSON格式返回最终决策。""",
    },
}


# ─── 智能体实现 ─────────────────────────────────────────────

class Agent:
    """单个智能体"""

    def __init__(self, role: AgentRole):
        self.role = role
        config = AGENT_CONFIG[role]
        self.name = config["name"]
        self.role_cn = config["role_cn"]
        self.system_prompt = config["system_prompt"]

    def build_analyst_prompt(
        self,
        stock_code: str,
        stock_name: str,
        current_price: float,
        price_history: List[Dict],
        cash: float,
        position_qty: int,
        position_avg_cost: float,
    ) -> str:
        """构建分析师的user prompt"""
        history_str = ""
        for h in price_history[-20:]:
            history_str += f"  {h.get('timestamp', '')}  价格: {h.get('price', 0):.2f}  涨跌幅: {h.get('change_percent', 0):.2f}%\n"

        position_desc = "无持仓" if position_qty == 0 else (
            f"持有 {position_qty} 股，均价 {position_avg_cost:.2f}，"
            f"浮动盈亏 {((current_price - position_avg_cost) / position_avg_cost * 100):.2f}%"
        )

        total_assets_hint = ""
        if position_qty > 0:
            position_value = position_qty * current_price
            total_estimate = cash + position_value
            position_ratio = position_value / total_estimate * 100 if total_estimate > 0 else 0
            cash_ratio = cash / total_estimate * 100 if total_estimate > 0 else 0
            total_assets_hint = f"\n- 持仓市值: ¥{position_value:.2f} (占总资产{position_ratio:.1f}%)\n- 现金占比: {cash_ratio:.1f}%"

        return f"""## 当前任务
请从你的专业视角分析以下股票数据并给出意见。

## 股票信息
- 代码: {stock_code}
- 名称: {stock_name}
- 当前价格: {current_price:.2f}

## 最近价格走势
{history_str if history_str else "  暂无历史数据"}

## 账户状态
- 可用现金: ¥{cash:.2f}
- 持仓: {position_desc}{total_assets_hint}

## 交易规则
1. A股最低买入100股（1手），卖出也必须是100的整数倍
2. 不能透支（现金不足则无法买入）
3. 不能卖空（持仓不足则无法卖出）
4. 买入时需预留少量资金余量
5. T+1规则：今天买入的股票今天不能卖出

请以JSON返回你的意见，格式如下：
```json
{{"action": "BUY或SELL或HOLD", "quantity": 买卖数量(整数, HOLD时为0), "confidence": 0.0到1.0, "reasoning": "简短理由(50字以内)"}}
```"""

    def build_moderator_prompt(self, opinions: List[Dict]) -> str:
        """构建主席的裁决prompt"""
        opinions_str = ""
        for op in opinions:
            opinions_str += f"\n### {op['role_cn']}（{op['agent_name']}）\n"
            opinions_str += f"- 建议: **{op['action']}**\n"
            opinions_str += f"- 数量: {op['quantity']}股\n"
            opinions_str += f"- 置信度: {op['confidence']:.0%}\n"
            opinions_str += f"- 理由: {op['reasoning']}\n"

        # 统计意见分布
        buy_count = sum(1 for o in opinions if o["action"] == "BUY")
        sell_count = sum(1 for o in opinions if o["action"] == "SELL")
        hold_count = sum(1 for o in opinions if o["action"] == "HOLD")
        avg_confidence = {
            "BUY": sum(o["confidence"] for o in opinions if o["action"] == "BUY") / buy_count if buy_count else 0,
            "SELL": sum(o["confidence"] for o in opinions if o["action"] == "SELL") / sell_count if sell_count else 0,
            "HOLD": sum(o["confidence"] for o in opinions if o["action"] == "HOLD") / hold_count if hold_count else 0,
        }

        return f"""## 裁决任务
请审阅以下4位分析师的意见，做出最终交易决策。

## 分析师意见汇总
{opinions_str}

## 意见统计
- 看多(BUY): {buy_count}人，平均置信度 {avg_confidence['BUY']:.0%}
- 看空(SELL): {sell_count}人，平均置信度 {avg_confidence['SELL']:.0%}
- 观望(HOLD): {hold_count}人，平均置信度 {avg_confidence['HOLD']:.0%}

## 裁决要求
1. 综合各方意见和置信度做出最终决策
2. 如果风控经理明确要求止损/减仓，该意见具有一票否决权
3. 当多空分歧大时，倾向于保守（HOLD或减少交易量）
4. 最终数量应该是综合考虑后的合理值

请以JSON返回最终决策：
```json
{{"action": "BUY或SELL或HOLD", "quantity": 买卖数量(整数, HOLD时为0), "confidence": 0.0到1.0, "reasoning": "裁决理由(80字以内,说明如何综合各方意见)"}}
```"""


class MultiAgentSystem:
    """多智能体辩论交易决策系统"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.client: Optional[httpx.AsyncClient] = None
        self.use_mock = not bool(self.api_key)

        # 初始化5个智能体
        self.agents = {
            role: Agent(role) for role in AgentRole
        }

        if self.use_mock:
            logger.warning("未配置DEEPSEEK_API_KEY，多智能体系统将使用模拟决策")

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

    async def debate(
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
        多智能体辩论，返回辩论结果。

        Returns:
            {
                "debate_id": str,
                "opinions": [每个分析师的意见],
                "final_decision": {最终裁决},
            }
        """
        debate_id = datetime.now().strftime("%Y%m%d%H%M%S") + f"_{stock_code}_{uuid.uuid4().hex[:6]}"

        if self.use_mock:
            return await self._mock_debate(
                debate_id, stock_code, stock_name, current_price,
                price_history, cash, position_qty, position_avg_cost
            )

        # ── 阶段1：4个分析师并行分析 ──
        analyst_roles = [AgentRole.BULL, AgentRole.BEAR, AgentRole.TECH, AgentRole.RISK]
        tasks = []
        for role in analyst_roles:
            agent = self.agents[role]
            prompt = agent.build_analyst_prompt(
                stock_code, stock_name, current_price, price_history,
                cash, position_qty, position_avg_cost
            )
            tasks.append(self._call_agent(agent, prompt, current_price, cash, position_qty))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        opinions = []
        for i, role in enumerate(analyst_roles):
            agent = self.agents[role]
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"智能体 {agent.role_cn} 分析失败: {result}")
                opinions.append({
                    "agent_name": agent.name,
                    "role_cn": agent.role_cn,
                    "action": "HOLD",
                    "quantity": 0,
                    "confidence": 0.2,
                    "reasoning": f"分析失败，保守观望",
                })
            else:
                result["agent_name"] = agent.name
                result["role_cn"] = agent.role_cn
                opinions.append(result)

        # ── 阶段2：主席裁决 ──
        moderator = self.agents[AgentRole.MODERATOR]
        moderator_prompt = moderator.build_moderator_prompt(opinions)

        try:
            final = await self._call_agent(moderator, moderator_prompt, current_price, cash, position_qty)
            final["agent_name"] = moderator.name
            final["role_cn"] = moderator.role_cn
        except Exception as e:
            logger.error(f"主席裁决失败: {e}")
            # 降级：取多数意见
            final = self._fallback_decision(opinions, current_price, cash, position_qty)
            final["agent_name"] = moderator.name
            final["role_cn"] = moderator.role_cn

        return {
            "debate_id": debate_id,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "opinions": opinions,
            "final_decision": final,
        }

    async def _call_agent(
        self, agent: Agent, prompt: str,
        current_price: float, cash: float, position_qty: int
    ) -> Dict:
        """调用AI获取单个智能体的意见"""
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": agent.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 500,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return self._parse_response(content, current_price, cash, position_qty)

    def _parse_response(self, content: str, current_price: float, cash: float, position_qty: int) -> Dict:
        """解析AI返回的JSON"""
        try:
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
                    reasoning = "资金不足买入1手，改为持有观望"
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

    def _fallback_decision(self, opinions: List[Dict], current_price: float, cash: float, position_qty: int) -> Dict:
        """主席裁决失败时的降级逻辑：简单多数投票"""
        from collections import Counter
        vote_counts = Counter(o["action"] for o in opinions if o["agent_name"] != "moderator")

        # 加权投票（置信度加权）
        weighted = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        for o in opinions:
            if o["agent_name"] != "moderator":
                weighted[o["action"]] += o["confidence"]

        # 风控否决权：如果风控要求SELL且置信度>0.7，则执行
        risk_opinion = next((o for o in opinions if o["agent_name"] == "risk"), None)
        if risk_opinion and risk_opinion["action"] == "SELL" and risk_opinion["confidence"] > 0.7:
            action = "SELL"
            quantity = min(risk_opinion.get("quantity", 100), position_qty)
            reasoning = "风控要求止损，执行卖出"
        else:
            action = max(weighted, key=weighted.get)
            if action == "BUY":
                quantity = int(cash / current_price / 100) * 100
                quantity = min(quantity, 300)
                if quantity < 100:
                    action = "HOLD"
                    quantity = 0
                reasoning = f"多数看多(加权分{weighted['BUY']:.2f})，买入"
            elif action == "SELL":
                quantity = min(100, position_qty)
                reasoning = f"多数看空(加权分{weighted['SELL']:.2f})，卖出"
            else:
                quantity = 0
                reasoning = f"意见分歧或均倾向观望(加权分{weighted['HOLD']:.2f})，持有"

        return {
            "action": action,
            "quantity": quantity,
            "confidence": 0.5,
            "reasoning": reasoning,
        }

    # ─── Mock模式：每个智能体有独立的规则逻辑 ──────────────

    async def _mock_debate(
        self,
        debate_id: str,
        stock_code: str,
        stock_name: str,
        current_price: float,
        price_history: List[Dict],
        cash: float,
        position_qty: int,
        position_avg_cost: float,
    ) -> Dict:
        """模拟多智能体辩论"""
        if len(price_history) < 3:
            opinions = [
                {"agent_name": "bull", "role_cn": "多头分析师", "action": "HOLD", "quantity": 0, "confidence": 0.3, "reasoning": "数据不足，暂不买入"},
                {"agent_name": "bear", "role_cn": "空头分析师", "action": "HOLD", "quantity": 0, "confidence": 0.4, "reasoning": "数据不足，风险不明"},
                {"agent_name": "tech", "role_cn": "技术分析师", "action": "HOLD", "quantity": 0, "confidence": 0.3, "reasoning": "数据不足，无法分析"},
                {"agent_name": "risk", "role_cn": "风控经理", "action": "HOLD", "quantity": 0, "confidence": 0.5, "reasoning": "数据不足，保守观望"},
            ]
            final = {"agent_name": "moderator", "role_cn": "决策主席", "action": "HOLD", "quantity": 0, "confidence": 0.3, "reasoning": "数据不足，全部观望"}
            return {"debate_id": debate_id, "stock_code": stock_code, "stock_name": stock_name, "opinions": opinions, "final_decision": final}

        # 计算基础指标
        recent_changes = [h.get("change_percent", 0) for h in price_history[-5:]]
        avg_change = sum(recent_changes) / len(recent_changes)
        recent_prices = [h.get("price", current_price) for h in price_history[-10:]]
        price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100 if len(recent_prices) >= 2 else 0
        volatility = (max(recent_prices) - min(recent_prices)) / min(recent_prices) * 100 if min(recent_prices) > 0 else 0

        pnl_percent = ((current_price - position_avg_cost) / position_avg_cost * 100) if position_avg_cost > 0 else 0
        position_value = position_qty * current_price
        total_assets = cash + position_value
        position_ratio = position_value / total_assets * 100 if total_assets > 0 else 0

        # ── 多头分析师 ──
        if avg_change < -1.5 and cash >= current_price * 100:
            qty = int(cash / current_price / 100) * 100
            qty = max(100, min(qty, 500))
            bull = {"agent_name": "bull", "role_cn": "多头分析师", "action": "BUY", "quantity": qty, "confidence": 0.7, "reasoning": f"近期跌幅{avg_change:.1f}%，超跌反弹机会"}
        elif avg_change < -0.5 and cash >= current_price * 100:
            qty = int(cash / current_price / 100) * 100
            qty = max(100, min(qty, 300))
            bull = {"agent_name": "bull", "role_cn": "多头分析师", "action": "BUY", "quantity": qty, "confidence": 0.55, "reasoning": f"小幅回调{avg_change:.1f}%，可轻仓介入"}
        else:
            bull = {"agent_name": "bull", "role_cn": "多头分析师", "action": "HOLD", "quantity": 0, "confidence": 0.4, "reasoning": "未发现明显买入信号"}

        # ── 空头分析师 ──
        if avg_change > 1.5 and position_qty > 0:
            bear = {"agent_name": "bear", "role_cn": "空头分析师", "action": "SELL", "quantity": min(position_qty, 100), "confidence": 0.7, "reasoning": f"近期涨幅{avg_change:.1f}%，获利了结"}
        elif avg_change > 0.8 and position_qty > 0:
            bear = {"agent_name": "bear", "role_cn": "空头分析师", "action": "SELL", "quantity": min(position_qty, 100), "confidence": 0.5, "reasoning": f"上涨动能{avg_change:.1f}%，注意回调风险"}
        elif price_trend > 3 and position_qty > 0:
            bear = {"agent_name": "bear", "role_cn": "空头分析师", "action": "SELL", "quantity": min(position_qty, 100), "confidence": 0.6, "reasoning": f"趋势上涨{price_trend:.1f}%，谨防冲高回落"}
        else:
            bear = {"agent_name": "bear", "role_cn": "空头分析师", "action": "HOLD", "quantity": 0, "confidence": 0.4, "reasoning": "未发现明显卖出信号"}

        # ── 技术分析师 ──
        if volatility > 3:
            tech = {"agent_name": "tech", "role_cn": "技术分析师", "action": "HOLD", "quantity": 0, "confidence": 0.6, "reasoning": f"波动率{volatility:.1f}%偏高，建议观望"}
        elif price_trend > 1 and avg_change > 0:
            tech = {"agent_name": "tech", "role_cn": "技术分析师", "action": "BUY", "quantity": 100, "confidence": 0.55, "reasoning": f"上升趋势{price_trend:.1f}%，趋势延续"}
        elif price_trend < -1 and avg_change < 0:
            tech = {"agent_name": "tech", "role_cn": "技术分析师", "action": "SELL", "quantity": min(position_qty, 100), "confidence": 0.55, "reasoning": f"下降趋势{price_trend:.1f}%，趋势延续"}
        else:
            tech = {"agent_name": "tech", "role_cn": "技术分析师", "action": "HOLD", "quantity": 0, "confidence": 0.5, "reasoning": "趋势不明，技术面中性"}

        # ── 风控经理 ──
        risk_action = "HOLD"
        risk_qty = 0
        risk_conf = 0.5
        risk_reason = "仓位适中，风险可控"

        if position_ratio > 60:
            risk_action = "SELL"
            risk_qty = min(position_qty, int(position_qty * 0.3 / 100) * 100)
            risk_qty = max(risk_qty, 100) if risk_qty > 0 else 100
            risk_qty = min(risk_qty, position_qty)
            risk_conf = 0.8
            risk_reason = f"仓位占比{position_ratio:.0f}%过高，需减仓"
        elif pnl_percent < -8 and position_qty > 0:
            risk_action = "SELL"
            risk_qty = min(position_qty, 100)
            risk_conf = 0.85
            risk_reason = f"亏损{pnl_percent:.1f}%超止损线，执行止损"
        elif pnl_percent > 20 and position_qty > 0:
            risk_action = "SELL"
            risk_qty = min(position_qty, 100)
            risk_conf = 0.7
            risk_reason = f"盈利{pnl_percent:.1f}%达止盈线，部分止盈"
        elif cash < total_assets * 0.2 and position_qty > 0:
            risk_action = "SELL"
            risk_qty = min(position_qty, 100)
            risk_conf = 0.75
            risk_reason = "现金不足总资产20%，需减仓补充流动性"

        risk = {"agent_name": "risk", "role_cn": "风控经理", "action": risk_action, "quantity": risk_qty, "confidence": risk_conf, "reasoning": risk_reason}

        opinions = [bull, bear, tech, risk]

        # ── 主席裁决（模拟）──
        final = self._fallback_decision(opinions, current_price, cash, position_qty)
        final["agent_name"] = "moderator"
        final["role_cn"] = "决策主席"

        return {
            "debate_id": debate_id,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "opinions": opinions,
            "final_decision": final,
        }


# 全局实例
multi_agent = MultiAgentSystem()
