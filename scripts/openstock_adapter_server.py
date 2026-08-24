# -*- coding: utf-8 -*-
"""
Server test nhẹ cho OpenStock adapter (Starlette + uvicorn).

Mục đích: cho phép test thủ công `OpenStockFetcher` / `OpenStockFundamentalAdapter`
qua HTTP mà KHÔNG cần dựng toàn bộ app daily_stock_analysis (vốn cần fastapi +
efinance/akshare/tushare/litellm + .env chưa cài trong môi trường này).

Chạy (mặc định port 8010, không đụng port 3000 của OpenStock):
    OPENSTOCK_ENABLED=true python scripts/openstock_adapter_server.py
    # đổi port: ADAPTER_PORT=8011 python scripts/openstock_adapter_server.py

Endpoint:
    GET /                       trang index (liệt kê link)
    GET /health
    GET /name/{symbol}
    GET /quote/{symbol}
    GET /daily/{symbol}?days=30
    GET /fundamental/{symbol}
    GET /capital-flow/{symbol}
    GET /all/{symbol}           gộp tất cả
"""

import os
import sys
import types

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Tránh numpy/OpenBLAS ngốn RAM trong môi trường hạn chế
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENSTOCK_ENABLED", "true")

# data_provider/__init__.py import sẵn toàn bộ fetcher (efinance/akshare/...) vốn
# chưa cài. Đăng ký package stub chỉ có __path__ để import tương đối hoạt động mà
# bỏ qua __init__.py nặng.
_PKG = "data_provider"
if _PKG not in sys.modules:
    _stub = types.ModuleType(_PKG)
    _stub.__path__ = [os.path.join(_ROOT, _PKG)]
    _stub.__package__ = _PKG
    sys.modules[_PKG] = _stub

import pandas as pd
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route

from data_provider.openstock_fetcher import OpenStockFetcher
from data_provider.openstock_fundamental_adapter import OpenStockFundamentalAdapter

_fetcher = OpenStockFetcher()
_fund = OpenStockFundamentalAdapter()


def _df_to_records(df: pd.DataFrame):
    if df is None or df.empty:
        return []
    out = df.copy()
    if "date" in out.columns:
        out["date"] = out["date"].astype(str)
    return out.where(pd.notnull(out), None).to_dict(orient="records")


async def index(request):
    base = str(request.base_url).rstrip("/")
    sym = "FPT"
    links = [
        f"/health",
        f"/all/{sym}",
        f"/name/{sym}",
        f"/quote/{sym}",
        f"/daily/{sym}?days=30",
        f"/fundamental/{sym}",
        f"/capital-flow/{sym}",
    ]
    items = "".join(f'<li><a href="{base}{l}">{l}</a></li>' for l in links)
    html = f"""
    <html><head><meta charset="utf-8"><title>OpenStock Adapter Test</title></head>
    <body style="font-family:system-ui;max-width:720px;margin:40px auto">
      <h2>OpenStock Adapter — test server</h2>
      <p>Base URL OpenStock: <code>{_fetcher._base_url}</code></p>
      <p>Đổi mã: thay <code>{sym}</code> bằng mã VN khác (VNM, HPG, MWG...).</p>
      <ul>{items}</ul>
    </body></html>
    """
    return HTMLResponse(html)


async def health(request):
    return JSONResponse({"status": "ok", "openstock_base_url": _fetcher._base_url})


async def name(request):
    sym = request.path_params["symbol"].upper()
    return JSONResponse({"symbol": sym, "name": _fetcher.get_stock_name(sym)})


async def quote(request):
    sym = request.path_params["symbol"].upper()
    q = _fetcher.get_realtime_quote(sym)
    return JSONResponse(q.to_dict() if q else {"error": "no quote", "symbol": sym})


async def daily(request):
    sym = request.path_params["symbol"].upper()
    days = int(request.query_params.get("days", 30))
    try:
        df = _fetcher.get_daily_data(sym, days=days)
        return JSONResponse({"symbol": sym, "rows": len(df), "data": _df_to_records(df)})
    except Exception as exc:
        return JSONResponse({"error": str(exc), "symbol": sym}, status_code=502)


async def fundamental(request):
    sym = request.path_params["symbol"].upper()
    return JSONResponse(_fund.get_fundamental_bundle(sym))


async def capital_flow(request):
    sym = request.path_params["symbol"].upper()
    return JSONResponse(_fund.get_capital_flow(sym))


async def all_in_one(request):
    sym = request.path_params["symbol"].upper()
    q = _fetcher.get_realtime_quote(sym)
    try:
        df = _fetcher.get_daily_data(sym, days=30)
        daily_data = {"rows": len(df), "tail": _df_to_records(df.tail(5))}
    except Exception as exc:
        daily_data = {"error": str(exc)}
    return JSONResponse({
        "symbol": sym,
        "name": _fetcher.get_stock_name(sym),
        "quote": q.to_dict() if q else None,
        "daily": daily_data,
        "fundamental": _fund.get_fundamental_bundle(sym),
        "capital_flow": _fund.get_capital_flow(sym),
        "dragon_tiger": _fund.get_dragon_tiger_flag(sym),
    })


app = Starlette(routes=[
    Route("/", index),
    Route("/health", health),
    Route("/name/{symbol}", name),
    Route("/quote/{symbol}", quote),
    Route("/daily/{symbol}", daily),
    Route("/fundamental/{symbol}", fundamental),
    Route("/capital-flow/{symbol}", capital_flow),
    Route("/all/{symbol}", all_in_one),
])


if __name__ == "__main__":
    host = os.getenv("ADAPTER_HOST", "127.0.0.1")
    port = int(os.getenv("ADAPTER_PORT", "8010"))
    print(f"OpenStock adapter test server: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
