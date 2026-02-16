"""
Base WebSocket collector with auto-reconnect, multiplexed streams,
and graceful shutdown support.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseCollector:
    """
    Connects to a Binance combined-stream WebSocket URL, reads messages,
    and dispatches them to a handler coroutine.

    Supports:
    - multiplexed streams (up to ws_max_streams_per_conn per connection)
    - automatic reconnect with exponential back-off
    - graceful cancellation
    """

    def __init__(
        self,
        streams: List[str],
        handler: Callable[[Dict[str, Any]], Coroutine],
        name: str = "collector",
    ) -> None:
        self.streams = streams
        self.handler = handler
        self.name = name
        self._tasks: List[asyncio.Task] = []
        self._running = False

    # ── Public API ────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True
        # Chunk streams to respect Binance per-connection limit
        chunk_size = settings.ws_max_streams_per_conn
        for i in range(0, len(self.streams), chunk_size):
            chunk = self.streams[i : i + chunk_size]
            task = asyncio.create_task(self._run_connection(chunk))
            self._tasks.append(task)
        logger.info(
            "[%s] started %d connection(s) for %d streams",
            self.name,
            len(self._tasks),
            len(self.streams),
        )

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("[%s] stopped", self.name)

    # ── Internal ──────────────────────────────────────────────────

    async def _run_connection(self, streams: List[str]) -> None:
        """Maintain a single WebSocket connection with reconnect logic."""
        url = self._build_url(streams)
        backoff = settings.ws_reconnect_delay

        while self._running:
            try:
                async with websockets.connect(
                    url,
                    ping_interval=settings.ws_ping_interval,
                    ping_timeout=10,
                    close_timeout=5,
                    max_size=2**22,  # 4 MB
                ) as ws:
                    backoff = settings.ws_reconnect_delay  # reset on success
                    logger.info("[%s] connected (%d streams)", self.name, len(streams))
                    async for raw_msg in ws:
                        if not self._running:
                            break
                        try:
                            msg = json.loads(raw_msg)
                            await self.handler(msg)
                        except json.JSONDecodeError:
                            logger.warning("[%s] bad JSON payload", self.name)
                        except Exception:
                            logger.exception("[%s] handler error", self.name)

            except (ConnectionClosed, ConnectionError, OSError) as exc:
                logger.warning(
                    "[%s] connection lost (%s) — reconnecting in %.1fs",
                    self.name,
                    exc,
                    backoff,
                )
            except asyncio.CancelledError:
                logger.info("[%s] task cancelled", self.name)
                return
            except Exception:
                logger.exception("[%s] unexpected error", self.name)

            if self._running:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 30)  # exponential up to 30 s

    @staticmethod
    def _build_url(streams: List[str]) -> str:
        combined = "/".join(streams)
        return f"{settings.binance_futures_ws}/stream?streams={combined}"
