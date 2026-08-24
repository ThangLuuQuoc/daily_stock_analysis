# -*- coding: utf-8 -*-
"""Regression: dich chuoi xu huong KHONG duoc lam hong _infer_trend_direction.

Bug that (da kiem chung bang cach chay truoc khi sua): ban fork dich
`result.ma_alignment` sang tieng Viet ngay trong `stock_analyzer.py`.
`analyzer.py::_infer_trend_direction()` PARSE chuoi do de suy ra bullish/bearish
theo `_BULLISH_TREND_HINTS` (tieng Trung + "bullish"/"uptrend") hoac fallback
mau `MA5>MA10>MA20`. Chuoi tieng Viet khong co ca hai:

    STRONG_BULL: upstream -> bullish  |  fork dich tai cho -> neutral   SAI
    STRONG_BEAR: upstream -> bearish  |  fork dich tai cho -> neutral   SAI

Dung 2 trang thai MANH NHAT bi ha xuong trung tinh. Cac trang thai khac thoat
duoc nho tinh co giu lai "MA5>MA10>MA20" trong chuoi.

Sua: `stock_analyzer.py` giu nguyen ban upstream (canonical noi bo), dich o BIEN
dung prompt qua `src/trend_text_vi.py`. Cong them lop phong thu thu hai la nap
keyword tieng Viet vao hint list.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import src.analyzer as az
from src.analyzer import _infer_trend_direction
from src.stock_analyzer import TrendStatus, VolumeStatus
from src import trend_text_vi as tv

_SRC = Path(__file__).resolve().parents[1] / "src" / "stock_analyzer.py"


def _assigned(field: str) -> set:
    """Moi chuoi ma stock_analyzer.py gan vao `field` (doc tu source that)."""
    text = _SRC.read_text(encoding="utf-8")
    return set(re.findall(rf'result\.{field}\s*=\s*"([^"]+)"', text))


# (trend_status enum value, ma_alignment upstream, huong ky vong)
_CASES = [
    (TrendStatus.STRONG_BULL.value, "强势多头排列，均线发散上行", "bullish"),
    (TrendStatus.BULL.value, "多头排列 MA5>MA10>MA20", "bullish"),
    (TrendStatus.WEAK_BULL.value, "弱势多头，MA5>MA10 但 MA10≤MA20", "bullish"),
    (TrendStatus.CONSOLIDATION.value, "均线缠绕，趋势不明", "neutral"),
    (TrendStatus.WEAK_BEAR.value, "弱势空头，MA5<MA10 但 MA10≥MA20", "bearish"),
    (TrendStatus.BEAR.value, "空头排列 MA5<MA10<MA20", "bearish"),
    (TrendStatus.STRONG_BEAR.value, "强势空头排列，均线发散下行", "bearish"),
]


class TrendInferenceTest(unittest.TestCase):
    def setUp(self):
        tv.register_trend_hints()

    def test_upstream_zh_suy_luan_dung(self):
        """Duong co ban: gia tri canonical cua upstream phai suy luan dung."""
        for status, ma, expected in _CASES:
            got = _infer_trend_direction({"trend_status": status, "ma_alignment": ma})
            self.assertEqual(got, expected, f"zh {status}/{ma!r}")

    def test_ban_dich_vi_suy_luan_GIONG_ban_zh(self):
        """Day la test chan bug. Dich xong khong duoc doi ket qua suy luan."""
        for status, ma, expected in _CASES:
            localized = tv.localize_trend_for_prompt(
                {"trend_status": status, "ma_alignment": ma}, "vi"
            )
            got = _infer_trend_direction(localized)
            self.assertEqual(
                got, expected,
                f"vi {status}: {localized.get('ma_alignment')!r} -> {got}, can {expected}",
            )

    def test_strong_bull_bear_khong_con_ve_neutral(self):
        """Goi ten ro 2 case tung sai, de neu tai dien thi doc log biet ngay."""
        for status, ma, expected in (_CASES[0], _CASES[-1]):
            localized = tv.localize_trend_for_prompt(
                {"trend_status": status, "ma_alignment": ma}, "vi"
            )
            got = _infer_trend_direction(localized)
            self.assertNotEqual(got, "neutral", f"{status} lai ve neutral (bug cu)")
            self.assertEqual(got, expected)


class TrendTextCoverageTest(unittest.TestCase):
    def test_bao_phu_ma_alignment(self):
        """Upstream them/doi chuoi ma_alignment -> test do, khong ro tieng Trung."""
        missing = _assigned("ma_alignment") - set(tv.MA_ALIGNMENT_VI)
        self.assertEqual(
            missing, set(),
            "Thieu ban dich. Them vao MA_ALIGNMENT_VI trong src/trend_text_vi.py: "
            f"{sorted(missing)}",
        )

    def test_bao_phu_volume_trend(self):
        missing = _assigned("volume_trend") - set(tv.VOLUME_TREND_VI)
        self.assertEqual(
            missing, set(),
            f"Thieu ban dich VOLUME_TREND_VI: {sorted(missing)}",
        )

    def test_bao_phu_enum(self):
        for enum_cls, mapping, where in (
            (TrendStatus, tv.TREND_STATUS_VI, "TREND_STATUS_VI"),
            (VolumeStatus, tv.VOLUME_STATUS_VI, "VOLUME_STATUS_VI"),
        ):
            missing = {e.value for e in enum_cls} - set(mapping)
            self.assertEqual(missing, set(), f"Thieu key trong {where}: {sorted(missing)}")

    def test_stock_analyzer_giu_nguyen_ban_upstream(self):
        """Chan viec ai do lai dich tai cho trong stock_analyzer.py.

        Moi chuoi gan vao ma_alignment/volume_trend phai la tieng Trung (canonical),
        vi _infer_trend_direction phu thuoc vao do.
        """
        has_cjk = lambda t: any("一" <= c <= "鿿" for c in t)  # noqa: E731
        for field in ("ma_alignment", "volume_trend"):
            for value in _assigned(field):
                self.assertTrue(
                    has_cjk(value),
                    f"stock_analyzer.py gan chuoi khong phai canonical vao {field}: "
                    f"{value!r}. Dich o src/trend_text_vi.py, khong dich tai cho.",
                )


class LocalizeBehaviourTest(unittest.TestCase):
    def test_ngon_ngu_khac_khong_bi_doi(self):
        original = {"trend_status": "多头排列", "ma_alignment": "多头排列 MA5>MA10>MA20"}
        for lang in ("zh", "en", "ko", None, ""):
            self.assertIs(tv.localize_trend_for_prompt(original, lang), original)

    def test_chuoi_la_thi_giu_nguyen_khong_lam_mat_du_lieu(self):
        out = tv.localize_trend_for_prompt(
            {"ma_alignment": "chuoi upstream moi chua dich"}, "vi"
        )
        self.assertEqual(out["ma_alignment"], "chuoi upstream moi chua dich")

    def test_khong_sua_dict_goc(self):
        original = {"ma_alignment": "多头排列 MA5>MA10>MA20"}
        tv.localize_trend_for_prompt(original, "vi")
        self.assertEqual(original["ma_alignment"], "多头排列 MA5>MA10>MA20")

    def test_register_hints_idempotent(self):
        tv.register_trend_hints()
        before = len(az._BULLISH_TREND_HINTS)
        tv.register_trend_hints()
        self.assertEqual(len(az._BULLISH_TREND_HINTS), before)


if __name__ == "__main__":
    unittest.main()
