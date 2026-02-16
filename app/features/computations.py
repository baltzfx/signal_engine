"""
Real-time feature computation helpers.
All functions are pure — they take data and return computed values.
"""

from __future__ import annotations

import math
from typing import List, Dict, Any, Optional, Tuple


# ── Market structure ──────────────────────────────────────────────

def compute_higher_high_lower_low(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Determine HH/HL or LH/LL state from recent candles.
    Returns: {"state": "uptrend"|"downtrend"|"neutral", "hh": bool, "ll": bool}
    """
    if len(candles) < 4:
        return {"state": "neutral", "hh": False, "ll": False}

    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]

    # Candles are newest-first: index 0 = most recent
    recent_high = max(highs[:3])
    prev_high = max(highs[3:6]) if len(highs) >= 6 else highs[-1]
    recent_low = min(lows[:3])
    prev_low = min(lows[3:6]) if len(lows) >= 6 else lows[-1]

    hh = recent_high > prev_high
    ll = recent_low < prev_low
    hl = recent_low > prev_low
    lh = recent_high < prev_high

    if hh and hl:
        state = "uptrend"
    elif ll and lh:
        state = "downtrend"
    else:
        state = "neutral"

    return {"state": state, "hh": hh, "ll": ll, "hl": hl, "lh": lh}


def detect_breakout(candles: List[Dict[str, Any]], lookback: int = 20) -> Dict[str, Any]:
    """
    Detect if latest close exceeds the lookback-period high/low.
    """
    if len(candles) < lookback + 1:
        return {"breakout": "none", "level": 0.0}

    history = candles[1 : lookback + 1]  # exclude latest
    latest = candles[0]

    high_max = max(float(c["h"]) for c in history)
    low_min = min(float(c["l"]) for c in history)
    close = float(latest["c"])

    if close > high_max:
        return {"breakout": "bullish", "level": high_max}
    elif close < low_min:
        return {"breakout": "bearish", "level": low_min}
    return {"breakout": "none", "level": 0.0}


# ── Volatility ────────────────────────────────────────────────────

def compute_atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    """Average True Range over *period* candles."""
    if len(candles) < period + 1:
        return 0.0

    trs: List[float] = []
    for i in range(period):
        c = candles[i]
        prev_c = candles[i + 1]
        h, l, prev_close = float(c["h"]), float(c["l"]), float(prev_c["c"])
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)

    return sum(trs) / len(trs)


def candle_range_expansion(candles: List[Dict[str, Any]], period: int = 14) -> float:
    """Ratio of latest candle range to average range over *period*."""
    if len(candles) < period + 1:
        return 1.0

    latest_range = float(candles[0]["h"]) - float(candles[0]["l"])
    avg_range = sum(float(c["h"]) - float(c["l"]) for c in candles[1 : period + 1]) / period

    if avg_range == 0:
        return 1.0
    return latest_range / avg_range


# ── Trend ─────────────────────────────────────────────────────────

def compute_ema(values: List[float], period: int) -> List[float]:
    """Exponential moving average (returns list same length as values)."""
    if not values or period <= 0:
        return []
    k = 2.0 / (period + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def ema_slope(candles: List[Dict[str, Any]], period: int = 9, lookback: int = 3) -> float:
    """
    Slope of EMA over last *lookback* candles (normalised).
    Positive → uptrend, negative → downtrend.
    """
    if len(candles) < period + lookback:
        return 0.0

    closes = [float(c["c"]) for c in reversed(candles[: period + lookback])]
    ema_vals = compute_ema(closes, period)

    if len(ema_vals) < lookback + 1:
        return 0.0

    recent = ema_vals[-1]
    past = ema_vals[-lookback - 1]
    mid = (recent + past) / 2
    if mid == 0:
        return 0.0
    return (recent - past) / mid


def compute_vwap_distance(candles: List[Dict[str, Any]], period: int = 20) -> float:
    """
    Distance of current price from rolling VWAP (normalised to %).
    Positive → above VWAP, negative → below.
    """
    if len(candles) < period:
        return 0.0

    cum_pv = 0.0
    cum_vol = 0.0
    for c in candles[:period]:
        typical = (float(c["h"]) + float(c["l"]) + float(c["c"])) / 3
        vol = float(c["v"])
        cum_pv += typical * vol
        cum_vol += vol

    if cum_vol == 0:
        return 0.0

    vwap = cum_pv / cum_vol
    price = float(candles[0]["c"])
    return (price - vwap) / vwap


# ── Derivatives ───────────────────────────────────────────────────

def compute_oi_delta(oi_history: List[Dict[str, Any]], window: int = 10) -> float:
    """
    Percentage change of OI over *window* samples.
    Positive → OI expanding.
    """
    if len(oi_history) < 2:
        return 0.0

    newest = float(oi_history[0].get("oi", 0))
    idx = min(window, len(oi_history) - 1)
    oldest = float(oi_history[idx].get("oi", 0))

    if oldest == 0:
        return 0.0
    return (newest - oldest) / oldest


def compute_funding_zscore(
    funding_history: List[Dict[str, Any]], window: int = 50
) -> float:
    """Z-score of the latest funding rate relative to rolling history."""
    rates = [float(f.get("funding_rate", 0)) for f in funding_history[:window]]
    if len(rates) < 5:
        return 0.0

    mean = sum(rates) / len(rates)
    var = sum((r - mean) ** 2 for r in rates) / len(rates)
    std = math.sqrt(var) if var > 0 else 1e-9
    return (rates[0] - mean) / std


def compute_liquidation_ratio(
    liquidations: List[Dict[str, Any]], window: int = 20
) -> Dict[str, Any]:
    """
    Ratio of long-liquidations vs short-liquidations in the window.
    Returns: {"long_liqs": int, "short_liqs": int, "ratio": float, "total_usd": float}
    ratio > 1 → more longs liquidated (bearish bias)
    """
    recent = liquidations[:window]
    long_liqs = 0
    short_liqs = 0
    total_usd = 0.0
    for liq in recent:
        qty = float(liq.get("qty", 0))
        price = float(liq.get("price", 0))
        usd = qty * price
        total_usd += usd
        if liq.get("side") == "SELL":
            long_liqs += 1  # SELL order = long position liquidated
        else:
            short_liqs += 1

    denom = max(short_liqs, 1)
    return {
        "long_liqs": long_liqs,
        "short_liqs": short_liqs,
        "ratio": long_liqs / denom,
        "total_usd": total_usd,
    }


# ── Orderflow ─────────────────────────────────────────────────────

def compute_orderbook_imbalance(bids: list, asks: list) -> float:
    """
    Orderbook imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
    Range: -1 (all asks) to +1 (all bids).
    """
    bid_vol = sum(float(b[1]) for b in bids) if bids else 0.0
    ask_vol = sum(float(a[1]) for a in asks) if asks else 0.0
    total = bid_vol + ask_vol
    if total == 0:
        return 0.0
    return (bid_vol - ask_vol) / total


def detect_wall_pressure(
    bids: list,
    asks: list,
    threshold_multiplier: float = 5.0,
) -> Dict[str, Any]:
    """
    Detect unusually large orders ("walls") relative to the mean level size.
    Returns: {"bid_wall": bool, "ask_wall": bool, "bid_wall_price": float, "ask_wall_price": float}
    """
    result = {"bid_wall": False, "ask_wall": False, "bid_wall_price": 0.0, "ask_wall_price": 0.0}

    if not bids or not asks:
        return result

    all_sizes = [float(b[1]) for b in bids] + [float(a[1]) for a in asks]
    mean_size = sum(all_sizes) / len(all_sizes) if all_sizes else 1.0

    threshold = mean_size * threshold_multiplier

    for b in bids:
        if float(b[1]) >= threshold:
            result["bid_wall"] = True
            result["bid_wall_price"] = float(b[0])
            break

    for a in asks:
        if float(a[1]) >= threshold:
            result["ask_wall"] = True
            result["ask_wall_price"] = float(a[0])
            break

    return result
