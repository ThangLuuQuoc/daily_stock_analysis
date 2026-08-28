"""fork VN: chỉ mục autocomplete mặc định là thị trường Việt Nam.

Chỉ mục của upstream (``stocks.index.json``, ~31.700 mục) **không có một mã VN
nào** — kể cả VNINDEX lẫn FPT/VIC. Repo này phục vụ thị trường VN nên mặc định
phải là ``stocks.index.vn.json``, có env để chuyển ngược về upstream.
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.data.stock_index_market import (
    UPSTREAM_STOCK_INDEX_FILENAME,
    VN_STOCK_INDEX_FILENAME,
    get_stock_index_market,
    is_vn_index_market,
    stock_index_filename,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VN_INDEX_PATH = REPO_ROOT / "apps" / "dsa-web" / "public" / VN_STOCK_INDEX_FILENAME


class ThiTruongMacDinhTest(unittest.TestCase):
    def test_mac_dinh_la_vn(self):
        """Khong dat env -> phai la VN. Day la diem chinh cua ca tinh nang."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STOCK_INDEX_MARKET", None)
            self.assertEqual(get_stock_index_market(), "vn")
            self.assertTrue(is_vn_index_market())
            self.assertEqual(stock_index_filename(), VN_STOCK_INDEX_FILENAME)

    def test_env_chuyen_ve_upstream(self):
        for value in ("cn", "CN", " Cn ", "upstream"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"STOCK_INDEX_MARKET": value}):
                    self.assertFalse(is_vn_index_market())
                    self.assertEqual(stock_index_filename(), UPSTREAM_STOCK_INDEX_FILENAME)

    def test_gia_tri_la_roi_ve_vn_khong_nem_loi(self):
        """Chi muc autocomplete hong khong duoc lam sap tien trinh phan tich."""
        with patch.dict(os.environ, {"STOCK_INDEX_MARKET": "khong-ton-tai"}):
            self.assertTrue(is_vn_index_market())
            self.assertEqual(stock_index_filename(), VN_STOCK_INDEX_FILENAME)

    def test_env_rong_coi_nhu_khong_dat(self):
        with patch.dict(os.environ, {"STOCK_INDEX_MARKET": "   "}):
            self.assertEqual(get_stock_index_market(), "vn")


@unittest.skipUnless(VN_INDEX_PATH.is_file(), f"chua sinh {VN_STOCK_INDEX_FILENAME}")
class NoiDungChiMucVnTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(VN_INDEX_PATH, encoding="utf-8") as fh:
            cls.rows = json.load(fh)

    def test_dinh_dang_10_truong(self):
        for row in self.rows[:50]:
            self.assertEqual(len(row), 10, f"dong phai co 10 truong: {row}")

    def test_toan_bo_la_market_vn(self):
        khac = {row[6] for row in self.rows} - {"VN"}
        self.assertEqual(khac, set(), f"co market khong phai VN: {khac}")

    def test_co_du_chi_so_bat_buoc(self):
        codes = {row[0] for row in self.rows}
        for must in ("VNINDEX", "VN30", "VN100", "HNXINDEX", "UPCOMINDEX"):
            self.assertIn(must, codes)

    def test_co_ma_pho_bien(self):
        codes = {row[0] for row in self.rows}
        for must in ("FPT", "VIC", "HPG", "VCB", "VNM"):
            self.assertIn(must, codes)

    def test_khong_trung_ma(self):
        codes = [row[0] for row in self.rows]
        self.assertEqual(len(codes), len(set(codes)))

    def test_truong_tim_kiem_ascii_khong_dau(self):
        """pinyinFull duoc tai su dung lam dang ASCII de go khong dau."""
        loi = [(row[0], row[3]) for row in self.rows if not row[3].isascii()]
        self.assertEqual(loi, [], f"{len(loi)} dong con ky tu co dau o pinyinFull: {loi[:5]}")


@unittest.skipUnless(VN_INDEX_PATH.is_file(), f"chua sinh {VN_STOCK_INDEX_FILENAME}")
class LoaderDungFileVnTest(unittest.TestCase):
    def test_tra_duoc_ten_ma_vn(self):
        """BUG THAT truoc khi co tinh nang nay: FPT/VIC/VNINDEX deu tra ve rong,
        nen lich su phan tich hien 'FPT(FPT)', 'HPG', 'KSB' tran trui."""
        from src.data.stock_index_loader import get_stock_name_index_map

        m = get_stock_name_index_map()
        for code in ("VNINDEX", "VN30", "FPT", "VIC", "HPG"):
            with self.subTest(code=code):
                self.assertTrue(m.get(code), f"{code} khong tra duoc ten")


if __name__ == "__main__":
    unittest.main()
