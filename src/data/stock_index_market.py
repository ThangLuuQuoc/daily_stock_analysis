"""fork VN: chọn thị trường cho chỉ mục tự động hoàn thành (autocomplete).

Repo này phục vụ thị trường Việt Nam nên **mặc định là ``vn``**. Upstream sinh
``stocks.index.json`` gồm ~31.700 mã Trung/HK/Mỹ/Nhật/Hàn và **không có một mã
Việt Nam nào** — kể cả VNINDEX lẫn FPT/VIC. Hệ quả trước khi có module này:

  * gõ "FPT" trong ô tìm kiếm không ra gợi ý nào;
  * lịch sử phân tích hiện ``FPT(FPT)``, ``HPG``, ``KSB`` trần trụi vì không tra
    được tên đầy đủ (những mã có tên là do LLM/OpenStock trả về, không phải từ
    chỉ mục).

Vì sao KHÔNG dùng registry chỉ số mới của upstream (`scripts/generate_index_from_csv.py`
`--index-only`): nó khoá cứng cho A-share —

    if not _INDEX_NAMESPACE_RE.match(canonical):   # ^(sh|sz|csi)\\d{6}$
        raise ValueError(...)
    if market != "CN":
        raise ValueError(f"index market must be CN: {canonical!r}")

``VNINDEX`` trượt cả hai. Nhét mã VN vào đó buộc phải sửa validator của upstream
— đúng kiểu ghi đè mà `docs/vn-fork-touchpoints.md` mục 1.1f cấm.

Thêm một bẫy: ``run_index_only()`` **xoá sạch mọi dòng ``assetType=index``** rồi
ghi lại từ seed của upstream. Nếu ai đó thêm chỉ số VN thẳng vào
``stocks.index.json``, lần chạy ``--index-only`` kế tiếp sẽ xoá mất mà không báo.

Nên fork dùng **file riêng** ``stocks.index.vn.json``, sinh bởi
``scripts/generate_vn_index.py``. File của upstream giữ nguyên, chạy song song.

Chuyển thị trường::

    STOCK_INDEX_MARKET=vn    # mặc định — dùng stocks.index.vn.json
    STOCK_INDEX_MARKET=cn    # hành vi upstream — dùng stocks.index.json

Frontend có biến tương ứng ``VITE_STOCK_INDEX_MARKET`` (cũng mặc định ``vn``).
"""

from __future__ import annotations

import os

__all__ = [
    "DEFAULT_STOCK_INDEX_MARKET",
    "UPSTREAM_STOCK_INDEX_FILENAME",
    "VN_STOCK_INDEX_FILENAME",
    "get_stock_index_market",
    "stock_index_filename",
    "is_vn_index_market",
]

DEFAULT_STOCK_INDEX_MARKET = "vn"
UPSTREAM_STOCK_INDEX_FILENAME = "stocks.index.json"
VN_STOCK_INDEX_FILENAME = "stocks.index.vn.json"

_ENV_VAR = "STOCK_INDEX_MARKET"


def get_stock_index_market() -> str:
    """Thị trường đang chọn cho chỉ mục autocomplete (đã chuẩn hoá, chữ thường).

    Giá trị lạ -> rơi về mặc định ``vn`` thay vì ném lỗi: chỉ mục autocomplete
    hỏng không đáng làm sập cả tiến trình phân tích.
    """
    raw = (os.getenv(_ENV_VAR) or "").strip().lower()
    return raw or DEFAULT_STOCK_INDEX_MARKET


def is_vn_index_market() -> bool:
    return get_stock_index_market() not in {"cn", "upstream"}


def stock_index_filename() -> str:
    """Tên file chỉ mục ứng với thị trường đang chọn."""
    return VN_STOCK_INDEX_FILENAME if is_vn_index_market() else UPSTREAM_STOCK_INDEX_FILENAME
