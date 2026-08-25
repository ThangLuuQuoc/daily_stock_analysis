# -*- coding: utf-8 -*-
"""
Lớp phủ (overlay) tiếng Việt cho ``src/report_language.py``.

**Vì sao tồn tại file này.** Upstream lưu bản dịch theo hình dạng
``key -> {lang: text}``::

    _OPERATION_ADVICE_TRANSLATIONS = {
        "buy": {"zh": "买入", "en": "Buy", "ko": "매수"},
    }

Thêm một ngôn ngữ theo cách đó nghĩa là **sửa từng dòng** của mọi dict — đúng chỗ
mà upstream cũng sửa khi họ thêm ngôn ngữ của họ (v3.25.0 thêm ``ko``). Đó là
nguyên nhân của 13 hunk xung đột trong ``report_language.py`` khi merge lên
v3.31.0.

File này giữ **toàn bộ** dữ liệu tiếng Việt ở một chỗ và tiêm vào các dict của
upstream lúc import. ``report_language.py`` chỉ còn 3 điểm chạm nhỏ (xem
``docs/vn-fork-touchpoints.md``). Cách này hợp lệ vì mọi hàm tra cứu của upstream
(``_translate_from_map`` / ``get_report_labels`` / ``localize_*``) đọc dict ở
module level **lúc runtime**, không snapshot lúc định nghĩa.

**Bẫy cần biết.** ``_translate_from_map`` dùng ``translations[canonical][lang]``
— thiếu key là ``KeyError``, không phải fallback. Nên nếu upstream thêm một
canonical key mới mà overlay chưa dịch thì sẽ **nổ lúc chạy**. Đó là lý do có
``tests/test_report_language_vi_coverage.py``: nó quét mọi ``*_TRANSLATIONS`` và
bắt buộc mỗi canonical key phải có entry ``vi``. Upstream thêm key mới → test đỏ
ngay, thay vì rò tiếng Trung (hoặc crash) trong báo cáo.
"""

from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# 1. Bản dịch nhãn canonical  (bơm vào các dict ``*_TRANSLATIONS``)
# ---------------------------------------------------------------------------
VI_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # --- v3.27.0: multi-strategy opinion synthesis ---
    "_CONFLICT_SEVERITY_TRANSLATIONS": {
        "none": "Không",
        "low": "Thấp",
        "medium": "Trung bình",
        "high": "Cao",
    },
    "_CONSENSUS_LEVEL_TRANSLATIONS": {
        "high": "Cao",
        "medium": "Trung bình",
        "low": "Thấp",
        "insufficient": "Không đủ bằng chứng",
    },
    "_STRATEGY_SIGNAL_TRANSLATIONS": {
        "strong_buy": "Mua mạnh",
        "buy": "Mua",
        "hold": "Nắm giữ",
        "sell": "Bán",
        "strong_sell": "Bán mạnh",
    },
    "_STRATEGY_SKILL_TRANSLATIONS": {
        "bull_trend": "Xu hướng tăng mặc định",
        "hot_theme": "Chủ đề nóng",
        "volume_breakout": "Bứt phá kèm khối lượng",
        "ma_golden_cross": "Giao cắt vàng đường MA",
        "growth_quality": "Chất lượng tăng trưởng",
        "bottom_volume": "Khối lượng tại đáy",
        "box_oscillation": "Dao động trong hộp",
        "chan_theory": "Cấu trúc lý thuyết Chan",
        "dragon_head": "Chiến pháp cổ phiếu dẫn dắt",
        "emotion_cycle": "Chu kỳ tâm lý",
        "event_driven": "Dẫn dắt bởi sự kiện",
        "expectation_repricing": "Định giá lại kỳ vọng",
        "one_yang_three_yin": "Một dương ba âm",
        "shrink_pullback": "Điều chỉnh kèm khối lượng thấp",
        "wave_theory": "Lý thuyết sóng",
    },
    "_BIAS_STATUS_TRANSLATIONS": {
        "safe": "An toàn",
        "caution": "Cảnh giác",
        "danger": "Nguy hiểm",
    },
    "_CHIP_HEALTH_TRANSLATIONS": {
        "healthy": "Lành mạnh",
        "average": "Trung bình",
        "caution": "Thận trọng",
    },
    "_CONFIDENCE_LEVEL_TRANSLATIONS": {
        "high": "Cao",
        "medium": "Trung bình",
        "low": "Thấp",
    },
    "_OPERATION_ADVICE_TRANSLATIONS": {
        "strong_buy": "Mua mạnh",
        "buy": "Mua",
        "hold": "Nắm giữ",
        "watch": "Quan sát",
        "reduce": "Giảm tỷ trọng",
        "sell": "Bán",
        "strong_sell": "Bán mạnh",
    },
    "_TREND_PREDICTION_TRANSLATIONS": {
        "strong_bullish": "Rất tích cực",
        "bullish": "Tích cực",
        "sideways": "Đi ngang",
        "bearish": "Tiêu cực",
        "strong_bearish": "Rất tiêu cực",
    },
}

