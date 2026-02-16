"""
Feature engine — reads raw data from Redis, computes features,
and writes them back for the event / signal engines.

**Architecture:**
The engine runs a **hybrid** approach:
  1. A **Redis Streams consumer** (primary) recomputes features when
     collectors push new data (event-driven, low latency).
  2. A **timer fallback** (safety net) sweeps all symbols periodically
     to ensure no symbol is stale if a stream message is lost.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.core.redis_pool import get_redis, redis_set, redis_set_hash, DATA_UPDATE_STREAM
from app.core.monitoring import inc
from app.features.computations import (
    compute_higher_high_lower_low,
    detect_breakout,
    compute_atr,
    candle_range_expansion,
    ema_slope,
    compute_vwap_distance,
    compute_oi_delta,
    compute_funding_zscore,
    compute_liquidation_ratio,
    compute_orderbook_imbalance,
    detect_wall_pressure,
)

logger = logging.getLogger(__name__)

_stream_task: Optional[asyncio.Task] = None
_fallback_task: Optional[asyncio.Task] = None
_running = False

# Fallback timer interval — only fires for symbols that haven't been
# updated via the stream within this window.
FALLBACK_INTERVAL = 10.0            # seconds
# How long to block on XREAD before looping
STREAM_BLOCK_MS = 1000              # 1 second

# Track last-computed timestamp per symbol for staleness detection
_last_computed: Dict[str, float] = {}


async def start_feature_engine() -> None:
    global _stream_task, _fallback_task, _running
    _running = True
    _stream_task = asyncio.create_task(_stream_consumer())
    _fallback_task = asyncio.create_task(_fallback_loop())
    logger.info("Feature engine started (stream consumer + %.0fs fallback)", FALLBACK_INTERVAL)


async def stop_feature_engine() -> None:
    global _stream_task, _fallback_task, _running
    _running = False
    for t in (_stream_task, _fallback_task):
        if t:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
    _stream_task = None
    _fallback_task = None
    logger.info("Feature engine stopped")


# ── Stream consumer (primary) ─────────────────────────────────────

async def _stream_consumer() -> None:
    """
    XREAD from the data-update stream.  Each message carries a symbol +
    data_type.  We batch-collect all symbols seen in a read, then
    recompute features for each unique symbol once.
    """
    r = get_redis()
    last_id = "$"                           # only new messages

    while _running:
        try:
            result = await r.xread(
                {DATA_UPDATE_STREAM: last_id},
                count=200,
                block=STREAM_BLOCK_MS,
            )
            if not result:
                continue

            dirty_symbols: Set[str] = set()
            for _stream_name, messages in result:
                for msg_id, fields in messages:
                    last_id = msg_id
                    sym = fields.get("symbol")
                    if sym and sym in settings.symbols:
                        dirty_symbols.add(sym)

            if dirty_symbols:
                tasks = [_compute_symbol_features(sym) for sym in dirty_symbols]
                await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Feature stream consumer error")
            await asyncio.sleep(1)


# ── Fallback timer ────────────────────────────────────────────────

async def _fallback_loop() -> None:
    """
    Safety-net timer: recomputes features for any symbol that hasn't
    been updated via the stream within ``FALLBACK_INTERVAL``.
    """
    while _running:
        try:
            now = time.time()
            stale = [
                sym for sym in settings.symbols
                if now - _last_computed.get(sym, 0) > FALLBACK_INTERVAL
            ]
            if stale:
                logger.debug("Fallback sweep: %d stale symbols", len(stale))
                tasks = [_compute_symbol_features(sym) for sym in stale]
                await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Feature fallback loop error")
        await asyncio.sleep(FALLBACK_INTERVAL)


# ── Per-symbol computation ────────────────────────────────────────

async def _compute_symbol_features(symbol: str) -> None:
    """Read raw data from Redis and compute all features for one symbol across all timeframes."""
    r = get_redis()

    # Compute features for each configured timeframe
    for timeframe in settings.timeframes:
        await _compute_timeframe_features(symbol, timeframe)

    # Update last computed timestamp
    _last_computed[symbol] = time.time()


async def _compute_timeframe_features(symbol: str, timeframe: str) -> None:
    """Compute features for a specific symbol and timeframe."""
    r = get_redis()

    # ── Load raw data ─────────────────────────────────────────────
    candles = await _load_list(r, f"{symbol}:klines_{timeframe}", 50)
    oi_history = await _load_list(r, f"{symbol}:oi_history", settings.oi_delta_window + 5)
    funding_history = await _load_list(r, f"{symbol}:funding_history", settings.funding_zscore_window + 5)
    liquidations = await _load_list(r, f"{symbol}:liquidations", settings.liq_ratio_window + 5)
    depth_raw = await r.hgetall(f"{symbol}:depth")

    if not candles:
        return  # no data yet for this symbol/timeframe

    # ── Market structure ──────────────────────────────────────────
    structure = compute_higher_high_lower_low(candles)
    breakout = detect_breakout(candles, settings.structure_lookback)

    # ── Volatility ────────────────────────────────────────────────
    atr = compute_atr(candles, settings.atr_period)
    range_exp = candle_range_expansion(candles, settings.atr_period)

    # ── Trend ─────────────────────────────────────────────────────
    ema_sl = ema_slope(candles, settings.ema_fast)
    vwap_dist = compute_vwap_distance(candles, settings.vwap_period)

    # ── Derivatives (shared across timeframes) ────────────────────
    oi_delta = compute_oi_delta(oi_history, settings.oi_delta_window)
    funding_z = compute_funding_zscore(funding_history, settings.funding_zscore_window)
    liq_ratio = compute_liquidation_ratio(liquidations, settings.liq_ratio_window)

    # ── Orderflow ─────────────────────────────────────────────────
    bids = _parse_json_field(depth_raw, "bids", [])
    asks = _parse_json_field(depth_raw, "asks", [])
    ob_imbalance = compute_orderbook_imbalance(bids, asks)
    wall_pressure = detect_wall_pressure(bids, asks, settings.wall_pressure_threshold)

    # ── Write features to Redis ───────────────────────────────────
    features: Dict[str, Any] = {
        "timeframe": timeframe,
        "structure_state": structure["state"],
        "structure_hh": str(structure["hh"]),
        "structure_ll": str(structure["ll"]),
        "breakout": breakout["breakout"],
        "breakout_level": str(breakout["level"]),
        "atr": str(round(atr, 6)),
        "range_expansion": str(round(range_exp, 4)),
        "ema_slope": str(round(ema_sl, 6)),
        "vwap_distance": str(round(vwap_dist, 6)),
        "oi_delta": str(round(oi_delta, 6)),
        "funding_zscore": str(round(funding_z, 4)),
        "liq_long": str(liq_ratio["long_liqs"]),
        "liq_short": str(liq_ratio["short_liqs"]),
        "liq_ratio": str(round(liq_ratio["ratio"], 4)),
        "liq_total_usd": str(round(liq_ratio["total_usd"], 2)),
        "ob_imbalance": str(round(ob_imbalance, 4)),
        "bid_wall": str(wall_pressure["bid_wall"]),
        "ask_wall": str(wall_pressure["ask_wall"]),
        "ts": str(time.time()),
    }

    # Store features per timeframe
    await redis_set_hash(f"{symbol}:features:{timeframe}", features, ttl=settings.redis_key_ttl)
    
    # Also maintain primary timeframe as default
    if timeframe == settings.primary_timeframe:
        await redis_set_hash(f"{symbol}:features", features, ttl=settings.redis_key_ttl)
    
    inc("features_computed")

    # Persist snapshot to SQLite (fire-and-forget)
    try:
        from app.storage.database import insert_feature_snapshot
        await insert_feature_snapshot(symbol, features, float(features["ts"]))
    except Exception:
        pass  # SQLite write failure should not block feature engine


# ── Helpers ───────────────────────────────────────────────────────

async def _load_list(r, key: str, count: int) -> List[Dict[str, Any]]:
    """Load a Redis list, JSON-parse each element."""
    raw = await r.lrange(key, 0, count - 1)
    out: List[Dict[str, Any]] = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except (json.JSONDecodeError, TypeError):
            pass
    return out


def _parse_json_field(mapping: dict, field: str, default: Any = None) -> Any:
    raw = mapping.get(field)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default
