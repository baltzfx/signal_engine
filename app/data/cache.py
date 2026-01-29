"""
Market Data Cache
Simple in-memory cache with TTL support
"""
import time
from typing import Any, Optional, Dict
from threading import Lock

from config.settings import settings


class MarketDataCache:
    """Thread-safe in-memory cache with TTL"""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._lock = Lock()
        self.default_ttl = settings.CACHE_TTL_SECONDS
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                else:
                    # Remove expired entry
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cache value with TTL in seconds"""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        
        with self._lock:
            self._cache[key] = (value, expiry)
    
    def delete(self, key: str) -> None:
        """Remove key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries, return count removed"""
        current_time = time.time()
        removed = 0
        
        with self._lock:
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if current_time >= expiry
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1
        
        return removed
