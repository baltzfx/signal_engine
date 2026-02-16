"""
Integration test — pushes mock data through the full pipeline:
  mock candles → feature computation → event detection → signal scoring

No Redis or WebSocket needed.  Tests the pure-logic path end-to-end.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.features.computations import (
    compute_atr,
    candle_range_expansion,
    ema_slope,
    compute_vwap_distance,
    compute_higher_high_lower_low,
    detect_breakout,
    compute_oi_delta,
    compute_funding_zscore,
    compute_liquidation_ratio,
    compute_orderbook_imbalance,
)
from app.signals.scoring import compute_signal_score
from app.core.event_queue import push_event, pop_event


# ── Helpers ───────────────────────────────────────────────────────

def _make_candle(o, h, l, c, v=100.0):
    return {"o": str(o), "h": str(h), "l": str(l), "c": str(c), "v": str(v)}


def _make_uptrend_candles(n=30, base=100.0, step=0.5):
    """Candles with a clear uptrend, newest first."""
    candles = []
    for i in range(n):
        o = base + i * step
        h = o + 1.5
        l = o - 0.3
        c = o + 1.0
        candles.append(_make_candle(o, h, l, c, v=1000 + i * 10))
    candles.reverse()
    return candles


def _make_oi_history(expanding=True):
    base = 1_000_000
    return [
        {"oi": base + (i * 5000 if expanding else -i * 5000)}
        for i in range(20, -1, -1)
    ]


def _make_funding_history(extreme=False):
    rate = 0.001
    history = [{"funding_rate": rate}] * 50
    if extreme:
        history[0] = {"funding_rate": 0.05}  # very high latest
    return history


def _make_liquidations(bias="bearish"):
    """bias='bearish' → more longs liquidated (SELL orders)."""
    liqs = []
    for _ in range(15):
        liqs.append({"side": "SELL", "qty": 1, "price": 100})
    for _ in range(5):
        liqs.append({"side": "BUY", "qty": 1, "price": 100})
    if bias == "bullish":
        liqs = liqs[::-1]  # flip majority to BUY
    return liqs


def _compute_full_features(
    candles, oi_history, funding_history, liquidations, bids, asks,
) -> Dict[str, str]:
    """Run the same computations as the real feature engine and return
    the feature dict (as string values, mimicking Redis hash)."""
    structure = compute_higher_high_lower_low(candles)
    breakout = detect_breakout(candles, settings.structure_lookback)
    atr = compute_atr(candles, settings.atr_period)
    range_exp = candle_range_expansion(candles, settings.atr_period)
    ema_sl = ema_slope(candles, settings.ema_fast)
    vwap_dist = compute_vwap_distance(candles, settings.vwap_period)
    oi_delta = compute_oi_delta(oi_history, settings.oi_delta_window)
    funding_z = compute_funding_zscore(funding_history, settings.funding_zscore_window)
    liq_ratio = compute_liquidation_ratio(liquidations, settings.liq_ratio_window)
    ob_imbalance = compute_orderbook_imbalance(bids, asks)

    return {
        "structure_state": structure["state"],
        "breakout": breakout["breakout"],
        "breakout_level": str(breakout["level"]),
        "atr": str(round(atr, 6)),
        "range_expansion": str(round(range_exp, 4)),
        "ema_slope": str(round(ema_sl, 6)),
        "vwap_distance": str(round(vwap_dist, 6)),
        "oi_delta": str(round(oi_delta, 6)),
        "funding_zscore": str(round(funding_z, 4)),
        "liq_ratio": str(round(liq_ratio["ratio"], 4)),
        "liq_total_usd": str(round(liq_ratio["total_usd"], 2)),
        "ob_imbalance": str(round(ob_imbalance, 4)),
        "ts": str(time.time()),
    }


# ── Tests ─────────────────────────────────────────────────────────

class TestEndToEnd:
    def test_uptrend_bullish_signal(self):
        """Full pipeline: uptrend candles + expanding OI + bid-heavy book → bullish signal."""
        candles = _make_uptrend_candles()
        oi = _make_oi_history(expanding=True)
        funding = _make_funding_history(extreme=False)
        liqs = _make_liquidations(bias="bullish")  # shorts getting liquidated
        bids = [["100", "50"], ["99.9", "50"], ["99.8", "50"]]
        asks = [["100.1", "5"], ["100.2", "5"], ["100.3", "5"]]

        features = _compute_full_features(candles, oi, funding, liqs, bids, asks)

        # Simulate events that would fire in this scenario
        events = [
            {"type": "oi_expansion", "detail": {"oi_delta_pct": 5.0}},
            {"type": "structure_breakout", "detail": {"direction": "bullish"}},
        ]

        result = compute_signal_score(features, events)

        assert result["direction"] == "long"
        assert result["score"] > 0.0
        assert result["components"]["trend"] > 0
        assert result["components"]["structure"] > 0

    def test_downtrend_bearish_signal(self):
        """Full pipeline: downtrend + more long liquidations → bearish signal."""
        candles = []
        base = 200.0
        for i in range(30):
            o = base - i * 0.5
            h = o + 0.3
            l = o - 1.5
            c = o - 1.0
            candles.append(_make_candle(o, h, l, c))
        candles.reverse()

        oi = _make_oi_history(expanding=True)
        funding = _make_funding_history(extreme=True)  # crowded longs
        liqs = _make_liquidations(bias="bearish")  # longs getting liquidated
        bids = [["100", "5"], ["99.9", "5"]]
        asks = [["100.1", "50"], ["100.2", "50"]]

        features = _compute_full_features(candles, oi, funding, liqs, bids, asks)

        events = [
            {"type": "liquidation_spike", "detail": {"bias": "bearish"}},
            {"type": "funding_extreme", "detail": {"bias": "bearish"}},
        ]

        result = compute_signal_score(features, events)

        assert result["direction"] == "short"
        assert result["score"] > 0.0
        assert result["votes"]["bear"] > result["votes"]["bull"]

    def test_flat_market_low_score(self):
        """Flat candles → low score, no meaningful signal."""
        candles = [_make_candle(100, 100.1, 99.9, 100)] * 30
        oi = [{"oi": 1_000_000}] * 20
        funding = [{"funding_rate": 0.001}] * 50
        liqs = []
        bids = [["100", "10"]]
        asks = [["100.1", "10"]]

        features = _compute_full_features(candles, oi, funding, liqs, bids, asks)
        result = compute_signal_score(features, [])

        assert result["score"] < settings.signal_score_threshold

    def test_feature_snapshot_consistency(self):
        """Verify that computed features are internally consistent."""
        candles = _make_uptrend_candles()
        oi = _make_oi_history(expanding=True)
        funding = _make_funding_history()
        liqs = _make_liquidations()
        bids = [["100", "10"]]
        asks = [["100.1", "10"]]

        features = _compute_full_features(candles, oi, funding, liqs, bids, asks)

        # All expected keys present
        expected_keys = {
            "structure_state", "breakout", "atr", "range_expansion",
            "ema_slope", "vwap_distance", "oi_delta", "funding_zscore",
            "liq_ratio", "liq_total_usd", "ob_imbalance", "ts",
        }
        assert expected_keys.issubset(set(features.keys()))

        # Values are parseable numbers
        for key in ["atr", "ema_slope", "vwap_distance", "oi_delta", "funding_zscore", "liq_ratio"]:
            float(features[key])  # should not raise

    @pytest.mark.asyncio
    async def test_event_queue_pipeline(self):
        """Events pushed → popped in FIFO order with correct shape."""
        events = [
            {"type": "oi_expansion", "symbol": "BTCUSDT", "ts": 1.0, "detail": {}},
            {"type": "atr_expansion", "symbol": "BTCUSDT", "ts": 2.0, "detail": {}},
            {"type": "structure_breakout", "symbol": "BTCUSDT", "ts": 3.0, "detail": {}},
        ]
        for e in events:
            await push_event(e)

        for expected in events:
            got = await asyncio.wait_for(pop_event(), timeout=1.0)
            assert got["type"] == expected["type"]
            assert got["symbol"] == expected["symbol"]

    def test_scoring_respects_threshold(self):
        """Weak features should produce a score below the threshold."""
        features = {
            "ema_slope": "0.0001",
            "vwap_distance": "0.0001",
            "liq_ratio": "1.0",
            "range_expansion": "1.0",
            "oi_delta": "0.001",
            "structure_state": "neutral",
            "breakout": "none",
        }
        result = compute_signal_score(features, [])
        assert result["score"] < settings.signal_score_threshold, (
            f"Weak features should not exceed threshold, got {result['score']}"
        )

    def test_multiple_events_boost_score(self):
        """More diverse events should increase the event_quality component."""
        features = {
            "ema_slope": "0.01",
            "vwap_distance": "0.01",
            "liq_ratio": "0.5",
            "range_expansion": "1.5",
            "oi_delta": "0.05",
            "structure_state": "uptrend",
            "breakout": "bullish",
        }

        one_event = [{"type": "oi_expansion", "detail": {}}]
        four_events = [
            {"type": "oi_expansion", "detail": {}},
            {"type": "atr_expansion", "detail": {}},
            {"type": "structure_breakout", "detail": {}},
            {"type": "liquidation_spike", "detail": {}},
        ]

        r1 = compute_signal_score(features, one_event)
        r4 = compute_signal_score(features, four_events)

        assert r4["components"]["event_quality"] >= r1["components"]["event_quality"]
