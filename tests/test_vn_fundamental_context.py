# -*- coding: utf-8 -*-
"""越南标的基本面上下文（OpenStock）——回归测试。

Bug được khoá lại ở đây: trước bản fix, `get_fundamental_context` route
`us/hk/jp/kr` sang yfinance còn lại rơi vào nhánh A-share (AkShare), nên mã VN
gọi AkShare với "FPT"; `capital_flow` thì bị guard `!= "cn"` chặn.
Kết quả: `OpenStockFundamentalAdapter` là dead code — revenue_yoy / gross_margin /
operating_cash_flow và **dòng tiền khối ngoại** không bao giờ tới LLM.

Các test dưới đây assert trên context pack mà pipeline thực sự dùng, KHÔNG phải
trên adapter, nên nếu ai đó lỡ tay tháo hook thì test đỏ.
"""

import unittest
from unittest.mock import patch

from data_provider.base import DataFetcherManager


_OVERVIEW = {
    "roe": 0.2682,
    "dividendYield": 0.0215,
    "priceDate": "2026-08-22T00:00:00Z",
    "foreignOwnedPct": 48.9,
    "foreignRoomLeftPct": 0.1,
}

_INCOME = [
    {"periodEndDate": "2024-12-31", "revenue": 62_000e9, "netProfit": 9_427e9, "grossProfit": 23_380e9},
    {"periodEndDate": "2023-12-31", "revenue": 52_600e9, "netProfit": 7_788e9, "grossProfit": 19_600e9},
]
_CASHFLOW = [
    {"periodEndDate": "2024-12-31", "operatingCashFlow": 11_070e9},
]
_CAPITAL_FLOW = [
    {"time": "2026-08-20", "close": 71.0, "amount": 5.1e11, "foreignNet": -1.2e10},
    {"time": "2026-08-21", "close": 71.5, "amount": 4.8e11, "foreignNet": 3.4e10},
]


class _FakeQuote:
    pe_ratio = 18.4
    pb_ratio = 3.9
    total_mv = 105_000e9
    circ_mv = 98_000e9


def _fake_openstock_get(self, path, params=None):
    """Giả lập REST của OpenStock ở tầng `_get` của adapter."""
    if path.endswith("/overview"):
        return _OVERVIEW
    if "financial" in path or "statements" in path:
        section = (params or {}).get("section") or (params or {}).get("statement") or ""
        if "CASH" in str(section).upper() or "cash" in path:
            return {"data": _CASHFLOW}
        return {"data": _INCOME}
    if "capital-flow" in path:
        return {"data": _CAPITAL_FLOW}
    return None


