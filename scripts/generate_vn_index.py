#!/usr/bin/env python3
"""fork VN: sinh ``stocks.index.vn.json`` — chỉ mục autocomplete cho thị trường VN.

Nguồn:
  * cổ phiếu — OpenStock ``GET /stocks`` (HOSE/HNX/UPCOM, ~3.600 mã kèm tên)
  * chỉ số  — ``scripts/stock_index_seeds/vn_index_registry.csv`` (fork tự giữ)

Vì sao là script RIÊNG chứ không mở rộng ``generate_index_from_csv.py`` của
upstream: script đó khoá cứng cho A-share (canonical phải khớp
``^(sh|sz|csi)\\d{6}$`` và ``market`` phải là ``CN``), và ``--index-only`` của nó
xoá sạch mọi dòng ``assetType=index`` trước khi ghi lại từ seed của chính nó.
Xem ``src/data/stock_index_market.py`` để biết chi tiết.

Định dạng một dòng (khớp ``apps/dsa-web/src/utils/stockIndexFields.ts``)::

    [canonicalCode, displayCode, nameZh, pinyinFull, pinyinAbbr,
     aliases, market, assetType, active, popularity]

Với mã VN, hai trường "pinyin" được dùng đúng ý nghĩa gốc là **dạng ASCII để tìm
kiếm**:
  * ``pinyinFull`` — tên đã bỏ dấu, chữ thường (gõ "ngan hang ngoai thuong" ra)
  * ``pinyinAbbr`` — viết tắt các chữ cái đầu

Dùng::

    python scripts/generate_vn_index.py            # ghi file
    python scripts/generate_vn_index.py --test     # chỉ kiểm tra, không ghi
    OPENSTOCK_BASE_URL=... python scripts/generate_vn_index.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = REPO_ROOT / "scripts" / "stock_index_seeds" / "vn_index_registry.csv"
OUTPUT_PATHS = (
    REPO_ROOT / "apps" / "dsa-web" / "public" / "stocks.index.vn.json",
    REPO_ROOT / "static" / "stocks.index.vn.json",
)

DEFAULT_OPENSTOCK_BASE_URL = "http://localhost:3000/api/v1"

# Sàn hợp lệ; mã ngoài danh sách này bị bỏ để không lẫn rác vào chỉ mục.
VALID_EXCHANGES = {"HOSE", "HNX", "UPCOM"}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def strip_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt -> ASCII chữ thường (đ/Đ xử lý riêng vì NFD không tách)."""
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", without_marks).lower()


def searchable_full(name: str) -> str:
    """Dạng ASCII đầy đủ để tìm kiếm: bỏ dấu, gom khoảng trắng."""
    return _NON_ALNUM.sub(" ", strip_diacritics(name)).strip()


def searchable_abbr(name: str) -> str:
    """Viết tắt: chữ cái đầu của mỗi từ (bỏ từ 1 ký tự không có nghĩa)."""
    words = [w for w in searchable_full(name).split() if w]
    return "".join(w[0] for w in words)


def fetch_openstock_symbols(base_url: str) -> List[Dict[str, Any]]:
    """Lấy danh sách mã từ OpenStock. Lỗi mạng -> ném để người chạy biết ngay."""
    import urllib.request

    url = f"{base_url.rstrip('/')}/stocks"
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 (localhost)
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        raise ValueError(f"OpenStock {url} trả về dạng không mong đợi: {type(data).__name__}")
    return data


def load_vn_index_seed(path: Path = SEED_PATH) -> List[Dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"khong tim thay seed chi so VN: {path}")
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            canonical = (row.get("canonical_code") or "").strip()
            name = (row.get("name_vi") or "").strip()
            if not canonical or not name:
                raise ValueError(f"dong seed thieu truong bat buoc: {row}")
            aliases = [a.strip() for a in (row.get("aliases") or "").split("|") if a.strip()]
            rows.append({
                "canonical": canonical,
                "display": (row.get("display_code") or canonical).strip(),
                "name": name,
                "aliases": aliases,
                "popularity": int((row.get("popularity") or "100").strip() or 100),
            })
    return rows


def build_tuples(symbols: Iterable[Dict[str, Any]], seed: Iterable[Dict[str, Any]]) -> List[List[Any]]:
    out: List[List[Any]] = []
    seen: set[str] = set()

    # Chỉ số trước (popularity cao) — cùng định dạng, khác assetType.
    for row in seed:
        code = row["canonical"].upper()
        seen.add(code)
        out.append([
            code, row["display"].upper(), row["name"],
            searchable_full(row["name"]), searchable_abbr(row["name"]),
            [a.upper() for a in row["aliases"]],
            "VN", "index", True, row["popularity"],
        ])

    for item in symbols:
        code = str(item.get("symbol") or "").strip().upper()
        if not code or code in seen:
            continue
        if str(item.get("exchange") or "").strip().upper() not in VALID_EXCHANGES:
            continue
        if item.get("isActive") is False:
            continue
        seen.add(code)
        name = str(item.get("name") or "").strip() or code
        out.append([
            code, code, name,
            searchable_full(name), searchable_abbr(name),
            [], "VN", "stock", True, 100,
        ])

    out.sort(key=lambda row: (row[7] != "index", -row[9], str(row[0])))
    return out


def validate(tuples: List[List[Any]]) -> None:
    """Kiểm tra bất biến trước khi ghi — chỉ mục hỏng thì autocomplete chết câm."""
    if len(tuples) < 100:
        raise ValueError(f"chi muc qua it muc ({len(tuples)}), nghi OpenStock tra thieu")
    codes: set[str] = set()
    for row in tuples:
        if len(row) != 10:
            raise ValueError(f"dong phai co dung 10 truong: {row}")
        code = row[0]
        if code in codes:
            raise ValueError(f"ma trung trong chi muc: {code}")
        codes.add(code)
        if row[6] != "VN":
            raise ValueError(f"market phai la VN: {row}")
        if row[7] not in {"stock", "index"}:
            raise ValueError(f"assetType khong hop le: {row}")
        if not row[2]:
            raise ValueError(f"thieu ten: {row}")
    for must in ("VNINDEX", "VN30"):
        if must not in codes:
            raise ValueError(f"thieu chi so bat buoc: {must}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh chi muc autocomplete cho thi truong VN")
    ap.add_argument("--test", "-t", action="store_true", help="chi kiem tra, khong ghi file")
    ap.add_argument("--base-url", default=os.getenv("OPENSTOCK_BASE_URL", DEFAULT_OPENSTOCK_BASE_URL))
    args = ap.parse_args()

    print(f"Nguon OpenStock : {args.base_url}")
    symbols = fetch_openstock_symbols(args.base_url)
    print(f"  co phieu lay ve: {len(symbols)}")

    seed = load_vn_index_seed()
    print(f"  chi so tu seed : {len(seed)}")

    tuples = build_tuples(symbols, seed)
    validate(tuples)
    n_idx = sum(1 for r in tuples if r[7] == "index")
    print(f"  tong muc       : {len(tuples)}  ({n_idx} chi so + {len(tuples) - n_idx} co phieu)")

    if args.test:
        print("--test: khong ghi file.")
        return 0

    blob = json.dumps(tuples, ensure_ascii=False, separators=(",", ":"))
    for path in OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(blob, encoding="utf-8")
        tmp.replace(path)  # ghi nguyen tu: doc gia khong bao gio thay file mot nua
        print(f"  da ghi {path}  ({len(blob) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
