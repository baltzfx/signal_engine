"""
Signal engine — Version 1 (rule-based).

Consumes events from the async queue, scores them per symbol, and emits
signals when the aggregate score exceeds the configured threshold.

The AI layer (Version 2) is an optional overlay — see app.ai.inference.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.event_queue import pop_event
from app.core.redis_pool import get_redis, redis_set, redis_get_hash
from app.core.monitoring import inc
from app.core import prometheus_metrics as prom
from app.signals.scoring import compute_signal_score
from app.signals.tracker import has_open_signal, register_signal
from app.storage.signal_log import log_signal

logger = logging.getLogger(__name__)

_task: Optional[asyncio.Task] = None
_running = False

# Per-symbol cooldown tracker: symbol → last_signal_ts
_cooldowns: Dict[str, float] = {}

# Pending events buffer: symbol → [events]
_event_buffer: Dict[str, List[Dict[str, Any]]] = {}

# Internal signal queue for Telegram
_signal_queue: Optional[asyncio.Queue] = None


def get_signal_queue() -> asyncio.Queue:
    global _signal_queue
    if _signal_queue is None:
        _signal_queue = asyncio.Queue(maxsize=10000)
    return _signal_queue


async def start_signal_engine() -> None:
    global _task, _running
    _running = True
    _task = asyncio.create_task(_signal_loop())
    logger.info("Signal engine (V1 rule-based) started")


async def stop_signal_engine() -> None:
    global _task, _running
    _running = False
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
    logger.info("Signal engine stopped")


# ── Main consumer loop ────────────────────────────────────────────

async def _signal_loop() -> None:
    """Consume events and evaluate signals."""
    while _running:
        try:
            event = await asyncio.wait_for(pop_event(), timeout=1.0)
        except asyncio.TimeoutError:
            # Flush any stale buffers periodically
            await _flush_buffers()
            continue
        except asyncio.CancelledError:
            return

        symbol = event.get("symbol", "")
        if not symbol:
            continue

        # Buffer event
        _event_buffer.setdefault(symbol, []).append(event)

        # Evaluate immediately on every event
        await _evaluate_symbol(symbol)


async def _flush_buffers() -> None:
    """Evaluate buffered events and age out stale data."""
    now = time.time()
    stale_symbols = []
    for sym, events in _event_buffer.items():
        if events and (now - events[-1].get("ts", now)) > 30:
            stale_symbols.append(sym)
    for sym in stale_symbols:
        _event_buffer.pop(sym, None)


async def _evaluate_symbol(symbol: str) -> None:
    """Score the symbol based on buffered events + current features."""
    # Guard: if tracker is enabled, block while a signal is open for this symbol;
    # otherwise fall back to the legacy time-based cooldown.
    now = time.time()
    if settings.tracker_enabled:
        if has_open_signal(symbol):
            return
    else:
        last_signal = _cooldowns.get(symbol, 0)
        if now - last_signal < settings.signal_cooldown_seconds:
            return

    events = _event_buffer.get(symbol, [])
    if not events:
        return

    # Read current features (primary timeframe)
    r = get_redis()
    features = await r.hgetall(f"{symbol}:features")
    if not features:
        return

    # ── Multi-timeframe alignment check ──────────────────────────
    mtf_aligned = True
    mtf_score = 1.0
    mtf_details = {}
    
    if settings.mtf_alignment_required:
        try:
            from app.features.mtf import get_mtf_score
            mtf_result = await get_mtf_score(symbol)
            mtf_aligned = mtf_result["alignment"]["aligned"]
            mtf_score = mtf_result["mtf_score"]
            mtf_details = mtf_result
            
            if not mtf_aligned:
                logger.debug(
                    "MTF not aligned for %s: %s", 
                    symbol, 
                    mtf_result["alignment"]["details"]
                )
                return
        except Exception:
            logger.warning("MTF check failed for %s — proceeding without MTF", symbol, exc_info=True)

    # ── Scoring ───────────────────────────────────────────────────
    result = compute_signal_score(features, events)
    score = result["score"]
    direction = result["direction"]

    if score < settings.signal_score_threshold:
        return

    # ── Build signal ──────────────────────────────────────────────
    trigger_event_types = list({e["type"] for e in events})
    signal = {
        "symbol": symbol,
        "direction": direction,
        "score": round(score, 4),
        "mtf_score": round(mtf_score, 4),
        "mtf_aligned": mtf_aligned,
        "mtf_details": mtf_details,
        "trigger_events": trigger_event_types,
        "features_snapshot": {k: v for k, v in features.items() if k != "ts"},
        "timestamp": now,
    }

    # ── AI overlay (V2 — optional) ────────────────────────────────
    if settings.ai_enabled:
        try:
            from app.ai.inference import predict
            ai_result = await predict(symbol, features)
            if ai_result and ai_result["confidence"] < settings.ai_confidence_threshold:
                logger.info(
                    "AI filtered signal for %s (confidence=%.3f)",
                    symbol,
                    ai_result["confidence"],
                )
                return
            if ai_result:
                signal["ai"] = ai_result
        except Exception:
            logger.warning("AI inference failed for %s — using rule-based only", symbol)

    # ── Emit signal ───────────────────────────────────────────────
    logger.info(
        "SIGNAL: %s %s score=%.3f mtf_score=%.3f triggers=%s",
        direction.upper(),
        symbol,
        score,
        mtf_score,
        trigger_event_types,
        extra={"symbol": symbol, "event": "signal"},
    )

    # Update Prometheus metrics
    prom.signals_generated_total.labels(symbol=symbol, direction=direction).inc()
    prom.signal_score.labels(direction=direction).observe(score)

    # ── Register in tracker (compute TP/SL from ATR + mark price) ─
    if settings.tracker_enabled:
        # Get entry price from mark price stream (preferred) or latest kline close
        r = get_redis()
        mark_data = await r.hgetall(f"{symbol}:mark_price")
        if mark_data:
            entry_price = float(mark_data.get("mark_price", 0))
        else:
            kline_data = await r.hgetall(f"{symbol}:kline")
            entry_price = float(kline_data.get("c", 0)) if kline_data else 0.0
        atr_val = float(features.get("atr", 0))
        if entry_price > 0 and atr_val > 0:
            tracked = await register_signal(signal, entry_price, atr_val)
            signal["entry_price"] = tracked.entry_price
            signal["tp_price"] = tracked.tp_price
            signal["sl_price"] = tracked.sl_price
            signal["atr"] = tracked.atr
        else:
            # Can't compute TP/SL — use legacy cooldown as fallback
            _cooldowns[symbol] = now
    else:
        _cooldowns[symbol] = now

    # 1. Persist to database FIRST (ensures signal is saved before Telegram)
    await log_signal(signal)
    inc("signals_emitted")
    inc(f"signal_{direction}")

    # 2. Broadcast to WebSocket clients for real-time UI updates
    try:
        from app.core.websocket_broadcast import broadcast_signal
        await broadcast_signal(signal)
    except Exception:
        logger.debug("WebSocket broadcast failed (no clients or not started)")

    # 3. Then push to Telegram queue
    sq = get_signal_queue()
    try:
        sq.put_nowait(signal)
        logger.debug(f"Signal queued for Telegram: {symbol} {direction} (queue size: {sq.qsize()}/{sq.maxsize})")
    except asyncio.QueueFull:
        logger.error(f"Signal queue full ({sq.maxsize}) — dropping signal for {symbol}")
        inc("telegram_queue_full")

    # Store latest signal in Redis
    await redis_set(f"{symbol}:signal", json.dumps(signal), ttl=settings.signal_max_ttl)

    # Clear event buffer for this symbol
    _event_buffer.pop(symbol, None)
