"""
SQLite storage layer — persistent local database for signals, events,
and feature snapshots.

Uses aiosqlite for async non-blocking access.  All tables are created
automatically on first call to ``init_db()``.

Writes are **batched** — individual inserts go into an in-memory buffer
and are flushed to disk periodically (every ``_FLUSH_INTERVAL`` seconds)
or when the buffer reaches ``_FLUSH_SIZE`` rows.  This avoids the
one-commit-per-row bottleneck under high event throughput.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from app.core.config import settings

logger = logging.getLogger(__name__)

_db: Optional[aiosqlite.Connection] = None

DB_DIR = "data/db"
os.makedirs(DB_DIR, exist_ok=True)

# ── Write-buffer settings ─────────────────────────────────────────
_FLUSH_INTERVAL: float = 2.0   # seconds between flushes
_FLUSH_SIZE: int = 50           # flush when buffer reaches this many rows

_write_buffer: List[Tuple[str, tuple]] = []   # (sql, params) pairs
_buffer_lock: asyncio.Lock | None = None
_flush_task: Optional[asyncio.Task] = None
_flushing = False


def _get_lock() -> asyncio.Lock:
    global _buffer_lock
    if _buffer_lock is None:
        _buffer_lock = asyncio.Lock()
    return _buffer_lock


async def _buffer_write(sql: str, params: tuple) -> None:
    """Append an INSERT to the write buffer — never blocks on disk."""
    async with _get_lock():
        _write_buffer.append((sql, params))
        if len(_write_buffer) >= _FLUSH_SIZE:
            await _flush_buffer_locked()


async def _flush_buffer() -> None:
    """Flush all buffered writes to SQLite in a single transaction."""
    async with _get_lock():
        await _flush_buffer_locked()


async def _flush_buffer_locked() -> None:
    """Must be called while holding _buffer_lock."""
    if not _write_buffer or _db is None:
        return
    batch = list(_write_buffer)
    _write_buffer.clear()
    try:
        async with _db.cursor() as cur:
            for sql, params in batch:
                await cur.execute(sql, params)
        await _db.commit()
    except Exception:
        logger.warning("SQLite batch flush failed (%d rows)", len(batch), exc_info=True)


async def _flush_loop() -> None:
    """Background task that flushes the write buffer on a timer."""
    global _flushing
    _flushing = True
    while _flushing:
        try:
            await asyncio.sleep(_FLUSH_INTERVAL)
            await _flush_buffer()
        except asyncio.CancelledError:
            # Final drain on shutdown
            await _flush_buffer()
            return
        except Exception:
            logger.exception("Flush loop error")


# ── Lifecycle ─────────────────────────────────────────────────────

async def init_db() -> aiosqlite.Connection:
    """Open (or create) the SQLite database and ensure schema exists."""
    global _db, _flush_task
    if _db is not None:
        return _db

    db_path = os.path.join(DB_DIR, settings.sqlite_db_name)
    _db = await aiosqlite.connect(db_path)
    _db.row_factory = aiosqlite.Row

    # WAL mode for better concurrent read performance
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA synchronous=NORMAL")
    await _db.execute("PRAGMA busy_timeout=5000")

    await _create_tables()
    _flush_task = asyncio.create_task(_flush_loop())
    logger.info("SQLite database initialised at %s (batch flush every %.1fs / %d rows)",
                db_path, _FLUSH_INTERVAL, _FLUSH_SIZE)
    return _db


async def close_db() -> None:
    global _db, _flush_task, _flushing
    _flushing = False
    if _flush_task:
        _flush_task.cancel()
        try:
            await _flush_task
        except asyncio.CancelledError:
            pass
        _flush_task = None
    # Final flush
    await _flush_buffer()
    if _db:
        await _db.close()
        _db = None
        logger.info("SQLite database closed")


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("SQLite not initialised — call init_db() first")
    return _db


# ── Schema ────────────────────────────────────────────────────────

async def _create_tables() -> None:
    assert _db is not None
    await _db.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL,
            direction   TEXT NOT NULL,
            score       REAL NOT NULL,
            trigger_events TEXT,          -- JSON array
            features    TEXT,              -- JSON object
            ai_result   TEXT,              -- JSON object (nullable)
            entry_price REAL,              -- Entry price from tracker
            tp_price    REAL,              -- Take profit price
            sl_price    REAL,              -- Stop loss price
            atr         REAL,              -- ATR value at signal time
            timestamp   REAL NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
        CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(timestamp);

        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            type        TEXT NOT NULL,
            symbol      TEXT NOT NULL,
            detail      TEXT,              -- JSON object
            timestamp   REAL NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);

        CREATE TABLE IF NOT EXISTS feature_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL,
            features    TEXT NOT NULL,      -- JSON object
            timestamp   REAL NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_features_symbol ON feature_snapshots(symbol);
        CREATE INDEX IF NOT EXISTS idx_features_ts ON feature_snapshots(timestamp);

        -- ── NEW: Signal performance tracking ─────────────────────
        CREATE TABLE IF NOT EXISTS signal_performance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id       INTEGER,
            symbol          TEXT NOT NULL,
            direction       TEXT NOT NULL,
            timeframe       TEXT DEFAULT '5m',
            entry_price     REAL NOT NULL,
            exit_price      REAL,
            entry_time      REAL NOT NULL,
            exit_time       REAL,
            outcome         TEXT,           -- tp_hit, sl_hit, expired, manual
            return_pct      REAL,           -- percentage return
            duration_sec    REAL,           -- signal duration
            score           REAL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        );

        CREATE INDEX IF NOT EXISTS idx_perf_symbol ON signal_performance(symbol);
        CREATE INDEX IF NOT EXISTS idx_perf_outcome ON signal_performance(outcome);
        CREATE INDEX IF NOT EXISTS idx_perf_timeframe ON signal_performance(timeframe);
        CREATE INDEX IF NOT EXISTS idx_perf_entry_time ON signal_performance(entry_time);

        -- ── NEW: Feature importance tracking ─────────────────────
        CREATE TABLE IF NOT EXISTS feature_importance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            model_type      TEXT NOT NULL,
            feature_name    TEXT NOT NULL,
            importance      REAL NOT NULL,
            timestamp       REAL NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_importance_model ON feature_importance(model_type);
        CREATE INDEX IF NOT EXISTS idx_importance_ts ON feature_importance(timestamp);
    """)
    await _db.commit()


