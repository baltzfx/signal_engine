"""Tests for app.core.event_queue."""

import pytest
import asyncio

from app.core.event_queue import push_event, pop_event, queue_size


@pytest.mark.asyncio
class TestEventQueue:
    async def test_push_and_pop(self):
        event = {"type": "test", "symbol": "BTCUSDT", "ts": 1.0}
        await push_event(event)
        assert queue_size() >= 1

        result = await asyncio.wait_for(pop_event(), timeout=1.0)
        assert result["type"] == "test"
        assert result["symbol"] == "BTCUSDT"

    async def test_fifo_order(self):
        for i in range(3):
            await push_event({"type": "test", "order": i})

        for i in range(3):
            result = await asyncio.wait_for(pop_event(), timeout=1.0)
            assert result["order"] == i

    async def test_queue_size(self):
        initial = queue_size()
        await push_event({"type": "size_test"})
        assert queue_size() == initial + 1
        await asyncio.wait_for(pop_event(), timeout=1.0)
        assert queue_size() == initial
