"""
股票数据获取模块 - 使用akshare获取A股实时数据
"""
import akshare as ak
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class StockDataFetcher:
    def __init__(self):
        self.cache: Dict[str, Dict] = {}  # stock_code -> latest data

    def fetch_realtime(self, stock_code: str) -> Optional[Dict]:
        """获取单只股票的实时数据"""
        try:
            df = ak.stock_zh_a_spot()
            possible_codes = self._normalize_code(stock_code)

            for code in possible_codes:
                row = df[df['代码'] == code]
                if not row.empty:
                    r = row.iloc[0]
                    data = {
                        'stock_code': stock_code,
                        'name': str(r.get('名称', '')),
                        'price': float(r.get('最新价', 0)),
                        'open': float(r.get('今开', 0)),
                        'high': float(r.get('最高', 0)),
                        'low': float(r.get('最低', 0)),
                        'prev_close': float(r.get('昨收', 0)),
                        'volume': int(r.get('成交量', 0)),
                        'change': float(r.get('涨跌额', 0)),
                        'change_percent': float(r.get('涨跌幅', 0)),
                        'timestamp': datetime.now().isoformat(),
                    }
                    self.cache[stock_code] = data
                    return data

            logger.warning(f"未找到股票: {stock_code}")
            return None
        except Exception as e:
            logger.error(f"获取股票数据失败 {stock_code}: {e}")
            return None

    def fetch_batch(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """批量获取多只股票的实时数据"""
        if not stock_codes:
            return {}
        try:
            df = ak.stock_zh_a_spot()
            results = {}
            for stock_code in stock_codes:
                possible_codes = self._normalize_code(stock_code)
                for code in possible_codes:
                    row = df[df['代码'] == code]
                    if not row.empty:
                        r = row.iloc[0]
                        data = {
                            'stock_code': stock_code,
                            'name': str(r.get('名称', '')),
                            'price': float(r.get('最新价', 0)),
                            'open': float(r.get('今开', 0)),
                            'high': float(r.get('最高', 0)),
                            'low': float(r.get('最低', 0)),
                            'prev_close': float(r.get('昨收', 0)),
                            'volume': int(r.get('成交量', 0)),
                            'change': float(r.get('涨跌额', 0)),
                            'change_percent': float(r.get('涨跌幅', 0)),
                            'timestamp': datetime.now().isoformat(),
                        }
                        results[stock_code] = data
                        self.cache[stock_code] = data
                        break
            return results
        except Exception as e:
            logger.error(f"批量获取数据失败: {e}")
            return {}

    def get_cached(self, stock_code: str) -> Optional[Dict]:
        """获取缓存数据"""
        return self.cache.get(stock_code)

    def get_all_cached_prices(self) -> Dict[str, float]:
        """获取所有缓存中的最新价格"""
        return {code: d['price'] for code, d in self.cache.items() if d.get('price')}

    def _normalize_code(self, stock_code: str) -> List[str]:
        """规范化股票代码"""
        if stock_code.startswith(('sz', 'sh', 'bj')):
            return [stock_code]
        return [f"sz{stock_code}", f"sh{stock_code}", stock_code]


fetcher = StockDataFetcher()
