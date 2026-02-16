"""
System monitoring — CPU, memory, and engine metrics.

Exposes counters that can be incremented from anywhere in the codebase
and read via the /metrics endpoint. Now integrated with Prometheus.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict

from app.core import prometheus_metrics as prom

logger = logging.getLogger(__name__)

# ── Atomic counters ───────────────────────────────────────────────

_counters: Dict[str, int] = defaultdict(int)
_gauges: Dict[str, float] = defaultdict(float)
_start_time: float = time.time()


def inc(name: str, amount: int = 1) -> None:
    """Increment a named counter."""
    _counters[name] += amount


def gauge(name: str, value: float) -> None:
    """Set a named gauge to an absolute value."""
    _gauges[name] = value


def get_counters() -> Dict[str, int]:
    return dict(_counters)


def get_gauges() -> Dict[str, float]:
    return dict(_gauges)


# ── System metrics via psutil ─────────────────────────────────────

def get_system_metrics() -> Dict[str, Any]:
    """Return CPU, memory, and uptime stats."""
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        return {
            "cpu_percent": proc.cpu_percent(interval=None),
            "memory_rss_mb": round(mem.rss / 1024 / 1024, 2),
            "memory_vms_mb": round(mem.vms / 1024 / 1024, 2),
            "threads": proc.num_threads(),
            "open_files": len(proc.open_files()),
            "system_cpu_percent": psutil.cpu_percent(interval=None),
            "system_memory_percent": psutil.virtual_memory().percent,
            "uptime_seconds": round(time.time() - _start_time, 1),
        }
    except ImportError:
        return {
            "error": "psutil not installed",
            "uptime_seconds": round(time.time() - _start_time, 1),
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "uptime_seconds": round(time.time() - _start_time, 1),
        }


# ── Background health-check loop ─────────────────────────────────

_monitor_task = None
_running = False
MONITOR_INTERVAL = 30.0  # seconds


async def start_monitor() -> None:
    global _monitor_task, _running
    _running = True
    _monitor_task = asyncio.create_task(_monitor_loop())
    logger.info("System monitor started")


async def stop_monitor() -> None:
    global _monitor_task, _running
    _running = False
    if _monitor_task:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
        _monitor_task = None


async def _monitor_loop() -> None:
    """Periodically log system metrics and warn on thresholds."""
    while _running:
        try:
            metrics = get_system_metrics()
            rss = metrics.get("memory_rss_mb", 0)
            cpu = metrics.get("cpu_percent", 0)

            if rss > 1024:
                logger.warning("High memory usage: %.1f MB RSS", rss, extra={"component": "monitor"})
            if isinstance(cpu, (int, float)) and cpu > 80:
                logger.warning("High CPU usage: %.1f%%", cpu, extra={"component": "monitor"})

            # Update gauges for /metrics (legacy)
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    gauge(f"system_{k}", v)

            # Update Prometheus metrics
            if "cpu_percent" in metrics:
                prom.system_cpu_percent.set(metrics["cpu_percent"])
            if "memory_rss_mb" in metrics:
                prom.system_memory_rss_bytes.set(metrics["memory_rss_mb"] * 1024 * 1024)
            if "system_memory_percent" in metrics:
                prom.system_memory_percent.set(metrics["system_memory_percent"])
            if "threads" in metrics:
                prom.system_threads.set(metrics["threads"])
            if "uptime_seconds" in metrics:
                prom.system_uptime_seconds.set(metrics["uptime_seconds"])

        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Monitor loop error")

        await asyncio.sleep(MONITOR_INTERVAL)
