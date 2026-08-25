# -*- coding: utf-8 -*-
"""
Market context detection for LLM prompts.

Detects the market (A-shares, HK, US) from a stock code and returns
market-specific role descriptions so prompts are not hardcoded to a
single market.

Fixes: https://github.com/ZhuLinsen/daily_stock_analysis/issues/644
"""

import re
from typing import Optional

from src.services.market_symbol_utils import get_suffix_market


def detect_market(stock_code: Optional[str]) -> str:
    """Detect market from stock code.

    Returns:
        One of 'cn', 'hk', 'us', or 'cn' as fallback.
    """
    if not stock_code:
        return "cn"

    code = stock_code.strip().upper()

    # HK stocks: HK00700, 00700.HK, or 5-digit pure numbers
    if code.startswith("HK") or code.endswith(".HK"):
        return "hk"
    lower = code.lower()
    if lower.endswith(".hk"):
        return "hk"
    # 5-digit pure numbers are HK (A-shares are 6-digit)
    if code.isdigit() and len(code) == 5:
        return "hk"

    # Suffix-only Yahoo symbols for JP/KR/TW. Bare Korean/Taiwan numeric
    # codes keep existing fallback semantics to avoid cross-market collisions.
    suffix_market = get_suffix_market(code)
    if suffix_market:
        return suffix_market

    # US stocks: 1-5 uppercase letters (AAPL, TSLA, GOOGL)
    # Also handles suffixed forms like BRK.B
    if re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', code):
        return "us"

    # Default: A-shares (6-digit numbers like 600519, 000001)
    return "cn"


# -- Market-specific role descriptions --

_MARKET_ROLES = {
    "cn": {
        "zh": "cổ phiếu A-share",
        "en": "China A-shares",
    },
    "hk": {
        "zh": "cổ phiếu Hồng Kông",
        "en": "Hong Kong stock",
    },
    "us": {
        "zh": "cổ phiếu Mỹ",
        "en": "US stock",
    },
    "jp": {
        "zh": "cổ phiếu Nhật",
        "en": "Japan stock",
    },
    "kr": {
        "zh": "cổ phiếu Hàn Quốc",
        "en": "Korea stock",
    },
    "tw": {
        "zh": "台股",
        "en": "Taiwan stock",
    },
}

