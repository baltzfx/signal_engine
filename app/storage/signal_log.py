"""
Persistent signal logging — appends every emitted signal to:
  1. Daily JSONL file
  2. Redis list (recent 500)
  3. SQLite signals table
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

import aiofiles

from app.core.redis_pool import get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)

SIGNAL_LOG_DIR = "data/signals"
os.makedirs(SIGNAL_LOG_DIR, exist_ok=True)


async def log_signal(signal: Dict[str, Any]) -> None:
    """Append signal to JSONL, Redis, and SQLite."""
    # Only persist high-quality signals to database
    score = signal.get("score", 0)
    if score < settings.signal_score_threshold:
        logger.debug(
            "Skipping database save for low-score signal: %s score=%.2f (threshold=%.2f)",
            signal.get("symbol"), score, settings.signal_score_threshold
        )
        # Still log to JSONL and Redis for debugging, but skip SQLite
        pass
    # 1. File log
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(SIGNAL_LOG_DIR, f"signals_{today}.jsonl")
    try:
        async with aiofiles.open(path, mode="a") as f:
            await f.write(json.dumps(signal) + "\n")
    except Exception:
        logger.warning("Failed to write signal to %s", path, exc_info=True)

    # 2. Redis list (keep last 500 signals)
    try:
        r = get_redis()
        await r.lpush("signals:log", json.dumps(signal))
        await r.ltrim("signals:log", 0, 499)
    except Exception:
        logger.warning("Failed to push signal to Redis log", exc_info=True)

    # 3. SQLite (only for high-quality signals)
    if score >= settings.signal_score_threshold:
        try:
            from app.storage.database import insert_signal
            await insert_signal(signal)
        except Exception:
            logger.warning("Failed to insert signal into SQLite", exc_info=True)
