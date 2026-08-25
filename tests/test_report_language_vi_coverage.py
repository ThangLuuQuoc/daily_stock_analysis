# -*- coding: utf-8 -*-
"""Bao phu tieng Viet cho report_language — lop an toan cua overlay.

Toan bo du lieu `vi` nam trong `src/report_language_vi.py` va duoc tiem vao cac
dict cua upstream luc import. Cach nay giu `report_language.py` gan nhu nguyen
ban (3 diem cham) nhung doi lai MOT RUI RO:

    `_translate_from_map` dung `translations[canonical][normalized_language]`
    -> thieu key la KeyError, KHONG phai fallback.

Nghia la khi upstream them mot canonical key moi (ho da them `ko` o v3.25.0 va
se con them nua), overlay khong biet -> loi luc chay hoac ro tieng Trung vao bao
cao tieng Viet.

Cac test duoi day la thu DUY NHAT bat duoc viec do. Chung quet dong (introspect)
moi dict `*_TRANSLATIONS` trong module, nen khong can cap nhat khi upstream them
dict moi — test tu dong phu.
"""

from __future__ import annotations

import unittest

import src.report_language as rl
from src import report_language_vi as vi_overlay


def _translation_dicts():
    """Moi (ten_dict, dict) co dang canonical -> {lang: text}."""
    found = []
    for name in dir(rl):
        if not name.endswith("_TRANSLATIONS"):
            continue
        value = getattr(rl, name)
        if isinstance(value, dict) and value and all(
            isinstance(v, dict) for v in value.values()
        ):
            found.append((name, value))
    return found


