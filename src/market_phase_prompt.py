# -*- coding: utf-8 -*-
"""Prompt rendering for Issue #1386 runtime market phase context."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


_PHASE_LABELS_ZH = {
    "premarket": "trước phiên",
    "intraday": "trong phiên",
    "lunch_break": "nghỉ trưa",
    "closing_auction": "gần đóng cửa",
    "postmarket": "sau phiên",
    "non_trading": "ngày không giao dịch",
    "unknown": "giai đoạn chưa rõ",
}

_PHASE_LABELS_EN = {
    "premarket": "pre-market",
    "intraday": "intraday",
    "lunch_break": "lunch break",
    "closing_auction": "near close",
    "postmarket": "post-market",
    "non_trading": "non-trading day",
    "unknown": "unknown phase",
}

_KNOWN_PHASES = set(_PHASE_LABELS_ZH)

_WARNING_LABELS_ZH = {
    "unknown_market": "thị trường chưa rõ",
    "calendar_unavailable": "lịch giao dịch không khả dụng",
    "calendar_error": "lỗi lịch giao dịch",
}

_WARNING_LABELS_EN = {
    "unknown_market": "unknown market",
    "calendar_unavailable": "trading calendar unavailable",
    "calendar_error": "trading calendar error",
}


def format_market_phase_prompt_section(
    market_phase_context: Optional[Dict[str, Any]],
    *,
    report_language: str = "zh",
) -> str:
    """Return a human-readable prompt section for a P1a market phase payload.

    The helper is intentionally narrow: callers pass the runtime dict produced
    by ``MarketPhaseContext.to_dict()`` when available. Missing optional fields
    are omitted, unknown phases use the conservative ``unknown`` template, and
    raw runtime keys such as ``market_phase_context`` are never rendered.
    """
    if not isinstance(market_phase_context, dict) or not market_phase_context:
        return ""

    lang = "en" if str(report_language or "").lower() == "en" else "zh"
    raw_phase = market_phase_context.get("phase")
    phase = raw_phase if isinstance(raw_phase, str) and raw_phase in _KNOWN_PHASES else "unknown"

    if lang == "en":
        return _format_en(market_phase_context, phase)
    return _format_zh(market_phase_context, phase)


def _format_zh(ctx: Dict[str, Any], phase: str) -> str:
    label = _PHASE_LABELS_ZH[phase]
    lines = ["", "## Bối cảnh giai đoạn thị trường", f"- Giai đoạn thị trường hiện tại: {label}"]
    lines.extend(_metadata_lines_zh(ctx))
    lines.append(f"- Ràng buộc giai đoạn: {_phase_rule_zh(ctx, phase)}")

    warning_text = _warning_text(ctx.get("warnings"), lang="zh")
    if warning_text:
        lines.append(f"- Ghi chú suy giảm: {warning_text}, hãy giữ cách diễn đạt thận trọng.")

    return "\n".join(lines) + "\n"


def _format_en(ctx: Dict[str, Any], phase: str) -> str:
    label = _PHASE_LABELS_EN[phase]
    lines = ["", "## Market Phase Context", f"- Current market phase: {label}"]
    lines.extend(_metadata_lines_en(ctx))
    lines.append(f"- Phase constraint: {_phase_rule_en(ctx, phase)}")

    warning_text = _warning_text(ctx.get("warnings"), lang="en")
    if warning_text:
        lines.append(f"- Degradation note: {warning_text}; keep the analysis conservative.")

    return "\n".join(lines) + "\n"


def _metadata_lines_zh(ctx: Dict[str, Any]) -> List[str]:
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


def _metadata_lines_en(ctx: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    market = _string_value(ctx.get("market"))
    market_time = _string_value(ctx.get("market_local_time"))
    effective_date = _string_value(ctx.get("effective_daily_bar_date"))
    minutes_to_open = _int_like(ctx.get("minutes_to_open"))
    minutes_to_close = _int_like(ctx.get("minutes_to_close"))

    if market:
        items.append(f"- Market: {market}")
    if market_time:
        items.append(f"- Market-local time: {market_time}")
    if effective_date:
        items.append(f"- Latest reusable complete daily bar date: {effective_date}")
    if minutes_to_open is not None:
        items.append(f"- About {minutes_to_open} minutes until the regular session opens.")
    if minutes_to_close is not None:
        items.append(f"- About {minutes_to_close} minutes until the regular session closes.")
    return items


def _phase_rule_zh(ctx: Dict[str, Any], phase: str) -> str:
    effective_date = _string_value(ctx.get("effective_daily_bar_date"))
    date_hint = f" ({effective_date})" if effective_date else ""

    if phase == "premarket":
        return (
            f"Hiện chưa mở cửa, không được mô tả \"diễn biến hôm nay đã xảy ra\"; chỉ được dựa vào phiên giao dịch hoàn chỉnh gần nhất{date_hint} "
            "và thông tin trước phiên để tạo kế hoạch mở cửa, vùng giá quan sát và phương án phòng ngừa rủi ro."
        )
    if phase in {"intraday", "lunch_break", "closing_auction"}:
        base = "Hiện không phải phục thị sau phiên, nên tập trung vào trạng thái trong phiên hiện tại, điều kiện quan sát và điểm kiểm tra tiếp theo."
        if ctx.get("is_partial_bar") is True:
            base += " Cây nến ngày cuối cùng của hôm nay có thể chưa hoàn thành, không được coi là phục thị nến ngày hoàn chỉnh."
        if phase == "lunch_break":
            base += " Trong giờ nghỉ trưa, cần nêu rõ việc phục thị sau đó vẫn cần phiên chiều xác nhận."
        if phase == "closing_auction":
            base += " Khi gần đóng cửa nên thiên về kiểm soát rủi ro trước đóng cửa và quyết định có giữ qua đêm hay không."
        return base
    if phase == "postmarket":
        return "Phiên giao dịch thường đã kết thúc, có thể giữ ngữ nghĩa phục thị cho cả ngày giao dịch hoàn chỉnh."
    if phase == "non_trading":
        return f"Hiện không phải ngày giao dịch hoặc thuộc trường hợp chạy cưỡng bức, chỉ được dựa vào phiên giao dịch hoàn chỉnh gần nhất{date_hint} và các sự kiện đã biết để phân tích, không được bịa ra diễn biến trong phiên hôm nay."
    return "Không thể suy luận đáng tin cậy giai đoạn thị trường hiện tại, không bổ sung các sự kiện trong phiên hoặc trước phiên không tồn tại, kết luận cần giữ thận trọng."


def _phase_rule_en(ctx: Dict[str, Any], phase: str) -> str:
    effective_date = _string_value(ctx.get("effective_daily_bar_date"))
    date_hint = f" ({effective_date})" if effective_date else ""

    if phase == "premarket":
        return (
            f"The regular session has not opened. Do not describe today's price action as already happened; "
            f"use only the latest complete daily bar{date_hint} and pre-market information for the opening plan."
        )
    if phase in {"intraday", "lunch_break", "closing_auction"}:
        base = "This is not a post-market recap. Focus on the current intraday state, watch conditions, and next check point."
        if ctx.get("is_partial_bar") is True:
            base += " The latest daily bar may be unfinished; do not treat it as a complete daily candle."
        if phase == "lunch_break":
            base += " During the lunch break, later confirmation depends on the afternoon session."
        if phase == "closing_auction":
            base += " Near the close, emphasize end-of-day risk control and overnight-position decisions."
        return base
    if phase == "postmarket":
        return "The regular session has ended, so a complete-session recap style is acceptable."
    if phase == "non_trading":
        return (
            f"This is a non-trading day or forced run. Use the latest complete daily bar{date_hint} and known events; "
            "do not invent today's intraday movement."
        )
    return "The market phase cannot be inferred reliably. Do not invent pre-market or intraday facts, and keep conclusions conservative."


def _warning_text(value: Any, *, lang: str) -> str:
    if not isinstance(value, list):
        return ""
    labels = _WARNING_LABELS_EN if lang == "en" else _WARNING_LABELS_ZH
    rendered = [labels[item] for item in value if isinstance(item, str) and item in labels]
    if not rendered:
        return ""
    if lang == "en":
        return ", ".join(rendered)
    return ", ".join(rendered)


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _int_like(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None
