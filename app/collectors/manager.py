"""
Collector manager — wires up all stream collectors and REST pollers,
launches them as background tasks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

from app.core.config import settings
from app.collectors.base import BaseCollector
from app.collectors.handlers import (
    handle_kline,
    handle_depth,
    handle_mark_price,
    handle_force_order,
    poll_open_interest,
    poll_funding_rate,
)

logger = logging.getLogger(__name__)

_collectors: List[BaseCollector] = []
_rest_tasks: List[asyncio.Task] = []


def _build_streams(symbols: List[str], suffix: str) -> List[str]:
    """Generate stream names: btcusdt@kline_5m, ethusdt@kline_5m, ..."""
    return [f"{s.lower()}@{suffix}" for s in symbols]


async def start_collectors() -> None:
    global _collectors, _rest_tasks
    symbols = settings.symbols

    # ── WebSocket collectors ──────────────────────────────────────
    # Multi-timeframe kline collectors
    for tf in settings.timeframes:
        tf_suffix = f"kline_{tf}"
        kline_collector = BaseCollector(
            streams=_build_streams(symbols, tf_suffix),
            handler=handle_kline,
            name=tf_suffix,
        )
        _collectors.append(kline_collector)
        logger.info(f"Added kline collector for timeframe: {tf}")

    depth_collector = BaseCollector(
        streams=_build_streams(symbols, "depth10@100ms"),
        handler=handle_depth,
        name="depth10",
    )
    mark_collector = BaseCollector(
        streams=_build_streams(symbols, "markPrice@1s"),
        handler=handle_mark_price,
        name="markPrice",
    )

    # Force order — Binance supports an "all market" stream
    force_collector = BaseCollector(
        streams=["!forceOrder@arr"],
        handler=handle_force_order,
        name="forceOrder",
    )

    _collectors.extend([depth_collector, mark_collector, force_collector])

    for c in _collectors:
        await c.start()

    # ── REST pollers (OI + Funding) ──────────────────────────────
    _rest_tasks.append(asyncio.create_task(_oi_loop(symbols)))
    _rest_tasks.append(asyncio.create_task(_funding_loop(symbols)))

    logger.info("All collectors started for %d symbols across %d timeframes", len(symbols), len(settings.timeframes))


async def stop_collectors() -> None:
    for c in _collectors:
        await c.stop()
    for t in _rest_tasks:
        t.cancel()
    await asyncio.gather(*_rest_tasks, return_exceptions=True)
    _rest_tasks.clear()
    _collectors.clear()
    logger.info("All collectors stopped")


# ── REST polling loops ────────────────────────────────────────────

async def _oi_loop(symbols: List[str]) -> None:
    """Periodically poll open interest via REST."""
    while True:
        try:
            await poll_open_interest(symbols)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("OI polling loop error")
        await asyncio.sleep(settings.funding_poll_interval)


async def _funding_loop(symbols: List[str]) -> None:
    """Periodically poll funding rates via REST."""
    while True:
        try:
            await poll_funding_rate(symbols)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Funding polling loop error")
        await asyncio.sleep(settings.funding_poll_interval)
