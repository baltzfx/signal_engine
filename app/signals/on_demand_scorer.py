"""
On-demand scorer for query responses.

Scores all configured symbols in batch and returns ranked results
with explanations for top performers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.redis_pool import get_redis, redis_get_hash
from app.signals.scoring import compute_signal_score
from app.ai.inference import predict

logger = logging.getLogger(__name__)


async def score_all_symbols() -> List[Dict[str, Any]]:
    """
    Score all configured symbols and return ranked results.

    Returns list of dicts with:
    - symbol: str
    - score: float
    - direction: str
    - features: dict
    - explanation: str
    """
    redis = get_redis()
    symbols = settings.symbols
    results = []

    # Get features for all symbols in parallel
    feature_tasks = []
    for symbol in symbols:
        task = redis_get_hash(f"{symbol}:features")
        feature_tasks.append(task)

    feature_results = await asyncio.gather(*feature_tasks, return_exceptions=True)

    for symbol, features_result in zip(symbols, feature_results):
        if isinstance(features_result, Exception):
            logger.warning(f"Failed to get features for {symbol}: {features_result}")
            continue

        features = features_result or {}

        # Skip if no features available
        if not features:
            continue

        try:
            # Use AI scoring if enabled, otherwise rule-based
            if settings.ai_enabled:
                # Get AI score
                ai_result = await predict(symbol, features)
                if ai_result:
                    prob_long = ai_result.get("probability_long", 0.5)
                    prob_short = ai_result.get("probability_short", 0.5)
                    confidence = ai_result.get("confidence", 0.0)

                    # Convert to score and direction
                    if prob_long > prob_short:
                        score = confidence
                        direction = "long"
                    else:
                        score = confidence
                        direction = "short"
                else:
                    # Fallback to rule-based if AI fails
                    rule_score = compute_signal_score(features, [])
                    score = rule_score.get("score", 0.0)
                    direction = rule_score.get("direction", "neutral")
            else:
                # Use rule-based scoring (empty events list for on-demand)
                rule_score = compute_signal_score(features, [])
                score = rule_score.get("score", 0.0)
                direction = rule_score.get("direction", "neutral")

            # Generate explanation
            explanation = _generate_explanation(symbol, features, score, direction)

            results.append({
                "symbol": symbol,
                "score": score,
                "direction": direction,
                "features": features,
                "explanation": explanation
            })

        except Exception as e:
            logger.error(f"Failed to score {symbol}: {e}")
            continue

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


def _generate_explanation(symbol: str, features: Dict[str, Any], score: float, direction: str) -> str:
    """Generate human-readable explanation for the score."""
    try:
        ema_slope = float(features.get("ema_slope", "0"))
        vwap_dist = float(features.get("vwap_distance", "0"))
        atr = float(features.get("atr", "0"))
        range_exp = float(features.get("range_expansion", "0"))
        oi_delta = float(features.get("oi_delta", "0"))
        funding_z = float(features.get("funding_zscore", "0"))
        liq_ratio = float(features.get("liq_ratio", "0"))

        explanation_parts = []

        # Trend analysis
        if abs(ema_slope) > 0.001:
            trend = "bullish" if ema_slope > 0 else "bearish"
            explanation_parts.append(f"Trend: {trend} (EMA slope: {ema_slope:.4f})")

        # VWAP position
        if abs(vwap_dist) > 0.001:
            position = "above" if vwap_dist > 0 else "below"
            explanation_parts.append(f"Price: {position} VWAP by {abs(vwap_dist):.4f}")

        # Volatility
        if range_exp > 0.01:
            explanation_parts.append(f"Volatility: Expanding (range: {range_exp:.4f})")

        # Open interest
        if abs(oi_delta) > 0.001:
            oi_trend = "increasing" if oi_delta > 0 else "decreasing"
            explanation_parts.append(f"OI: {oi_trend} ({oi_delta:.4f})")

        # Funding rate
        if abs(funding_z) > 1.0:
            funding_bias = "premium" if funding_z > 0 else "discount"
            explanation_parts.append(f"Funding: {funding_bias} ({funding_z:.2f}σ)")

        # Liquidations
        if liq_ratio > 0.1:
            explanation_parts.append(f"Liquidations: High ratio ({liq_ratio:.4f})")

        if not explanation_parts:
            explanation_parts.append("Mixed signals, low conviction")

        score_pct = int(score * 100)
        return f"{symbol}: {score_pct}% {direction} confidence. {' | '.join(explanation_parts)}"

    except Exception as e:
        logger.error(f"Failed to generate explanation for {symbol}: {e}")
        return f"{symbol}: {int(score * 100)}% {direction} confidence (analysis unavailable)"


async def get_top_symbols(count: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get top N symbols by score."""
    if count is None:
        count = settings.query_top_symbols_count

    all_scores = await score_all_symbols()
    return all_scores[:count]