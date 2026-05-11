"""
基本面数据获取模块
使用 akshare 获取A股基本面数据，供基本面分析师智能体使用

提供的数据：
1. 个股基本信息（行业、市值、PE等）
2. 财务摘要（净利润、营收、ROE、每股收益等）
3. 资金流向（主力/超大单/大单净流入）
4. 综合评分（东方财富综合评价）
5. 股息率信息
"""
import logging
import time
from typing import Dict, Optional
from datetime import datetime

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)

# 缓存：避免重复请求（5分钟有效期）
_cache: Dict[str, dict] = {}
_CACHE_TTL = 300  # 5分钟


def _is_cache_valid(key: str) -> bool:
    if key not in _cache:
        return False
    return (time.time() - _cache[key].get("_ts", 0)) < _CACHE_TTL


def _set_cache(key: str, data: dict):
    data["_ts"] = time.time()
    _cache[key] = data


def _convert_stock_code(stock_code: str) -> tuple:
    """将6位股票代码转换为akshare需要的格式，返回 (symbol, market)"""
    if stock_code.startswith("6"):
        return stock_code, "sh"
    elif stock_code.startswith(("0", "3")):
        return stock_code, "sz"
    elif stock_code.startswith("4") or stock_code.startswith("8"):
        return stock_code, "bj"
    return stock_code, "sz"


def fetch_fundamental_data(stock_code: str) -> Dict:
    """
    获取单只股票的基本面综合数据

    Returns:
        {
            "basic_info": {...},       # 基本信息
            "financial_summary": {...}, # 财务摘要
            "fund_flow": {...},         # 资金流向
            "comment_score": {...},     # 综合评分
        }
    """
    cache_key = f"fundamental_{stock_code}"
    if _is_cache_valid(cache_key):
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    result = {
        "basic_info": {},
        "financial_summary": {},
        "fund_flow": {},
        "comment_score": {},
    }

    symbol, market = _convert_stock_code(stock_code)

    # 1. 基本信息
    try:
        info_df = ak.stock_individual_info_em(symbol=stock_code)
        if info_df is not None and not info_df.empty:
            result["basic_info"] = dict(zip(info_df["item"], info_df["value"]))
    except Exception as e:
        logger.warning(f"获取 {stock_code} 基本信息失败: {e}")

    # 2. 财务摘要（最新2期）
    try:
        fin_df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")
        if fin_df is not None and not fin_df.empty:
            # 数据是按时间正序排列，取最后2条（最新报告期）
            latest = fin_df.tail(2)
            summaries = []
            for _, row in latest.iterrows():
                summaries.append({
                    "report_date": str(row.get("报告期", "")),
                    "net_profit": str(row.get("净利润", "")),
                    "net_profit_yoy": str(row.get("净利润同比增长率", "")),
                    "revenue": str(row.get("营业总收入", "")),
                    "revenue_yoy": str(row.get("营业总收入同比增长率", "")),
                    "eps": str(row.get("基本每股收益", "")),
                    "bps": str(row.get("每股净资产", "")),
                    "cfps": str(row.get("每股经营现金流", "")),
                    "roe": str(row.get("净资产收益率", "")),
                    "gross_margin": str(row.get("销售净利率", "")),
                    "debt_ratio": str(row.get("资产负债率", "")),
                    "current_ratio": str(row.get("流动比率", "")),
                })
            result["financial_summary"] = summaries
    except Exception as e:
        logger.warning(f"获取 {stock_code} 财务摘要失败: {e}")

    # 3. 资金流向（最近5日）
    try:
        flow_df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
        if flow_df is not None and not flow_df.empty:
            recent = flow_df.tail(5)
            flows = []
            for _, row in recent.iterrows():
                flows.append({
                    "date": str(row.get("日期", "")),
                    "close": float(row.get("收盘价", 0)),
                    "change_pct": str(row.get("涨跌幅", "")),
                    "main_net_inflow": float(row.get("主力净流入-净额", 0)),
                    "main_net_pct": float(row.get("主力净流入-净占比", 0)),
                    "huge_net_inflow": float(row.get("超大单净流入-净额", 0)),
                    "big_net_inflow": float(row.get("大单净流入-净额", 0)),
                })
            result["fund_flow"] = flows
    except Exception as e:
        logger.warning(f"获取 {stock_code} 资金流向失败: {e}")

    # 4. 综合评分
    try:
        score_df = ak.stock_comment_detail_zhpj_lspf_em(symbol=stock_code)
        if score_df is not None and not score_df.empty:
            recent = score_df.tail(5)
            scores = []
            for _, row in recent.iterrows():
                scores.append({
                    "date": str(row.get("交易日", "")),
                    "score": float(row.get("评分", 0)),
                })
            result["comment_score"] = scores
    except Exception as e:
        logger.warning(f"获取 {stock_code} 综合评分失败: {e}")

    _set_cache(cache_key, result)
    return result


