# -*- coding: utf-8 -*-
"""
OpenStockFetcher — 越南市场数据源 (Priority 0，仅越南标的)

数据来源：本地运行的 OpenStock REST 服务（Bun/Elysia），默认
``http://localhost:3000/api/v1``。该服务提供 HOSE/HNX/UPCOM 三大交易所数据。

实现范围：
- ``_fetch_raw_data``     → ``GET /stocks/:symbol/candles?from&to``
- ``get_realtime_quote``  → ``GET /stock/quote?enrich=true``（一次调用拿全量字段）
- ``get_stock_name``      → ``GET /search?q=``
- ``get_main_indices``    → ``GET /dashboard/market/overview``
- ``get_market_stats``    → ``GET /dashboard/market/overview``（breadth）
- ``get_sector_rankings`` → ``GET /dashboard/market/overview``（sectorLeadership）
- ``get_hot_stocks``      → ``GET /dashboard/market/leaders``
- ``get_limit_up_pool``   → ``GET /dashboard/market/ceiling-floor``（越南涨跌停 = 价格触及天花板/地板）

中国市场特有的方法（龙虎榜、筹码分布、概念板块）不适用越南市场，
保持基类默认（返回 None）。缺口与后续计划见 plan/openstock_adapter_gaps.md。

单位说明（重要）：
- 价格（open/high/low/close）单位为「千越南盾」（71 == 71,000 VND），历史与
  实时口径一致。
- 成交额 ``value`` / 市值 ``marketCap`` 为完整 VND。
- candle 接口当前 ``amount`` 多为 null，历史成交额以 ``close * volume`` 估算
  （见 gaps 文档 item 5）。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

from .base import BaseFetcher, DataFetchError, STANDARD_COLUMNS
from .realtime_types import (
    RealtimeSource,
    UnifiedRealtimeQuote,
    safe_float,
    safe_int,
)
from .openstock_symbols import is_vn_stock_code, normalize_vn_symbol

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:3000/api/v1"
_HTTP_TIMEOUT = 15


class OpenStockFetcher(BaseFetcher):
    name = "OpenStockFetcher"
    priority = 0  # 越南标的最高优先级（仅处理越南标的，其余直接放行）

    def __init__(self):
        base_url = _DEFAULT_BASE_URL
        enabled = False
        try:
            from src.config import get_config

            config = get_config()
            base_url = getattr(config, "openstock_base_url", None) or _DEFAULT_BASE_URL
            enabled = bool(getattr(config, "openstock_enabled", False))
        except Exception as exc:  # 配置不可用时退回默认值，便于独立测试
            logger.debug("[OpenStock] 读取配置失败，使用默认 base_url: %s", exc)

        self._base_url = base_url.rstrip("/")
        self._enabled = enabled
        self._session = requests.Session()
        if not self._enabled:
            logger.debug("[OpenStock] 未启用（OPENSTOCK_ENABLED=false），仅在显式调用时生效")

    # ------------------------------------------------------------------
    # 内部 HTTP 工具
    # ------------------------------------------------------------------
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        try:
            resp = self._session.get(url, params=params, timeout=_HTTP_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise DataFetchError(f"[OpenStock] 请求失败 {url}: {exc}") from exc

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        """OpenStock 大部分 endpoint 用 ``{\"data\": ...}`` 包裹，统一解包。"""
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def _is_vn(self, stock_code: str) -> bool:
        return is_vn_stock_code(stock_code)

    # ------------------------------------------------------------------
    # 历史日线
    # ------------------------------------------------------------------
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        if not self._is_vn(stock_code):
            raise DataFetchError(f"[OpenStock] {stock_code} 非越南市场标的")

        symbol = normalize_vn_symbol(stock_code)
        payload = self._get(
            f"/stocks/{symbol}/candles",
            params={"from": start_date, "to": end_date},
        )
        rows = self._unwrap(payload)
        if not isinstance(rows, list) or not rows:
            raise DataFetchError(f"[OpenStock] {symbol} 在 {start_date}~{end_date} 无日线数据")

        df = pd.DataFrame(rows)
        if "time" not in df.columns:
            raise DataFetchError(f"[OpenStock] {symbol} 日线数据缺少 time 字段")
        return df

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["code"] + STANDARD_COLUMNS)

        df = df.copy()
        # time 为 unix 秒
        df["date"] = pd.to_datetime(df["time"], unit="s").dt.date
        df = df.sort_values("date", ascending=True).reset_index(drop=True)

        for col in ("open", "high", "low", "close", "volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["pct_chg"] = (df["close"].pct_change() * 100).fillna(0).round(2)

        # OpenStock candle 的 amount 部分为 null（仅近端交易日填充真实成交额，单位为
        # 完整 VND）。缺失时用 close*volume 估算——注意 close 单位为「千 VND」，故乘
        # 1000 使估算值与真实 amount 的完整 VND 口径一致（见 gaps 文档 item 5）。
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        else:
            df["amount"] = pd.NA
        est_amount = df["close"] * df["volume"] * 1000
        df["amount"] = df["amount"].fillna(est_amount)

        df["code"] = normalize_vn_symbol(stock_code)

        keep = ["code"] + STANDARD_COLUMNS
        return df[[c for c in keep if c in df.columns]]

    # ------------------------------------------------------------------
    # 实时行情
    # ------------------------------------------------------------------
    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        if not self._is_vn(stock_code):
            return None

        symbol = normalize_vn_symbol(stock_code)
        # ``enrich=true`` 让 OpenStock 一次返回完整字段（估值 + 52周区间 + 量比 +
        # 换手率 + 60日涨跌幅）。OpenStock 侧的 ``getEnrichedQuote()`` 就是为本
        # adapter 的 UnifiedRealtimeQuote 写的，无需再单独请求 overview。
        try:
            quote = self._unwrap(
                self._get("/stock/quote", params={"symbol": symbol, "enrich": "true"})
            )
        except DataFetchError as exc:
            logger.warning("[OpenStock] 实时行情失败 %s: %s", symbol, exc)
            return None

        if not isinstance(quote, dict) or quote.get("price") is None:
            return None

        price = safe_float(quote.get("price"))
        pre_close = safe_float(quote.get("previousClose"))
        high = safe_float(quote.get("high"))
        low = safe_float(quote.get("low"))

        # 振幅(%) = (最高 - 最低) / 昨收 * 100
        amplitude = None
        if high is not None and low is not None and pre_close:
            amplitude = round((high - low) / pre_close * 100, 2)

        # enrich 字段缺失时（服务端旧版本或 enrich 未生效）回退到 overview，
        # 保持向后兼容而不是直接丢字段。
        pe = safe_float(quote.get("peRatio"))
        pb = safe_float(quote.get("pbRatio"))
        total_mv = safe_float(quote.get("marketCap"))
        turnover_rate = safe_float(quote.get("turnoverRatio"))
        if pe is None and pb is None and total_mv is None:
            pe, pb, total_mv, turnover_rate = self._fetch_valuation_fallback(
                symbol, safe_float(quote.get("volume"))
            )

        provider_ts = None
        ts = safe_int(quote.get("timestamp"))
        if ts:
            provider_ts = datetime.utcfromtimestamp(ts).isoformat()

        return UnifiedRealtimeQuote(
            code=symbol,
            source=RealtimeSource.OPENSTOCK,
            provider_timestamp=provider_ts,
            price=price,
            change_pct=safe_float(quote.get("percentChange")),
            change_amount=safe_float(quote.get("change")),
            volume=safe_int(quote.get("volume")),
            amount=safe_float(quote.get("value")),
            volume_ratio=safe_float(quote.get("volumeRatio")),
            turnover_rate=turnover_rate,
            amplitude=amplitude,
            open_price=safe_float(quote.get("open")),
            high=high,
            low=low,
            pre_close=pre_close,
            pe_ratio=pe,
            pb_ratio=pb,
            total_mv=total_mv,
            change_60d=safe_float(quote.get("change60d")),
            high_52w=safe_float(quote.get("high52w")),
            low_52w=safe_float(quote.get("low52w")),
        )

    def _fetch_valuation_fallback(self, symbol: str, volume: Optional[float]):
        """``enrich`` 不可用时用 overview 补估值字段（旧行为，保留兼容）。"""
        pe = pb = total_mv = turnover_rate = None
        try:
            overview = self._get(f"/fundamentals/{symbol}/overview")
        except DataFetchError as exc:
            logger.debug("[OpenStock] overview 补充失败 %s: %s", symbol, exc)
            return pe, pb, total_mv, turnover_rate

        if isinstance(overview, dict):
            pe = safe_float(overview.get("peRatio"))
            pb = safe_float(overview.get("pbRatio"))
            total_mv = safe_float(overview.get("marketCap"))
            shares = safe_float(overview.get("sharesOutstanding"))
            if shares and volume is not None:
                turnover_rate = round(volume / shares * 100, 4)
        return pe, pb, total_mv, turnover_rate

    # ------------------------------------------------------------------
    # 股票名称
    # ------------------------------------------------------------------
    def get_stock_name(self, stock_code: str) -> Optional[str]:
        if not self._is_vn(stock_code):
            return None

        symbol = normalize_vn_symbol(stock_code)
        try:
            payload = self._get("/search", params={"q": symbol})
        except DataFetchError as exc:
            logger.debug("[OpenStock] 名称查询失败 %s: %s", symbol, exc)
            return None

        results = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return None
        for item in results:
            if isinstance(item, dict) and normalize_vn_symbol(item.get("symbol")) == symbol:
                name = item.get("name")
                if name:
                    return str(name)
        return None

    # ------------------------------------------------------------------
    # Chỉ số thị trường (cho market review thị trường Việt Nam)
    # ------------------------------------------------------------------
    _VN_INDEX_NAMES = {
        "VNINDEX": "VN-Index",
        "VN30": "VN30",
        "VN100": "VN100",
        "HNXINDEX": "HNX-Index",
        "UPCOMINDEX": "UPCOM-Index",
    }

    def get_main_indices(self, region: str = "cn"):
        """Chỉ số chính thị trường Việt Nam (chỉ phục vụ region 'vn').

        Lấy VN-Index từ ``/dashboard/market/overview`` của OpenStock. Các region
        khác (cn/us/hk) trả None để manager chuyển sang nguồn phù hợp.
        """
        if region != "vn":
            return None
        try:
            payload = self._get("/dashboard/market/overview")
        except DataFetchError as exc:
            logger.warning("[OpenStock] get_main_indices thất bại: %s", exc)
            return None

        data = self._unwrap(payload)
        idx = data.get("index") if isinstance(data, dict) else None
        if not isinstance(idx, dict):
            return None

        symbol = str(idx.get("symbol", "VNINDEX")).strip().upper()
        last = safe_float(idx.get("last"))
        if last is None:
            return None
        return [{
            "code": symbol,
            "name": self._VN_INDEX_NAMES.get(symbol, symbol),
            "current": last,
            "change": safe_float(idx.get("change")),
            "change_pct": safe_float(idx.get("percentChange")),
            "volume": None,
            "amount": None,
        }]

    # ------------------------------------------------------------------
    # 市场概况（越南）
    # ------------------------------------------------------------------
    def _market_overview(self) -> Optional[Dict[str, Any]]:
        """``/dashboard/market/overview`` 的解包结果（失败返回 None，fail-open）。"""
        try:
            payload = self._get("/dashboard/market/overview")
        except DataFetchError as exc:
            logger.warning("[OpenStock] market/overview 失败: %s", exc)
            return None
        data = self._unwrap(payload)
        return data if isinstance(data, dict) else None

    def get_market_stats(self) -> Optional[Dict[str, Any]]:
        """涨跌家数统计（越南）。

        来源 ``/dashboard/market/overview`` 的 ``breadth`` 块。越南没有 A 股的
        「涨停/跌停家数」口径，但有价格天花板/地板（trần/sàn），用触及价板的
        个股数近似填充 ``limit_up_count`` / ``limit_down_count``。
        """
        data = self._market_overview()
        if data is None:
            return None
        breadth = data.get("breadth")
        if not isinstance(breadth, dict):
            return None

        up = safe_int(breadth.get("advancers"))
        down = safe_int(breadth.get("decliners"))
        flat = safe_int(breadth.get("unchanged"))
        if up is None and down is None:
            return None

        liquidity = data.get("liquidity") if isinstance(data.get("liquidity"), dict) else {}
        limit_up, limit_down = self._ceiling_floor_counts()

        return {
            "up_count": up,
            "down_count": down,
            "flat_count": flat,
            "limit_up_count": limit_up,
            "limit_down_count": limit_down,
            "total_amount": safe_float(liquidity.get("todayValue")),
        }

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """行业涨跌榜（越南）。

        来源 ``sectorLeadership.all``（按平均日收益排序）。OpenStock 暂不提供
        每个行业的领涨/领跌个股，因此不填 ``top_stock``。
        """
        data = self._market_overview()
        if data is None:
            return None
        leadership = data.get("sectorLeadership")
        if not isinstance(leadership, dict):
            return None
        sectors = leadership.get("all")
        if not isinstance(sectors, list) or not sectors:
            return None

        rows = []
        for item in sectors:
            if not isinstance(item, dict):
                continue
            name = str(item.get("sector") or "").strip()
            pct = safe_float(item.get("avgReturnPct"))
            if not name or pct is None:
                continue
            rows.append({
                "name": name,
                "change_pct": pct,
                "count": safe_int(item.get("count")),
            })
        if not rows:
            return None

        rows.sort(key=lambda r: r["change_pct"], reverse=True)
        limit = max(1, int(n))
        gainers = rows[:limit]
        losers = list(reversed(rows[-limit:]))
        return gainers, losers

    def get_hot_stocks(self, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """人气股/异动榜（越南）—— ``/dashboard/market/leaders`` 的 movers 榜。"""
        try:
            payload = self._get(
                "/dashboard/market/leaders",
                params={"tab": "movers", "limit": max(1, int(n))},
            )
        except DataFetchError as exc:
            logger.warning("[OpenStock] market/leaders 失败: %s", exc)
            return None

        rows = self._unwrap(payload)
        if not isinstance(rows, list) or not rows:
            return None

        result = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            result.append({
                "code": symbol,
                "name": item.get("name") or symbol,
                "price": safe_float(item.get("price")),
                "change_pct": safe_float(item.get("percentChange")),
                "volume": safe_int(item.get("volume")),
            })
        return result or None

    def _ceiling_floor_board(self) -> Optional[Dict[str, Any]]:
        """``/dashboard/market/ceiling-floor`` 解包结果。"""
        try:
            payload = self._get("/dashboard/market/ceiling-floor")
        except DataFetchError as exc:
            logger.warning("[OpenStock] market/ceiling-floor 失败: %s", exc)
            return None
        data = self._unwrap(payload)
        return data if isinstance(data, dict) else None

    def _ceiling_floor_counts(self) -> Tuple[Optional[int], Optional[int]]:
        """触及天花板/地板的个股数（用于 get_market_stats 的涨停/跌停近似）。"""
        board = self._ceiling_floor_board()
        if board is None:
            return None, None
        ceiling = board.get("ceiling")
        floor = board.get("floor")
        up = len(ceiling) if isinstance(ceiling, list) else None
        down = len(floor) if isinstance(floor, list) else None
        return up, down

    def get_limit_up_pool(
        self,
        date: Optional[str] = None,
        n: int = 20,
    ) -> Optional[List[Dict[str, Any]]]:
        """涨停池（越南 = 触及价格天花板 trần 的个股）。

        越南三大交易所每日有固定涨跌幅上限（HOSE ±7%、HNX ±10%、UPCOM ±15%），
        价格触及上限即为「trần」，语义上对应 A 股涨停。``date`` 参数被忽略——
        OpenStock 该 endpoint 只提供当日盘面。
        """
        board = self._ceiling_floor_board()
        if board is None:
            return None
        rows = board.get("ceiling")
        if not isinstance(rows, list) or not rows:
            return None

        limit = max(1, int(n))
        result = []
        for item in rows[:limit]:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            result.append({
                "code": symbol,
                "name": item.get("name") or symbol,
                "price": safe_float(item.get("price")),
                "change_pct": safe_float(item.get("percentChange")),
                "volume": safe_int(item.get("volume")),
                "amount": safe_float(item.get("value")),
                "exchange": item.get("exchange"),
            })
        return result or None
