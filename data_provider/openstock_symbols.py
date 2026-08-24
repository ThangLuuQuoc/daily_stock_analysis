# -*- coding: utf-8 -*-
"""
越南市场代码识别工具 (OpenStock adapter 专用)

OpenStock 提供越南三大交易所数据：HOSE / HNX / UPCOM。

判定策略（按优先级）：
1. **symbol universe**（首选）—— 向 OpenStock ``GET /stocks`` 拉取全量代码表并
   缓存。这是唯一准确的判定方式：既不会把 3 字母美股（IBM/AMD/KEY）误判成越南
   标的，也不会漏掉非 3 字母的真实越南标的（ETF ``FUEVFVND`` / ``E1VFVN30``、
   衍生品 ``VN30F2409``）。
2. **正则回退** —— universe 不可用时（OpenStock 未启动 / 旧版本没有该 endpoint）
   退回原来的保守正则。此时上述误判/漏判风险仍然存在，属于已知降级行为。

设计原则：
- 仅在“高置信度是越南标的”时返回 True，避免误抢 A 股 / 美股代码的路由。
- 缓存失败一律 fail-open（回退正则），绝不因为网络问题让整条分析链路挂掉。
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Optional, Set

logger = logging.getLogger(__name__)

# 越南主要指数代码（OpenStock 内部使用的符号）
# Phải khớp với danh sách INDICES của syncIndexWorker.ts bên OpenStock —
# index nào không được sync thì adapter nhận mã hợp lệ rồi query rỗng.
VN_INDEX_MAPPING = {
    "VNINDEX": "VN-Index (HOSE)",
    "VN30": "VN30",
    "VN100": "VN100",
    "HNXINDEX": "HNX-Index",
    "UPCOMINDEX": "UPCOM-Index",
}

# 3 个大写字母的普通股代码（HOSE/HNX/UPCOM 绝大多数标的）
_VN_TICKER_RE = re.compile(r"^[A-Z]{3}$")

# 衍生品 / 权证等带数字后缀的代码（如 CFPT1901），保守起见也识别为越南标的
_VN_DERIVATIVE_RE = re.compile(r"^[A-Z]{2,4}[0-9]{2,6}$")

# ---------------------------------------------------------------------------
# Symbol universe cache
# ---------------------------------------------------------------------------
_UNIVERSE_TTL_SECONDS = 6 * 3600  # 上市/退市才会变，半天刷新一次足够
_HTTP_TIMEOUT = 10

_universe_lock = threading.Lock()
_universe: Optional[Set[str]] = None
_universe_fetched_at: float = 0.0
# 拉取失败后的静默期，避免每次判定都去撞一个挂掉的服务
_universe_failed_at: float = 0.0
_FAILURE_BACKOFF_SECONDS = 60


def normalize_vn_symbol(stock_code: str) -> str:
    """统一格式：去空白、转大写。"""
    return str(stock_code or "").strip().upper()


def is_vn_index_code(stock_code: str) -> bool:
    """是否为越南主要指数代码。"""
    return normalize_vn_symbol(stock_code) in VN_INDEX_MAPPING


def _fetch_universe() -> Optional[Set[str]]:
    """从 OpenStock ``GET /stocks`` 拉取全量代码表。失败返回 None。"""
    try:
        from src.config import get_config

        config = get_config()
        if not getattr(config, "openstock_enabled", False):
            return None
        base_url = (getattr(config, "openstock_base_url", "") or "").rstrip("/")
        if not base_url:
            return None
    except Exception as exc:
        logger.debug("[OpenStock] 读取配置失败，无法拉取代码表: %s", exc)
        return None

    try:
        import requests

        resp = requests.get(f"{base_url}/stocks", timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.warning("[OpenStock] 拉取代码表失败，回退正则判定: %s", exc)
        return None

    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        logger.warning("[OpenStock] 代码表为空，回退正则判定")
        return None

    symbols = {
        normalize_vn_symbol(row.get("symbol"))
        for row in rows
        if isinstance(row, dict) and row.get("symbol")
    }
    symbols.discard("")
    if not symbols:
        return None

    logger.info("[OpenStock] 代码表已缓存：%d 个越南标的", len(symbols))
    return symbols


def get_vn_universe(*, force_refresh: bool = False) -> Optional[Set[str]]:
    """返回缓存的越南代码表；不可用时返回 None（调用方回退正则）。"""
    global _universe, _universe_fetched_at, _universe_failed_at

    now = time.time()
    with _universe_lock:
        if not force_refresh:
            if _universe is not None and (now - _universe_fetched_at) < _UNIVERSE_TTL_SECONDS:
                return _universe
            if _universe is None and (now - _universe_failed_at) < _FAILURE_BACKOFF_SECONDS:
                return None

        fetched = _fetch_universe()
        if fetched is None:
            _universe_failed_at = time.time()
            return _universe  # 有旧缓存就继续用旧的，没有则 None
        _universe = fetched
        _universe_fetched_at = time.time()
        _universe_failed_at = 0.0
        return _universe


def reset_vn_universe_cache() -> None:
    """清空缓存（测试用）。"""
    global _universe, _universe_fetched_at, _universe_failed_at
    with _universe_lock:
        _universe = None
        _universe_fetched_at = 0.0
        _universe_failed_at = 0.0


def _matches_vn_pattern(code: str) -> bool:
    """保守正则判定（universe 不可用时的降级路径）。"""
    return bool(_VN_TICKER_RE.match(code) or _VN_DERIVATIVE_RE.match(code))


def is_vn_stock_code(stock_code: str) -> bool:
    """
    判断是否为越南市场标的代码。

    优先查 OpenStock 代码表（准确）；代码表不可用时回退保守正则（可能误判 3 字母
    美股、漏判 ETF/衍生品，属已知降级行为，见模块 docstring）。
    """
    code = normalize_vn_symbol(stock_code)
    if not code:
        return False
    if code.isdigit():
        return False
    if is_vn_index_code(code):
        return True

    universe = get_vn_universe()
    if universe is not None:
        return code in universe

    return _matches_vn_pattern(code)
