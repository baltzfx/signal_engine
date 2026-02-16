"""Tests for app.collectors.validation."""

from app.collectors.validation import (
    validate_kline,
    validate_depth,
    validate_mark_price,
    validate_force_order,
    validate_open_interest,
    validate_funding,
)


class TestValidateKline:
    def test_valid_kline(self):
        msg = {"data": {"k": {
            "s": "BTCUSDT", "t": 1000, "o": "100", "h": "110",
            "l": "90", "c": "105", "v": "500", "q": "50000", "x": True,
        }}}
        result = validate_kline(msg)
        assert result is not None
        assert result["s"] == "BTCUSDT"

    def test_missing_k_field(self):
        assert validate_kline({"data": {}}) is None

    def test_missing_required_field(self):
        msg = {"data": {"k": {"s": "BTCUSDT", "t": 1000}}}  # missing ohlcv
        assert validate_kline(msg) is None

    def test_invalid_price(self):
        msg = {"data": {"k": {
            "s": "BTCUSDT", "t": 1000, "o": "bad", "h": "110",
            "l": "90", "c": "105", "v": "500", "q": "50000", "x": True,
        }}}
        assert validate_kline(msg) is None

    def test_unwrapped_message(self):
        """Some streams send data without the 'data' wrapper."""
        msg = {"k": {
            "s": "ETHUSDT", "t": 1000, "o": "10", "h": "11",
            "l": "9", "c": "10.5", "v": "100", "q": "1000", "x": False,
        }}
        result = validate_kline(msg)
        assert result is not None


class TestValidateDepth:
    def test_valid_depth(self):
        msg = {
            "stream": "btcusdt@depth10@100ms",
            "data": {"bids": [["100", "1"]], "asks": [["101", "1"]]},
        }
        result = validate_depth(msg)
        assert result is not None
        assert result["symbol"] == "BTCUSDT"

    def test_no_stream_name(self):
        assert validate_depth({"data": {"bids": [], "asks": []}}) is None

    def test_missing_bids(self):
        msg = {"stream": "btcusdt@depth10", "data": {"asks": []}}
        assert validate_depth(msg) is None


class TestValidateMarkPrice:
    def test_valid(self):
        msg = {"data": {"s": "BTCUSDT", "p": "50000", "i": "50010", "r": "0.001"}}
        result = validate_mark_price(msg)
        assert result["s"] == "BTCUSDT"

    def test_missing_symbol(self):
        msg = {"data": {"p": "50000", "i": "50010", "r": "0.001"}}
        assert validate_mark_price(msg) is None

    def test_invalid_price(self):
        msg = {"data": {"s": "BTCUSDT", "p": "NaN", "i": "50010", "r": "0.001"}}
        # NaN is parseable by float, so this should pass
        result = validate_mark_price(msg)
        assert result is not None

    def test_missing_field(self):
        msg = {"data": {"s": "BTCUSDT", "p": "50000"}}  # missing i, r
        assert validate_mark_price(msg) is None


class TestValidateForceOrder:
    def test_valid(self):
        msg = {"data": {"o": {
            "s": "BTCUSDT", "S": "SELL", "p": "50000", "q": "0.5",
        }}}
        result = validate_force_order(msg)
        assert result["s"] == "BTCUSDT"

    def test_invalid_side(self):
        msg = {"data": {"o": {
            "s": "BTCUSDT", "S": "INVALID", "p": "50000", "q": "0.5",
        }}}
        assert validate_force_order(msg) is None

    def test_no_symbol(self):
        msg = {"data": {"o": {"S": "SELL", "p": "50000", "q": "0.5"}}}
        assert validate_force_order(msg) is None


class TestValidateREST:
    def test_valid_oi(self):
        assert validate_open_interest({"openInterest": "12345.678"}) is True

    def test_missing_oi(self):
        assert validate_open_interest({}) is False

    def test_invalid_oi(self):
        assert validate_open_interest({"openInterest": "bad"}) is False

    def test_valid_funding(self):
        data = {"lastFundingRate": "0.001", "markPrice": "50000", "indexPrice": "50010"}
        assert validate_funding(data) is True

    def test_missing_funding_field(self):
        assert validate_funding({"lastFundingRate": "0.001"}) is False
