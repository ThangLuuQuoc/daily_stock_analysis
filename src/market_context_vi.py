"""Bối cảnh thị trường tiếng Việt + thị trường Việt Nam cho ``src.market_context``.

Trước đây fork ghi bản dịch tiếng Việt **vào thẳng khoá ``"zh"``** của
``_MARKET_ROLES`` / ``_MARKET_GUIDELINES``. Hậu quả:

  * ``REPORT_LANGUAGE=zh`` nhận tiếng Việt (``get_market_role("600519", "zh")``
    trả ``"cổ phiếu A-share"`` thay vì ``" A 股"``);
  * ``"tw"`` bị bỏ sót nên Đài Loan vẫn ra tiếng Trung — không nhất quán;
  * mỗi lần upstream sửa hướng dẫn thị trường là một conflict.

Quan trọng hơn: ``detect_market()`` của upstream **không có nhánh VN**. Ticker
Việt Nam 3 chữ (VIC, FPT, HPG) khớp regex ``^[A-Z]{1,5}$`` nên bị phân loại là
``"us"``. Cộng với việc bản dịch nằm ở khoá ``"zh"``, prompt gửi cho LLM mô tả
VIC là *"cổ phiếu Mỹ"* kèm hướng dẫn thị trường Mỹ (không trần sàn, T+0, Fed,
SEC) — sai hoàn toàn với HOSE (biên ±7%, T+2, giới hạn sở hữu nước ngoài).

Nay:
  * ``market_context.py`` giữ nguyên literal tiếng Trung của upstream;
  * bản dịch ``vi`` và thị trường ``vn`` đăng ký từ đây qua ``register()``;
  * ``detect_market()`` hỏi ``_is_vn_market()`` trước (đã có guard
    ``OPENSTOCK_ENABLED`` nên deployment CN/US không bị nhận nhầm mã Mỹ 3 chữ).

Xem docs/vn-fork-touchpoints.md mục 1.1f.

DANH DOI DA BIET
================
``_is_vn_market()`` uu tien bang ma OpenStock (chinh xac). Khi OpenStock khong
chay, no rot ve regex bao thu, luc do ticker My **dung 3 chu** bi nhan nham la
VN (IBM, GME -> "vn"); 4 chu tro len (AAPL) va 1-2 chu (F, KO) van dung.

Van la cai thien ro rang: TRUOC day 100% co phieu VN bi goi la "co phieu My"
kem huong dan thi truong My. NAY chi sai voi ticker My 3 chu, va chi trong luc
OpenStock down. Luu y AMD/SSI thuc su LA ma HOSE nen "vn" moi la dung.

Muon triet tieu han: dat ``OPENSTOCK_ENABLED=false`` (moi ma quay ve hanh vi
upstream) hoac giu OpenStock chay.
"""

from typing import Any, Dict

__all__ = ["VI_MARKET_ROLES", "VI_MARKET_GUIDELINES", "VN_ROLE", "VN_GUIDELINES", "register"]



# Bản dịch tiếng Việt cho các thị trường upstream đã có.
VI_MARKET_ROLES: Dict[str, str] = {
    "cn": 'cổ phiếu A-share',
    "hk": 'cổ phiếu Hồng Kông',
    "us": 'cổ phiếu Mỹ',
    "jp": 'cổ phiếu Nhật',
    "kr": 'cổ phiếu Hàn Quốc',
}

VI_MARKET_GUIDELINES: Dict[str, str] = {
    "cn": (
        '- Đối tượng phân tích lần này là **cổ phiếu A-share** (niêm yết trên sàn Thượng Hải/Thâm Quyến của Trung Quốc).\n'
        '- Hãy chú ý cơ chế trần/sàn đặc thù của A-share (±10%/±20%/±30%), chế độ giao dịch T+1 và các yếu tố chính sách liên quan.'
    ),
    "hk": (
        '- Đối tượng phân tích lần này là **cổ phiếu Hồng Kông** (niêm yết trên Sở giao dịch Hồng Kông).\n'
        '- Cổ phiếu Hồng Kông không có giới hạn trần/sàn, hỗ trợ giao dịch T+0, cần chú ý tỷ giá HKD, dòng vốn Nam-Bắc và các quy tắc đặc thù của HKEX.'
    ),
    "us": (
        '- Đối tượng phân tích lần này là **cổ phiếu Mỹ** (niêm yết trên sàn Mỹ).\n'
        '- Cổ phiếu Mỹ không có giới hạn trần/sàn (nhưng có cơ chế ngắt mạch), hỗ trợ giao dịch T+0 và giao dịch trước/sau giờ, cần chú ý tỷ giá USD, chính sách của Fed và động thái giám sát của SEC.'
    ),
    "jp": (
        '- Đối tượng phân tích lần này là **cổ phiếu Nhật** (niêm yết trên sàn Nhật, hậu tố Yahoo Finance như `.T`).\n'
        '- Hãy phân tích theo bối cảnh thị trường Nhật, chú ý tỷ giá JPY, chính sách của BOJ, quản trị doanh nghiệp và chu kỳ ngành; không áp dụng các khái niệm đặc thù của A-share như trần/sàn, dòng vốn phía Bắc, bảng Long Hổ, ký quỹ.'
    ),
    "kr": (
        '- Đối tượng phân tích lần này là **cổ phiếu Hàn Quốc** (niêm yết trên sàn Hàn Quốc/KOSDAQ, bắt buộc có hậu tố `.KS` / `.KQ`).\n'
        '- Hãy phân tích theo bối cảnh thị trường Hàn Quốc, chú ý tỷ giá KRW, chính sách của Ngân hàng Trung ương Hàn Quốc, chu kỳ ngành bán dẫn/internet và chế độ giao dịch Hàn Quốc; không áp dụng các khái niệm đặc thù của A-share như trần/sàn, dòng vốn phía Bắc, bảng Long Hổ, ký quỹ.'
    ),
}

