"""Chan cac bang tra cuu tieng Viet TROI XA khoi upstream.

Ba bang duoi day dung khoa = literal tieng Trung cua upstream, giu nguyen tai
cho trong file upstream. Khi upstream doi mot chuoi, khoa cu thanh MO: khong
con khop nen chuoi moi am tham khong duoc dich, va khong ai biet.

Test nay bat truong hop do ngay tai CI thay vi de nguoi dung phat hien qua bao
cao sai ngon ngu.
"""

import io
import unittest


def _doc(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class LookupTableDriftTest(unittest.TestCase):
    def _kiem_tra(self, table, ten_bang, ten_file, *files):
        """Moi khoa phai xuat hien trong it nhat mot file upstream."""
        noi_dung = "\n".join(_doc(f) for f in files)
        mo = [k for k in table if k not in noi_dung]
        self.assertEqual(
            mo, [],
            f"{len(mo)} khoa trong {ten_bang} khong con trong {', '.join(files)} "
            f"(upstream da doi chuoi?). Cap nhat {ten_file}:\n  "
            + "\n  ".join(repr(k) for k in mo),
        )

    def test_prompt_labels_vi(self):
        from src.analyzer_prompts_vi import PROMPT_LABELS_VI

        self._kiem_tra(
            PROMPT_LABELS_VI, "PROMPT_LABELS_VI", "src/analyzer_prompts_vi.py",
            "src/analyzer.py",
        )

    def test_api_messages_vi(self):
        from api.v1.messages_vi import API_MESSAGES_VI

        self._kiem_tra(
            API_MESSAGES_VI, "API_MESSAGES_VI", "api/v1/messages_vi.py",
            "api/v1/endpoints/analysis.py",
            "api/v1/endpoints/stocks.py",
            "api/middlewares/error_handler.py",
        )

    def test_progress_vi(self):
        from src.core.pipeline_progress_vi import PROGRESS_VI

        self._kiem_tra(
            PROGRESS_VI, "PROGRESS_VI", "src/core/pipeline_progress_vi.py",
            "src/core/pipeline.py",
        )


class KhongTraKeyErrorTest(unittest.TestCase):
    """Khoa chua dich phai tra ve nguyen van, khong bao gio nem KeyError."""

    def test_prompt_label(self):
        from src.analyzer_prompts_vi import label

        self.assertEqual(label("某个新标签", "vi"), "某个新标签")
        self.assertEqual(label("今日行情", "zh"), "今日行情")

    def test_api_msg(self):
        from api.v1.messages_vi import msg

        self.assertEqual(msg("某个新消息"), "某个新消息")

    def test_progress(self):
        from src.core.pipeline_progress_vi import translate

        self.assertEqual(translate("某个新进度", "vi"), "某个新进度")
        self.assertEqual(translate("某个新进度", "zh"), "某个新进度")


if __name__ == "__main__":
    unittest.main()
