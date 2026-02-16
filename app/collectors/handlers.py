"""
Individual stream handlers that parse raw Binance messages and push
data into Redis.  Each handler is a plain async function.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict

from app.core.redis_pool import redis_set, redis_set_hash, get_redis, redis_stream_notify
from app.core.config import settings
from app.core.monitoring import inc
from app.collectors.validation import (
    validate_kline,
    validate_depth,
    validate_mark_price,
    validate_force_order,
    validate_open_interest,
    validate_funding,
)

logger = logging.getLogger(__name__)


# ── Kline (multi-timeframe) ──────────────────────────────────────

async def handle_kline(msg: Dict[str, Any]) -> None:
    """
    Stream: <symbol>@kline_1m, <symbol>@kline_5m, etc.
    Stores latest OHLCV candle in SYMBOL:kline:TIMEFRAME hash.
    Also appends to a Redis list for rolling history.
    """
    kline = validate_kline(msg)
    if kline is None:
        inc("ws_kline_invalid")
        return

    symbol = kline["s"].upper()
    
    # Extract timeframe from stream name (e.g., "btcusdt@kline_5m" -> "5m")
    stream_name = msg.get("stream", "")
    if "@kline_" in stream_name:
        timeframe = stream_name.split("@kline_")[1]
    else:
        timeframe = "5m"  # fallback
    
    candle = {
        "t": kline["t"],        # open time ms
        "o": kline["o"],
        "h": kline["h"],
        "l": kline["l"],
        "c": kline["c"],
        "v": kline["v"],        # base volume
        "q": kline["q"],        # quote volume
        "closed": str(kline["x"]),  # is candle closed
        "ts": time.time(),
    }
    
    # Store per-timeframe
    await redis_set_hash(f"{symbol}:kline:{timeframe}", candle, ttl=600)
    inc("ws_kline_messages")

    # If candle closed, push to rolling list (keep last N)
    if kline["x"]:
        import json
        r = get_redis()
        list_key = f"{symbol}:klines_{timeframe}"
        await r.lpush(list_key, json.dumps(candle))
        await r.ltrim(list_key, 0, settings.structure_lookback + settings.atr_period + 5)
        await r.expire(list_key, 3600)
        await redis_stream_notify(symbol, f"kline_{timeframe}")


# ── Depth (top 10 levels) ────────────────────────────────────────

async def handle_depth(msg: Dict[str, Any]) -> None:
    """
    Stream: <symbol>@depth10@100ms
    Stores bid/ask arrays in SYMBOL:depth hash.
    """
    validated = validate_depth(msg)
    if validated is None:
        inc("ws_depth_invalid")
        return

    symbol = validated["symbol"]
    import json
    depth = {
        "bids": json.dumps(validated["bids"]),
        "asks": json.dumps(validated["asks"]),
        "ts": str(time.time()),
    }
    await redis_set_hash(f"{symbol}:depth", depth, ttl=30)
    inc("ws_depth_messages")
    await redis_stream_notify(symbol, "depth")


# ── Mark price ────────────────────────────────────────────────────

async def handle_mark_price(msg: Dict[str, Any]) -> None:
    """
    Stream: <symbol>@markPrice@1s
    Stores mark price + funding rate.
    """
    data = validate_mark_price(msg)
    if data is None:
        inc("ws_markprice_invalid")
        return
    symbol = data["s"].upper()

    info = {
        "mark_price": data.get("p", "0"),
        "index_price": data.get("i", "0"),
        "funding_rate": data.get("r", "0"),
        "next_funding_time": str(data.get("T", 0)),
        "ts": str(time.time()),
    }
    await redis_set_hash(f"{symbol}:mark_price", info, ttl=60)
    inc("ws_markprice_messages")


# ── Force orders (liquidations) ──────────────────────────────────

async def handle_force_order(msg: Dict[str, Any]) -> None:
    """
    Stream: <symbol>@forceOrder  (or !forceOrder@arr)
    Pushes liquidation events into a Redis list for window analysis.
    """
    order = validate_force_order(msg)
    if order is None:
        inc("ws_forceorder_invalid")
        return

    symbol = order["s"].upper()

    import json
    liq = {
        "symbol": symbol,
        "side": order.get("S", ""),        # SELL = long liq, BUY = short liq
        "price": order.get("p", "0"),
        "qty": order.get("q", "0"),
        "trade_time": order.get("T", 0),
        "ts": time.time(),
    }

    r = get_redis()
    list_key = f"{symbol}:liquidations"
    await r.lpush(list_key, json.dumps(liq))
    await r.ltrim(list_key, 0, 199)  # keep last 200
    await r.expire(list_key, 600)
    inc("ws_forceorder_messages")

    # Also store aggregate counter (per 5-min window key)
    window_key = f"{symbol}:liq_count"
    await r.incr(window_key)
    await r.expire(window_key, 300)
    await redis_stream_notify(symbol, "liquidation")


# ── Open Interest (via REST, not WS) ─────────────────────────────

async def poll_open_interest(symbols: list[str]) -> None:
    """
    REST poller — called periodically from the collector manager.
    /fapi/v1/openInterest?symbol=BTCUSDT
    """
    import httpx

    base = settings.binance_futures_rest
    async with httpx.AsyncClient(timeout=10) as client:
        for symbol in symbols:
            try:
                resp = await client.get(
                    f"{base}/fapi/v1/openInterest",
                    params={"symbol": symbol},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if not validate_open_interest(data):
                        inc("rest_oi_invalid")
                        continue
                    oi_info = {
                        "oi": data.get("openInterest", "0"),
                        "symbol": symbol,
                        "ts": str(time.time()),
                    }
                    await redis_set_hash(f"{symbol}:open_interest", oi_info, ttl=300)

                    # Push to rolling list for delta computation
                    import json
                    r = get_redis()
                    list_key = f"{symbol}:oi_history"
                    await r.lpush(list_key, json.dumps(oi_info))
                    await r.ltrim(list_key, 0, settings.oi_delta_window + 5)
                    await r.expire(list_key, 3600)
                    await redis_stream_notify(symbol, "oi")
            except Exception:
                logger.warning("OI poll failed for %s", symbol, exc_info=True)
            # Small delay to avoid rate limits
            await asyncio.sleep(0.05)


# ── Funding rate (via REST) ──────────────────────────────────────

async def poll_funding_rate(symbols: list[str]) -> None:
    """
    REST poller — /fapi/v1/premiumIndex
    """
    import httpx

    base = settings.binance_futures_rest
    async with httpx.AsyncClient(timeout=10) as client:
        for symbol in symbols:
            try:
                resp = await client.get(
                    f"{base}/fapi/v1/premiumIndex",
                    params={"symbol": symbol},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if not validate_funding(data):
                        inc("rest_funding_invalid")
                        continue
                    funding = {
                        "funding_rate": data.get("lastFundingRate", "0"),
                        "mark_price": data.get("markPrice", "0"),
                        "index_price": data.get("indexPrice", "0"),
                        "next_funding_time": str(data.get("nextFundingTime", 0)),
                        "ts": str(time.time()),
                    }
                    await redis_set_hash(f"{symbol}:funding", funding, ttl=600)

                    # Rolling history for z-score
                    import json
                    r = get_redis()
                    list_key = f"{symbol}:funding_history"
                    await r.lpush(list_key, json.dumps(funding))
                    await r.ltrim(list_key, 0, settings.funding_zscore_window + 5)
                    await r.expire(list_key, 86400)
                    await redis_stream_notify(symbol, "funding")
            except Exception:
                logger.warning("Funding poll failed for %s", symbol, exc_info=True)
            await asyncio.sleep(0.05)
