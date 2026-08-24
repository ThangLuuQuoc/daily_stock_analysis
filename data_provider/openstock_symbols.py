# -*- coding: utf-8 -*-
"""
越南市场代码识别工具 (OpenStock adapter 专用)

OpenStock 提供越南三大交易所数据：HOSE / HNX / UPCOM。
越南普通股代码通常为 3 个大写字母（FPT, VNM, HPG...），
与中国 A 股（6 位数字）、美股（多为 1-5 字母但语义不同）区分开来。

设计原则：
- 仅在“高置信度是越南标的”时返回 True，避免误抢 A 股 / 美股代码的路由。
- 提供越南主要指数代码映射，供 get_main_indices 使用。
"""

from __future__ import annotations

import re

# 越南主要指数代码（OpenStock 内部使用的符号）
VN_INDEX_MAPPING = {
    "VNINDEX": "VN-Index (HOSE)",
    "VN30": "VN30",
    "HNXINDEX": "HNX-Index",
    "HNX30": "HNX30",
    "UPCOMINDEX": "UPCOM-Index",
}

# 3 个大写字母的普通股代码（HOSE/HNX/UPCOM 绝大多数标的）
_VN_TICKER_RE = re.compile(r"^[A-Z]{3}$")

# 衍生品 / 权证等带数字后缀的代码（如 CFPT1901），保守起见也识别为越南标的
_VN_DERIVATIVE_RE = re.compile(r"^[A-Z]{2,4}[0-9]{2,6}$")


def normalize_vn_symbol(stock_code: str) -> str:
    """统一格式：去空白、转大写。"""
    return str(stock_code or "").strip().upper()


def is_vn_index_code(stock_code: str) -> bool:
    """是否为越南主要指数代码。"""
    return normalize_vn_symbol(stock_code) in VN_INDEX_MAPPING


def is_vn_stock_code(stock_code: str) -> bool:
    """
    判断是否为越南市场标的代码（高置信度）。

    匹配规则：
    - 3 个大写字母（绝大多数越南普通股）
    - 指数代码（VNINDEX 等）
    - 带数字后缀的衍生品/权证（CFPT1901 等）

    不匹配：纯数字（A 股）、长度不符的代码。
    """
    code = normalize_vn_symbol(stock_code)
    if not code:
        return False
    if code.isdigit():
        return False
    if is_vn_index_code(code):
        return True
    if _VN_TICKER_RE.match(code):
        return True
    if _VN_DERIVATIVE_RE.match(code):
        return True
    return False
