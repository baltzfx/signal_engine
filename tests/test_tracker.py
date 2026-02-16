"""Tests for app.signals.tracker — signal lifecycle management."""

import time
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.signals.tracker import (
    TrackedSignal,
    Outcome,
    has_open_signal,
    get_open_signal,
    get_all_open_signals,
    get_closed_signals,
    get_tracker_stats,
    register_signal,
    close_signal_manual,
    _open_signals,
    _closed_signals,
    _close_signal,
)


@pytest.fixture(autouse=True)
def _clear_tracker():
    """Reset tracker state between tests."""
    _open_signals.clear()
    _closed_signals.clear()
    yield
    _open_signals.clear()
    _closed_signals.clear()


def _make_signal(symbol="BTCUSDT", direction="long", score=0.75):
    return {
        "symbol": symbol,
        "direction": direction,
        "score": score,
        "trigger_events": ["oi_expansion", "atr_expansion"],
        "timestamp": time.time(),
    }


# ── TrackedSignal dataclass ──────────────────────────────────────

class TestTrackedSignal:
    def test_to_dict(self):
        sig = TrackedSignal(
            symbol="BTCUSDT", direction="long", score=0.80,
            entry_price=50000, tp_price=50200, sl_price=49900,
            atr=100, opened_at=time.time(),
        )
        d = sig.to_dict()
        assert d["symbol"] == "BTCUSDT"
        assert d["outcome"] == "open"
        assert isinstance(d["trigger_events"], list)

    def test_is_open(self):
        sig = TrackedSignal(
            symbol="ETHUSDT", direction="short", score=0.70,
            entry_price=3000, tp_price=2800, sl_price=3100,
            atr=50, opened_at=time.time(),
        )
        assert sig.is_open is True
        sig.outcome = Outcome.TP_HIT
        assert sig.is_open is False


# ── Registration ─────────────────────────────────────────────────

class TestRegisterSignal:
    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.hset = AsyncMock()
        r.expire = AsyncMock()
        with patch("app.signals.tracker.get_redis", return_value=r):
            yield r

    async def test_register_long(self, mock_redis):
        sig = _make_signal(direction="long")
        tracked = await register_signal(sig, entry_price=50000, atr=100)
        assert tracked.symbol == "BTCUSDT"
        assert tracked.direction == "long"
        assert tracked.tp_price == 50200  # 50000 + 100 * 2.0
        assert tracked.sl_price == 49900  # 50000 - 100 * 1.0
        assert tracked.is_open

    async def test_register_short(self, mock_redis):
        sig = _make_signal(direction="short")
        tracked = await register_signal(sig, entry_price=50000, atr=100)
        assert tracked.tp_price == 49800  # 50000 - 100 * 2.0
        assert tracked.sl_price == 50100  # 50000 + 100 * 1.0

    async def test_register_blocks_second_signal(self, mock_redis):
        sig = _make_signal()
        await register_signal(sig, entry_price=50000, atr=100)
        assert has_open_signal("BTCUSDT") is True

    async def test_reverse_closes_previous(self, mock_redis):
        sig_long = _make_signal(direction="long")
        await register_signal(sig_long, entry_price=50000, atr=100)
        assert has_open_signal("BTCUSDT") is True

        # Now register a short — should close the long as "reversed"
        sig_short = _make_signal(direction="short")
        await register_signal(sig_short, entry_price=49500, atr=100)

        # The short should now be open
        current = get_open_signal("BTCUSDT")
        assert current.direction == "short"

        # The long should be in closed signals
        closed = get_closed_signals()
        assert len(closed) == 1
        assert closed[0]["outcome"] == "reversed"

    async def test_custom_tp_sl_multipliers(self, mock_redis):
        sig = _make_signal()
        tracked = await register_signal(sig, entry_price=50000, atr=100, tp_mult=3.0, sl_mult=1.5)
        assert tracked.tp_price == 50300  # 50000 + 100 * 3.0
        assert tracked.sl_price == 49850  # 50000 - 100 * 1.5


# ── Open / Close helpers ─────────────────────────────────────────