# ---------------------------------------------------------------------------
# 2. Nhận diện output tiếng Việt của LLM  (bơm vào các ``*_CANONICAL_MAP``)
#    Không có phần này thì LLM trả "Mua mạnh" sẽ không map về canonical
#    ``strong_buy``, và DecisionSignal / thống kê hiệu suất sẽ mất tín hiệu.
# ---------------------------------------------------------------------------
VI_CANONICAL_ALIASES: Dict[str, Dict[str, str]] = {
    "_BIAS_STATUS_CANONICAL_MAP": {
        "an toàn": "safe",
        "cảnh giác": "caution",
        "nguy hiểm": "danger",
    },
    "_CHIP_HEALTH_CANONICAL_MAP": {
        "lành mạnh": "healthy",
        "trung bình": "average",
        "thận trọng": "caution",
        "cảnh báo": "caution",
    },
    "_CONFIDENCE_LEVEL_CANONICAL_MAP": {
        "cao": "high",
        "trung bình": "medium",
        "thấp": "low",
    },
    "_OPERATION_ADVICE_CANONICAL_MAP": {
        "mua mạnh": "strong_buy",
        "mua": "buy",
        "mua thêm": "buy",
        "gia tăng": "buy",
        "nắm giữ": "hold",
        "giữ": "hold",
        "quan sát": "hold",
        "theo dõi": "hold",
        "giảm tỷ trọng": "reduce",
        "bán": "sell",
        "bán mạnh": "strong_sell",
        "tránh": "sell",
    },
    "_TREND_PREDICTION_CANONICAL_MAP": {
        "rất tích cực": "strong_bullish",
        "tăng mạnh": "strong_bullish",
        "tích cực": "bullish",
        "tăng giá": "bullish",
        "đi ngang": "sideways",
        "dao động": "sideways",
        "tiêu cực": "bearish",
        "giảm giá": "bearish",
        "rất tiêu cực": "strong_bearish",
        "giảm mạnh": "strong_bearish",
    },
}

# ---------------------------------------------------------------------------
# 3. Alias mã ngôn ngữ  (bơm vào ``_REPORT_LANGUAGE_ALIASES``)
# ---------------------------------------------------------------------------
VI_LANGUAGE_ALIASES: Dict[str, str] = {
    "vi-vn": "vi",
    "vi_vn": "vi",
    "vietnamese": "vi",
    "tieng_viet": "vi",
    "vn": "vi",
}

