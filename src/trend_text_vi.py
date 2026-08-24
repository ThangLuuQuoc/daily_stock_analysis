# -*- coding: utf-8 -*-
"""
Bản tiếng Việt của các chuỗi phân tích xu hướng (`stock_analyzer`).

**Vì sao KHÔNG dịch thẳng trong `stock_analyzer.py`** — bản fork trước đây làm
vậy và tạo ra một bug thật, đã kiểm chứng bằng cách chạy:

    _infer_trend_direction() trong analyzer.py PARSE chuỗi `trend_status` +
    `ma_alignment` để suy ra bullish/bearish.

Nó khớp theo `_BULLISH_TREND_HINTS` (tiếng Trung + "bullish"/"uptrend") hoặc
fallback theo mẫu `MA5>MA10>MA20`. Chuỗi tiếng Việt không có cả hai:

    | Trạng thái  | upstream (zh) | fork dịch tại chỗ (vi) |
    |-------------|---------------|------------------------|
    | STRONG_BULL | bullish       | **neutral**  ← SAI     |
    | STRONG_BEAR | bearish       | **neutral**  ← SAI     |

Đúng hai trạng thái **mạnh nhất** bị hạ xuống trung tính, vì
`强势多头排列，均线发散上行` có chứa `多头排列` (nằm trong hint list) còn
`Xu hướng tăng mạnh, các đường MA phân kỳ đi lên` thì không chứa gì cả. Các
trạng thái còn lại thoát được nhờ tình cờ giữ lại `MA5>MA10>MA20` trong chuỗi.

Nên giờ: `stock_analyzer.py` giữ **nguyên bản upstream** (giá trị canonical nội
bộ, parser hoạt động đúng), và bản dịch chỉ áp ở **biên dựng prompt**.

Hai lớp bảo vệ:
1. `localize_trend_for_prompt()` — dịch ở biên, không ảnh hưởng parser.
2. `register_trend_hints()` — nạp thêm keyword tiếng Việt vào hint list của
   `analyzer.py`, để nếu chuỗi tiếng Việt có lọt vào parser (LLM trả về, hoặc
   một call-site khác) thì vẫn suy luận đúng thay vì âm thầm ra `neutral`.

Bao phủ: `tests/test_trend_text_vi.py` khẳng định mọi chuỗi mà
`stock_analyzer.py` gán đều có bản dịch, và `_infer_trend_direction` cho cùng
kết quả với cả chuỗi zh lẫn vi.
"""

from __future__ import annotations

from typing import Any, Dict

# Khóa = chuỗi upstream gán vào `result.ma_alignment`. Nếu upstream đổi chuỗi,
# test bao phủ sẽ đỏ (không tự đoán, không im lặng bỏ qua).
MA_ALIGNMENT_VI: Dict[str, str] = {
    "强势多头排列，均线发散上行": "Xu hướng tăng mạnh, các đường MA phân kỳ đi lên (MA5>MA10>MA20)",
    "多头排列 MA5>MA10>MA20": "Xu hướng tăng MA5>MA10>MA20",
    "弱势多头，MA5>MA10 但 MA10≤MA20": "Xu hướng tăng yếu, MA5>MA10 nhưng MA10≤MA20",
    "均线缠绕，趋势不明": "Các đường MA đan xen, xu hướng không rõ",
    "弱势空头，MA5<MA10 但 MA10≥MA20": "Xu hướng giảm yếu, MA5<MA10 nhưng MA10≥MA20",
    "空头排列 MA5<MA10<MA20": "Xu hướng giảm MA5<MA10<MA20",
    "强势空头排列，均线发散下行": "Xu hướng giảm mạnh, các đường MA phân kỳ đi xuống (MA5<MA10<MA20)",
}

VOLUME_TREND_VI: Dict[str, str] = {
    "放量上涨，多头力量强劲": "Tăng kèm khối lượng lớn, lực mua mạnh",
    "放量下跌，注意风险": "Giảm kèm khối lượng lớn, chú ý rủi ro",
    "缩量上涨，上攻动能不足": "Tăng kèm khối lượng thấp, động lực đi lên yếu",
    "缩量回调，洗盘特征明显（好）": "Điều chỉnh kèm khối lượng thấp, đặc điểm rũ hàng rõ (tốt)",
    "量能正常": "Khối lượng bình thường",
}