# `tw` upstream co nhung fork chua dich -> them de bang khong con lo hong.
VI_MARKET_ROLES["tw"] = "cổ phiếu Đài Loan"
VI_MARKET_GUIDELINES["tw"] = (
    "- Đối tượng phân tích lần này là **cổ phiếu Đài Loan** (niêm yết trên TWSE/TPEx, "
    "hậu tố Yahoo Finance như `.TW` / `.TWO`).\n"
    "- Hãy phân tích theo bối cảnh thị trường Đài Loan, chú ý tỷ giá TWD, chu kỳ ngành "
    "bán dẫn và chế độ giao dịch Đài Loan; không áp dụng các khái niệm đặc thù của "
    "A-share như trần/sàn, dòng vốn phía Bắc, bảng Long Hổ, ký quỹ."
)


# ---------------------------------------------------------------------------
# Thị trường Việt Nam — upstream không có.
#
# Trước đây mã VN bị `detect_market()` phân loại thành "us" nên prompt dùng
# hướng dẫn thị trường Mỹ. Ba đặc thù bắt buộc phải nói đúng:
#   * biên độ: HOSE ±7%, HNX ±10%, UPCOM ±15% (Mỹ không có trần/sàn)
#   * thanh toán T+2 (Mỹ cho phép T+0 trong phiên)
#   * giới hạn sở hữu nước ngoài (foreign room) — Mỹ không có khái niệm này
# ---------------------------------------------------------------------------
VN_ROLE = {
    "zh": "越南股",
    "en": "Vietnam stock",
    "vi": "cổ phiếu Việt Nam",
}

VN_GUIDELINES = {
    "zh": (
        "- 本次分析对象为 **越南股**（胡志明 HOSE / 河内 HNX / UPCOM 上市股票）。\n"
        "- 请关注越南市场特有的涨跌停幅度（HOSE ±7%、HNX ±10%、UPCOM ±15%）、"
        "T+2 交收制度、外资持股上限（foreign room）及越南盾汇率；不要套用美股"
        "无涨跌停、T+0 或美联储/SEC 等美国市场概念。"
    ),
    "en": (
        "- This analysis targets a **Vietnam stock** (listed on HOSE / HNX / UPCOM).\n"
        "- Mind Vietnam-specific daily price bands (HOSE ±7%, HNX ±10%, UPCOM ±15%), "
        "T+2 settlement, the foreign ownership limit (foreign room), and the VND rate; "
        "do not apply US-market concepts such as no price limits, T+0, or Fed/SEC policy."
    ),
    "vi": (
        "- Đối tượng phân tích lần này là **cổ phiếu Việt Nam** (niêm yết trên HOSE / HNX / UPCOM).\n"
        "- Hãy chú ý biên độ dao động đặc thù của thị trường Việt Nam (HOSE ±7%, HNX ±10%, "
        "UPCOM ±15%), chế độ thanh toán T+2, giới hạn sở hữu nước ngoài (foreign room) và "
        "tỷ giá VND; không áp dụng các khái niệm của thị trường Mỹ như không có trần/sàn, "
        "T+0 hay chính sách Fed/SEC."
    ),
}


def register() -> None:
    """Tiêm dữ liệu tiếng Việt + thị trường ``vn`` vào ``src.market_context``.

    Idempotent. Được gọi một lần ở cuối ``market_context.py``.
    """
    import src.market_context as mc

    for market, text in VI_MARKET_ROLES.items():
        slot = mc._MARKET_ROLES.get(market)
        if isinstance(slot, dict):
            slot["vi"] = text
    for market, text in VI_MARKET_GUIDELINES.items():
        slot = mc._MARKET_GUIDELINES.get(market)
        if isinstance(slot, dict):
            slot["vi"] = text

    mc._MARKET_ROLES["vn"] = dict(VN_ROLE)
    mc._MARKET_GUIDELINES["vn"] = dict(VN_GUIDELINES)
