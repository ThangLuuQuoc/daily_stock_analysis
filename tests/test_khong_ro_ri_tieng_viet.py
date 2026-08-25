"""Bao cao KHONG phai tieng Viet thi khong duoc chua tieng Viet.

Day la kiem tra HANH VI, khong phai kiem tra tinh (grep). Fork da tung dich
tai cho hang tram chuoi cua upstream, lam `REPORT_LANGUAGE=zh|en|ko` nhan tieng
Viet. Quet tinh khong bat duoc vi khong biet dong nao nam trong nhanh `vi` hop
le — nen dung render that roi doi chieu.

Bat duoc that: `## 📈 Dữ liệu kỹ thuật` con sot trong f-string cua
`_format_prompt` sau khi da sua ban trong `_legacy_audit_marker_specs`. Quet
tinh bo qua vi tuong da xu ly; test nay do ngay.
"""

import re
import unittest

VI_CHARS = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩị"
    r"óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]"
)


def _dong_co_tieng_viet(text):
    return [l.strip() for l in (text or "").split("\n") if VI_CHARS.search(l)]


class KhongRoRiTiengVietTest(unittest.TestCase):
    NGON_NGU_KHAC = ("zh", "en", "ko")

    def setUp(self):
        from src.analyzer import GeminiAnalyzer

        self.analyzer = GeminiAnalyzer.__new__(GeminiAnalyzer)
        self.analyzer._get_skill_prompt_sections = lambda: ("", "", False)

    def _context(self, code):
        return {
            "code": code,
            "date": "2026-08-25",
            "today": {"close": 45.2, "ma5": 44.0, "ma10": 43.5, "ma20": 43.0},
            "realtime": {"price": 45.2, "volume_ratio": 1.2, "turnover_rate": 0.8},
            "ma_status": "多头排列",
        }

    def test_user_prompt(self):
        for code in ("600519", "AAPL", "VIC"):
            for lang in self.NGON_NGU_KHAC:
                with self.subTest(code=code, lang=lang):
                    out = self.analyzer._format_prompt(
                        self._context(code), code, report_language=lang
                    )
                    self.assertEqual(
                        _dong_co_tieng_viet(out), [],
                        f"prompt nguoi dung (ma={code}, lang={lang}) ro ri tieng Viet",
                    )

    def test_system_prompt(self):
        for code in ("600519", "AAPL", "VIC"):
            for lang in self.NGON_NGU_KHAC:
                with self.subTest(code=code, lang=lang):
                    out = self.analyzer._get_analysis_system_prompt(lang, code)
                    self.assertEqual(
                        _dong_co_tieng_viet(out), [],
                        f"prompt he thong (ma={code}, lang={lang}) ro ri tieng Viet",
                    )

    def test_vi_van_ra_tieng_viet(self):
        """Doi chung: `vi` phai THUC SU nhan tieng Viet (khong phai xanh gia)."""
        out = self.analyzer._format_prompt(
            self._context("VIC"), "VIC", report_language="vi"
        )
        self.assertGreater(len(_dong_co_tieng_viet(out)), 10)
        out = self.analyzer._get_analysis_system_prompt("vi", "VIC")
        self.assertGreater(len(_dong_co_tieng_viet(out)), 10)


class MarketContextKhongRoRiTest(unittest.TestCase):
    def test_role_va_guidelines(self):
        from src.market_context import get_market_role, get_market_guidelines

        for code in ("600519", "AAPL", "00700", "VIC"):
            for lang in ("zh", "en", "ko"):
                with self.subTest(code=code, lang=lang):
                    self.assertEqual(_dong_co_tieng_viet(get_market_role(code, lang)), [])
                    self.assertEqual(_dong_co_tieng_viet(get_market_guidelines(code, lang)), [])


class MarketStrategyKhongRoRiTest(unittest.TestCase):
    def test_blueprint_cua_thi_truong_khac(self):
        from src.core.market_strategy import get_market_strategy_blueprint

        for region in ("cn", "hk", "us", "jp", "kr"):
            with self.subTest(region=region):
                bp = get_market_strategy_blueprint(region)
                self.assertEqual(_dong_co_tieng_viet(bp.to_prompt_block()), [])
                self.assertEqual(_dong_co_tieng_viet(bp.to_markdown_block()), [])

    def test_vn_van_ra_tieng_viet(self):
        from src.core.market_strategy import get_market_strategy_blueprint

        bp = get_market_strategy_blueprint("vn")
        self.assertGreater(len(_dong_co_tieng_viet(bp.to_prompt_block())), 5)


class GuardrailKhongRoRiTest(unittest.TestCase):
    def test_softened_advice(self):
        from src.daily_market_context_guardrail import (
            _softened_position_advice,
            _softened_position_strategy,
        )

        for lang in ("zh", "en", "ko"):
            with self.subTest(lang=lang):
                for d in (_softened_position_advice(lang), _softened_position_strategy(lang)):
                    for k, v in d.items():
                        self.assertEqual(
                            _dong_co_tieng_viet(v), [],
                            f"{lang}/{k} ro ri tieng Viet",
                        )


if __name__ == "__main__":
    unittest.main()
