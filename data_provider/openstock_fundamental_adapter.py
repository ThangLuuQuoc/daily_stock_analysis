# -*- coding: utf-8 -*-
"""
OpenStock fundamental adapter (越南市场, fail-open).

与 AkshareFundamentalAdapter 保持相同的返回契约，供 DataFetcherManager 调用。
数据来源为本地 OpenStock REST 服务的公开 endpoint：
- ``GET /fundamentals/:symbol/overview``   → 估值/盈利能力/股息率/外资持股
- ``GET /stocks/:symbol/financials``        → 财报（当前 DB 未填充，见 gaps 文档）
- ``GET /stocks/:symbol/capital-flow``      → 按日外资净额（越南版「资金流」）

不适用越南市场的方法（龙虎榜）返回 not_supported 占位。

本 adapter 绝不向上抛异常，缺失数据以空 dict / None 表示。
缺口追踪见 plan/openstock_adapter_gaps.md。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from .openstock_symbols import is_vn_stock_code, normalize_vn_symbol
from .realtime_types import safe_float, safe_int

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:3000/api/v1"
_HTTP_TIMEOUT = 15


class OpenStockFundamentalAdapter:
    """越南市场基本面 / 资金流适配器（fail-open）。"""

    def __init__(self, base_url: Optional[str] = None):
        resolved = base_url
        if resolved is None:
            try:
                from src.config import get_config

                resolved = getattr(get_config(), "openstock_base_url", None)
            except Exception:
                resolved = None
        self._base_url = (resolved or _DEFAULT_BASE_URL).rstrip("/")
        self._session = requests.Session()

    # ------------------------------------------------------------------
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        url = f"{self._base_url}/{path.lstrip('/')}"
        try:
            resp = self._session.get(url, params=params, timeout=_HTTP_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.debug("[OpenStock] 请求失败 %s: %s", url, exc)
            return None

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    # ------------------------------------------------------------------
    def get_fundamental_bundle(self, stock_code: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status": "not_supported",
            "growth": {},
            "earnings": {},
            "institution": {},
            "source_chain": [],
            "errors": [],
        }
        if not is_vn_stock_code(stock_code):
            return result

        symbol = normalize_vn_symbol(stock_code)

        # YoY / 毛利率 现在可从 financials 年报序列算出（financial_statements 已填充，
        # 见 openstock_adapter_gaps.md item 1 —— 该 gap 已关闭）。
        growth_from_fs = self._compute_growth_from_financials(symbol)

        overview = self._get(f"/fundamentals/{symbol}/overview")
        if isinstance(overview, dict):
            roe = safe_float(overview.get("roe"))
            result["growth"] = {
                "revenue_yoy": growth_from_fs.get("revenue_yoy"),
                "net_profit_yoy": growth_from_fs.get("net_profit_yoy"),
                "roe": round(roe * 100, 4) if roe is not None else None,  # 比例→百分比
                "gross_margin": growth_from_fs.get("gross_margin"),
            }
            div_yield = safe_float(overview.get("dividendYield"))
            if div_yield is not None and div_yield > 0:
                result["earnings"]["dividend"] = {
                    "dividend_yield": round(div_yield * 100, 4),
                    "coverage": "dividend_yield_only",
                    "as_of": (overview.get("priceDate") or "")[:10] or None,
                }
            # 外资持股快照（越南特有），归入 institution 块
            foreign_owned = safe_float(overview.get("foreignOwnedPct"))
            foreign_room = safe_float(overview.get("foreignRoomLeftPct"))
            if foreign_owned is not None or foreign_room is not None:
                result["institution"]["foreign_ownership"] = {
                    "foreign_owned_pct": foreign_owned,
                    "foreign_room_left_pct": foreign_room,
                }
            result["source_chain"].append("overview:openstock")

        # 财报（income + cashflow）
        report = self._fetch_financial_report(symbol)
        if report:
            result["earnings"]["financial_report"] = report
            result["source_chain"].append("financials:openstock")
        else:
            result["errors"].append("financials:empty")

        has_content = bool(result["growth"] or result["earnings"] or result["institution"])
        result["status"] = "partial" if has_content else "not_supported"
        return result

    def _fetch_statements(self, symbol: str, statement: str, freq: str) -> list:
        """取某类报表的期序列（OpenStock 按 periodEndDate 倒序返回，最新在前）。"""
        payload = self._get(
            f"/stocks/{symbol}/financials",
            params={"statement": statement, "freq": freq},
        )
        data = self._unwrap(payload)
        statements = data.get("statements") if isinstance(data, dict) else None
        return statements if isinstance(statements, list) else []

    def _compute_growth_from_financials(self, symbol: str) -> Dict[str, Any]:
        """
        用年报序列算 YoY 与毛利率。

        为什么用年报而不是季报：季报存在季节性，相邻两期相比会失真；而 OpenStock
        的年报序列已按 periodEndDate 倒序，取 [0] 与 [1] 即最近两个完整年度。

        银行没有毛利率概念（后端 grossProfit 返回 null），此处保持 None 而不是填 0。
        """
        out: Dict[str, Any] = {
            "revenue_yoy": None,
            "net_profit_yoy": None,
            "gross_margin": None,
        }
        rows = self._fetch_statements(symbol, "income", "annual")
        if len(rows) < 1:
            return out

        cur = rows[0] if isinstance(rows[0], dict) else {}
        rev_cur = safe_float(cur.get("revenue"))
        np_cur = safe_float(cur.get("netProfit"))
        gp_cur = safe_float(cur.get("grossProfit"))

        if rev_cur and gp_cur is not None and rev_cur != 0:
            out["gross_margin"] = round(gp_cur / rev_cur * 100, 4)

        if len(rows) >= 2 and isinstance(rows[1], dict):
            prev = rows[1]
            rev_prev = safe_float(prev.get("revenue"))
            np_prev = safe_float(prev.get("netProfit"))
            # 分母为负或 0 时 YoY 无意义（亏损转盈等），宁可留 None 不给误导性数字
            if rev_cur is not None and rev_prev and rev_prev > 0:
                out["revenue_yoy"] = round((rev_cur - rev_prev) / rev_prev * 100, 4)
            if np_cur is not None and np_prev and np_prev > 0:
                out["net_profit_yoy"] = round((np_cur - np_prev) / np_prev * 100, 4)

        return out

    def _fetch_financial_report(self, symbol: str) -> Dict[str, Any]:
        """最近一期季报：营收 / 归母净利 / 经营现金流。"""
        rows = self._fetch_statements(symbol, "income", "quarterly")
        if not rows or not isinstance(rows[0], dict):
            return {}
        latest = rows[0]

        # 经营现金流在 cashflow 报表里，需另取一次
        ocf = None
        cf_rows = self._fetch_statements(symbol, "cashflow", "quarterly")
        if cf_rows and isinstance(cf_rows[0], dict):
            ocf = safe_float(cf_rows[0].get("operatingCashFlow"))

        return {
            "report_date": latest.get("date") or latest.get("period"),
            "revenue": safe_float(latest.get("revenue")),
            "net_profit_parent": safe_float(
                latest.get("netProfit") or latest.get("netIncome")
            ),
            "operating_cash_flow": ocf,
            "roe": None,
        }

    # ------------------------------------------------------------------
    def get_capital_flow(self, stock_code: str, top_n: int = 5) -> Dict[str, Any]:
        """越南资金流 = 按日外资净额（foreignNet）。"""
        result: Dict[str, Any] = {
            "status": "not_supported",
            "stock_flow": {},
            "sector_rankings": {"top": [], "bottom": []},
            "source_chain": [],
            "errors": [],
        }
        if not is_vn_stock_code(stock_code):
            return result

        symbol = normalize_vn_symbol(stock_code)
        payload = self._get(f"/stocks/{symbol}/capital-flow", params={"days": 20})
        rows = self._unwrap(payload)
        if not isinstance(rows, list) or not rows:
            result["errors"].append("capital_flow:empty")
            return result

        foreign_values = [
            safe_float(r.get("foreignNet"))
            for r in rows
            if isinstance(r, dict) and r.get("foreignNet") is not None
        ]
        foreign_values = [v for v in foreign_values if v is not None]
        if foreign_values:
            result["stock_flow"] = {
                # 越南无「主力资金」口径，用外资净额近似填充该字段
                "main_net_inflow": foreign_values[-1],
                "foreign_net_latest": foreign_values[-1],
                "foreign_net_sum": round(sum(foreign_values), 2),
                "days": len(foreign_values),
                "currency": "VND",
            }
            result["source_chain"].append("capital_flow:openstock")

        has_content = bool(result["stock_flow"])
        result["status"] = "partial" if has_content else "not_supported"
        return result

    # ------------------------------------------------------------------
    def get_dragon_tiger_flag(self, stock_code: str, lookback_days: int = 20) -> Dict[str, Any]:
        """龙虎榜为中国市场特有，越南市场不适用。"""
        return {
            "status": "not_supported",
            "is_on_list": False,
            "recent_count": 0,
            "latest_date": None,
            "source_chain": [],
            "errors": ["dragon_tiger:not_applicable_vn"],
        }
