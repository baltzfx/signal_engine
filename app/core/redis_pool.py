"""
Shared async Redis connection pool.
Provides get / set helpers with automatic serialization and TTL.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    """Create and return the global Redis connection pool."""
    global _pool
    if _pool is not None:
        return _pool
    _pool = aioredis.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
    )
    # Quick connectivity check
    await _pool.ping()
    logger.info("Redis connection pool initialised (%s)", settings.redis_url)
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Redis connection pool closed")


def get_redis() -> aioredis.Redis:
    """Return the live pool — call *after* init_redis()."""
    if _pool is None:
        raise RuntimeError("Redis pool not initialised — call init_redis() first")
    return _pool


# ── Convenience helpers ──────────────────────────────────────────

async def redis_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Serialise *value* to JSON and SET with optional TTL."""
    r = get_redis()
    payload = json.dumps(value) if not isinstance(value, str) else value
    if ttl is None:
        ttl = settings.redis_key_ttl
    await r.set(key, payload, ex=ttl)


async def redis_get(key: str, default: Any = None) -> Any:
    """GET and JSON-deserialise.  Returns *default* on miss."""
    r = get_redis()
    raw = await r.get(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def redis_set_hash(key: str, mapping: dict, ttl: Optional[int] = None) -> None:
    """HSET a flat dict then optionally set TTL."""
    r = get_redis()
    # Convert all values to strings for Redis hash
    str_mapping = {k: json.dumps(v) if not isinstance(v, (str, int, float)) else str(v) for k, v in mapping.items()}
    await r.hset(key, mapping=str_mapping)
    if ttl is None:
        ttl = settings.redis_key_ttl
    await r.expire(key, ttl)


async def redis_get_hash(key: str) -> dict:
    """HGETALL and return raw dict."""
    r = get_redis()
    return await r.hgetall(key)


async def redis_publish(channel: str, message: Any) -> None:
    """Publish a message to a Redis Pub/Sub channel."""
    r = get_redis()
    payload = json.dumps(message) if not isinstance(message, str) else message
    await r.publish(channel, payload)


# Stream name used by collectors to notify the feature engine of new data
DATA_UPDATE_STREAM = "stream:data_updates"
# Max stream length (auto-trimmed by Redis)
DATA_UPDATE_STREAM_MAXLEN = 10_000


async def redis_stream_notify(symbol: str, data_type: str) -> None:
    """
    Notify downstream consumers that new data is available for *symbol*.
    Uses Redis Streams (XADD) with approximate trimming.
    """
    r = get_redis()
    await r.xadd(
        DATA_UPDATE_STREAM,
        {"symbol": symbol, "data_type": data_type},
        maxlen=DATA_UPDATE_STREAM_MAXLEN,
        approximate=True,
    )
