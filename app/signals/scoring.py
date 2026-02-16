"""
Rule-based scoring logic (Version 1).

Computes a normalised score in [0, 1] based on:
  - Trend direction (EMA slope, VWAP position)
  - Liquidation bias
  - Volatility expansion
  - OI expansion
  - Market structure confirmation
  - Event quality

Returns {"score": float, "direction": "long"|"short"}.
"""

from __future__ import annotations

from typing import Any, Dict, List


# ── Weight table (must sum to 1.0) ───────────────────────────────
WEIGHTS = {
    "trend": 0.20,
    "liquidation": 0.15,
    "volatility": 0.15,
    "vwap": 0.10,
    "oi": 0.15,
    "structure": 0.15,
    "event_quality": 0.10,
}


def compute_signal_score(
    features: Dict[str, str],
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate features + events and return a composite score.
    All feature values arrive from Redis as strings.
    """

    # ── Direction vote ────────────────────────────────────────────
    bull_votes = 0
    bear_votes = 0

    # --- Trend (EMA slope) ---
    ema_sl = float(features.get("ema_slope", "0"))
    if ema_sl > 0.001:
        trend_score = min(abs(ema_sl) / 0.01, 1.0)
        bull_votes += 1
    elif ema_sl < -0.001:
        trend_score = min(abs(ema_sl) / 0.01, 1.0)
        bear_votes += 1
    else:
        trend_score = 0.0

    # --- VWAP distance ---
    vwap_dist = float(features.get("vwap_distance", "0"))
    if vwap_dist > 0:
        vwap_score = min(abs(vwap_dist) / 0.02, 1.0)
        bull_votes += 1
    elif vwap_dist < 0:
        vwap_score = min(abs(vwap_dist) / 0.02, 1.0)
        bear_votes += 1
    else:
        vwap_score = 0.0

    # --- Liquidation bias ---
    liq_ratio_val = float(features.get("liq_ratio", "1"))
    if liq_ratio_val > 1.3:
        liq_score = min((liq_ratio_val - 1) / 2.0, 1.0)
        bear_votes += 1  # longs getting liquidated → bearish pressure
    elif liq_ratio_val < 0.7 and liq_ratio_val > 0:
        liq_score = min((1 - liq_ratio_val) / 0.5, 1.0)
        bull_votes += 1  # shorts getting liquidated → bullish pressure
    else:
        liq_score = 0.2

    # --- Volatility expansion ---
    range_exp = float(features.get("range_expansion", "1"))
    vol_score = min(max(range_exp - 1, 0) / 2.0, 1.0)

    # --- OI expansion ---
    oi_delta = float(features.get("oi_delta", "0"))
    oi_score = min(abs(oi_delta) * 10, 1.0)  # delta is a fraction
    if oi_delta > 0:
        # OI expanding — confirming trend
        pass
    elif oi_delta < -0.02:
        # OI contracting — weakens signal
        oi_score *= 0.5

    # --- Structure ---
    structure_state = features.get("structure_state", "neutral")
    breakout = features.get("breakout", "none")
    structure_score = 0.0
    if structure_state == "uptrend":
        structure_score = 0.6
        bull_votes += 1
    elif structure_state == "downtrend":
        structure_score = 0.6
        bear_votes += 1
    if breakout == "bullish":
        structure_score = min(structure_score + 0.4, 1.0)
        bull_votes += 1
    elif breakout == "bearish":
        structure_score = min(structure_score + 0.4, 1.0)
        bear_votes += 1

    # --- Event quality (more unique event types = stronger) ---
    unique_types = {e["type"] for e in events}
    event_quality_score = min(len(unique_types) / 4.0, 1.0)

    # Event-level direction hints
    for e in events:
        detail = e.get("detail", {})
        bias = detail.get("bias") or detail.get("direction")
        if bias == "bullish":
            bull_votes += 1
        elif bias == "bearish":
            bear_votes += 1

    # ── Direction decision ────────────────────────────────────────
    direction = "long" if bull_votes >= bear_votes else "short"

    # ── Composite score ───────────────────────────────────────────
    score = (
        WEIGHTS["trend"] * trend_score
        + WEIGHTS["liquidation"] * liq_score
        + WEIGHTS["volatility"] * vol_score
        + WEIGHTS["vwap"] * vwap_score
        + WEIGHTS["oi"] * oi_score
        + WEIGHTS["structure"] * structure_score
        + WEIGHTS["event_quality"] * event_quality_score
    )

    return {
        "score": score,
        "direction": direction,
        "components": {
            "trend": round(trend_score, 3),
            "liquidation": round(liq_score, 3),
            "volatility": round(vol_score, 3),
            "vwap": round(vwap_score, 3),
            "oi": round(oi_score, 3),
            "structure": round(structure_score, 3),
            "event_quality": round(event_quality_score, 3),
        },
        "votes": {"bull": bull_votes, "bear": bear_votes},
    }
