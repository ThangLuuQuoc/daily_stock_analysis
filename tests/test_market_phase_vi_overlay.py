# -*- coding: utf-8 -*-
"""Overlay tiếng Việt cho market_phase_prompt / market_phase_summary.

Hai file upstream này trước đây bị ghi đè tại chỗ: `_PHASE_LABELS_ZH` chứa tiếng
Việt và `_format_zh()` emit tiếng Việt. Phase 3 chuyển sang registry + module `vi`
riêng.

Test ở đây khoá lại 3 thứ:

1. `vi` ra tiếng Việt (không hồi quy tính năng).
2. **`zh` ra tiếng Trung trở lại** — đây là thứ bị mất trước đó, và cũng là lý do
   `ko` của upstream (rơi vào nhánh `else -> zh`) từng nhận tiếng Việt.
3. **Bao phủ**: bảng `vi` phải đủ key như bảng `_ZH` của upstream. Upstream thêm
   một phase/warning/market/source mới -> test đỏ, thay vì rò tiếng Trung âm thầm
   vào báo cáo tiếng Việt.
"""

from __future__ import annotations

import unittest

import src.market_phase_prompt as mpp
import src.market_phase_summary as mps
from src import market_phase_prompt_vi as mpp_vi
from src import market_phase_summary_vi as mps_vi

_CJK = lambda text: any("一" <= ch <= "鿿" for ch in text)  # noqa: E731

_CTX = {
    "phase": "intraday",
    "market": "VN",
    "market_local_time": "2026-08-24 10:30",
    "effective_daily_bar_date": "2026-08-22",
    "minutes_to_close": 95,
    "is_partial_bar": True,
    "warnings": ["calendar_unavailable"],
}


class MarketPhasePromptViTest(unittest.TestCase):
    def test_vi_ra_tieng_viet_khong_lan_cjk(self):
        out = mpp.format_market_phase_prompt_section(_CTX, report_language="vi")
        self.assertIn("Bối cảnh giai đoạn thị trường", out)
        self.assertIn("trong phiên", out)
        self.assertFalse(_CJK(out), f"con ky tu Trung trong output vi: {out!r}")

    def test_zh_da_phuc_hoi_tieng_trung(self):
        """Truoc Phase 3, nhanh nay emit tieng Viet vi _format_zh bi ghi de."""
        out = mpp.format_market_phase_prompt_section(_CTX, report_language="zh")
        self.assertIn("市场阶段上下文", out)
        self.assertIn("盘中", out)

    def test_en_khong_bi_anh_huong(self):
        out = mpp.format_market_phase_prompt_section(_CTX, report_language="en")
        self.assertIn("Market Phase Context", out)
        self.assertFalse(_CJK(out))

    def test_ko_khong_con_nhan_tieng_viet(self):
        """Upstream them `ko` (v3.25.0) -> roi vao nhanh else->zh.

        Truoc Phase 3 nhanh do la tieng Viet, tuc merge `ko` ve se cho bao cao
        Han Quoc bang tieng Viet. Gio phai la tieng Trung (hanh vi upstream).
        """
        out = mpp.format_market_phase_prompt_section(_CTX, report_language="ko")
        self.assertIn("市场阶段上下文", out)

    def test_bao_phu_phase_labels(self):
        upstream = set(mpp._PHASE_LABELS_ZH)
        vi = set(mpp_vi._PHASE_LABELS_VI)
        self.assertEqual(
            upstream - vi, set(),
            "Thieu nhan phase 'vi'. Them vao _PHASE_LABELS_VI trong "
            f"src/market_phase_prompt_vi.py: {sorted(upstream - vi)}",
        )

    def test_bao_phu_warning_labels(self):
        upstream = set(mpp._WARNING_LABELS_ZH)
        vi = set(mpp_vi._WARNING_LABELS_VI)
        self.assertEqual(
            upstream - vi, set(),
            "Thieu nhan warning 'vi'. Them vao _WARNING_LABELS_VI: "
            f"{sorted(upstream - vi)}",
        )

    def test_moi_phase_deu_render_duoc_bang_vi(self):
        for phase in mpp._KNOWN_PHASES:
            out = mpp.format_market_phase_prompt_section(
                {**_CTX, "phase": phase}, report_language="vi"
            )
            self.assertTrue(out.strip(), f"phase={phase} tra ve rong")
            self.assertFalse(_CJK(out), f"phase={phase} con CJK: {out!r}")

    def test_phase_khong_hop_le_thi_ve_unknown(self):
        out = mpp.format_market_phase_prompt_section(
            {**_CTX, "phase": "phase_khong_ton_tai"}, report_language="vi"
        )
        self.assertIn("giai đoạn chưa rõ", out)

    def test_register_idempotent(self):
        mpp_vi.register()
        mpp_vi.register()
        out = mpp.format_market_phase_prompt_section(_CTX, report_language="vi")
        self.assertIn("Bối cảnh giai đoạn thị trường", out)


class MarketPhaseSummaryViTest(unittest.TestCase):
    def test_vi_va_zh(self):
        summary = {"phase": "intraday", "market": "vn"}
        vi = mps.format_public_market_status_line(summary, report_language="vi")
        zh = mps.format_public_market_status_line(summary, report_language="zh")
        en = mps.format_public_market_status_line(summary, report_language="en")

        self.assertEqual(vi, "Trạng thái thị trường: Việt Nam · trong phiên")
        self.assertFalse(_CJK(vi))
        # zh phuc hoi
        self.assertIn("市场状态", zh)
        self.assertIn("盘中", zh)
        self.assertIn("Market status", en)

    def test_bao_phu_bang_nhan(self):
        for upstream_table, vi_table, where in (
            (mps._PHASE_LABELS_ZH, mps_vi.PHASE_LABELS_VI, "PHASE_LABELS_VI"),
            (mps._MARKET_LABELS_ZH, mps_vi.MARKET_LABELS_VI, "MARKET_LABELS_VI"),
            (mps._PUBLIC_SOURCE_LABELS_ZH, mps_vi.SOURCE_LABELS_VI, "SOURCE_LABELS_VI"),
        ):
            missing = set(upstream_table) - set(vi_table)
            self.assertEqual(
                missing, set(),
                f"Thieu key trong {where} (src/market_phase_summary_vi.py): {sorted(missing)}",
            )

    def test_market_khong_biet_thi_giu_nguyen_khong_crash(self):
        out = mps.format_public_market_status_line(
            {"phase": "postmarket", "market": "jp"}, report_language="vi"
        )
        self.assertIn("sau phiên", out)

    def test_register_idempotent(self):
        mps_vi.register()
        mps_vi.register()
        out = mps.format_public_market_status_line(
            {"phase": "intraday", "market": "vn"}, report_language="vi"
        )
        self.assertEqual(out, "Trạng thái thị trường: Việt Nam · trong phiên")


if __name__ == "__main__":
    unittest.main()