# ---------------------------------------------------------------------------
# 4. Nhãn báo cáo  (bơm vào ``_REPORT_LABELS["vi"]``)
#    Hình dạng ``lang -> {key: text}`` nên về lý thuyết thêm block "vi" vào
#    upstream cũng merge được, nhưng để hết dữ liệu vi ở một file thì dễ rà soát
#    và dễ thêm ngôn ngữ thứ tư hơn.
# ---------------------------------------------------------------------------
VI_REPORT_LABELS: Dict[str, str] = {
    # --- v3.27.0: nhan multi-strategy synthesis ---
    "strategy_synthesis_heading": "Tổng hợp đa chiến lược",
    "strategy_summary_label": "Tóm tắt chiến lược",
    "strategy_final_signal_label": "Tín hiệu cuối cùng",
    "strategy_consensus_level_label": "Mức đồng thuận",
    "strategy_conflict_label": "Mức xung đột",
    "strategy_confidence_label": "Độ tin cậy",
    "strategy_supporting_skills_label": "Chiến lược ủng hộ",
    "strategy_opposing_skills_label": "Chiến lược phản đối",
    "strategy_invalid_opinions_label": "Ý kiến không hợp lệ",
    "none_label": "Không có",
    # --- v3.25.0: dong tien 3 nhom to chuc (dac thu thi truong Dai Loan) ---
    "institutional_flow_heading": "Động thái ba nhóm tổ chức",
    "institutional_flow_note": "Số dương = mua ròng, số âm = bán ròng; đơn vị: cổ phiếu.",
    "inst_total_label": "Tổng ba nhóm tổ chức",
    "inst_foreign_label": "Khối ngoại",
    "inst_trust_label": "Quỹ đầu tư nội",
    "inst_dealer_label": "Tự doanh",
    # --- v3.24.0: signal attribution + industry/concept boards ---
    "signal_attribution_heading": "Phân tích quy kết tín hiệu",
    "attribution_weights_label": "Trọng số quy kết",
    "technical_indicators_label": "Chỉ báo kỹ thuật",
    "news_sentiment_label": "Tin tức và tâm lý",
    "fundamentals_label": "Yếu tố cơ bản",
    "market_conditions_label": "Bối cảnh thị trường",
    "strongest_bullish_signal_label": "Tín hiệu tăng giá mạnh nhất",
    "strongest_bearish_signal_label": "Tín hiệu giảm giá mạnh nhất",
    "industry_boards_heading": "Nhóm ngành",
    "concept_boards_heading": "Nhóm chủ đề",
    "dashboard_title": "Bảng điều khiển quyết định",
    "brief_title": "Báo cáo quyết định",
    "analyzed_prefix": "Đã phân tích",
    "stock_unit": "cổ phiếu",
    "stock_unit_compact": "mã",
    "buy_label": "Mua",
    "watch_label": "Quan sát",
    "sell_label": "Bán",
    "summary_heading": "Tóm tắt",
    "info_heading": "Thông tin quan trọng",
    "sentiment_summary_label": "Tâm lý thị trường",
    "earnings_outlook_label": "Triển vọng lợi nhuận",
    "risk_alerts_label": "Cảnh báo rủi ro",
    "positive_catalysts_label": "Yếu tố hỗ trợ",
    "latest_news_label": "Tin tức mới nhất",
    "core_conclusion_heading": "Nhận định cốt lõi",
    "one_sentence_label": "Quyết định một câu",
    "time_sensitivity_label": "Tính thời điểm",
    "default_time_sensitivity": "Trong tuần này",
    "position_status_label": "Tình trạng nắm giữ",
    "action_advice_label": "Khuyến nghị hành động",
    "no_position_label": "Chưa có vị thế",
    "has_position_label": "Đang nắm giữ",
    "continue_holding": "Tiếp tục nắm giữ",
    "market_snapshot_heading": "Diễn biến trong ngày",
    "close_label": "Đóng cửa",
    "prev_close_label": "Đóng cửa phiên trước",
    "open_label": "Mở cửa",
    "high_label": "Cao nhất",
    "low_label": "Thấp nhất",
    "change_pct_label": "Thay đổi (%)",
    "change_amount_label": "Thay đổi",
    "amplitude_label": "Biên độ",
    "volume_label": "Khối lượng",
    "amount_label": "Giá trị giao dịch",
    "current_price_label": "Giá hiện tại",
    "volume_ratio_label": "Tỷ lệ khối lượng",
    "turnover_rate_label": "Tỷ lệ thanh khoản",
    "source_label": "Nguồn dữ liệu",
    "data_perspective_heading": "Phân tích dữ liệu",
    "ma_alignment_label": "Sắp xếp đường MA",
    "bullish_alignment_label": "Sắp xếp tăng giá",
    "yes_label": "Có",
    "no_label": "Không",
    "trend_strength_label": "Sức mạnh xu hướng",
    "price_metrics_label": "Chỉ số giá",
    "ma5_label": "MA5",
    "ma10_label": "MA10",
    "ma20_label": "MA20",
    "bias_ma5_label": "Độ lệch (MA5)",
    "support_level_label": "Hỗ trợ",
    "resistance_level_label": "Kháng cự",
    "chip_label": "Cấu trúc giao dịch",
    "phase_decision_heading": "Lan can quyết định trong phiên",
    "action_window_label": "Cửa sổ hành động",
    "immediate_action_label": "Hành động hiện tại",
    "watch_conditions_label": "Điều kiện theo dõi",
    "next_check_time_label": "Lần kiểm tra tiếp theo",
    "confidence_reason_label": "Lý do độ tin cậy",
    "data_limitations_label": "Hạn chế dữ liệu",
    "battle_plan_heading": "Kế hoạch hành động",
    "ideal_buy_label": "Điểm mua lý tưởng",
    "secondary_buy_label": "Điểm mua thứ hai",
    "stop_loss_label": "Cắt lỗ",
    "take_profit_label": "Chốt lời",
    "suggested_position_label": "Tỷ trọng đề xuất",
    "entry_plan_label": "Chiến lược vào lệnh",
    "risk_control_label": "Quản trị rủi ro",
    "checklist_heading": "Danh sách kiểm tra",
    "failed_checks_heading": "Mục chưa đạt",
    "history_compare_heading": "So sánh tín hiệu lịch sử",
    "time_label": "Thời gian",
    "score_label": "Điểm",
    "advice_label": "Khuyến nghị",
    "trend_label": "Xu hướng",
    "generated_at_label": "Thời điểm tạo báo cáo",
    "report_time_label": "Thời điểm tạo",
    "no_results": "Không có kết quả phân tích",
    "report_title": "Báo cáo phân tích cổ phiếu",
    "avg_score_label": "Điểm trung bình",
    "action_points_heading": "Điểm hành động",
    "position_advice_heading": "Khuyến nghị nắm giữ",
    "analysis_model_label": "Mô hình phân tích",
    "not_investment_advice": "Nội dung do AI tạo, chỉ mang tính tham khảo, không phải khuyến nghị đầu tư.",
    "details_report_hint": "Xem báo cáo chi tiết:",
    "financial_summary_heading": "Tóm tắt tài chính",
    "report_date_label": "Kỳ báo cáo",
    "revenue_label": "Doanh thu",
    "net_profit_label": "Lợi nhuận sau thuế (cổ đông công ty mẹ)",
    "operating_cash_flow_label": "Dòng tiền hoạt động kinh doanh",
    "roe_label": "ROE",
    "revenue_yoy_label": "Doanh thu cùng kỳ",
    "net_profit_yoy_label": "Lợi nhuận ròng cùng kỳ",
    "gross_margin_label": "Biên lợi nhuận gộp",
    "shareholder_return_heading": "Lợi ích cổ đông",
    "ttm_cash_dividend_label": "Cổ tức tiền mặt/cổ phiếu 12 tháng (trước thuế)",
    "ttm_event_count_label": "Số lần chia cổ tức 12 tháng",
    "ttm_dividend_yield_label": "Tỷ suất cổ tức TTM",
    "latest_ex_dividend_label": "Ngày giao dịch không hưởng quyền gần nhất",
    "related_boards_heading": "Nhóm ngành liên quan",
    "board_name_label": "Nhóm ngành",
    "board_type_label": "Loại",
    "board_status_label": "Diễn biến nhóm ngành",
    "board_change_pct_label": "Thay đổi nhóm ngành (%)",
    "leading_board_label": "Dẫn dắt tăng",
    "lagging_board_label": "Dẫn dắt giảm",
}

