"""fork VN: `src/market_context.py` + `src/market_context_vi.py`.

Chan hai loi that da co trong fork truoc day:
  1. Ban dich tieng Viet bi ghi vao thang khoa "zh" -> REPORT_LANGUAGE=zh nhan
     tieng Viet.
  2. `detect_market()` khong co nhanh VN -> ticker VN 3 chu roi vao regex US,
     prompt goi VIC la "co phieu My" kem huong dan Fed/SEC/T+0.
"""

import unittest
from unittest.mock import patch

import src.market_context as mc
import src.market_context_vi as mc_vi


class MarketContextZhKhongBiGhiDeTest(unittest.TestCase):
    """Khoa "zh" phai la tieng Trung cua upstream, khong phai tieng Viet."""

    VI_CHARS = set("ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")

    def _co_tieng_viet(self, text):
        return bool(self.VI_CHARS & set(text))

    def test_khoa_zh_khong_chua_tieng_viet(self):
        for ten, bang in (("_MARKET_ROLES", mc._MARKET_ROLES),
                          ("_MARKET_GUIDELINES", mc._MARKET_GUIDELINES)):
            for market, entry in bang.items():
                if market == "vn":
                    continue  # thi truong cua fork, khong co ban upstream
                with self.subTest(bang=ten, market=market):
                    self.assertFalse(
                        self._co_tieng_viet(entry["zh"]),
                        f'{ten}["{market}"]["zh"] chua tieng Viet. Ban dich phai '
                        f'nam o khoa "vi" (src/market_context_vi.py), khong ghi de "zh".',
                    )

    def test_moi_thi_truong_deu_co_khoa_vi(self):
        for ten, bang in (("_MARKET_ROLES", mc._MARKET_ROLES),
                          ("_MARKET_GUIDELINES", mc._MARKET_GUIDELINES)):
            thieu = [m for m, e in bang.items() if "vi" not in e]
            self.assertEqual(
                thieu, [],
                f"{ten}: thi truong thieu khoa 'vi' -> bao cao tieng Viet rot ve "
                f"tieng Trung. Them vao VI_MARKET_* trong market_context_vi.py: {thieu}",
            )

    def test_get_market_role_dung_ngon_ngu(self):
        self.assertEqual(mc.get_market_role("600519", "zh"), " A 股")
        self.assertEqual(mc.get_market_role("600519", "en"), "China A-shares")
        self.assertEqual(mc.get_market_role("600519", "vi"), "cổ phiếu A-share")

    def test_khoa_thieu_rot_ve_zh_khong_nem_keyerror(self):
        """Upstream them thi truong moi ma fork chua dich -> khong duoc vo."""
        with patch.dict(mc._MARKET_ROLES, {"xx": {"zh": "新市场", "en": "New"}}, clear=False):
            with patch.object(mc, "detect_market", return_value="xx"):
                self.assertEqual(mc.get_market_role("ANY", "vi"), "新市场")


class DetectMarketVnTest(unittest.TestCase):
    def test_ma_vn_nhan_dung(self):
        with patch.object(mc, "_is_vn_market_code", return_value=True):
            self.assertEqual(mc.detect_market("VIC"), "vn")

    def test_khong_pha_thi_truong_cua_upstream(self):
        """`_is_vn_market_code` tra True cung KHONG duoc lam sai cn/hk/jp/kr.

        Ma 6 so (A股), 5 so (HK) va ma co hau to Yahoo phai giu nguyen phan loai
        du guard VN co bat — vi `is_vn_stock_code` loai chuoi toan so va
        `detect_market` chi hoi VN cho phan con lai.
        """
        for code, expected in (("600519", "cn"), ("00700", "hk"),
                               ("7203.T", "jp"), ("005930.KS", "kr")):
            with self.subTest(code=code):
                self.assertEqual(mc.detect_market(code), expected)

    def test_loi_data_provider_rot_ve_hanh_vi_upstream(self):
        """market_context duoc import rat som; data_provider co the chua san sang."""
        with patch("data_provider.base._is_vn_market", side_effect=RuntimeError("chua san sang")):
            self.assertFalse(mc._is_vn_market_code("VIC"))

    def test_thi_truong_vn_co_dac_thu_bat_buoc(self):
        """Huong dan VN phai neu bien do, T+2 va foreign room."""
        for lang in ("zh", "en", "vi"):
            text = mc_vi.VN_GUIDELINES[lang]
            with self.subTest(lang=lang):
                self.assertIn("7%", text)
                self.assertIn("T+2", text)
                self.assertIn("foreign room", text)


if __name__ == "__main__":
    unittest.main()