# Giá trị enum `TrendStatus` / `VolumeStatus` (dùng cho cột "trạng thái").
TREND_STATUS_VI: Dict[str, str] = {
    "强势多头": "Tăng mạnh",
    "多头排列": "Xu hướng tăng",
    "弱势多头": "Tăng yếu",
    "盘整": "Đi ngang",
    "弱势空头": "Giảm yếu",
    "空头排列": "Xu hướng giảm",
    "强势空头": "Giảm mạnh",
}

VOLUME_STATUS_VI: Dict[str, str] = {
    "放量上涨": "Tăng kèm khối lượng lớn",
    "放量下跌": "Giảm kèm khối lượng lớn",
    "缩量上涨": "Tăng kèm khối lượng thấp",
    "缩量下跌": "Giảm kèm khối lượng thấp",
    "缩量回调": "Điều chỉnh kèm khối lượng thấp",
    "量能正常": "Khối lượng bình thường",
}

# Keyword tiếng Việt cho `_infer_trend_direction`. Chỉ dùng cụm mang hướng rõ
# ràng — "Xu hướng tăng" / "Xu hướng giảm" — tránh từ đơn dễ nhập nhằng.
VI_BULLISH_HINTS = ("xu hướng tăng", "tăng mạnh")
VI_BEARISH_HINTS = ("xu hướng giảm", "giảm mạnh")
VI_WEAK_BULLISH_HINTS = ("tăng yếu",)
VI_WEAK_BEARISH_HINTS = ("giảm yếu",)

_FIELD_MAPS = {
    "ma_alignment": MA_ALIGNMENT_VI,
    "volume_trend": VOLUME_TREND_VI,
    "trend_status": TREND_STATUS_VI,
    "volume_status": VOLUME_STATUS_VI,
}


def localize_trend_for_prompt(trend: Any, report_language: str) -> Any:
    """Trả về bản copy của dict `trend` với các chuỗi hiển thị đã dịch.

    Chỉ dịch khi `report_language == "vi"`; ngôn ngữ khác trả về nguyên trạng
    (không copy) để không đổi hành vi upstream. Chuỗi không có trong map được
    **giữ nguyên** thay vì trả rỗng — thà hiện tiếng Trung còn hơn mất dữ liệu,
    và test bao phủ sẽ báo chỗ thiếu.
    """
    if str(report_language or "").lower() != "vi" or not isinstance(trend, dict):
        return trend

    localized = dict(trend)
    for field, mapping in _FIELD_MAPS.items():
        value = localized.get(field)
        if isinstance(value, str) and value in mapping:
            localized[field] = mapping[value]
    return localized


def register_trend_hints() -> None:
    """Nạp keyword tiếng Việt vào hint list của `analyzer.py`.

    Lớp phòng thủ thứ hai: nếu chuỗi tiếng Việt lọt vào `_infer_trend_direction`
    (LLM trả về, hoặc một call-site chưa localize) thì vẫn suy luận đúng hướng
    thay vì âm thầm ra `neutral` — đúng bug đã xảy ra trước Phase 3.
    Idempotent.
    """
    import src.analyzer as az

    def _extend(name: str, extra: tuple) -> None:
        current = getattr(az, name, None)
        if not isinstance(current, tuple):
            return
        missing = tuple(h for h in extra if h not in current)
        if missing:
            setattr(az, name, current + missing)

    _extend("_BULLISH_TREND_HINTS", VI_BULLISH_HINTS)
    _extend("_BEARISH_TREND_HINTS", VI_BEARISH_HINTS)
    _extend("_WEAK_BULLISH_TREND_HINTS", VI_WEAK_BULLISH_HINTS)
    _extend("_WEAK_BEARISH_TREND_HINTS", VI_WEAK_BEARISH_HINTS)


__all__ = [
    "MA_ALIGNMENT_VI",
    "VOLUME_TREND_VI",
    "TREND_STATUS_VI",
    "VOLUME_STATUS_VI",
    "localize_trend_for_prompt",
    "register_trend_hints",
]
