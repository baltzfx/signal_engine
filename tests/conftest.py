"""
Shared fixtures for the SignalEngine test suite.
"""

from __future__ import annotations

import os
import sys
import asyncio
from typing import List, Dict, Any

import pytest

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ── Candle fixture ────────────────────────────────────────────────

def _make_candle(
    o: float, h: float, l: float, c: float, v: float = 100.0
) -> Dict[str, Any]:
    return {"o": str(o), "h": str(h), "l": str(l), "c": str(c), "v": str(v)}


@pytest.fixture
def uptrend_candles() -> List[Dict[str, Any]]:
    """25 candles with a clear uptrend (higher highs / higher lows)."""
    candles = []
    base = 100.0
    for i in range(25):
        o = base + i * 0.5
        h = o + 1.5
        l = o - 0.3
        c = o + 2.0  # close exceeds previous candle's high for clear breakout
        candles.append(_make_candle(o, h, l, c))
    candles.reverse()  # newest first
    return candles


@pytest.fixture
def downtrend_candles() -> List[Dict[str, Any]]:
    """25 candles with a clear downtrend (lower highs / lower lows)."""
    candles = []
    base = 200.0
    for i in range(25):
        o = base - i * 0.5
        h = o + 0.3
        l = o - 1.5
        c = o - 2.0  # close below previous candle's low for clear breakout
        candles.append(_make_candle(o, h, l, c))
    candles.reverse()
    return candles


@pytest.fixture
def flat_candles() -> List[Dict[str, Any]]:
    """25 flat candles hovering around 100."""
    candles = []
    for _ in range(25):
        candles.append(_make_candle(100.0, 100.1, 99.9, 100.0))
    return candles


# ── Orderbook fixture ────────────────────────────────────────────

@pytest.fixture
def balanced_book():
    bids = [["100.0", "10"], ["99.9", "10"], ["99.8", "10"]]
    asks = [["100.1", "10"], ["100.2", "10"], ["100.3", "10"]]
    return bids, asks


@pytest.fixture
def bid_heavy_book():
    bids = [["100.0", "50"], ["99.9", "50"], ["99.8", "50"]]
    asks = [["100.1", "5"], ["100.2", "5"], ["100.3", "5"]]
    return bids, asks


# ── SQLite fixture ────────────────────────────────────────────────

@pytest.fixture
async def tmp_db(tmp_path):
    """Create a temporary SQLite database for testing."""
    import aiosqlite
    from app.storage import database as db_mod

    db_path = str(tmp_path / "test.db")
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")

    # Inject temp connection and ensure lock exists
    db_mod._db = conn
    db_mod._buffer_lock = asyncio.Lock()
    db_mod._write_buffer.clear()
    await db_mod._create_tables()
    yield conn
    # Flush remaining buffer before closing
    await db_mod._flush_buffer()
    await conn.close()
    db_mod._db = None