def format_fundamental_for_prompt(fundamental: Dict) -> str:
    """将基本面数据格式化为智能体可读的文本"""

    parts = []

    # 基本信息
    basic = fundamental.get("basic_info", {})
    if basic:
        parts.append("### 公司基本信息")
        # 选择关键字段
        key_fields = {
            "股票简称": "名称",
            "行业": "行业",
            "总市值": "总市值",
            "流通市值": "流通市值",
            "总股本": "总股本",
            "流通股": "流通股",
        }
        for k, label in key_fields.items():
            if k in basic:
                val = basic[k]
                # 格式化大数字
                if k in ("总市值", "流通市值") and isinstance(val, (int, float)):
                    val = f"¥{val/1e8:.1f}亿"
                elif k in ("总股本", "流通股") and isinstance(val, (int, float)):
                    val = f"{val/1e8:.2f}亿股"
                parts.append(f"- {label}: {val}")

    # 财务摘要
    financial = fundamental.get("financial_summary", [])
    if financial:
        parts.append("\n### 财务数据（最近报告期）")
        for i, report in enumerate(financial):
            label = "最新" if i == 0 else "上期"
            parts.append(f"\n**{label} ({report.get('report_date', '')})**")
            if report.get("net_profit"):
                parts.append(f"- 净利润: {report['net_profit']}")
            if report.get("net_profit_yoy") and report["net_profit_yoy"] != "False":
                parts.append(f"- 净利润同比: {report['net_profit_yoy']}")
            if report.get("revenue"):
                parts.append(f"- 营收: {report['revenue']}")
            if report.get("revenue_yoy") and report["revenue_yoy"] != "False":
                parts.append(f"- 营收同比: {report['revenue_yoy']}")
            if report.get("eps") and report["eps"] != "False":
                parts.append(f"- 每股收益: {report['eps']}元")
            if report.get("bps") and report["bps"] != "False":
                parts.append(f"- 每股净资产: {report['bps']}元")
            if report.get("cfps") and report["cfps"] != "False":
                parts.append(f"- 每股经营现金流: {report['cfps']}元")
            if report.get("roe") and report["roe"] != "False":
                parts.append(f"- ROE: {report['roe']}")
            if report.get("debt_ratio") and report["debt_ratio"] != "False":
                parts.append(f"- 资产负债率: {report['debt_ratio']}")
            if report.get("current_ratio") and report["current_ratio"] != "False":
                parts.append(f"- 流动比率: {report['current_ratio']}")

    # 资金流向
    flows = fundamental.get("fund_flow", [])
    if flows:
        parts.append("\n### 最近资金流向")
        for flow in flows[-3:]:  # 只显示最近3日
            main_net = flow.get("main_net_inflow", 0)
            direction = "流入" if main_net > 0 else "流出"
            parts.append(
                f"- {flow.get('date', '')}: 主力净{direction} {abs(main_net)/1e4:.0f}万 "
                f"({flow.get('main_net_pct', 0):.1f}%)"
            )
        # 计算近5日主力净流入趋势
        total_main = sum(f.get("main_net_inflow", 0) for f in flows)
        avg_main_pct = sum(f.get("main_net_pct", 0) for f in flows) / len(flows) if flows else 0
        direction = "净流入" if total_main > 0 else "净流出"
        parts.append(f"- 近{len(flows)}日主力合计{direction} {abs(total_main)/1e4:.0f}万，平均占比 {avg_main_pct:.2f}%")

    # 综合评分
    scores = fundamental.get("comment_score", [])
    if scores:
        parts.append("\n### 东方财富综合评分")
        latest_score = scores[-1] if scores else {}
        if latest_score:
            parts.append(f"- 最新评分: {latest_score.get('score', 'N/A')}/100")
        if len(scores) >= 2:
            trend = scores[-1].get("score", 0) - scores[0].get("score", 0)
            parts.append(f"- 近期趋势: {'上升' if trend > 0 else '下降'} {abs(trend):.1f}分")

    return "\n".join(parts) if parts else "暂无基本面数据"


# 全局实例
fundamental_fetcher = type("FundamentalFetcher", (), {
    "fetch": staticmethod(fetch_fundamental_data),
    "format": staticmethod(format_fundamental_for_prompt),
})()
