# -*- coding: utf-8 -*-
"""Tim kiem co phieu VN (OpenStock) qua /api/v1/stocks/search.

Endpoint nay o `api/v1/endpoints/vn_search.py` (tach rieng khoi `stocks.py` cua
upstream, xem docs/vn-fork-touchpoints.md Phase 2c) nhung phai mount dung
prefix `/stocks` de giu nguyen URL cu (`apps/dsa-web/src/api/stocks.ts` goi
`/api/v1/stocks/search`). Test nay khoa lai dung URL do — neu ai lo tay doi
prefix khi tach file, test se do ngay thay vi phai phat hien qua frontend.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.app import app


class VnSearchEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        patcher = patch("src.config.get_config")
        self.addCleanup(patcher.stop)
        self.get_config = patcher.start()
        cfg = self.get_config.return_value
        cfg.openstock_enabled = True
        cfg.openstock_base_url = "http://localhost:3000/api/v1"

    def test_duong_dan_van_la_stocks_search(self):
        """Khoa lai URL: /api/v1/stocks/search, khong duoc doi khi tach file."""
        resp = self.client.get("/api/v1/stocks/search", params={"q": "FPT"})
        self.assertEqual(resp.status_code, 200)

    def test_query_rong_tra_ve_rong_khong_goi_openstock(self):
        with patch("requests.get") as mock_get:
            resp = self.client.get("/api/v1/stocks/search", params={"q": ""})
        self.assertEqual(resp.json(), {"count": 0, "result": []})
        mock_get.assert_not_called()

    def test_openstock_tat_tra_ve_rong(self):
        self.get_config.return_value.openstock_enabled = False
        with patch("requests.get") as mock_get:
            resp = self.client.get("/api/v1/stocks/search", params={"q": "FPT"})
        self.assertEqual(resp.json(), {"count": 0, "result": []})
        mock_get.assert_not_called()

    def test_map_dung_field_cho_frontend_autocomplete(self):
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "result": [
                {"symbol": "fpt", "name": "FPT Corporation", "is_active": True, "exchange": "HOSE"},
            ]
        }
        with patch("requests.get", return_value=fake_resp) as mock_get:
            resp = self.client.get("/api/v1/stocks/search", params={"q": "FPT"})

        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        self.assertEqual(called_url, "http://localhost:3000/api/v1/search")

        body = resp.json()
        self.assertEqual(body["count"], 1)
        item = body["result"][0]
        self.assertEqual(item["canonicalCode"], "FPT")
        self.assertEqual(item["market"], "VN")
        self.assertEqual(item["matchType"], "exact")
        self.assertEqual(item["exchange"], "HOSE")

    def test_openstock_loi_thi_fail_open(self):
        with patch("requests.get", side_effect=ConnectionError("boom")):
            resp = self.client.get("/api/v1/stocks/search", params={"q": "FPT"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"count": 0, "result": []})


if __name__ == "__main__":
    unittest.main()
