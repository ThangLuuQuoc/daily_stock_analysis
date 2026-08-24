# -*- coding: utf-8 -*-
"""
冒烟测试：针对本地运行的 OpenStock 服务验证 OpenStock adapter。

用法（仓库根目录）：
    OPENSTOCK_ENABLED=true python scripts/test_openstock_adapter.py [SYMBOL]

默认 SYMBOL=FPT。需要本地 OpenStock 服务运行在
``OPENSTOCK_BASE_URL``（默认 http://localhost:3000/api/v1）。

该脚本不依赖 pytest，直接打印各能力的返回，便于人工核对。
"""

import os
import sys
import types

# 允许从仓库根目录直接运行
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

os.environ.setdefault("OPENSTOCK_ENABLED", "true")

# data_provider/__init__.py 会预先导入全部 fetcher（efinance/akshare/...），
# 这些第三方库在测试环境未必安装。此处注册一个仅含 __path__ 的轻量包桩，
# 使相对导入（from .base import ...）能解析，但跳过 __init__.py 的重型导入。
_PKG = "data_provider"
if _PKG not in sys.modules:
    _stub = types.ModuleType(_PKG)
    _stub.__path__ = [os.path.join(_ROOT, _PKG)]
    _stub.__package__ = _PKG
    sys.modules[_PKG] = _stub

from data_provider.openstock_fetcher import OpenStockFetcher
from data_provider.openstock_fundamental_adapter import OpenStockFundamentalAdapter
from data_provider.openstock_symbols import is_vn_stock_code


def _hr(title: str) -> None:
    print(f"\n{'=' * 12} {title} {'=' * 12}")


def main() -> int:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "FPT"
    print(f"Testing OpenStock adapter with symbol={symbol}")
    print(f"is_vn_stock_code({symbol!r}) = {is_vn_stock_code(symbol)}")

    fetcher = OpenStockFetcher()
    fund = OpenStockFundamentalAdapter()
    print(f"base_url = {fetcher._base_url}")

    failures = []

    _hr("get_stock_name")
    try:
        name = fetcher.get_stock_name(symbol)
        print(f"name = {name!r}")
        assert name, "名称为空"
    except Exception as exc:
        failures.append(("get_stock_name", exc))
        print(f"FAIL: {exc}")

    _hr("get_daily_data (last 30d)")
    try:
        df = fetcher.get_daily_data(symbol, days=30)
        print(f"rows = {len(df)}; columns = {list(df.columns)}")
        print(df.tail(3).to_string())
        assert not df.empty, "日线为空"
    except Exception as exc:
        failures.append(("get_daily_data", exc))
        print(f"FAIL: {exc}")

    _hr("get_realtime_quote")
    try:
        quote = fetcher.get_realtime_quote(symbol)
        assert quote is not None, "quote 为 None"
        for k, v in quote.to_dict().items():
            print(f"  {k}: {v}")
        assert quote.has_basic_data(), "缺少基础价格"
    except Exception as exc:
        failures.append(("get_realtime_quote", exc))
        print(f"FAIL: {exc}")

    _hr("get_fundamental_bundle")
    try:
        bundle = fund.get_fundamental_bundle(symbol)
        import json

        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        assert bundle["status"] != "not_supported", "基本面 not_supported"
    except Exception as exc:
        failures.append(("get_fundamental_bundle", exc))
        print(f"FAIL: {exc}")

    _hr("get_capital_flow")
    try:
        flow = fund.get_capital_flow(symbol)
        import json

        print(json.dumps(flow, ensure_ascii=False, indent=2))
    except Exception as exc:
        failures.append(("get_capital_flow", exc))
        print(f"FAIL: {exc}")

    _hr("get_dragon_tiger_flag (expect not_supported)")
    print(fund.get_dragon_tiger_flag(symbol))

    _hr("SUMMARY")
    if failures:
        print(f"{len(failures)} capability(ies) FAILED:")
        for name, exc in failures:
            print(f"  - {name}: {exc}")
        return 1
    print("All core capabilities OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
