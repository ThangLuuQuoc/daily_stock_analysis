# -*- coding: utf-8 -*-
"""
越南市场股票搜索（OpenStock）

独立成文件而非塞进 `stocks.py`（upstream 文件），目的是把 fork 对 upstream 文件的
改动面降到最低——见 docs/vn-fork-touchpoints.md。挂载路径与之前保持一致
（`/api/v1/stocks/search`，见 api/v1/router.py 里与 `stocks.router` 相同的
`prefix="/stocks"`），前端 `apps/dsa-web/src/api/stocks.ts` 无需改动。
"""

import logging

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/search",
    summary="搜索股票（越南市场 / OpenStock）",
    description="按代码或名称搜索股票；启用 OpenStock 时直接查询越南三大交易所。",
)
def search_stocks(q: str = Query("", description="搜索关键词（代码或名称）")) -> dict:
    """通过 OpenStock /search 实时搜索越南市场标的。

    返回结构对齐前端自动补全（StockSuggestion）：
    ``{"count": n, "result": [{canonicalCode, displayCode, nameZh, market, ...}]}``
    未启用 OpenStock 或查询为空时返回空列表（前端回退到本地索引）。
    """
    query = (q or "").strip()
    if not query:
        return {"count": 0, "result": []}

    from src.config import get_config

    config = get_config()
    if not getattr(config, "openstock_enabled", False):
        return {"count": 0, "result": []}

    base_url = (getattr(config, "openstock_base_url", "") or "").rstrip("/")
    suggestions: list = []
    try:
        import requests

        resp = requests.get(f"{base_url}/search", params={"q": query}, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("result", []) if isinstance(payload, dict) else []
        for item in rows:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            name = str(item.get("name", "")).strip()
            exact = symbol == query.upper()
            suggestions.append({
                "canonicalCode": symbol,
                "displayCode": symbol,
                # 前端字段名为 nameZh（历史原因），此处填越南语公司名
                "nameZh": name or symbol,
                "nameEn": name,
                "market": "VN",
                "matchType": "exact" if exact else "contains",
                "matchField": "code" if symbol.startswith(query.upper()) else "name",
                "score": 100 if exact else 50,
                "active": bool(item.get("is_active", True)),
                "exchange": item.get("exchange"),
            })
    except Exception as exc:
        logger.warning("[搜索] OpenStock 搜索失败 q=%s: %s", query, exc)
        return {"count": 0, "result": []}

    return {"count": len(suggestions), "result": suggestions}
