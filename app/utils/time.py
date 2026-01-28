"""
Time Utilities
Helper functions for time and datetime operations
"""
from datetime import datetime, timedelta, timezone
from typing import Optional


def utc_now() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def to_timestamp(dt: datetime) -> int:
    """Convert datetime to Unix timestamp (milliseconds)"""
    return int(dt.timestamp() * 1000)


def from_timestamp(ts: int) -> datetime:
    """Convert Unix timestamp (milliseconds) to datetime"""
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """Format datetime to string"""
    return dt.strftime(fmt)


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string (ISO format)"""
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        return None


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string
    
    Example: "2 hours ago", "5 minutes ago"
    """
    now = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    return "just now"


def get_timeframe_minutes(timeframe: str) -> int:
    """
    Convert timeframe string to minutes
    
    Examples: '1m' -> 1, '1h' -> 60, '4h' -> 240, '1d' -> 1440
    """
    mapping = {
        'm': 1,
        'h': 60,
        'd': 1440,
        'w': 10080
    }
    
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    
    return value * mapping.get(unit, 1)
