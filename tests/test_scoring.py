"""Tests for app.signals.scoring."""

from app.signals.scoring import compute_signal_score, WEIGHTS


class TestScoring:
    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_strong_bullish_score(self):
        features = {
            "ema_slope": "0.015",
            "vwap_distance": "0.025",
            "liq_ratio": "0.4",         # shorts liquidated → bullish
            "range_expansion": "2.5",
            "oi_delta": "0.08",
            "structure_state": "uptrend",
            "breakout": "bullish",
        }
        events = [
            {"type": "atr_expansion", "detail": {"bias": "bullish"}},
            {"type": "oi_expansion", "detail": {"bias": "bullish"}},
            {"type": "structure_breakout", "detail": {"direction": "bullish"}},
        ]
        result = compute_signal_score(features, events)
        assert result["direction"] == "long"
        assert result["score"] >= 0.60

    def test_strong_bearish_score(self):
        features = {
            "ema_slope": "-0.015",
            "vwap_distance": "-0.025",
            "liq_ratio": "2.0",          # longs liquidated → bearish
            "range_expansion": "2.5",
            "oi_delta": "0.08",
            "structure_state": "downtrend",
            "breakout": "bearish",
        }
        events = [
            {"type": "atr_expansion", "detail": {"bias": "bearish"}},
            {"type": "oi_expansion", "detail": {"bias": "bearish"}},
        ]
        result = compute_signal_score(features, events)
        assert result["direction"] == "short"
        assert result["score"] >= 0.50

    def test_neutral_low_score(self):
        features = {
            "ema_slope": "0",
            "vwap_distance": "0",
            "liq_ratio": "1",
            "range_expansion": "1",
            "oi_delta": "0",
            "structure_state": "neutral",
            "breakout": "none",
        }
        result = compute_signal_score(features, [])
        assert result["score"] < 0.30
        assert "components" in result
        assert "votes" in result

    def test_score_bounded(self):
        """Score should always be in [0, 1]."""
        features = {
            "ema_slope": "0.1",
            "vwap_distance": "0.5",
            "liq_ratio": "10",
            "range_expansion": "10",
            "oi_delta": "1.0",
            "structure_state": "uptrend",
            "breakout": "bullish",
        }
        events = [{"type": f"evt_{i}", "detail": {}} for i in range(10)]
        result = compute_signal_score(features, events)
        assert 0 <= result["score"] <= 1.0

    def test_components_present(self):
        features = {"ema_slope": "0.01"}
        result = compute_signal_score(features, [])
        for key in WEIGHTS:
            assert key in result["components"]