# ---------------------------------------------------------------------------
# 5. Nhãn cảm xúc theo dải điểm  (bơm vào ``_SENTIMENT_LABEL_BANDS``)
#    Thứ tự: >=80, >=60, >=40, >=20, còn lại.
# ---------------------------------------------------------------------------
VI_SENTIMENT_BANDS = (
    "Rất tích cực",
    "Tích cực",
    "Trung tính",
    "Tiêu cực",
    "Rất tiêu cực",
)



# ---------------------------------------------------------------------------
# Các dict PHẲNG dạng ``{lang: text}`` trong report_language.py.
#
# Khác với VI_TRANSLATIONS (dict lồng nhau ``{canonical: {lang: text}}``),
# nhóm này tra thẳng bằng ``d[language]`` nên thiếu khoá "vi" là KeyError
# ngay lúc chạy, không phải cảnh báo. Đã từng xảy ra thật:
# ``AI 分析 HPG(HPG) 失败: 'vi'`` (logs/api_server_20260625.log) — mọi phân tích
# rơi vào nhánh except và trả về kết quả trung tính giả (score 50).
#
# tests/test_report_language_vi_coverage.py có test quét mọi dict phẳng
# ``*_BY_LANGUAGE`` để chặn tái diễn khi upstream thêm dict mới.
# ---------------------------------------------------------------------------
VI_FLAT_BY_LANGUAGE = {
    "_UNKNOWN_BY_LANGUAGE": "Không rõ",
    "_NO_DATA_BY_LANGUAGE": "Thiếu dữ liệu",
    "_PLACEHOLDER_BY_LANGUAGE": "Chờ bổ sung",
    "_GENERIC_STOCK_NAME_BY_LANGUAGE": "Cổ phiếu chưa xác định",
    "_CHIP_UNAVAILABLE_BY_LANGUAGE": (
        "Phân bố chip chưa bật hoặc nguồn dữ liệu tạm thời không khả dụng, "
        "không đưa vào nhận định chip."
    ),
}


