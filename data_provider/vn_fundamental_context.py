# -*- coding: utf-8 -*-
"""
越南市场基本面上下文聚合 (OpenStock)

为什么单独一个文件：`DataFetcherManager.get_fundamental_context` 里
`market in {"us","hk","jp","kr"}` 走 yfinance，其余全部落到 A 股 AkShare 分支。
越南标的 (`market == "vn"`) 因此会拿 `"FPT"` 去调 AkShare —— 返回空/报错；
而 `capital_flow` / `dragon_tiger` / `boards` 又被 `_market_tag != "cn"` 直接跳过，
导致 `OpenStockFundamentalAdapter` 在真实分析链路里从未被调用（写好了但是死代码），
财报同比、毛利率、经营现金流和**外资净流入**（越南最重要的资金信号）全都到不了 LLM。

本模块把这段逻辑放在 fork 自己的文件里，`base.py` 只留 3 行 hook，
把 fork 对上游文件的改动面降到最低（见 docs/vn-fork-touchpoints.md）。

契约与 `_build_offshore_fundamental_context` 完全一致：调用方不需要区分市场。
  valuation / growth / earnings / institution / capital_flow / dragon_tiger / boards
  + belong_boards / coverage / source_chain / errors / status / elapsed_ms

不适用越南市场的块（保持 not_supported，不伪造数据）：
  - dragon_tiger  龙虎榜：中国市场特有
  - boards        概念板块排行：越南按行业，暂不映射
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 越南市场不适用的块，统一按 not_supported 处理
_UNSUPPORTED_BLOCKS = ("dragon_tiger", "boards")

_NOT_APPLICABLE_REASON = "not applicable for VN market"


def build_vn_fundamental_context(
    manager: Any,
    stock_code: str,
    budget_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """聚合越南标的基本面上下文（fail-open，任何一块失败都不影响其余块）。

    Args:
        manager: :class:`DataFetcherManager` 实例（复用其缓存、重试与块构造工具）。
        stock_code: 越南标的代码，如 ``FPT`` / ``VNM``。
        budget_seconds: 本阶段总预算；None 则用 config 默认值。

    Returns:
        与 CN/offshore 路径同形状的 dict。
    """
    from src.config import get_config

    config = get_config()
    market = "vn"

    stage_timeout = float(
        budget_seconds if budget_seconds is not None else config.fundamental_stage_timeout_seconds
    )
    stage_timeout = max(0.0, stage_timeout)
    fetch_timeout = max(0.0, float(config.fundamental_fetch_timeout_seconds))

    cache_ttl = int(config.fundamental_cache_ttl_seconds)
    cache_max_entries = max(0, int(getattr(config, "fundamental_cache_max_entries", 256)))
    cache_key = manager._get_fundamental_cache_key(stock_code, stage_timeout)
    if cache_ttl > 0:
        manager._prune_fundamental_cache(cache_ttl, cache_max_entries)
        with manager._fundamental_cache_lock:
            cache_item = manager._fundamental_cache.get(cache_key)
            if cache_item:
                age = time.time() - float(cache_item.get("ts", 0))
                if age <= cache_ttl:
                    return cache_item.get("context", {})

    result_ctx: Dict[str, Any] = {
        "market": market,
        "valuation": {},
        "growth": {},
        "earnings": {},
        "institution": {},
        "capital_flow": {},
        "dragon_tiger": {},
        "boards": {},
        "belong_boards": [],
        "coverage": {},
        "source_chain": [],
        "errors": [],
    }

    start_ts = time.time()
    remaining_seconds = stage_timeout

    def _consume(consumed_ms: int) -> None:
        nonlocal remaining_seconds
        remaining_seconds = max(0.0, remaining_seconds - consumed_ms / 1000.0)

    # ------------------------------------------------------------------
    # 1) valuation —— 复用 OpenStock 实时行情（pe/pb/市值已在 quote 里）
    # ------------------------------------------------------------------
    valuation_timeout = min(fetch_timeout, remaining_seconds)
    if valuation_timeout > 0:
        quote_payload, valuation_err, valuation_ms = manager._run_with_retry(
            lambda: manager.get_realtime_quote(stock_code),
            valuation_timeout,
            "fundamental_valuation",
        )
        _consume(valuation_ms)
    else:
        quote_payload, valuation_err, valuation_ms = None, "fundamental stage timeout", 0

    valuation_payload = {
        "pe_ratio": getattr(quote_payload, "pe_ratio", None) if quote_payload else None,
        "pb_ratio": getattr(quote_payload, "pb_ratio", None) if quote_payload else None,
        "total_mv": getattr(quote_payload, "total_mv", None) if quote_payload else None,
        "circ_mv": getattr(quote_payload, "circ_mv", None) if quote_payload else None,
    }
    valuation_status = manager._infer_block_status(
        valuation_payload,
        "partial" if quote_payload is not None else "not_supported",
    )
    if valuation_status == "partial" and valuation_err and not manager._has_meaningful_payload(valuation_payload):
        valuation_status = "failed"
    result_ctx["valuation"] = manager._build_fundamental_block(
        valuation_status,
        valuation_payload,
        manager._normalize_source_chain(
            [{"provider": "realtime_quote", "result": valuation_status, "duration_ms": valuation_ms}],
            "realtime_quote",
            valuation_status,
            valuation_ms,
        ),
        [valuation_err] if valuation_err else [],
    )

    adapter = _get_adapter()
    if adapter is None:
        _finalize_unavailable(manager, result_ctx, valuation_status, start_ts)
        return result_ctx

    # ------------------------------------------------------------------
    # 2) growth / earnings / institution —— 一次 bundle 调用
    #    growth: revenue_yoy / net_profit_yoy / roe / gross_margin (年报序列算出)
    #    earnings: financial_report (含 operating_cash_flow) + dividend
    #    institution: foreign_ownership (越南特有：外资持股/剩余额度)
    # ------------------------------------------------------------------
    bundle_timeout = min(fetch_timeout, remaining_seconds)
    if bundle_timeout <= 0:
        bundle_payload, bundle_err, bundle_ms = {}, "fundamental stage timeout", 0
    else:
        bundle_payload, bundle_err, bundle_ms = manager._run_with_retry(
            lambda: adapter.get_fundamental_bundle(stock_code),
            bundle_timeout,
            "fundamental_bundle_openstock",
        )
        _consume(bundle_ms)
    if not isinstance(bundle_payload, dict):
        bundle_payload = {}

    bundle_status = str(bundle_payload.get("status", "not_supported"))
    bundle_chain = manager._normalize_source_chain(
        bundle_payload.get("source_chain", []),
        "fundamental_bundle_openstock",
        bundle_status,
        bundle_ms,
    )
    bundle_errors = list(bundle_payload.get("errors", []))
    if bundle_err:
        bundle_errors.append(bundle_err)

    for block in ("growth", "earnings", "institution"):
        payload = bundle_payload.get(block)
        payload = payload if isinstance(payload, dict) else {}
        result_ctx[block] = manager._build_fundamental_block(
            manager._infer_block_status(payload, bundle_status),
            payload,
            bundle_chain,
            list(bundle_errors),
        )

    belong_boards = bundle_payload.get("belong_boards")
    result_ctx["belong_boards"] = belong_boards if isinstance(belong_boards, list) else []

    # ------------------------------------------------------------------
    # 3) capital_flow —— 越南口径 = 按日外资净额 (foreignNet)
    #    这是越南市场最重要的资金信号，A 股的「主力资金」在越南没有对应口径。
    # ------------------------------------------------------------------
    flow_timeout = min(fetch_timeout, remaining_seconds)
    result_ctx["capital_flow"], flow_ms = _build_capital_flow_block(
        manager, adapter, stock_code, flow_timeout
    )
    _consume(flow_ms)

    # ------------------------------------------------------------------
    # 4) 不适用越南的块
    # ------------------------------------------------------------------
    for block in _UNSUPPORTED_BLOCKS:
        result_ctx[block] = manager._build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [_NOT_APPLICABLE_REASON],
        )

    _finalize(manager, result_ctx, start_ts, cache_key, cache_ttl, cache_max_entries)
    return result_ctx


def build_vn_capital_flow_block(
    manager: Any,
    stock_code: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    """单独的资金流块，供 ``DataFetcherManager.get_capital_flow_context`` 调用。

    Agent 工具 (``src/agent/tools/data_tools.py``) 直接走这个入口，所以不能只在
    ``build_vn_fundamental_context`` 里覆盖 —— 否则问股链路看不到外资流向。
    """
    adapter = _get_adapter()
    if adapter is None:
        return manager._build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            ["OpenStock fundamental adapter unavailable"],
        )
    block, _ = _build_capital_flow_block(manager, adapter, stock_code, timeout_seconds)
    return block


# ----------------------------------------------------------------------
# 内部工具
# ----------------------------------------------------------------------
def _build_capital_flow_block(
    manager: Any,
    adapter: Any,
    stock_code: str,
    timeout_seconds: float,
):
    """构造 capital_flow 块，返回 ``(block, cost_ms)``。"""
    if timeout_seconds <= 0:
        return (
            manager._build_fundamental_block(
                "failed",
                {},
                [{"provider": "fundamental_pipeline", "result": "failed", "duration_ms": 0}],
                ["fundamental stage timeout"],
            ),
            0,
        )

    payload, err, cost_ms = manager._run_with_retry(
        lambda: adapter.get_capital_flow(stock_code),
        timeout_seconds,
        "fundamental_capital_flow_openstock",
    )
    if not isinstance(payload, dict):
        payload = {}

    status = str(payload.get("status", "not_supported"))
    errors = list(payload.get("errors", []))
    if err:
        errors.append(err)
    data = {
        key: value
        for key, value in payload.items()
        if key not in ("status", "source_chain", "errors")
    }
    block = manager._build_fundamental_block(
        manager._infer_block_status(data, status),
        data,
        manager._normalize_source_chain(
            payload.get("source_chain", []),
            "fundamental_capital_flow_openstock",
            status,
            cost_ms,
        ),
        errors,
    )
    return block, cost_ms


def _get_adapter():
    """惰性构造 adapter；OpenStock 未启用或导入失败时返回 None（fail-open）。"""
    try:
        from src.config import get_config

        if not getattr(get_config(), "openstock_enabled", False):
            logger.debug("[基本面-VN] OPENSTOCK_ENABLED=false，跳过 OpenStock 基本面")
            return None
    except Exception as exc:
        logger.debug("[基本面-VN] 读取配置失败: %s", exc)
        return None

    try:
        from .openstock_fundamental_adapter import OpenStockFundamentalAdapter

        return OpenStockFundamentalAdapter()
    except Exception as exc:
        logger.warning("[基本面-VN] OpenStockFundamentalAdapter 不可用: %s", exc)
        return None


def _roll_up(result_ctx: Dict[str, Any], active_statuses: Dict[str, str]) -> None:
    """汇总 coverage / errors / source_chain / status（与 CN、offshore 路径口径一致）。"""
    blocks = ("valuation", "growth", "earnings", "institution", "capital_flow", "dragon_tiger", "boards")
    result_ctx["coverage"] = {
        block: result_ctx[block].get("status", "not_supported") for block in blocks
    }
    for block in blocks:
        result_ctx["errors"].extend(result_ctx[block].get("errors", []))
        result_ctx["source_chain"].extend(result_ctx[block].get("source_chain", []))

    if all(value == "not_supported" for value in active_statuses.values()):
        result_ctx["status"] = "not_supported"
    elif "failed" in active_statuses.values() or "partial" in active_statuses.values():
        result_ctx["status"] = "partial"
    else:
        result_ctx["status"] = "ok"


def _finalize(
    manager: Any,
    result_ctx: Dict[str, Any],
    start_ts: float,
    cache_key: str,
    cache_ttl: int,
    cache_max_entries: int,
) -> None:
    _roll_up(
        result_ctx,
        {
            "valuation": result_ctx["valuation"].get("status", "not_supported"),
            "growth": result_ctx["growth"].get("status", "not_supported"),
            "earnings": result_ctx["earnings"].get("status", "not_supported"),
            "capital_flow": result_ctx["capital_flow"].get("status", "not_supported"),
        },
    )
    result_ctx["elapsed_ms"] = int((time.time() - start_ts) * 1000)
    if cache_ttl > 0 and manager._should_cache_fundamental_context(result_ctx):
        with manager._fundamental_cache_lock:
            manager._fundamental_cache[cache_key] = {"ts": time.time(), "context": result_ctx}
        manager._prune_fundamental_cache(cache_ttl, cache_max_entries)


def _finalize_unavailable(
    manager: Any,
    result_ctx: Dict[str, Any],
    valuation_status: str,
    start_ts: float,
) -> None:
    """adapter 不可用：valuation 仍可能有值，其余块标 not_supported。不写缓存。"""
    reason = "OpenStock fundamental adapter unavailable"
    for block in ("growth", "earnings", "institution", "capital_flow", *_UNSUPPORTED_BLOCKS):
        result_ctx[block] = manager._build_fundamental_block(
            "not_supported",
            {},
            [{"provider": "fundamental_pipeline", "result": "not_supported", "duration_ms": 0}],
            [reason],
        )
    _roll_up(result_ctx, {"valuation": valuation_status})
    result_ctx["elapsed_ms"] = int((time.time() - start_ts) * 1000)


__all__: List[str] = ["build_vn_fundamental_context", "build_vn_capital_flow_block"]
