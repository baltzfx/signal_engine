"""
Prometheus metrics instrumentation for SignalEngine.

Exposes comprehensive metrics for monitoring:
  - Request counters and latencies
  - Signal generation metrics
  - Data collection metrics
  - System resource utilization
  - Custom business metrics
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ── Custom registry to avoid conflicts ───────────────────────────
registry = CollectorRegistry()

# ── Application info ──────────────────────────────────────────────
app_info = Info(
    "signalengine_app",
    "SignalEngine application information",
    registry=registry,
)
app_info.info({"version": "3.0.0", "name": "SignalEngine"})

# ── HTTP Metrics ──────────────────────────────────────────────────
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

# ── Data Collection Metrics ───────────────────────────────────────
websocket_messages_total = Counter(
    "websocket_messages_total",
    "Total WebSocket messages received",
    ["stream_type"],
    registry=registry,
)

websocket_errors_total = Counter(
    "websocket_errors_total",
    "Total WebSocket errors",
    ["stream_type", "error_type"],
    registry=registry,
)

websocket_reconnections_total = Counter(
    "websocket_reconnections_total",
    "Total WebSocket reconnections",
    ["stream_type"],
    registry=registry,
)

rest_api_calls_total = Counter(
    "rest_api_calls_total",
    "Total REST API calls to Binance",
    ["endpoint"],
    registry=registry,
)

# ── Feature Engine Metrics ────────────────────────────────────────
features_computed_total = Counter(
    "features_computed_total",
    "Total feature computations",
    ["symbol", "timeframe"],
    registry=registry,
)

feature_computation_duration_seconds = Histogram(
    "feature_computation_duration_seconds",
    "Feature computation latency",
    ["timeframe"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

feature_errors_total = Counter(
    "feature_errors_total",
    "Feature computation errors",
    ["symbol", "error_type"],
    registry=registry,
)

# ── Event Engine Metrics ──────────────────────────────────────────
events_detected_total = Counter(
    "events_detected_total",
    "Total events detected",
    ["event_type"],
    registry=registry,
)

event_queue_size = Gauge(
    "event_queue_size",
    "Current event queue depth",
    registry=registry,
)

event_processing_duration_seconds = Histogram(
    "event_processing_duration_seconds",
    "Event processing latency",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
    registry=registry,
)

# ── Signal Engine Metrics ─────────────────────────────────────────
signals_generated_total = Counter(
    "signals_generated_total",
    "Total signals generated",
    ["symbol", "direction"],
    registry=registry,
)

signal_score = Histogram(
    "signal_score",
    "Signal score distribution",
    ["direction"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=registry,
)

signals_active = Gauge(
    "signals_active",
    "Currently active signals",
    ["direction"],
    registry=registry,
)

signal_outcomes_total = Counter(
    "signal_outcomes_total",
    "Signal outcomes",
    ["symbol", "direction", "outcome"],
    registry=registry,
)

signal_returns = Histogram(
    "signal_returns",
    "Signal return distribution (percentage)",
    ["direction"],
    buckets=(-10, -5, -2, -1, 0, 1, 2, 5, 10, 20),
    registry=registry,
)

signal_duration_seconds = Histogram(
    "signal_duration_seconds",
    "Signal duration from entry to close",
    ["outcome"],
    buckets=(60, 300, 600, 1800, 3600, 7200, 14400),
    registry=registry,
)

# ── AI Metrics ────────────────────────────────────────────────────
ai_inference_total = Counter(
    "ai_inference_total",
    "Total AI inferences",
    ["model_type"],
    registry=registry,
)

ai_inference_duration_seconds = Histogram(
    "ai_inference_duration_seconds",
    "AI inference latency",
    ["model_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

ai_model_reloads_total = Counter(
    "ai_model_reloads_total",
    "Total AI model reloads (hot reload)",
    ["model_type"],
    registry=registry,
)

# ── Performance Tracking Metrics ──────────────────────────────────
symbol_win_rate = Gauge(
    "symbol_win_rate",
    "Win rate by symbol (0.0 to 1.0)",
    ["symbol", "timeframe"],
    registry=registry,
)

symbol_avg_return = Gauge(
    "symbol_avg_return",
    "Average return by symbol (percentage)",
    ["symbol", "timeframe"],
    registry=registry,
)

symbol_sharpe_ratio = Gauge(
    "symbol_sharpe_ratio",
    "Sharpe ratio by symbol",
    ["symbol", "timeframe"],
    registry=registry,
)

symbol_signal_count = Counter(
    "symbol_signal_count_total",
    "Total signals per symbol",
    ["symbol", "timeframe"],
    registry=registry,
)

# ── Feature Importance Metrics ────────────────────────────────────
feature_importance = Gauge(
    "feature_importance",
    "Feature importance score from AI model",
    ["feature_name", "model_type"],
    registry=registry,
)

# ── System Metrics ────────────────────────────────────────────────
system_cpu_percent = Gauge(
    "system_cpu_percent",
    "CPU usage percentage",
    registry=registry,
)

system_memory_percent = Gauge(
    "system_memory_percent",
    "Memory usage percentage",
    registry=registry,
)

system_memory_rss_bytes = Gauge(
    "system_memory_rss_bytes",
    "Process RSS memory in bytes",
    registry=registry,
)

system_threads = Gauge(
    "system_threads",
    "Number of threads",
    registry=registry,
)

system_uptime_seconds = Gauge(
    "system_uptime_seconds",
    "Application uptime in seconds",
    registry=registry,
)

redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation"],
    registry=registry,
)

redis_errors_total = Counter(
    "redis_errors_total",
    "Total Redis errors",
    ["operation"],
    registry=registry,
)

database_operations_total = Counter(
    "database_operations_total",
    "Total database operations",
    ["operation"],
    registry=registry,
)

database_batch_size = Histogram(
    "database_batch_size",
    "Database batch write size",
    buckets=(1, 5, 10, 25, 50, 100, 200, 500),
    registry=registry,
)


# ── Helper functions ──────────────────────────────────────────────

@asynccontextmanager
async def track_duration(histogram: Histogram, labels: dict | None = None) -> AsyncIterator[None]:
    """Context manager to track duration of async operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        if labels:
            histogram.labels(**labels).observe(duration)
        else:
            histogram.observe(duration)


def get_metrics() -> bytes:
    """Generate Prometheus metrics in text format."""
    return generate_latest(registry)


def get_content_type() -> str:
    """Return the Prometheus metrics content type."""
    return CONTENT_TYPE_LATEST