class VnFundamentalContextTest(unittest.TestCase):
    def setUp(self):
        self.manager = DataFetcherManager()
        # tat cache de moi test doc lap
        patcher = patch("src.config.get_config")
        self.addCleanup(patcher.stop)
        self.get_config = patcher.start()
        cfg = self.get_config.return_value
        cfg.enable_fundamental_pipeline = True
        cfg.openstock_enabled = True
        cfg.openstock_base_url = "http://localhost:3000/api/v1"
        cfg.fundamental_stage_timeout_seconds = 30.0
        cfg.fundamental_fetch_timeout_seconds = 10.0
        cfg.fundamental_cache_ttl_seconds = 0
        cfg.fundamental_cache_max_entries = 0
        cfg.fundamental_retry_max = 1

    # ------------------------------------------------------------------
    def test_vn_code_khong_di_qua_akshare(self):
        """Mã VN phải route sang OpenStock, KHÔNG được gọi AkshareFundamentalAdapter."""
        with patch.object(self.manager, "get_realtime_quote", return_value=_FakeQuote()), \
             patch("data_provider.openstock_fundamental_adapter.OpenStockFundamentalAdapter._get",
                   _fake_openstock_get), \
             patch.object(self.manager._fundamental_adapter, "get_fundamental_bundle") as akshare_bundle:
            ctx = self.manager.get_fundamental_context("FPT")

        akshare_bundle.assert_not_called()
        self.assertEqual(ctx["market"], "vn")

    def test_growth_va_financial_report_toi_duoc_context(self):
        """revenue_yoy / net_profit_yoy / gross_margin / OCF phai co trong context pack."""
        with patch.object(self.manager, "get_realtime_quote", return_value=_FakeQuote()), \
             patch("data_provider.openstock_fundamental_adapter.OpenStockFundamentalAdapter._get",
                   _fake_openstock_get):
            ctx = self.manager.get_fundamental_context("FPT")

        growth = ctx["growth"]["data"]
        self.assertIn("revenue_yoy", growth)
        self.assertIn("net_profit_yoy", growth)
        self.assertIn("gross_margin", growth)
        # roe cua overview la ti le 0.2682 -> adapter quy doi sang %
        self.assertAlmostEqual(growth["roe"], 26.82, places=2)

        self.assertNotEqual(ctx["growth"]["status"], "not_supported")

    def test_capital_flow_khoi_ngoai_khong_bi_chan(self):
        """Guard `!= "cn"` truoc day chan hoan toan dong tien khoi ngoai cua VN."""
        with patch.object(self.manager, "get_realtime_quote", return_value=_FakeQuote()), \
             patch("data_provider.openstock_fundamental_adapter.OpenStockFundamentalAdapter._get",
                   _fake_openstock_get):
            ctx = self.manager.get_fundamental_context("FPT")

        flow = ctx["capital_flow"]
        self.assertNotEqual(flow["status"], "not_supported", "capital_flow VN bi chan lai roi")
        self.assertIn("foreign_net_latest", flow["data"].get("stock_flow", {}))

    def test_get_capital_flow_context_cho_agent_tool(self):
        """Agent tool goi truc tiep `get_capital_flow_context` -> cung phai co du lieu."""
        with patch("data_provider.openstock_fundamental_adapter.OpenStockFundamentalAdapter._get",
                   _fake_openstock_get):
            block = self.manager.get_capital_flow_context("FPT")

        self.assertNotEqual(block["status"], "not_supported")
        self.assertIn("stock_flow", block["data"])

    def test_khoi_dac_thu_trung_quoc_van_not_supported(self):
        """Dragon-tiger / boards khong ap dung VN -> khong duoc bia du lieu."""
        with patch.object(self.manager, "get_realtime_quote", return_value=_FakeQuote()), \
             patch("data_provider.openstock_fundamental_adapter.OpenStockFundamentalAdapter._get",
                   _fake_openstock_get):
            ctx = self.manager.get_fundamental_context("FPT")

        self.assertEqual(ctx["dragon_tiger"]["status"], "not_supported")
        self.assertEqual(ctx["boards"]["status"], "not_supported")

    def test_contract_giong_duong_offshore(self):
        """Caller khong duoc phai phan biet thi truong -> shape phai y het."""
        with patch.object(self.manager, "get_realtime_quote", return_value=_FakeQuote()), \
             patch("data_provider.openstock_fundamental_adapter.OpenStockFundamentalAdapter._get",
                   _fake_openstock_get):
            ctx = self.manager.get_fundamental_context("FPT")

        for key in ("market", "valuation", "growth", "earnings", "institution",
                    "capital_flow", "dragon_tiger", "boards", "belong_boards",
                    "coverage", "source_chain", "errors", "status", "elapsed_ms"):
            self.assertIn(key, ctx, f"thieu key '{key}' trong context VN")
        for block in ("valuation", "growth", "earnings", "institution",
                      "capital_flow", "dragon_tiger", "boards"):
            self.assertIn(block, ctx["coverage"])
            self.assertIn("status", ctx[block])
            self.assertIn("data", ctx[block])

    def test_adapter_khong_kha_dung_van_fail_open(self):
        """OpenStock bat nhung adapter chet (service down / import loi): khong duoc raise.

        valuation van giu duoc (tu realtime quote), cac khoi con lai not_supported
        kem ly do ro rang — khong bia du lieu.
        """
        with patch.object(self.manager, "get_realtime_quote", return_value=_FakeQuote()), \
             patch("data_provider.vn_fundamental_context._get_adapter", return_value=None):
            ctx = self.manager.get_fundamental_context("FPT")

        self.assertEqual(ctx["market"], "vn")
        self.assertEqual(ctx["growth"]["status"], "not_supported")
        self.assertNotEqual(ctx["valuation"]["status"], "not_supported")
        self.assertTrue(
            any("adapter unavailable" in e for e in ctx["errors"]),
            f"phai neu ro ly do, thay: {ctx['errors']}",
        )

    def test_flag_off_thi_ma_3_chu_bi_coi_la_my___han_che_da_biet(self):
        """Khoa lai han che P1-2: nhan dien VN dua vao `openstock_enabled`, khong phai
        vao ban chat ma chung khoan.

        `OPENSTOCK_ENABLED=false` -> `_market_tag("FPT")` = "us" vi
        `is_us_stock_code` cua upstream = 1-5 chu in hoa. Nghia la repo KHONG the
        phuc vu dong thoi VN va US/CN. Test nay khong phai de chuc mung hanh vi do,
        ma de neu ai sua cach nhan dien (Phase 2b: dung symbol universe cua OpenStock)
        thi biet ngay minh dang doi contract nay.
        """
        self.get_config.return_value.openstock_enabled = False
        with patch.object(self.manager, "get_realtime_quote", return_value=_FakeQuote()):
            ctx = self.manager.get_fundamental_context("FPT")

        self.assertEqual(ctx["market"], "us")


if __name__ == "__main__":
    unittest.main()