class TestOpenClose:
    def test_has_open_signal_empty(self):
        assert has_open_signal("BTCUSDT") is False

    def test_has_open_signal_with_expired(self):
        sig = TrackedSignal(
            symbol="BTCUSDT", direction="long", score=0.7,
            entry_price=50000, tp_price=50200, sl_price=49900,
            atr=100, opened_at=time.time() - 99999, ttl=10,
        )
        _open_signals["BTCUSDT"] = sig
        # Should auto-expire and return False
        assert has_open_signal("BTCUSDT") is False
        # Should now be in closed signals
        assert len(_closed_signals) == 1
        assert _closed_signals[0]["outcome"] == "expired"

    def test_get_all_open_signals(self):
        for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
            _open_signals[sym] = TrackedSignal(
                symbol=sym, direction="long", score=0.7,
                entry_price=100, tp_price=102, sl_price=99,
                atr=1, opened_at=time.time(),
            )
        result = get_all_open_signals()
        assert len(result) == 3
        assert all("age_seconds" in s for s in result)

    def test_manual_close(self):
        _open_signals["BTCUSDT"] = TrackedSignal(
            symbol="BTCUSDT", direction="long", score=0.7,
            entry_price=50000, tp_price=50200, sl_price=49900,
            atr=100, opened_at=time.time(),
        )
        result = close_signal_manual("BTCUSDT", 50150)
        assert result is not None
        assert result["outcome"] == "manual"
        assert result["pnl_pct"] > 0  # profitable close
        assert has_open_signal("BTCUSDT") is False

    def test_manual_close_nonexistent(self):
        result = close_signal_manual("XYZUSDT", 100)
        assert result is None


# ── PnL calculation ──────────────────────────────────────────────

class TestPnL:
    def test_long_profit(self):
        sig = TrackedSignal(
            symbol="BTCUSDT", direction="long", score=0.7,
            entry_price=50000, tp_price=50200, sl_price=49900,
            atr=100, opened_at=time.time(),
        )
        _open_signals["BTCUSDT"] = sig
        _close_signal(sig, Outcome.TP_HIT, 50200)
        assert sig.pnl_pct == pytest.approx(0.4, abs=0.01)  # +0.4%

    def test_long_loss(self):
        sig = TrackedSignal(
            symbol="BTCUSDT", direction="long", score=0.7,
            entry_price=50000, tp_price=50200, sl_price=49900,
            atr=100, opened_at=time.time(),
        )
        _open_signals["BTCUSDT"] = sig
        _close_signal(sig, Outcome.SL_HIT, 49900)
        assert sig.pnl_pct == pytest.approx(-0.2, abs=0.01)  # -0.2%

    def test_short_profit(self):
        sig = TrackedSignal(
            symbol="BTCUSDT", direction="short", score=0.7,
            entry_price=50000, tp_price=49800, sl_price=50100,
            atr=100, opened_at=time.time(),
        )
        _open_signals["BTCUSDT"] = sig
        _close_signal(sig, Outcome.TP_HIT, 49800)
        assert sig.pnl_pct == pytest.approx(0.4, abs=0.01)  # +0.4%

    def test_short_loss(self):
        sig = TrackedSignal(
            symbol="BTCUSDT", direction="short", score=0.7,
            entry_price=50000, tp_price=49800, sl_price=50100,
            atr=100, opened_at=time.time(),
        )
        _open_signals["BTCUSDT"] = sig
        _close_signal(sig, Outcome.SL_HIT, 50100)
        assert sig.pnl_pct == pytest.approx(-0.2, abs=0.01)  # -0.2%


# ── Tracker stats ────────────────────────────────────────────────

class TestTrackerStats:
    def test_stats_empty(self):
        stats = get_tracker_stats()
        assert stats["open_count"] == 0
        assert stats["closed_total"] == 0

    def test_stats_with_data(self):
        # Add some closed signals
        for i in range(5):
            _closed_signals.append({
                "outcome": "tp_hit" if i % 2 == 0 else "sl_hit",
                "pnl_pct": 0.5 if i % 2 == 0 else -0.3,
            })

        # Add an open signal
        _open_signals["BTCUSDT"] = TrackedSignal(
            symbol="BTCUSDT", direction="long", score=0.7,
            entry_price=50000, tp_price=50200, sl_price=49900,
            atr=100, opened_at=time.time(),
        )

        stats = get_tracker_stats()
        assert stats["open_count"] == 1
        assert stats["open_symbols"] == ["BTCUSDT"]
        assert stats["recent_100"]["tp_hits"] == 3
        assert stats["recent_100"]["sl_hits"] == 2
        assert stats["recent_100"]["win_rate"] == 0.6
