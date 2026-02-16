"""
Payload validation for incoming Binance WebSocket / REST messages.

Each validator returns True if the payload is safe to process, False otherwise.
Invalid payloads are logged and silently dropped — they should never crash
the handler.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def validate_kline(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate a kline stream message. Returns the kline dict or None."""
    data = msg.get("data", msg)
    kline = data.get("k")
    if not isinstance(kline, dict):
        logger.debug("Kline payload missing 'k' field")
        return None

    required = ("s", "t", "o", "h", "l", "c", "v", "q", "x")
    for field in required:
        if field not in kline:
            logger.debug("Kline payload missing field '%s'", field)
            return None

    # Sanity: prices should be parseable as float
    for price_field in ("o", "h", "l", "c"):
        try:
            float(kline[price_field])
        except (ValueError, TypeError):
            logger.debug("Kline field '%s' not a valid number: %s", price_field, kline[price_field])
            return None

    return kline


def validate_depth(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate a depth stream message. Returns the data dict or None."""
    data = msg.get("data", msg)
    stream = msg.get("stream", "")
    symbol = stream.split("@")[0].upper() if stream else ""
    if not symbol:
        logger.debug("Depth payload has no stream name")
        return None

    bids = data.get("bids", data.get("b"))
    asks = data.get("asks", data.get("a"))
    if not isinstance(bids, list) or not isinstance(asks, list):
        logger.debug("Depth payload missing bids/asks arrays")
        return None

    return {"symbol": symbol, "bids": bids, "asks": asks}


def validate_mark_price(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate a markPrice message. Returns the data dict or None."""
    data = msg.get("data", msg)
    symbol = data.get("s", "")
    if not symbol:
        logger.debug("Mark price payload missing symbol")
        return None

    for field in ("p", "i", "r"):
        val = data.get(field)
        if val is None:
            logger.debug("Mark price missing field '%s'", field)
            return None
        try:
            float(val)
        except (ValueError, TypeError):
            logger.debug("Mark price field '%s' not a number: %s", field, val)
            return None

    return data


def validate_force_order(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate a forceOrder (liquidation) message. Returns the order dict or None."""
    data = msg.get("data", msg)
    order = data.get("o", data)
    if not isinstance(order, dict):
        logger.debug("Force order payload has no 'o' field")
        return None

    symbol = order.get("s", "")
    if not symbol:
        logger.debug("Force order missing symbol")
        return None

    for field in ("S", "p", "q"):
        if field not in order:
            logger.debug("Force order missing field '%s'", field)
            return None

    # Side must be SELL or BUY
    side = order.get("S", "")
    if side not in ("SELL", "BUY"):
        logger.debug("Force order invalid side: %s", side)
        return None

    return order


def validate_open_interest(data: Dict[str, Any]) -> bool:
    """Validate an OI REST response body."""
    oi = data.get("openInterest")
    if oi is None:
        return False
    try:
        float(oi)
        return True
    except (ValueError, TypeError):
        return False


def validate_funding(data: Dict[str, Any]) -> bool:
    """Validate a premiumIndex REST response body."""
    for field in ("lastFundingRate", "markPrice", "indexPrice"):
        val = data.get(field)
        if val is None:
            return False
        try:
            float(val)
        except (ValueError, TypeError):
            return False
    return True