# ── Insert helpers (buffered) ─────────────────────────────────────

_SIGNAL_SQL = """
INSERT INTO signals (symbol, direction, score, trigger_events, features, ai_result, entry_price, tp_price, sl_price, atr, timestamp)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_EVENT_SQL = """
INSERT INTO events (type, symbol, detail, timestamp)
VALUES (?, ?, ?, ?)
"""

_SNAPSHOT_SQL = """
INSERT INTO feature_snapshots (symbol, features, timestamp)
VALUES (?, ?, ?)
"""


async def insert_signal(signal: Dict[str, Any]) -> int:
    """Buffer a signal record for batched write. Returns 0 (row id not available until flush)."""
    await _buffer_write(
        _SIGNAL_SQL,
        (
            signal.get("symbol", ""),
            signal.get("direction", ""),
            signal.get("score", 0),
            json.dumps(signal.get("trigger_events", [])),
            json.dumps(signal.get("features_snapshot", {})),
            json.dumps(signal.get("ai")) if signal.get("ai") else None,
            signal.get("entry_price"),
            signal.get("tp_price"),
            signal.get("sl_price"),
            signal.get("atr"),
            signal.get("timestamp", 0),
        ),
    )
    return 0


async def insert_event(event: Dict[str, Any]) -> int:
    """Buffer an event record for batched write."""
    await _buffer_write(
        _EVENT_SQL,
        (
            event.get("type", ""),
            event.get("symbol", ""),
            json.dumps(event.get("detail", {})),
            event.get("ts", 0),
        ),
    )
    return 0


async def insert_feature_snapshot(symbol: str, features: Dict[str, Any], ts: float) -> None:
    """Buffer a point-in-time feature snapshot."""
    await _buffer_write(
        _SNAPSHOT_SQL,
        (symbol, json.dumps(features), ts),
    )


# ── Query helpers ─────────────────────────────────────────────────

async def get_signals(
    symbol: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Fetch recent signals with performance status, optionally filtered by symbol."""
    db = get_db()
    
    # LEFT JOIN with signal_performance to get outcome status
    query = """
        SELECT 
            s.*,
            sp.outcome,
            sp.exit_price,
            sp.exit_time,
            sp.return_pct,
            sp.duration_sec
        FROM signals s
        LEFT JOIN signal_performance sp ON s.id = sp.signal_id
    """
    
    if symbol:
        query += " WHERE s.symbol = ?"
        params = [symbol]
    else:
        params = []
    
    query += " ORDER BY s.timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_events(
    symbol: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Fetch recent events with optional filters."""
    db = get_db()
    query = "SELECT * FROM events WHERE 1=1"
    params: list = []
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    if event_type:
        query += " AND type = ?"
        params.append(event_type)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_signal_stats() -> Dict[str, Any]:
    """Aggregate signal statistics."""
    db = get_db()

    total = await (await db.execute("SELECT COUNT(*) FROM signals")).fetchone()
    longs = await (await db.execute("SELECT COUNT(*) FROM signals WHERE direction='long'")).fetchone()
    shorts = await (await db.execute("SELECT COUNT(*) FROM signals WHERE direction='short'")).fetchone()
    avg_score = await (await db.execute("SELECT AVG(score) FROM signals")).fetchone()
    by_symbol = await (
        await db.execute(
            "SELECT symbol, COUNT(*) as cnt FROM signals GROUP BY symbol ORDER BY cnt DESC LIMIT 20"
        )
    ).fetchall()

    return {
        "total_signals": total[0] if total else 0,
        "long_signals": longs[0] if longs else 0,
        "short_signals": shorts[0] if shorts else 0,
        "avg_score": round(avg_score[0], 4) if avg_score and avg_score[0] else 0,
        "top_symbols": {r[0]: r[1] for r in by_symbol},
    }


async def get_event_stats() -> Dict[str, Any]:
    """Aggregate event statistics."""
    db = get_db()
    total = await (await db.execute("SELECT COUNT(*) FROM events")).fetchone()
    by_type = await (
        await db.execute("SELECT type, COUNT(*) as cnt FROM events GROUP BY type ORDER BY cnt DESC")
    ).fetchall()

    return {
        "total_events": total[0] if total else 0,
        "by_type": {r[0]: r[1] for r in by_type},
    }


def _row_to_dict(row: aiosqlite.Row) -> Dict[str, Any]:
    d = dict(row)
    # Parse JSON fields
    for field in ("trigger_events", "features", "ai_result", "detail"):
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


# ── NEW: Signal Performance Tracking ──────────────────────────────

_PERF_SQL = """
INSERT INTO signal_performance (
    signal_id, symbol, direction, timeframe, entry_price, exit_price,
    entry_time, exit_time, outcome, return_pct, duration_sec, score
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


async def record_signal_performance(
    signal_id: Optional[int],
    symbol: str,
    direction: str,
    entry_price: float,
    exit_price: Optional[float],
    entry_time: float,
    exit_time: Optional[float],
    outcome: str,
    timeframe: str = "5m",
    score: Optional[float] = None,
) -> None:
    """Record the outcome of a closed signal."""
    return_pct = None
    duration_sec = None

    if exit_price and entry_price:
        ret = (exit_price - entry_price) / entry_price
        if direction == "short":
            ret = -ret
        return_pct = ret * 100  # as percentage

    if exit_time and entry_time:
        duration_sec = exit_time - entry_time

    await _buffer_write(
        _PERF_SQL,
        (
            signal_id,
            symbol,
            direction,
            timeframe,
            entry_price,
            exit_price,
            entry_time,
            exit_time,
            outcome,
            return_pct,
            duration_sec,
            score,
        ),
    )


async def get_performance_stats(
    symbol: Optional[str] = None,
    timeframe: str = "5m",
    lookback_days: int = 30,
) -> Dict[str, Any]:
    """Get aggregated performance statistics."""
    db = get_db()
    lookback_ts = time.time() - (lookback_days * 86400)

    where = "WHERE entry_time >= ?"
    params = [lookback_ts]

    if symbol:
        where += " AND symbol = ?"
        params.append(symbol)

    if timeframe:
        where += " AND timeframe = ?"
        params.append(timeframe)

    query = f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'tp_hit' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'sl_hit' THEN 1 ELSE 0 END) as losses,
            AVG(return_pct) as avg_return,
            AVG(duration_sec) as avg_duration,
            symbol
        FROM signal_performance
        {where}
        GROUP BY symbol
        ORDER BY total DESC
    """

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    results = []
    for row in rows:
        total = row[0] or 0
        wins = row[1] or 0
        losses = row[2] or 0
        avg_ret = row[3] or 0
        avg_dur = row[4] or 0
        sym = row[5]

        win_rate = wins / total if total > 0 else 0

        results.append({
            "symbol": sym,
            "total_signals": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 4),
            "avg_return_pct": round(avg_ret, 4),
            "avg_duration_sec": round(avg_dur, 2),
        })

    return {"stats": results, "timeframe": timeframe, "lookback_days": lookback_days}


# ── NEW: Feature Importance Tracking ──────────────────────────────

_IMPORTANCE_SQL = """
INSERT INTO feature_importance (model_type, feature_name, importance, timestamp)
VALUES (?, ?, ?, ?)
"""


async def record_feature_importance(
    model_type: str,
    importances: Dict[str, float],
    timestamp: Optional[float] = None,
) -> None:
    """Record feature importance scores from a model."""
    if timestamp is None:
        timestamp = time.time()

    for feature_name, importance in importances.items():
        await _buffer_write(_IMPORTANCE_SQL, (model_type, feature_name, importance, timestamp))


async def get_latest_feature_importance(model_type: str) -> Dict[str, float]:
    """Get the most recent feature importance for a model."""
    db = get_db()
    query = """
        SELECT feature_name, importance
        FROM feature_importance
        WHERE model_type = ?
        AND timestamp = (
            SELECT MAX(timestamp)
            FROM feature_importance
            WHERE model_type = ?
        )
    """
    cursor = await db.execute(query, (model_type, model_type))
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}

