"""
Signal lifecycle tracker — manages open signals from entry to resolution.

Each emitted signal is registered with:
  - Entry price (mark price at signal time)
  - Take-profit / stop-loss levels (ATR-based by default)
  - Max TTL (auto-expire stale signals)

A signal is considered **open** until one of:
  1. Price hits the take-profit level   → outcome = "tp_hit"
  2. Price hits the stop-loss level     → outcome = "sl_hit"
  3. TTL expires                        → outcome = "expired"
  4. Manually closed via API / code     → outcome = "manual"

While a signal is open for a symbol, no new signal is emitted for that symbol.
This replaces the dumb time-based cooldown.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.redis_pool import get_redis, redis_get_hash
from app.core.monitoring import inc

logger = logging.getLogger(__name__)


# ── Configuration (added to Settings later) ──────────────────────

# These can be overridden via config; defaults are sensible for crypto futures
DEFAULT_TP_ATR_MULT = 2.0       # TP = entry ± (ATR × mult)
DEFAULT_SL_ATR_MULT = 1.0       # SL = entry ∓ (ATR × mult)
DEFAULT_SIGNAL_TTL = 21600      # 6 hours max before auto-expire
PRICE_CHECK_INTERVAL = 1.0      # seconds between mark-price scans


class Outcome(str, Enum):
    OPEN = "open"
    TP_HIT = "tp_hit"
    SL_HIT = "sl_hit"
    EXPIRED = "expired"
    MANUAL = "manual"
    REVERSED = "reversed"        # new signal in opposite direction


@dataclass
class TrackedSignal:
    """State of a single open signal."""
    symbol: str
    direction: str                  # "long" | "short"
    score: float
    entry_price: float
    tp_price: float
    sl_price: float
    atr: float
    opened_at: float                # timestamp
    ttl: float = DEFAULT_SIGNAL_TTL
    outcome: Outcome = Outcome.OPEN
    closed_at: float = 0.0
    close_price: float = 0.0
    pnl_pct: float = 0.0           # (close - entry) / entry × direction_sign
    trigger_events: List[str] = field(default_factory=list)

    @property
    def is_open(self) -> bool:
        return self.outcome == Outcome.OPEN

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome.value
        return d


# ── In-memory tracker ─────────────────────────────────────────────

# symbol → TrackedSignal  (only ONE open signal per symbol at a time)
_open_signals: Dict[str, TrackedSignal] = {}

# Historical closed signals (ring buffer, last 500)
_closed_signals: List[Dict[str, Any]] = []
_MAX_CLOSED = 500

# Background price monitor task
_monitor_task: Optional[asyncio.Task] = None
_running = False


# ── Public API ────────────────────────────────────────────────────

def has_open_signal(symbol: str) -> bool:
    """Check whether this symbol already has an active signal."""
    sig = _open_signals.get(symbol)
    if sig is None:
        return False
    # Also check TTL expiry inline
    if time.time() - sig.opened_at > sig.ttl:
        _close_signal(sig, Outcome.EXPIRED, sig.entry_price)
        return False
    return sig.is_open


def get_open_signal(symbol: str) -> Optional[TrackedSignal]:
    """Return the open signal for a symbol, if any."""
    sig = _open_signals.get(symbol)
    if sig and sig.is_open:
        if time.time() - sig.opened_at > sig.ttl:
            _close_signal(sig, Outcome.EXPIRED, sig.entry_price)
            return None
        return sig
    return None


def get_all_open_signals() -> List[Dict[str, Any]]:
    """Return all currently open signals as dicts with current price and P&L."""
    now = time.time()
    result = []
    for sym, sig in list(_open_signals.items()):
        if sig.is_open:
            if now - sig.opened_at > sig.ttl:
                _close_signal(sig, Outcome.EXPIRED, sig.entry_price)
                continue
            d = sig.to_dict()
            d["age_seconds"] = round(now - sig.opened_at, 1)
            result.append(d)
    return result


async def get_all_open_signals_with_price() -> List[Dict[str, Any]]:
    """Return all currently open signals with real-time price and P&L."""
    signals = get_all_open_signals()
    r = get_redis()
    
    for sig in signals:
        sym = sig['symbol']
        
        # Get current mark price
        mark_data = await r.hgetall(f"{sym}:mark_price")
        if mark_data:
            current_price = float(mark_data.get("mark_price", 0))
        else:
            # Fallback to kline close (use primary timeframe)
            kline_data = await r.hgetall(f"{sym}:kline:{settings.primary_timeframe}")
            current_price = float(kline_data.get("c", 0)) if kline_data else 0
        
        if current_price > 0:
            sig['current_price'] = current_price
            
            # Calculate real-time P&L
            entry = sig.get('entry_price', 0)
            if entry > 0:
                direction = sig.get('direction', 'long')
                pnl = ((current_price - entry) / entry) * 100
                if direction == 'short':
                    pnl = -pnl
                sig['current_pnl_pct'] = round(pnl, 2)
    
    return signals


def get_closed_signals(limit: int = 50) -> List[Dict[str, Any]]:
    """Return recently closed signals."""
    return list(reversed(_closed_signals[-limit:]))


def get_tracker_stats() -> Dict[str, Any]:
    """Summary statistics for the tracker."""
    open_sigs = [s for s in _open_signals.values() if s.is_open]
    closed = _closed_signals[-100:]  # last 100
    tp_hits = sum(1 for c in closed if c["outcome"] == "tp_hit")
    sl_hits = sum(1 for c in closed if c["outcome"] == "sl_hit")
    expired = sum(1 for c in closed if c["outcome"] == "expired")
    total = len(closed)
    win_rate = tp_hits / total if total > 0 else 0.0
    avg_pnl = sum(c.get("pnl_pct", 0) for c in closed) / total if total > 0 else 0.0

    return {
        "open_count": len(open_sigs),
        "open_symbols": [s.symbol for s in open_sigs],
        "closed_total": len(_closed_signals),
        "recent_100": {
            "tp_hits": tp_hits,
            "sl_hits": sl_hits,
            "expired": expired,
            "win_rate": round(win_rate, 4),
            "avg_pnl_pct": round(avg_pnl, 4),
        },
    }


async def register_signal(
    signal: Dict[str, Any],
    entry_price: float,
    atr: float,
    tp_mult: Optional[float] = None,
    sl_mult: Optional[float] = None,
    ttl: Optional[float] = None,
) -> TrackedSignal:
    """
    Register a new signal in the tracker.

    If a signal in the opposite direction already exists for this symbol,
    the old one is closed as 'reversed'.
    """
    symbol = signal["symbol"]
    direction = signal["direction"]

    _tp_mult = tp_mult or getattr(settings, "tp_atr_multiplier", DEFAULT_TP_ATR_MULT)
    _sl_mult = sl_mult or getattr(settings, "sl_atr_multiplier", DEFAULT_SL_ATR_MULT)
    _ttl = ttl or getattr(settings, "signal_max_ttl", DEFAULT_SIGNAL_TTL)

    # Compute TP / SL from ATR
    if direction == "long":
        tp_price = entry_price + (atr * _tp_mult)
        sl_price = entry_price - (atr * _sl_mult)
    else:
        tp_price = entry_price - (atr * _tp_mult)
        sl_price = entry_price + (atr * _sl_mult)

    # Close existing signal if direction reversed
    existing = _open_signals.get(symbol)
    if existing and existing.is_open and existing.direction != direction:
        _close_signal(existing, Outcome.REVERSED, entry_price)

    tracked = TrackedSignal(
        symbol=symbol,
        direction=direction,
        score=signal.get("score", 0),
        entry_price=entry_price,
        tp_price=round(tp_price, 6),
        sl_price=round(sl_price, 6),
        atr=atr,
        opened_at=time.time(),
        ttl=_ttl,
        trigger_events=signal.get("trigger_events", []),
    )

    _open_signals[symbol] = tracked

    logger.info(
        "TRACKED: %s %s entry=%.4f tp=%.4f sl=%.4f atr=%.4f ttl=%ds",
        direction.upper(), symbol, entry_price, tp_price, sl_price, atr, _ttl,
    )
    inc("signals_tracked")

    # Persist to Redis
    try:
        r = get_redis()
        await r.hset(f"{symbol}:tracked_signal", mapping={
            k: str(v) for k, v in tracked.to_dict().items()
            if not isinstance(v, list)
        })
        await r.hset(f"{symbol}:tracked_signal",
                      "trigger_events", json.dumps(tracked.trigger_events))
        await r.expire(f"{symbol}:tracked_signal", int(_ttl) + 60)
    except Exception:
        logger.warning("Failed to persist tracked signal to Redis", exc_info=True)

    return tracked


def close_signal_manual(symbol: str, close_price: float) -> Optional[Dict[str, Any]]:
    """Manually close an open signal (e.g., from API)."""
    sig = _open_signals.get(symbol)
    if sig and sig.is_open:
        _close_signal(sig, Outcome.MANUAL, close_price)
        return sig.to_dict()
    return None


# ── Internal helpers ──────────────────────────────────────────────

def _close_signal(sig: TrackedSignal, outcome: Outcome, close_price: float) -> None:
    """Close a signal and move it to history."""
    sig.outcome = outcome
    sig.close_price = close_price
    sig.closed_at = time.time()

    # PnL calculation
    if sig.entry_price > 0:
        raw_pnl = (close_price - sig.entry_price) / sig.entry_price
        sig.pnl_pct = round(raw_pnl * 100, 4) if sig.direction == "long" else round(-raw_pnl * 100, 4)

    duration = round(sig.closed_at - sig.opened_at, 1)
    logger.info(
        "CLOSED: %s %s outcome=%s entry=%.4f close=%.4f pnl=%.2f%% duration=%.0fs",
        sig.direction.upper(), sig.symbol, outcome.value,
        sig.entry_price, close_price, sig.pnl_pct, duration,
    )

    # Counters
    inc(f"signal_{outcome.value}")
    inc("signals_closed")

    # Archive
    _closed_signals.append(sig.to_dict())
    if len(_closed_signals) > _MAX_CLOSED:
        _closed_signals.pop(0)

    # Remove from open
    _open_signals.pop(sig.symbol, None)

    # Async Redis cleanup — fire-and-forget
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_closed_signal(sig))
    except RuntimeError:
        pass  # no event loop — skip Redis persistence


async def _persist_closed_signal(sig: TrackedSignal) -> None:
    """Persist closed signal to Redis list + clean up tracked key."""
    try:
        r = get_redis()
        await r.delete(f"{sig.symbol}:tracked_signal")
        await r.lpush("signals:closed_log", json.dumps(sig.to_dict()))
        await r.ltrim("signals:closed_log", 0, 999)
    except Exception:
        logger.warning("Failed to persist closed signal to Redis", exc_info=True)

    # Persist to SQLite event log
    try:
        from app.storage.database import insert_event
        await insert_event({
            "type": f"signal_closed_{sig.outcome.value}",
            "symbol": sig.symbol,
            "detail": sig.to_dict(),
            "timestamp": sig.closed_at,
        })
    except Exception:
        logger.warning("Failed to persist signal close event", exc_info=True)

    # NEW: Record performance metrics
    try:
        from app.storage.database import record_signal_performance, get_signals
        from app.core import prometheus_metrics as prom

        # Try to find the signal ID from the database
        signal_id = None
        try:
            # Query database for this signal by symbol and timestamp
            signals = await get_signals(symbol=sig.symbol, limit=10)
            for db_sig in signals:
                # Match by symbol and timestamp (within 5 seconds tolerance)
                if (db_sig['symbol'] == sig.symbol and 
                    abs(db_sig['timestamp'] - sig.opened_at) < 5 and
                    not db_sig.get('outcome')):  # No outcome yet
                    signal_id = db_sig.get('id')
                    break
        except Exception:
            logger.debug(f"Could not find signal_id for {sig.symbol}", exc_info=True)

        await record_signal_performance(
            signal_id=signal_id,
            symbol=sig.symbol,
            direction=sig.direction,
            entry_price=sig.entry_price,
            exit_price=sig.close_price,
            entry_time=sig.opened_at,
            exit_time=sig.closed_at,
            outcome=sig.outcome.value,
            timeframe="5m",
            score=sig.score,
        )

        # Update Prometheus metrics
        duration = sig.closed_at - sig.opened_at
        prom.signal_outcomes_total.labels(
            symbol=sig.symbol,
            direction=sig.direction,
            outcome=sig.outcome.value,
        ).inc()
        prom.signal_returns.labels(direction=sig.direction).observe(sig.pnl_pct)
        prom.signal_duration_seconds.labels(outcome=sig.outcome.value).observe(duration)

    except Exception:
        logger.warning("Failed to record signal performance", exc_info=True)


# ── Background price monitor ─────────────────────────────────────

async def start_price_monitor() -> None:
    """Launch background task that checks mark price against TP/SL."""
    global _monitor_task, _running
    _running = True
    _monitor_task = asyncio.create_task(_price_monitor_loop())
    logger.info("Signal price monitor started")


async def restore_open_signals_from_db() -> int:
    """
    On startup, restore open signals from the database into the in-memory tracker.
    This prevents duplicate signal creation after restarts.
    Returns the number of signals restored.
    """
    try:
        from app.storage.database import get_signals
        
        # Get recent signals (last 100)
        signals = await get_signals(limit=100)
        
        restored_count = 0
        for sig_dict in signals:
            # Only restore if no outcome (still open)
            if not sig_dict.get('outcome'):
                symbol = sig_dict['symbol']
                
                # Check if not already in tracker
                if symbol not in _open_signals:
                    # Reconstruct TrackedSignal from database
                    tracked = TrackedSignal(
                        symbol=symbol,
                        direction=sig_dict.get('direction', 'long'),
                        score=sig_dict.get('score', 0.5),
                        entry_price=sig_dict.get('entry_price', 0),
                        tp_price=sig_dict.get('tp_price', 0),
                        sl_price=sig_dict.get('sl_price', 0),
                        atr=sig_dict.get('atr', 0),
                        opened_at=sig_dict.get('timestamp', 0),
                        ttl=getattr(settings, 'signal_max_ttl', DEFAULT_SIGNAL_TTL),
                        outcome=Outcome.OPEN,
                        trigger_events=[],
                    )
                    
                    # Check if expired
                    if time.time() - tracked.opened_at > tracked.ttl:
                        # Mark as expired immediately
                        _close_signal(tracked, Outcome.EXPIRED, tracked.entry_price)
                    else:
                        # Restore to tracker
                        _open_signals[symbol] = tracked
                        restored_count += 1
        
        return restored_count
    
    except Exception:
        logger.warning("Failed to restore signals from database", exc_info=True)
        return 0


async def stop_price_monitor() -> None:
    global _monitor_task, _running
    _running = False
    if _monitor_task:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
        _monitor_task = None
    logger.info("Signal price monitor stopped")


async def _price_monitor_loop() -> None:
    """
    Periodically scan all open signals and compare current mark price
    against TP and SL levels.
    """
    while _running:
        try:
            await _check_all_open_signals()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Price monitor error")
        await asyncio.sleep(PRICE_CHECK_INTERVAL)


async def _check_all_open_signals() -> None:
    """Single sweep of all open signals."""
    if not _open_signals:
        return

    r = get_redis()
    now = time.time()
    
    logger.debug(f"Checking {len(_open_signals)} open signals for TP/SL")

    for symbol, sig in list(_open_signals.items()):
        if not sig.is_open:
            continue

        # TTL check
        age = now - sig.opened_at
        if age > sig.ttl:
            logger.info(f"{symbol} EXPIRED after {age:.0f}s (TTL: {sig.ttl}s)")
            _close_signal(sig, Outcome.EXPIRED, sig.entry_price)
            continue

        # Get current mark price from Redis
        mark_data = await r.hgetall(f"{symbol}:mark_price")
        if not mark_data:
            # Fallback: use latest kline close (primary timeframe)
            kline_data = await r.hgetall(f"{symbol}:kline:{settings.primary_timeframe}")
            if not kline_data:
                logger.warning(f"{symbol}: No price data in Redis (no mark_price or kline)")
                continue
            current_price = float(kline_data.get("c", 0))
            logger.debug(f"{symbol}: Using kline price {current_price}")
        else:
            current_price = float(mark_data.get("mark_price", 0))
            logger.debug(f"{symbol}: Using mark price {current_price}")

        if current_price <= 0:
            logger.warning(f"{symbol}: Invalid price {current_price}")
            continue

        # Log price vs TP/SL
        logger.debug(
            f"{symbol} {sig.direction.upper()}: current={current_price:.6f}, "
            f"entry={sig.entry_price:.6f}, TP={sig.tp_price:.6f}, SL={sig.sl_price:.6f}"
        )

        # Check TP / SL
        if sig.direction == "long":
            if current_price >= sig.tp_price:
                logger.info(f"{symbol} LONG TP HIT: {current_price:.6f} >= {sig.tp_price:.6f}")
                _close_signal(sig, Outcome.TP_HIT, current_price)
            elif current_price <= sig.sl_price:
                logger.info(f"{symbol} LONG SL HIT: {current_price:.6f} <= {sig.sl_price:.6f}")
                _close_signal(sig, Outcome.SL_HIT, current_price)
        else:  # short
            if current_price <= sig.tp_price:
                logger.info(f"{symbol} SHORT TP HIT: {current_price:.6f} <= {sig.tp_price:.6f}")
                _close_signal(sig, Outcome.TP_HIT, current_price)
            elif current_price >= sig.sl_price:
                logger.info(f"{symbol} SHORT SL HIT: {current_price:.6f} >= {sig.sl_price:.6f}")
                _close_signal(sig, Outcome.SL_HIT, current_price)
