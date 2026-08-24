# -*- coding: utf-8 -*-
"""
Bảng nhãn tiếng Việt cho `src/market_phase_summary.py`.

File này chỉ chứa **dữ liệu**, không có logic — vì `market_phase_summary.py` cũng
chỉ dùng các bảng nhãn để dựng một dòng gọn (`Trạng thái thị trường: VN · trong
phiên`), không có prose phức tạp.

Trước đây bản fork ghi thẳng tiếng Việt vào `_PHASE_LABELS_ZH`, `_MARKET_LABELS_ZH`,
`_PUBLIC_SOURCE_LABELS_ZH` và `_MARKET_STATUS_PREFIX["zh"]` của upstream. Hệ quả:
`zh` mất hẳn, và upstream thêm một `phase` mới thì nó về tiếng Trung rồi đi thẳng
vào báo cáo tiếng Việt mà không báo lỗi.

Bao phủ được kiểm bằng `tests/test_market_phase_summary_vi.py`: so key của bảng
`vi` với bảng `_ZH` của upstream — upstream thêm phase/market/source mới thì test đỏ.
"""

from __future__ import annotations

from typing import Dict

# Giai đoạn phiên. Key phải khớp `_PHASE_LABELS_ZH` của upstream.
PHASE_LABELS_VI: Dict[str, str] = {
    "premarket": "trước phiên",
    "intraday": "trong phiên",
    "lunch_break": "nghỉ trưa",
    "closing_auction": "gần đóng cửa",
    "postmarket": "sau phiên",
    "non_trading": "ngày không giao dịch",
    "unknown": "giai đoạn chưa rõ",
}

# Tên thị trường. Giữ "A-share" (không dịch) vì đó là cách gọi phổ biến trong
# tiếng Việt cho thị trường Trung Quốc đại lục.
MARKET_LABELS_VI: Dict[str, str] = {
    "cn": "A-share",
    "hk": "Hồng Kông",
    "us": "Mỹ",
    "vn": "Việt Nam",
}

# Nguồn dữ liệu hiển thị cho người dùng.
SOURCE_LABELS_VI: Dict[str, str] = {
    "alert_trigger_market_context": "bối cảnh kích hoạt cảnh báo",
    "analysis_history_snapshot": "ảnh chụp phân tích gần nhất",
    "evaluator_snapshot": "ảnh chụp bộ đánh giá",
    "legacy_text": "văn bản cũ",
}

STATUS_PREFIX_VI = "Trạng thái thị trường"
SEPARATOR_VI = ": "


def register() -> None:
    """Đăng ký bảng nhãn `vi` vào `market_phase_summary`. Idempotent."""
    import src.market_phase_summary as mps

    mps._EXTRA_PHASE_LABELS["vi"] = dict(PHASE_LABELS_VI)
    mps._EXTRA_MARKET_LABELS["vi"] = dict(MARKET_LABELS_VI)
    mps._EXTRA_SOURCE_LABELS["vi"] = dict(SOURCE_LABELS_VI)
    mps._EXTRA_STATUS_PREFIX["vi"] = STATUS_PREFIX_VI
    mps._EXTRA_SEPARATOR["vi"] = SEPARATOR_VI


__all__ = [
    "PHASE_LABELS_VI",
    "MARKET_LABELS_VI",
    "SOURCE_LABELS_VI",
    "STATUS_PREFIX_VI",
    "SEPARATOR_VI",
    "register",
]
