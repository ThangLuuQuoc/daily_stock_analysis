# -*- coding: utf-8 -*-
"""OpenStockFetcher — quote enrich + cac method market + symbol universe.

Cac test nay khoa lai 3 nhom thay doi:

1. `get_realtime_quote` dung `/stock/quote?enrich=true` (1 call thay vi 2) va map
   du volume_ratio / turnover_rate / change_60d / high_52w / low_52w. Ba field
   dau di TRUC TIEP vao prompt (src/analyzer.py ~3432-3438) nen truoc day chung
   hien "N/A" trong moi bao cao VN.

2. get_market_stats / get_sector_rankings / get_hot_stocks / get_limit_up_pool —
   truoc day de mac dinh None du OpenStock da co san du lieu.

3. openstock_symbols dung `GET /stocks` lam nguon su that thay vi doan regex.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from data_provider.openstock_fetcher import OpenStockFetcher
from data_provider import openstock_symbols


_ENRICHED_QUOTE = {
    "symbol": "FPT",
    "price": 71.5,
    "change": 0.5,
    "percentChange": 0.7,
    "volume": 3_200_000,
    "high": 72.0,
    "low": 70.8,
    "open": 71.0,
    "previousClose": 71.0,
    "value": 2.3e11,
    # enrich block
    "peRatio": 18.4,
    "pbRatio": 3.9,
    "marketCap": 105_000e9,
    "high52w": 78.2,
    "low52w": 55.1,
    "change60d": 12.34,
    "volumeRatio": 1.42,
    "turnoverRatio": 0.21,
}

_OVERVIEW = {"peRatio": 9.9, "pbRatio": 1.1, "marketCap": 1e12, "sharesOutstanding": 1_000_000_000}

_MARKET_OVERVIEW = {
    "breadth": {"advancers": 210, "decliners": 130, "unchanged": 40, "total": 380},
    "liquidity": {"todayValue": 1.8e13},
    "sectorLeadership": {
        "all": [
            {"sector": "Technology", "avgReturnPct": 2.1, "count": 12},
            {"sector": "Banks", "avgReturnPct": 0.8, "count": 27},
            {"sector": "Real Estate", "avgReturnPct": -1.4, "count": 33},
        ]
    },
    "index": {"symbol": "VNINDEX", "last": 1290.5, "change": 8.1, "percentChange": 0.63},
}

_CEILING_FLOOR = {
    "exchange": "ALL",
    "ceiling": [
        {"symbol": "AAA", "name": "An Phat", "price": 12.0, "percentChange": 6.9,
         "volume": 900_000, "value": 1.1e10, "exchange": "HOSE"},
        {"symbol": "BBB", "name": "B Corp", "price": 8.5, "percentChange": 9.8,
         "volume": 400_000, "value": 3.4e9, "exchange": "HNX"},
    ],
    "floor": [
        {"symbol": "CCC", "name": "C Corp", "price": 5.0, "percentChange": -6.9,
         "volume": 200_000, "value": 1e9, "exchange": "HOSE"},
    ],
}

_LEADERS = [
    {"symbol": "HPG", "name": "Hoa Phat", "price": 27.5, "percentChange": 4.2, "volume": 12_000_000},
    {"symbol": "SSI", "name": "SSI Sec", "price": 33.0, "percentChange": -3.8, "volume": 9_000_000},
]


class _FetcherBase(unittest.TestCase):
    def setUp(self):
        patcher = patch("src.config.get_config")
        self.addCleanup(patcher.stop)
        cfg = patcher.start().return_value
        cfg.openstock_enabled = True
        cfg.openstock_base_url = "http://localhost:3000/api/v1"
        # universe khong can thiet cho cac test fetcher -> dung regex fallback
        openstock_symbols.reset_vn_universe_cache()
        self.addCleanup(openstock_symbols.reset_vn_universe_cache)
        universe_patcher = patch.object(openstock_symbols, "_fetch_universe", return_value=None)
        self.addCleanup(universe_patcher.stop)
        universe_patcher.start()
        self.fetcher = OpenStockFetcher()


class EnrichedQuoteTest(_FetcherBase):
    def test_goi_enrich_true_va_chi_mot_lan(self):
        with patch.object(self.fetcher, "_get", return_value=_ENRICHED_QUOTE) as mock_get:
            quote = self.fetcher.get_realtime_quote("FPT")

        self.assertEqual(mock_get.call_count, 1, "phai 1 call, khong con goi overview rieng")
        path, kwargs = mock_get.call_args[0][0], mock_get.call_args[1]
        self.assertEqual(path, "/stock/quote")
        self.assertEqual(kwargs["params"]["enrich"], "true")
        self.assertIsNotNone(quote)

    def test_map_du_cac_field_di_vao_prompt(self):
        with patch.object(self.fetcher, "_get", return_value=_ENRICHED_QUOTE):
            q = self.fetcher.get_realtime_quote("FPT")

        # 3 field nay duoc render truc tiep trong bang prompt cua analyzer
        self.assertEqual(q.volume_ratio, 1.42)
        self.assertEqual(q.turnover_rate, 0.21)
        self.assertEqual(q.change_60d, 12.34)
        # 52w range
        self.assertEqual(q.high_52w, 78.2)
        self.assertEqual(q.low_52w, 55.1)
        # valuation lay tu enrich, khong phai tu overview
        self.assertEqual(q.pe_ratio, 18.4)
        self.assertEqual(q.pb_ratio, 3.9)

    def test_enrich_khong_kha_dung_thi_fallback_overview(self):
        """Server cu chua ho tro enrich -> khong duoc mat pe/pb/marketCap."""
        bare = {k: v for k, v in _ENRICHED_QUOTE.items()
                if k not in ("peRatio", "pbRatio", "marketCap", "turnoverRatio")}

        def fake_get(path, params=None):
            if path == "/stock/quote":
                return bare
            if path.endswith("/overview"):
                return _OVERVIEW
            raise AssertionError(f"unexpected path {path}")

        with patch.object(self.fetcher, "_get", side_effect=fake_get):
            q = self.fetcher.get_realtime_quote("FPT")

        self.assertEqual(q.pe_ratio, 9.9)
        self.assertEqual(q.pb_ratio, 1.1)
        self.assertAlmostEqual(q.turnover_rate, 0.32, places=2)  # 3.2M/1B*100


class MarketMethodsTest(_FetcherBase):
    def test_market_stats_breadth(self):
        def fake_get(path, params=None):
            if path == "/dashboard/market/overview":
                return _MARKET_OVERVIEW
            if path == "/dashboard/market/ceiling-floor":
                return _CEILING_FLOOR
            raise AssertionError(path)

        with patch.object(self.fetcher, "_get", side_effect=fake_get):
            stats = self.fetcher.get_market_stats()

        self.assertEqual(stats["up_count"], 210)
        self.assertEqual(stats["down_count"], 130)
        self.assertEqual(stats["flat_count"], 40)
        # VN khong co "涨停" that su -> dung so ma cham tran/san
        self.assertEqual(stats["limit_up_count"], 2)
        self.assertEqual(stats["limit_down_count"], 1)
        self.assertEqual(stats["total_amount"], 1.8e13)

    def test_sector_rankings_sap_xep_dung(self):
        with patch.object(self.fetcher, "_get", return_value=_MARKET_OVERVIEW):
            gainers, losers = self.fetcher.get_sector_rankings(n=2)

        self.assertEqual([g["name"] for g in gainers], ["Technology", "Banks"])
        self.assertEqual(losers[0]["name"], "Real Estate")
        self.assertEqual(gainers[0]["change_pct"], 2.1)

    def test_hot_stocks(self):
        with patch.object(self.fetcher, "_get", return_value=_LEADERS) as mock_get:
            rows = self.fetcher.get_hot_stocks(n=5)

        self.assertEqual(mock_get.call_args[1]["params"]["tab"], "movers")
        self.assertEqual([r["code"] for r in rows], ["HPG", "SSI"])
        self.assertEqual(rows[0]["change_pct"], 4.2)

    def test_limit_up_pool_la_co_phieu_tran(self):
        with patch.object(self.fetcher, "_get", return_value=_CEILING_FLOOR):
            rows = self.fetcher.get_limit_up_pool()

        self.assertEqual([r["code"] for r in rows], ["AAA", "BBB"])
        self.assertEqual(rows[0]["amount"], 1.1e10)

    def test_market_methods_fail_open(self):
        """OpenStock loi -> tra None, khong raise."""
        from data_provider.base import DataFetchError

        with patch.object(self.fetcher, "_get", side_effect=DataFetchError("down")):
            self.assertIsNone(self.fetcher.get_market_stats())
            self.assertIsNone(self.fetcher.get_sector_rankings())
            self.assertIsNone(self.fetcher.get_hot_stocks())
            self.assertIsNone(self.fetcher.get_limit_up_pool())


class SymbolUniverseTest(unittest.TestCase):
    def setUp(self):
        openstock_symbols.reset_vn_universe_cache()
        self.addCleanup(openstock_symbols.reset_vn_universe_cache)
        patcher = patch("src.config.get_config")
        self.addCleanup(patcher.stop)
        cfg = patcher.start().return_value
        cfg.openstock_enabled = True
        cfg.openstock_base_url = "http://localhost:3000/api/v1"

    def _mock_universe(self, symbols):
        resp = MagicMock()
        resp.json.return_value = {"data": [{"symbol": s} for s in symbols]}
        return patch("requests.get", return_value=resp)

    def test_universe_sua_duoc_ca_false_positive_va_false_negative(self):
        """Day la ly do ton tai cua GET /stocks."""
        with self._mock_universe(["FPT", "VNM", "HPG", "FUEVFVND", "E1VFVN30", "VN30F2409"]):
            # false negative truoc day: ETF va phai sinh khong khop regex 3 chu
            self.assertTrue(openstock_symbols.is_vn_stock_code("FUEVFVND"))
            self.assertTrue(openstock_symbols.is_vn_stock_code("E1VFVN30"))
            self.assertTrue(openstock_symbols.is_vn_stock_code("VN30F2409"))
            # false positive truoc day: ma My 3 chu bi coi la VN
            self.assertFalse(openstock_symbols.is_vn_stock_code("IBM"))
            self.assertFalse(openstock_symbols.is_vn_stock_code("AMD"))
            # ma VN that van dung
            self.assertTrue(openstock_symbols.is_vn_stock_code("FPT"))

    def test_chi_goi_endpoint_mot_lan_nho_cache(self):
        with self._mock_universe(["FPT", "VNM"]) as mock_get:
            openstock_symbols.is_vn_stock_code("FPT")
            openstock_symbols.is_vn_stock_code("VNM")
            openstock_symbols.is_vn_stock_code("HPG")
        self.assertEqual(mock_get.call_count, 1)

    def test_universe_loi_thi_fallback_regex(self):
        with patch("requests.get", side_effect=ConnectionError("down")):
            # degradation da biet: regex lai nhan IBM la VN
            self.assertTrue(openstock_symbols.is_vn_stock_code("FPT"))
            self.assertTrue(openstock_symbols.is_vn_stock_code("IBM"))
            self.assertFalse(openstock_symbols.is_vn_stock_code("FUEVFVND"))

    def test_index_luon_nhan_duoc_khong_can_universe(self):
        with patch("requests.get", side_effect=ConnectionError("down")):
            self.assertTrue(openstock_symbols.is_vn_stock_code("VNINDEX"))
            self.assertTrue(openstock_symbols.is_vn_index_code("VN100"))
        self.assertFalse(openstock_symbols.is_vn_index_code("HNX30"),
                         "HNX30 khong duoc syncIndexWorker sync -> khong nen nhan")

    def test_openstock_tat_thi_khong_goi_network(self):
        openstock_symbols.reset_vn_universe_cache()
        with patch("src.config.get_config") as gc, patch("requests.get") as mock_get:
            gc.return_value.openstock_enabled = False
            openstock_symbols.is_vn_stock_code("FPT")
        mock_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
