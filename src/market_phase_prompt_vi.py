# -*- coding: utf-8 -*-
"""
Bản tiếng Việt của khối prompt "giai đoạn thị trường".

**Vì sao tách file.** Bản trước đây ghi thẳng tiếng Việt vào `_PHASE_LABELS_ZH`
và `_format_zh()` của upstream — nghĩa là biến tên `ZH` thành nội dung `VI`. Ba
hậu quả:

1. Xung đột mỗi lần upstream sửa bất kỳ chuỗi nào trong đó.
2. Upstream thêm một `phase`/`warning` mới → nó về dưới dạng tiếng Trung và đi
   thẳng vào báo cáo tiếng Việt, **không báo lỗi**.
3. `zh` không dùng được nữa. Và khi merge `ko` của upstream về thì `ko` sẽ rơi
   vào nhánh `else → "zh"` và **nhận tiếng Việt**.

Giờ dữ liệu tiếng Việt nằm hết ở đây và đăng ký qua
`market_phase_prompt._EXTRA_FORMATTERS`. File upstream chỉ còn registry + dispatch.

Kiểm chứng bao phủ: `tests/test_market_phase_prompt_vi.py` so key của các dict
`vi` với dict `_ZH` của upstream — upstream thêm phase/warning mới thì test đỏ.
"""

from __future__ import annotations

from typing import Any, Dict, List

_PHASE_LABELS_VI = {
    "premarket": "trước phiên",
    "intraday": "trong phiên",
    "lunch_break": "nghỉ trưa",
    "closing_auction": "gần đóng cửa",
    "postmarket": "sau phiên",
    "non_trading": "ngày không giao dịch",
    "unknown": "giai đoạn chưa rõ",
}

_WARNING_LABELS_VI = {
    "unknown_market": "thị trường chưa rõ",
    "calendar_unavailable": "lịch giao dịch không khả dụng",
    "calendar_error": "lỗi lịch giao dịch",
}


def format_vi(ctx: Dict[str, Any], phase: str) -> str:
    """Dựng khối prompt tiếng Việt (cùng cấu trúc với `_format_zh`/`_format_en`)."""
    from src.market_phase_prompt import _string_value

    label = _PHASE_LABELS_VI.get(phase) or _PHASE_LABELS_VI["unknown"]
    lines = ["", "## Bối cảnh giai đoạn thị trường", f"- Giai đoạn thị trường hiện tại: {label}"]
    lines.extend(_metadata_lines_vi(ctx))
    lines.append(f"- Ràng buộc giai đoạn: {_phase_rule_vi(ctx, phase)}")

    warning_text = _warning_text_vi(ctx.get("warnings"))
    if warning_text:
        lines.append(f"- Ghi chú suy giảm: {warning_text}, hãy giữ cách diễn đạt thận trọng.")

    return "\n".join(lines) + "\n"


def _metadata_lines_vi(ctx: Dict[str, Any]) -> List[str]:
    from src.market_phase_prompt import _int_like, _string_value

    items: List[str] = []
    market = _string_value(ctx.get("market"))
    market_time = _string_value(ctx.get("market_local_time"))
    effective_date = _string_value(ctx.get("effective_daily_bar_date"))
    minutes_to_open = _int_like(ctx.get("minutes_to_open"))
    minutes_to_close = _int_like(ctx.get("minutes_to_close"))

    if market:
        items.append(f"- Thị trường: {market}")
    if market_time:
        items.append(f"- Giờ địa phương thị trường: {market_time}")
    if effective_date:
        items.append(f"- Ngày nến ngày hoàn chỉnh mới nhất có thể tái sử dụng: {effective_date}")
    if minutes_to_open is not None:
        items.append(f"- Còn khoảng {minutes_to_open} phút đến giờ mở cửa phiên thường.")
    if minutes_to_close is not None:
        items.append(f"- Còn khoảng {minutes_to_close} phút đến giờ đóng cửa phiên thường.")
    return items


def _phase_rule_vi(ctx: Dict[str, Any], phase: str) -> str:
    from src.market_phase_prompt import _string_value

    effective_date = _string_value(ctx.get("effective_daily_bar_date"))
    date_hint = f" ({effective_date})" if effective_date else ""

    if phase == "premarket":
        return (
            f'Hiện chưa mở cửa, không được mô tả "diễn biến hôm nay đã xảy ra"; chỉ được '
            f"dựa vào phiên giao dịch hoàn chỉnh gần nhất{date_hint} và thông tin trước "
            "phiên để tạo kế hoạch mở cửa, vùng giá quan sát và phương án phòng ngừa rủi ro."
        )
    if phase in {"intraday", "lunch_break", "closing_auction"}:
        base = (
            "Hiện không phải nhìn lại sau phiên, nên tập trung vào trạng thái trong phiên "
            "hiện tại, điều kiện quan sát và điểm kiểm tra tiếp theo."
        )
        if ctx.get("is_partial_bar") is True:
            base += (
                " Cây nến ngày cuối cùng của hôm nay có thể chưa hoàn thành, không được coi "
                "là nến ngày hoàn chỉnh."
            )
        if phase == "lunch_break":
            base += " Trong giờ nghỉ trưa, cần nêu rõ kết luận sau đó vẫn cần phiên chiều xác nhận."
        if phase == "closing_auction":
            base += (
                " Khi gần đóng cửa nên thiên về kiểm soát rủi ro trước đóng cửa và quyết định "
                "có giữ qua đêm hay không."
            )
        return base
    if phase == "postmarket":
        return (
            "Phiên giao dịch thường đã kết thúc, có thể giữ ngữ nghĩa nhìn lại cho cả ngày "
            "giao dịch hoàn chỉnh."
        )
    if phase == "non_trading":
        return (
            "Hiện không phải ngày giao dịch hoặc thuộc trường hợp chạy cưỡng bức, chỉ được dựa "
            f"vào phiên giao dịch hoàn chỉnh gần nhất{date_hint} và các sự kiện đã biết để phân "
            "tích, không được bịa ra diễn biến trong phiên hôm nay."
        )
    return (
        "Không thể suy luận đáng tin cậy giai đoạn thị trường hiện tại, không bổ sung các sự "
        "kiện trong phiên hoặc trước phiên không tồn tại, kết luận cần giữ thận trọng."
    )


def _warning_text_vi(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    rendered = [
        _WARNING_LABELS_VI[item]
        for item in value
        if isinstance(item, str) and item in _WARNING_LABELS_VI
    ]
    return ", ".join(rendered)


def register() -> None:
    """Đăng ký formatter `vi` vào `market_phase_prompt`. Idempotent."""
    import src.market_phase_prompt as mpp

    mpp._EXTRA_FORMATTERS["vi"] = format_vi


__all__ = ["format_vi", "register", "_PHASE_LABELS_VI", "_WARNING_LABELS_VI"]