def register() -> None:
    """Tiêm dữ liệu tiếng Việt vào ``src.report_language``.

    Idempotent — gọi nhiều lần không sao. Được gọi một lần ở cuối
    ``report_language.py``.
    """
    import src.report_language as rl

    for dict_name, entries in VI_TRANSLATIONS.items():
        target = getattr(rl, dict_name, None)
        if target is None:
            # Upstream đổi tên/bỏ dict — để test coverage báo, không tự đoán.
            continue
        for canonical, text in entries.items():
            slot = target.get(canonical)
            if isinstance(slot, dict):
                slot["vi"] = text

    for dict_name, entries in VI_CANONICAL_ALIASES.items():
        target = getattr(rl, dict_name, None)
        if isinstance(target, dict):
            target.update(entries)

    rl._REPORT_LANGUAGE_ALIASES.update(VI_LANGUAGE_ALIASES)
    rl._REPORT_LABELS["vi"] = dict(VI_REPORT_LABELS)
    rl._SENTIMENT_LABEL_BANDS["vi"] = VI_SENTIMENT_BANDS

    # Dict phẳng {lang: text} — thiếu khoá là KeyError lúc chạy.
    for dict_name, text in VI_FLAT_BY_LANGUAGE.items():
        target = getattr(rl, dict_name, None)
        if isinstance(target, dict):
            target["vi"] = text


__all__ = [
    "VI_TRANSLATIONS",
    "VI_CANONICAL_ALIASES",
    "VI_LANGUAGE_ALIASES",
    "VI_REPORT_LABELS",
    "VI_SENTIMENT_BANDS",
    "VI_FLAT_BY_LANGUAGE",
    "register",
]
