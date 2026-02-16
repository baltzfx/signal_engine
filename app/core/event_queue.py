"""
Central async event queue shared across all engine components.

Events are lightweight dicts pushed by the event engine and consumed
by the signal engine.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# The single shared queue instance
_queue: Optional[asyncio.Queue] = None


def get_event_queue() -> asyncio.Queue:
    """Return (or lazily create) the global event queue."""
    global _queue
    if _queue is None:
        _queue = asyncio.Queue(maxsize=settings.event_queue_maxsize)
        logger.info("Event queue initialised (maxsize=%d)", settings.event_queue_maxsize)
    return _queue


async def push_event(event: Dict[str, Any]) -> None:
    """
    Push an event dict into the queue (non-blocking).
    Drops the event if queue is full and logs a warning.
    """
    q = get_event_queue()
    try:
        q.put_nowait(event)
        logger.debug("Event pushed: %s %s", event.get("type"), event.get("symbol"))
    except asyncio.QueueFull:
        logger.warning(
            "Event queue full — dropping event %s for %s",
            event.get("type"),
            event.get("symbol"),
        )


async def pop_event() -> Dict[str, Any]:
    """Block until an event is available and return it."""
    q = get_event_queue()
    return await q.get()


def queue_size() -> int:
    q = get_event_queue()
    return q.qsize()
