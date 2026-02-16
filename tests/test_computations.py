"""Tests for app.features.computations."""

import pytest
from app.features.computations import (
    compute_higher_high_lower_low,
    detect_breakout,
    compute_atr,
    candle_range_expansion,
    compute_ema,
    ema_slope,
    compute_vwap_distance,
    compute_oi_delta,
    compute_funding_zscore,
    compute_liquidation_ratio,
    compute_orderbook_imbalance,
    detect_wall_pressure,
)


# ── Market Structure ──────────────────────────────────────────────

class TestMarketStructure:
    def test_uptrend_detection(self, uptrend_candles):
        result = compute_higher_high_lower_low(uptrend_candles)
        assert result["state"] == "uptrend"
        assert result["hh"] is True

    def test_downtrend_detection(self, downtrend_candles):
        result = compute_higher_high_lower_low(downtrend_candles)
        assert result["state"] == "downtrend"
        assert result["ll"] is True

    def test_insufficient_candles(self):
        result = compute_higher_high_lower_low([{"h": "1", "l": "0"}])
        assert result["state"] == "neutral"

    def test_breakout_bullish(self, uptrend_candles):
        result = detect_breakout(uptrend_candles, lookback=20)
        assert result["breakout"] == "bullish"
        assert result["level"] > 0

    def test_breakout_bearish(self, downtrend_candles):
        result = detect_breakout(downtrend_candles, lookback=20)
        assert result["breakout"] == "bearish"

    def test_breakout_insufficient_data(self):
        result = detect_breakout([{"h": "1", "l": "0", "c": "0.5"}] * 5, lookback=20)
        assert result["breakout"] == "none"


# ── Volatility ────────────────────────────────────────────────────

class TestVolatility:
    def test_atr_positive(self, uptrend_candles):
        atr = compute_atr(uptrend_candles, period=14)
        assert atr > 0

    def test_atr_insufficient_data(self):
        assert compute_atr([], period=14) == 0.0

    def test_range_expansion_flat(self, flat_candles):
        exp = candle_range_expansion(flat_candles, period=14)
        assert 0.9 <= exp <= 1.1  # flat candles, ratio near 1

    def test_range_expansion_insufficient(self):
        assert candle_range_expansion([], period=14) == 1.0


# ── Trend ─────────────────────────────────────────────────────────

class TestTrend:
    def test_ema_basic(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = compute_ema(values, period=3)
        assert len(result) == 5
        assert result[-1] > result[0]  # upward trend

    def test_ema_empty(self):
        assert compute_ema([], period=5) == []

    def test_ema_slope_positive(self, uptrend_candles):
        slope = ema_slope(uptrend_candles, period=9, lookback=3)
        assert slope > 0

    def test_ema_slope_negative(self, downtrend_candles):
        slope = ema_slope(downtrend_candles, period=9, lookback=3)
        assert slope < 0

    def test_vwap_distance_uptrend(self, uptrend_candles):
        dist = compute_vwap_distance(uptrend_candles, period=20)
        assert dist > 0  # price above VWAP

    def test_vwap_distance_downtrend(self, downtrend_candles):
        dist = compute_vwap_distance(downtrend_candles, period=20)
        assert dist < 0  # price below VWAP


# ── Derivatives ───────────────────────────────────────────────────

class TestDerivatives:
    def test_oi_delta_expanding(self):
        history = [{"oi": 110}, {"oi": 108}, {"oi": 105}, {"oi": 100}]
        delta = compute_oi_delta(history, window=3)
        assert delta > 0  # OI grew

    def test_oi_delta_contracting(self):
        history = [{"oi": 90}, {"oi": 95}, {"oi": 100}]
        delta = compute_oi_delta(history, window=2)
        assert delta < 0

    def test_oi_delta_empty(self):
        assert compute_oi_delta([], window=10) == 0.0

    def test_funding_zscore_extreme(self):
        # One very high rate among many normals
        history = [{"funding_rate": 0.05}] + [{"funding_rate": 0.001}] * 49
        z = compute_funding_zscore(history, window=50)
        assert z > 2.0  # significantly above mean

    def test_funding_zscore_normal(self):
        history = [{"funding_rate": 0.001}] * 50
        z = compute_funding_zscore(history, window=50)
        assert abs(z) < 0.1  # near zero

    def test_liq_ratio_bearish(self):
        liqs = [{"side": "SELL", "qty": 1, "price": 100}] * 10 + \
               [{"side": "BUY", "qty": 1, "price": 100}] * 2
        result = compute_liquidation_ratio(liqs, window=12)
        assert result["ratio"] > 1.0  # more longs liquidated
        assert result["long_liqs"] == 10
        assert result["short_liqs"] == 2

    def test_liq_ratio_empty(self):
        result = compute_liquidation_ratio([], window=20)
        assert result["ratio"] == 0.0
        assert result["total_usd"] == 0.0


# ── Orderflow ─────────────────────────────────────────────────────

class TestOrderflow:
    def test_imbalance_balanced(self, balanced_book):
        bids, asks = balanced_book
        imb = compute_orderbook_imbalance(bids, asks)
        assert abs(imb) < 0.01

    def test_imbalance_bid_heavy(self, bid_heavy_book):
        bids, asks = bid_heavy_book
        imb = compute_orderbook_imbalance(bids, asks)
        assert imb > 0.5

    def test_imbalance_empty(self):
        assert compute_orderbook_imbalance([], []) == 0.0

    def test_wall_detection(self):
        bids = [["100.0", "100"], ["99.9", "5"], ["99.8", "5"]]
        asks = [["100.1", "5"], ["100.2", "5"], ["100.3", "5"]]
        result = detect_wall_pressure(bids, asks, threshold_multiplier=3.0)
        assert result["bid_wall"] is True
        assert result["bid_wall_price"] == 100.0

    def test_no_wall(self, balanced_book):
        bids, asks = balanced_book
        result = detect_wall_pressure(bids, asks)
        assert result["bid_wall"] is False
        assert result["ask_wall"] is False
