"""
Multi-timeframe (MTF) analysis module.

Manages feature computation and alignment across multiple timeframes
to improve signal quality through timeframe confluence.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.redis_pool import get_redis

logger = logging.getLogger(__name__)

# Map kline intervals to Redis key suffixes
TIMEFRAME_MAP = {
    "1m": "kline_1m",
    "5m": "kline_5m",
    "15m": "kline_15m",
    "1h": "kline_1h",
}


async def get_mtf_features(symbol: str, timeframes: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
    """
    Retrieve features for multiple timeframes.
    
    Returns:
        {"5m": {...features...}, "15m": {...features...}, ...}
    """
    if timeframes is None:
        timeframes = settings.timeframes

    r = get_redis()
    result = {}

    for tf in timeframes:
        key = f"{symbol}:features:{tf}"
        features = await r.hgetall(key)
        if features:
            result[tf] = features

    return result


def check_mtf_alignment(
    mtf_features: Dict[str, Dict[str, str]],
    min_aligned: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Check if multiple timeframes are aligned (agreeing on direction).
    
    Returns:
        {
            "aligned": bool,
            "direction": "long" | "short" | "neutral",
            "aligned_count": int,
            "total_timeframes": int,
            "details": {...}
        }
    """
    if min_aligned is None:
        min_aligned = settings.mtf_min_aligned

    if not mtf_features:
        return {
            "aligned": False,
            "direction": "neutral",
            "aligned_count": 0,
            "total_timeframes": 0,
            "details": {},
        }

    # Analyze trend direction per timeframe
    directions = {}
    for tf, features in mtf_features.items():
        direction = _get_timeframe_direction(features)
        directions[tf] = direction

    # Count bullish vs bearish timeframes
    bullish_count = sum(1 for d in directions.values() if d == "long")
    bearish_count = sum(1 for d in directions.values() if d == "short")
    total = len(directions)

    # Determine overall alignment
    if bullish_count >= min_aligned and bullish_count > bearish_count:
        aligned = True
        direction = "long"
        aligned_count = bullish_count
    elif bearish_count >= min_aligned and bearish_count > bullish_count:
        aligned = True
        direction = "short"
        aligned_count = bearish_count
    else:
        aligned = False
        direction = "neutral"
        aligned_count = max(bullish_count, bearish_count)

    return {
        "aligned": aligned,
        "direction": direction,
        "aligned_count": aligned_count,
        "total_timeframes": total,
        "details": directions,
        "strength": aligned_count / total if total > 0 else 0.0,
    }


def _get_timeframe_direction(features: Dict[str, str]) -> str:
    """Determine trend direction from features."""
    # Use multiple signals to determine direction
    ema_slope = float(features.get("ema_slope", "0"))
    vwap_dist = float(features.get("vwap_distance", "0"))
    structure = features.get("structure_state", "neutral")
    breakout = features.get("breakout", "none")

    bullish_votes = 0
    bearish_votes = 0

    # EMA slope
    if ema_slope > 0.001:
        bullish_votes += 1
    elif ema_slope < -0.001:
        bearish_votes += 1

    # VWAP position
    if vwap_dist > 0.005:
        bullish_votes += 1
    elif vwap_dist < -0.005:
        bearish_votes += 1

    # Structure
    if structure == "uptrend":
        bullish_votes += 1
    elif structure == "downtrend":
        bearish_votes += 1

    # Breakout
    if breakout == "bullish":
        bullish_votes += 2
    elif breakout == "bearish":
        bearish_votes += 2

    if bullish_votes > bearish_votes:
        return "long"
    elif bearish_votes > bullish_votes:
        return "short"
    else:
        return "neutral"


async def get_mtf_score(symbol: str) -> Dict[str, Any]:
    """
    Get multi-timeframe alignment score for a symbol.
    Higher alignment = stronger signal.
    """
    mtf_features = await get_mtf_features(symbol)
    alignment = check_mtf_alignment(mtf_features)

    # Calculate composite MTF score
    strength = alignment.get("strength", 0.0)
    aligned_count = alignment.get("aligned_count", 0)
    total = alignment.get("total_timeframes", 1)

    # Bonus for having all timeframes aligned
    full_alignment_bonus = 0.2 if aligned_count == total and total >= 3 else 0.0

    mtf_score = min(strength + full_alignment_bonus, 1.0)

    return {
        "symbol": symbol,
        "mtf_score": round(mtf_score, 4),
        "alignment": alignment,
        "timeframes": list(mtf_features.keys()),
    }
