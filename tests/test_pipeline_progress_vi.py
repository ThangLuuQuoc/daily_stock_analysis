"""fork VN: dich thong bao tien trinh cua `src/core/pipeline.py`.

Truoc day fork dich thang 11 chuoi `_emit_progress()` tai cho, xoa han ban
tieng Trung cua upstream. Nay template tieng Trung giu nguyen tai cho lam khoa
tra cuu, `StockAnalysisPipeline._tr()` dich khi ngon ngu la `vi`.
"""

import unittest
from types import SimpleNamespace

from src.core.pipeline import StockAnalysisPipeline
from src.core.pipeline_progress_vi import PROGRESS_VI


def _pipeline(report_language=None):
    """Pipeline toi thieu; report_language=None nghia la KHONG co self.config."""
    o = StockAnalysisPipeline.__new__(StockAnalysisPipeline)
    if report_language is not None:
        o.config = SimpleNamespace(report_language=report_language)
    return o


class PipelineProgressViTest(unittest.TestCase):
    KEY = "{code}：正在准备分析任务"

    def test_vi_duoc_dich(self):
        out = _pipeline("vi")._tr(self.KEY, code="VIC")
        self.assertEqual(out, "VIC: Đang chuẩn bị tác vụ phân tích")

    def test_ngon_ngu_khac_giu_ban_upstream(self):
        for lang in ("zh", "en", "ko"):
            with self.subTest(lang=lang):
                out = _pipeline(lang)._tr(self.KEY, code="VIC")
                self.assertEqual(out, "VIC：正在准备分析任务")

    def test_khoa_chua_dich_tra_ve_nguyen_van(self):
        """Upstream them thong bao moi -> hien tieng Trung, KHONG nem KeyError."""
        out = _pipeline("vi")._tr("{code}：thong bao moi cua upstream", code="VIC")
        self.assertEqual(out, "VIC：thong bao moi cua upstream")

    def test_khong_co_self_config_van_chay(self):
        """BAY DA GAP THAT.

        `getattr(self.config, ...)` nem AttributeError khi pipeline duoc dung qua
        `__new__` hoac mock mot phan (nhieu test upstream lam vay). Loi bi nhanh
        `except` cua process_single_stock nuot -> ham tra ve None -> 6 test
        upstream do voi thong bao 'unexpectedly None', rat kho truy nguyen.

        Mot dong thong bao tien trinh khong bao gio duoc phep lam vo phan tich.
        """
        out = _pipeline(None)._tr(self.KEY, code="VIC")
        self.assertEqual(out, "VIC：正在准备分析任务")

    def test_thieu_kwarg_khong_lam_vo(self):
        """Noi suy that bai -> tra ve template tho, khong nem KeyError."""
        out = _pipeline("vi")._tr(self.KEY)
        self.assertIn("正在准备分析任务", out)

    def test_moi_khoa_deu_ton_tai_trong_pipeline(self):
        """Bang dich khong duoc troi xa: moi khoa phai co that trong pipeline.py.

        Upstream doi mot thong bao -> khoa cu thanh mo, thong bao moi khong duoc
        dich ma khong ai biet. Test nay bat ngay.
        """
        import io
        src = io.open("src/core/pipeline.py", encoding="utf-8").read()
        mo = [k for k in PROGRESS_VI if k not in src]
        self.assertEqual(
            mo, [],
            "Khoa trong PROGRESS_VI khong con trong pipeline.py (upstream da doi "
            "thong bao?). Cap nhat src/core/pipeline_progress_vi.py: " + str(mo),
        )


if __name__ == "__main__":
    unittest.main()