class ViCoverageTest(unittest.TestCase):
    def test_tim_thay_cac_dict_translations(self):
        """Neu upstream doi cach dat ten thi test khac se pass gia -> chan truoc."""
        dicts = _translation_dicts()
        self.assertGreaterEqual(len(dicts), 5, f"chi tim thay {len(dicts)} dict *_TRANSLATIONS")

    def test_moi_canonical_key_deu_co_ban_dich_vi(self):
        """Day la test quan trong nhat cua Phase 3.

        Upstream them canonical key moi -> test do voi ten key cu the, thay vi
        de KeyError no luc sinh bao cao.
        """
        missing = []
        for name, mapping in _translation_dicts():
            for canonical, per_lang in mapping.items():
                if "vi" not in per_lang:
                    missing.append(f"{name}[{canonical!r}]")
        self.assertEqual(
            missing, [],
            "Thieu ban dich 'vi'. Them vao VI_TRANSLATIONS trong "
            f"src/report_language_vi.py: {missing}",
        )

    def test_khong_lam_hong_zh_en_cua_upstream(self):
        """Overlay chi duoc THEM key 'vi', khong duoc sua zh/en."""
        for name, mapping in _translation_dicts():
            for canonical, per_lang in mapping.items():
                self.assertIn("zh", per_lang, f"{name}[{canonical}] mat 'zh'")
                self.assertIn("en", per_lang, f"{name}[{canonical}] mat 'en'")

    def test_localize_khong_raise_voi_moi_canonical(self):
        """Chay that qua _translate_from_map de bat KeyError."""
        pairs = [
            (rl.localize_operation_advice, rl._OPERATION_ADVICE_TRANSLATIONS),
            (rl.localize_trend_prediction, rl._TREND_PREDICTION_TRANSLATIONS),
            (rl.localize_confidence_level, rl._CONFIDENCE_LEVEL_TRANSLATIONS),
            (rl.localize_chip_health, rl._CHIP_HEALTH_TRANSLATIONS),
            (rl.localize_bias_status, rl._BIAS_STATUS_TRANSLATIONS),
        ]
        for fn, mapping in pairs:
            for canonical, per_lang in mapping.items():
                for source_lang in ("zh", "en"):
                    probe = per_lang[source_lang]
                    try:
                        result = fn(probe, "vi")
                    except KeyError as exc:
                        self.fail(f"{fn.__name__}({probe!r}, 'vi') -> KeyError {exc}")
                    self.assertTrue(result, f"{fn.__name__}({probe!r}, 'vi') tra ve rong")

    def test_report_labels_vi_du_key_nhu_zh(self):
        """Nhan bao cao thieu key -> KeyError o get_report_labels()[key]."""
        zh = set(rl._REPORT_LABELS["zh"])
        vi = set(rl._REPORT_LABELS["vi"])
        self.assertEqual(
            zh - vi, set(),
            "Thieu nhan 'vi'. Them vao VI_REPORT_LABELS trong "
            f"src/report_language_vi.py: {sorted(zh - vi)}",
        )

    def test_vi_nam_trong_supported(self):
        self.assertIn("vi", rl.SUPPORTED_REPORT_LANGUAGES)
        self.assertEqual(rl.normalize_report_language("vi"), "vi")
        self.assertEqual(rl.normalize_report_language("vi-VN"), "vi")
        self.assertEqual(rl.normalize_report_language("vietnamese"), "vi")

    def test_sentiment_band_dung_nguong(self):
        expect = [
            (95, "Rất tích cực"), (80, "Rất tích cực"),
            (79, "Tích cực"), (60, "Tích cực"),
            (59, "Trung tính"), (40, "Trung tính"),
            (39, "Tiêu cực"), (20, "Tiêu cực"),
            (19, "Rất tiêu cực"), (0, "Rất tiêu cực"),
        ]
        for score, label in expect:
            self.assertEqual(rl.get_sentiment_label(score, "vi"), label, f"score={score}")

    def test_sentiment_zh_en_khong_bi_doi(self):
        self.assertEqual(rl.get_sentiment_label(95, "en"), "Very Bullish")
        self.assertEqual(rl.get_sentiment_label(95, "zh"), "极度乐观")

    def test_nhan_dien_output_llm_tieng_viet(self):
        """LLM tra tieng Viet -> phai map ve canonical, neu khong DecisionSignal mat tin hieu."""
        cases = [
            (rl.localize_operation_advice, "Mua mạnh", "vi", "Mua mạnh"),
            (rl.localize_operation_advice, "mua", "en", "Buy"),
            (rl.localize_operation_advice, "nắm giữ", "en", "Hold"),
            (rl.localize_operation_advice, "bán", "zh", "卖出"),
            (rl.localize_trend_prediction, "tăng mạnh", "en", "Strong Bullish"),
            (rl.localize_trend_prediction, "đi ngang", "en", "Sideways"),
        ]
        for fn, probe, lang, expected in cases:
            self.assertEqual(fn(probe, lang), expected, f"{fn.__name__}({probe!r}, {lang!r})")

    def test_register_idempotent(self):
        """Goi lai register() khong duoc lam hong gi (import 2 lan, reload...)."""
        before = dict(rl._REPORT_LABELS["vi"])
        vi_overlay.register()
        vi_overlay.register()
        self.assertEqual(rl._REPORT_LABELS["vi"], before)
        self.assertEqual(rl.get_sentiment_label(95, "vi"), "Rất tích cực")

    def test_overlay_khong_doan_khi_upstream_bo_dict(self):
        """Upstream doi ten/bo mot dict -> register() phai bo qua, khong AttributeError."""
        vi_overlay.VI_TRANSLATIONS["_DICT_KHONG_TON_TAI_TRANSLATIONS"] = {"x": "y"}
        try:
            vi_overlay.register()  # khong duoc raise
        finally:
            vi_overlay.VI_TRANSLATIONS.pop("_DICT_KHONG_TON_TAI_TRANSLATIONS", None)

    def test_moi_dict_phang_by_language_deu_co_vi(self):
        """Quet MOI dict phang ``{lang: text}`` trong report_language.py.

        Nhom nay tra thang bang ``d[language]`` nen thieu khoa "vi" la KeyError
        LUC CHAY. Da xay ra that: `AI 分析 HPG(HPG) 失败: 'vi'`
        (logs/api_server_20260625.log) — `_format_prompt` goi `get_unknown_text`
        roi KeyError bi nhanh `except Exception` nuot, moi phan tich tra ve ket
        qua trung tinh gia (score 50) thay vi bao loi.

        Upstream them dict phang moi -> test nay do ngay, khong doi toi runtime.
        """
        import src.report_language as rl

        thieu = []
        for name in dir(rl):
            obj = getattr(rl, name)
            if not isinstance(obj, dict) or not obj:
                continue
            keys = set(obj)
            la_dict_phang = (
                {"zh", "en"} <= keys
                and all(not isinstance(v, dict) for v in obj.values())
            )
            if la_dict_phang and "vi" not in keys:
                thieu.append(name)

        self.assertEqual(
            thieu, [],
            "Dict phang thieu khoa 'vi' -> KeyError luc chay. Them vao "
            "VI_FLAT_BY_LANGUAGE trong src/report_language_vi.py: " + ", ".join(thieu),
        )



if __name__ == "__main__":
    unittest.main()
