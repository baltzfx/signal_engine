"""Tests for app.storage.database (SQLite layer)."""

import pytest
import time

from app.storage.database import (
    insert_signal,
    insert_event,
    insert_feature_snapshot,
    get_signals,
    get_events,
    get_signal_stats,
    get_event_stats,
    _flush_buffer,
)


@pytest.mark.asyncio
class TestDatabase:
    async def test_insert_and_get_signal(self, tmp_db):
        sig = {
            "symbol": "BTCUSDT",
            "direction": "long",
            "score": 0.78,
            "trigger_events": [{"type": "atr_expansion"}],
            "features_snapshot": {"ema_slope": 0.01},
            "timestamp": time.time(),
        }
        await insert_signal(sig)
        await _flush_buffer()

        signals = await get_signals(symbol="BTCUSDT", limit=10)
        assert len(signals) == 1
        assert signals[0]["direction"] == "long"
        assert signals[0]["score"] == 0.78

    async def test_insert_and_get_event(self, tmp_db):
        evt = {
            "type": "liquidation_spike",
            "symbol": "ETHUSDT",
            "detail": {"side": "long", "usd": 500_000},
            "ts": time.time(),
        }
        await insert_event(evt)
        await _flush_buffer()

        events = await get_events(symbol="ETHUSDT")
        assert len(events) == 1
        assert events[0]["type"] == "liquidation_spike"
        assert events[0]["detail"]["usd"] == 500_000

    async def test_insert_feature_snapshot(self, tmp_db):
        await insert_feature_snapshot(
            "SOLUSDT",
            {"ema_slope": 0.005, "atr": 1.2},
            time.time(),
        )
        await _flush_buffer()
        # Just verify no exception was raised (no public query helper for snapshots)

    async def test_signal_stats(self, tmp_db):
        ts = time.time()
        for i in range(5):
            await insert_signal({
                "symbol": "BTCUSDT",
                "direction": "long" if i < 3 else "short",
                "score": 0.7 + i * 0.01,
                "trigger_events": [],
                "features_snapshot": {},
                "timestamp": ts + i,
            })
        await _flush_buffer()

        stats = await get_signal_stats()
        assert stats["total_signals"] == 5
        assert stats["long_signals"] == 3
        assert stats["short_signals"] == 2
        assert stats["avg_score"] > 0

    async def test_event_stats(self, tmp_db):
        ts = time.time()
        for etype in ["liq_spike", "liq_spike", "oi_expansion"]:
            await insert_event({
                "type": etype,
                "symbol": "BTCUSDT",
                "detail": {},
                "ts": ts,
            })
        await _flush_buffer()

        stats = await get_event_stats()
        assert stats["total_events"] == 3
        assert stats["by_type"]["liq_spike"] == 2
        assert stats["by_type"]["oi_expansion"] == 1

    async def test_get_signals_with_filter(self, tmp_db):
        ts = time.time()
        for sym in ["BTCUSDT", "ETHUSDT", "BTCUSDT"]:
            await insert_signal({
                "symbol": sym, "direction": "long", "score": 0.7,
                "trigger_events": [], "features_snapshot": {},
                "timestamp": ts,
            })
        await _flush_buffer()

        all_sigs = await get_signals()
        assert len(all_sigs) == 3

        btc_sigs = await get_signals(symbol="BTCUSDT")
        assert len(btc_sigs) == 2

    async def test_get_events_with_type_filter(self, tmp_db):
        ts = time.time()
        await insert_event({"type": "atr_expansion", "symbol": "X", "detail": {}, "ts": ts})
        await insert_event({"type": "liq_spike", "symbol": "X", "detail": {}, "ts": ts})
        await _flush_buffer()

        filtered = await get_events(event_type="atr_expansion")
        assert len(filtered) == 1
        assert filtered[0]["type"] == "atr_expansion"

    async def test_batch_flush_at_threshold(self, tmp_db):
        """Verify that buffer auto-flushes when it reaches _FLUSH_SIZE."""
        from app.storage import database as db_mod
        old_size = db_mod._FLUSH_SIZE
        db_mod._FLUSH_SIZE = 3  # lower threshold for test
        try:
            ts = time.time()
            for i in range(4):
                await insert_event({"type": "batch_test", "symbol": "X", "detail": {}, "ts": ts + i})
            # First 3 should have auto-flushed, 4th still in buffer
            events = await get_events(event_type="batch_test")
            assert len(events) >= 3
        finally:
            db_mod._FLUSH_SIZE = old_size
            await _flush_buffer()
