# -*- coding: utf-8 -*-
"""
===================================
数据源策略层 - 包初始化
===================================

本包实现策略模式管理多个数据源，实现：
1. 统一的数据获取接口
2. 自动故障切换
3. 防封禁流控策略

数据源优先级（动态调整）：
【配置了 TUSHARE_TOKEN 时】
1. TushareFetcher (Priority 0) - 🔥 最高优先级（动态提升）
2. EfinanceFetcher (Priority 0) - 同优先级
3. AkshareFetcher (Priority 1) - 来自 akshare 库
4. PytdxFetcher (Priority 2) - 来自 pytdx 库（通达信）
5. BaostockFetcher (Priority 3) - 来自 baostock 库
6. YfinanceFetcher (Priority 4) - 来自 yfinance 库

【未配置 TUSHARE_TOKEN 时】
1. EfinanceFetcher (Priority 0) - 最高优先级，来自 efinance 库
2. AkshareFetcher (Priority 1) - 来自 akshare 库
3. PytdxFetcher (Priority 2) - 来自 pytdx 库（通达信）
4. TushareFetcher (Priority 2) - 来自 tushare 库（不可用）
5. BaostockFetcher (Priority 3) - 来自 baostock 库
6. YfinanceFetcher (Priority 4) - 来自 yfinance 库
7. LongbridgeFetcher (Priority 5) - 长桥 OpenAPI（美股/港股兜底）

提示：优先级数字越小越优先，同优先级按初始化顺序排列
"""

import logging as _logging

_logger = _logging.getLogger(__name__)

from .base import BaseFetcher, DataFetcherManager

# === 可选数据源（按第三方库是否安装做容错导入）===
# 设计：部分数据源依赖较重的第三方库（efinance/akshare/tushare/...），
# 在仅使用越南市场（OpenStock）的部署中可能未安装。此处对这些可选源做
# 防御性导入：缺库时记录 debug 日志并将符号置为 None，保证 import data_provider
# 不会因缺少某个数据源依赖而整体失败。OpenStock 与纯 Python 的工具模块保持硬导入。

EfinanceFetcher = None
TencentFetcher = None
AkshareFetcher = None
is_hk_stock_code = None
TushareFetcher = None
PytdxFetcher = None
BaostockFetcher = None
YfinanceFetcher = None
LongbridgeFetcher = None
FinnhubFetcher = None
AlphaVantageFetcher = None


def _optional_import(module_attr_pairs):
    """逐个尝试导入可选数据源，缺库时跳过并返回成功导入的名字。"""
    loaded = {}
    for module_name, attrs in module_attr_pairs:
        try:
            mod = __import__(f"{__name__}.{module_name}", fromlist=list(attrs))
            for attr in attrs:
                loaded[attr] = getattr(mod, attr)
        except Exception as exc:  # ImportError 及其依赖触发的各种错误
            _logger.debug("[数据源] 跳过可选数据源 %s（依赖缺失或加载失败）: %s", module_name, exc)
    return loaded


globals().update(_optional_import([
    ("efinance_fetcher", ["EfinanceFetcher"]),
    ("tencent_fetcher", ["TencentFetcher"]),
    ("akshare_fetcher", ["AkshareFetcher", "is_hk_stock_code"]),
    ("tushare_fetcher", ["TushareFetcher"]),
    ("pytdx_fetcher", ["PytdxFetcher"]),
    ("baostock_fetcher", ["BaostockFetcher"]),
    ("yfinance_fetcher", ["YfinanceFetcher"]),
    ("longbridge_fetcher", ["LongbridgeFetcher"]),
    ("finnhub_fetcher", ["FinnhubFetcher"]),
    ("alphavantage_fetcher", ["AlphaVantageFetcher"]),
]))

# is_hk_stock_code 缺失时提供安全兜底（akshare 未安装的越南部署）
if is_hk_stock_code is None:
    def is_hk_stock_code(stock_code):  # type: ignore
        return False

# OpenStock（越南市场）与纯 Python 工具模块——必须可用
from .openstock_fetcher import OpenStockFetcher
from .openstock_fundamental_adapter import OpenStockFundamentalAdapter
from .openstock_symbols import is_vn_stock_code, is_vn_index_code, VN_INDEX_MAPPING
from .us_index_mapping import is_us_index_code, is_us_stock_code, get_us_index_yf_symbol, US_INDEX_MAPPING

__all__ = [
    'BaseFetcher',
    'DataFetcherManager',
    'EfinanceFetcher',
    'TencentFetcher',
    'AkshareFetcher',
    'TushareFetcher',
    'PytdxFetcher',
    'BaostockFetcher',
    'YfinanceFetcher',
    'LongbridgeFetcher',
    'FinnhubFetcher',
    'AlphaVantageFetcher',
    'OpenStockFetcher',
    'OpenStockFundamentalAdapter',
    'is_vn_stock_code',
    'is_vn_index_code',
    'VN_INDEX_MAPPING',
    'is_us_index_code',
    'is_us_stock_code',
    'is_hk_stock_code',
    'get_us_index_yf_symbol',
    'US_INDEX_MAPPING',
]
