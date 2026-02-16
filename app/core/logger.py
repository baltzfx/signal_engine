"""
Structured JSON logging setup.
Call ``setup_logging()`` once at startup.
"""

from __future__ import annotations

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Attach any extra fields passed via `extra={}`
        for key in ("symbol", "event", "component", "latency_ms"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry)


class PlainFormatter(logging.Formatter):
    """Human-readable formatter for local development."""
    FMT = "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s"

    def __init__(self) -> None:
        super().__init__(fmt=self.FMT, datefmt="%Y-%m-%d %H:%M:%S")


def setup_logging(level: Optional[str] = None) -> None:
    """Configure root logger.  Safe to call more than once."""
    lvl = getattr(logging, (level or settings.log_level).upper(), logging.INFO)

    root = logging.getLogger()
    # Avoid duplicate handlers on repeated calls
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter() if settings.log_json else PlainFormatter())
    root.setLevel(lvl)
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for name in ("websockets", "httpcore", "httpx", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
