"""
Event engine — reads computed features from Redis and detects discrete events.
Events are pushed into the shared async event queue for the signal engine.

Runs as a background asyncio task.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.redis_pool import get_redis, redis_get, redis_get_hash
from app.core.event_queue import push_event
from app.core.monitoring import inc

logger = logging.getLogger(__name__)

_task: Optional[asyncio.Task] = None
_running = False

# How often the event engine scans features (seconds)
EVENT_SCAN_INTERVAL = 2.0

# Track previous feature snapshots to detect *changes* (flips / spikes)
_prev_features: Dict[str, Dict[str, Any]] = {}


async def start_event_engine() -> None:
    global _task, _running
    _running = True
    _task = asyncio.create_task(_event_loop())
    logger.info("Event engine started")


async def stop_event_engine() -> None:
    global _task, _running
    _running = False
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
    logger.info("Event engine stopped")


# ── Main loop ─────────────────────────────────────────────────────

async def _event_loop() -> None:
    while _running:
        t0 = time.time()
        try:
            tasks = [_scan_symbol(sym) for sym in settings.symbols]
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Event engine cycle error")

        elapsed = time.time() - t0
        sleep = max(0, EVENT_SCAN_INTERVAL - elapsed)
        await asyncio.sleep(sleep)


# ── Per-symbol event detection ────────────────────────────────────

async def _scan_symbol(symbol: str) -> None:
    r = get_redis()
    features = await r.hgetall(f"{symbol}:features")
    if not features:
        return

    prev = _prev_features.get(symbol, {})
    events_found: List[Dict[str, Any]] = []

    # 1 ── Liquidation spike ───────────────────────────────────────
    liq_total_usd = float(features.get("liq_total_usd", 0))
    prev_liq_usd = float(prev.get("liq_total_usd", 0))
    if prev_liq_usd > 0 and liq_total_usd > prev_liq_usd * settings.liq_spike_threshold:
        liq_ratio = float(features.get("liq_ratio", 1))
        events_found.append({
            "type": "liquidation_spike",
            "symbol": symbol,
            "detail": {
                "total_usd": liq_total_usd,
                "ratio": liq_ratio,
                "bias": "bearish" if liq_ratio > 1 else "bullish",
            },
            "ts": time.time(),
        })

    # 2 ── Open interest expansion ─────────────────────────────────
    oi_delta = float(features.get("oi_delta", 0))
    if abs(oi_delta) > settings.oi_expansion_threshold / 100:  # stored as fraction
        events_found.append({
            "type": "oi_expansion",
            "symbol": symbol,
            "detail": {"oi_delta_pct": round(oi_delta * 100, 2)},
            "ts": time.time(),
        })

    # 3 ── ATR volatility expansion ────────────────────────────────
    range_expansion = float(features.get("range_expansion", 1))
    if range_expansion > settings.atr_expansion_threshold:
        events_found.append({
            "type": "atr_expansion",
            "symbol": symbol,
            "detail": {"range_expansion": round(range_expansion, 3)},
            "ts": time.time(),
        })

    # 4 ── Market structure breakout ───────────────────────────────
    breakout = features.get("breakout", "none")
    prev_breakout = prev.get("breakout", "none")
    if breakout != "none" and breakout != prev_breakout:
        events_found.append({
            "type": "structure_breakout",
            "symbol": symbol,
            "detail": {
                "direction": breakout,
                "level": float(features.get("breakout_level", 0)),
            },
            "ts": time.time(),
        })

    # 5 ── Orderbook imbalance flip ────────────────────────────────
    ob_imb = float(features.get("ob_imbalance", 0))
    prev_imb = float(prev.get("ob_imbalance", 0))
    # Detect sign change with meaningful magnitude
    if (
        prev_imb != 0
        and ob_imb * prev_imb < 0  # sign flipped
        and abs(ob_imb) >= settings.imbalance_flip_threshold
    ):
        events_found.append({
            "type": "imbalance_flip",
            "symbol": symbol,
            "detail": {
                "from": round(prev_imb, 4),
                "to": round(ob_imb, 4),
                "direction": "bullish" if ob_imb > 0 else "bearish",
            },
            "ts": time.time(),
        })

    # 6 ── Funding extreme ─────────────────────────────────────────
    funding_z = float(features.get("funding_zscore", 0))
    if abs(funding_z) > settings.funding_extreme_threshold:
        events_found.append({
            "type": "funding_extreme",
            "symbol": symbol,
            "detail": {
                "zscore": round(funding_z, 3),
                "bias": "bearish" if funding_z > 0 else "bullish",  # high funding → crowded longs
            },
            "ts": time.time(),
        })

    # Push events
    for event in events_found:
        await push_event(event)
        inc("events_triggered")
        inc(f"event_{event['type']}")
        # Persist to SQLite
        try:
            from app.storage.database import insert_event
            await insert_event(event)
        except Exception:
            pass  # SQLite write failure should not block engine
        logger.info(
            "Event detected: %s on %s",
            event["type"],
            symbol,
            extra={"symbol": symbol, "event": event["type"]},
        )

    # Save current snapshot for next comparison
    _prev_features[symbol] = dict(features)