_MARKET_GUIDELINES = {
    "cn": {
        "zh": (
            "- Đối tượng phân tích lần này là **cổ phiếu A-share** (niêm yết trên sàn Thượng Hải/Thâm Quyến của Trung Quốc).\n"
            "- Hãy chú ý cơ chế trần/sàn đặc thù của A-share (±10%/±20%/±30%), chế độ giao dịch T+1 và các yếu tố chính sách liên quan."
        ),
        "en": (
            "- This analysis covers a **China A-share** (listed on Shanghai/Shenzhen exchanges).\n"
            "- Consider A-share-specific rules: daily price limits (±10%/±20%/±30%), T+1 settlement, and PRC policy factors."
        ),
    },
    "hk": {
        "zh": (
            "- Đối tượng phân tích lần này là **cổ phiếu Hồng Kông** (niêm yết trên Sở giao dịch Hồng Kông).\n"
            "- Cổ phiếu Hồng Kông không có giới hạn trần/sàn, hỗ trợ giao dịch T+0, cần chú ý tỷ giá HKD, dòng vốn Nam-Bắc và các quy tắc đặc thù của HKEX."
        ),
        "en": (
            "- This analysis covers a **Hong Kong stock** (listed on HKEX).\n"
            "- HK stocks have no daily price limits, allow T+0 trading. Consider HKD FX, Southbound/Northbound flows, and HKEX-specific rules."
        ),
    },
    "us": {
        "zh": (
            "- Đối tượng phân tích lần này là **cổ phiếu Mỹ** (niêm yết trên sàn Mỹ).\n"
            "- Cổ phiếu Mỹ không có giới hạn trần/sàn (nhưng có cơ chế ngắt mạch), hỗ trợ giao dịch T+0 và giao dịch trước/sau giờ, cần chú ý tỷ giá USD, chính sách của Fed và động thái giám sát của SEC."
        ),
        "en": (
            "- This analysis covers a **US stock** (listed on NYSE/NASDAQ).\n"
            "- US stocks have no daily price limits (but have circuit breakers), allow T+0 and pre/after-market trading. Consider USD FX, Fed policy, and SEC regulations."
        ),
    },
    "jp": {
        "zh": (
            "- Đối tượng phân tích lần này là **cổ phiếu Nhật** (niêm yết trên sàn Nhật, hậu tố Yahoo Finance như `.T`).\n"
            "- Hãy phân tích theo bối cảnh thị trường Nhật, chú ý tỷ giá JPY, chính sách của BOJ, quản trị doanh nghiệp và chu kỳ ngành; không áp dụng các khái niệm đặc thù của A-share như trần/sàn, dòng vốn phía Bắc, bảng Long Hổ, ký quỹ."
        ),
        "en": (
            "- This analysis covers a **Japan stock** (Yahoo Finance suffix such as `.T`).\n"
            "- Use Japan-market context: JPY FX, BOJ policy, corporate governance, and sector cycles; do not apply China A-share concepts such as daily price-limit boards, Northbound flows, Dragon Tiger lists, or margin-financing narratives."
        ),
    },
    "kr": {
        "zh": (
            "- Đối tượng phân tích lần này là **cổ phiếu Hàn Quốc** (niêm yết trên sàn Hàn Quốc/KOSDAQ, bắt buộc có hậu tố `.KS` / `.KQ`).\n"
            "- Hãy phân tích theo bối cảnh thị trường Hàn Quốc, chú ý tỷ giá KRW, chính sách của Ngân hàng Trung ương Hàn Quốc, chu kỳ ngành bán dẫn/internet và chế độ giao dịch Hàn Quốc; không áp dụng các khái niệm đặc thù của A-share như trần/sàn, dòng vốn phía Bắc, bảng Long Hổ, ký quỹ."
        ),
        "en": (
            "- This analysis covers a **Korea stock** (KOSPI/KOSDAQ suffix `.KS` / `.KQ`).\n"
            "- Use Korea-market context: KRW FX, Bank of Korea policy, semiconductor/internet cycles, and local trading rules; do not apply China A-share concepts such as daily price-limit boards, Northbound flows, Dragon Tiger lists, or margin-financing narratives."
        ),
    },
    "tw": {
        "zh": (
            "- 本次分析对象为 **台股**（台湾证券交易所上市 `.TW`，或台湾柜买中心上柜 `.TWO`）。\n"
            "- 请按台湾市场语境分析，关注新台币（TWD）汇率、台湾央行政策、半导体/电子代工产业链、"
            "三大法人（外资／投信／自营商）买卖超、融资融券与当冲，以及 TWSE/TPEx ±10% 涨跌停制度；"
            "不要套用 A 股专属的北向资金、龙虎榜等概念（台股的法人结构与资金流口径与 A 股不同）。"
        ),
        "en": (
            "- This analysis covers a **Taiwan stock** (TWSE-listed `.TW`, or TPEx/OTC `.TWO`).\n"
            "- Use Taiwan-market context: TWD FX, Central Bank of the ROC policy, the semiconductor/"
            "electronics-foundry supply chain, the three institutional investor groups (foreign / "
            "investment-trust / dealer), margin trading and day trading, and the TWSE/TPEx ±10% daily "
            "price limit; do not apply China A-share-specific concepts such as Northbound flows or Dragon Tiger lists."
        ),
    },
}


def get_market_role(stock_code: Optional[str], lang: str = "zh") -> str:
    """Return market-specific role description for LLM prompt.

    Args:
        stock_code: The stock code being analyzed.
        lang: 'zh' or 'en'.

    Returns:
        Role string like 'A 股投资分析' or 'US stock investment analysis'.
    """
    market = detect_market(stock_code)
    lang_key = "en" if lang in ("en", "ko") else "zh"
    return _MARKET_ROLES.get(market, _MARKET_ROLES["cn"])[lang_key]


def get_market_guidelines(stock_code: Optional[str], lang: str = "zh") -> str:
    """Return market-specific analysis guidelines for LLM prompt.

    Args:
        stock_code: The stock code being analyzed.
        lang: 'zh' or 'en'.

    Returns:
        Multi-line string with market-specific guidelines.
    """
    market = detect_market(stock_code)
    lang_key = "en" if lang in ("en", "ko") else "zh"
    return _MARKET_GUIDELINES.get(market, _MARKET_GUIDELINES["cn"])[lang_key]
