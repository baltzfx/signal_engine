"""
Research: Historical data loader.

Downloads kline + funding + OI data from Binance Futures REST API
and saves to parquet / CSV for offline analysis.
"""

from __future__ import annotations

import os
import time
from typing import List, Optional

import httpx
import pandas as pd

BASE_URL = "https://fapi.binance.com"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


async def fetch_klines(
    symbol: str,
    interval: str = "5m",
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 1500,
) -> pd.DataFrame:
    """Download historical klines and return a DataFrame."""
    params: dict = {"symbol": symbol, "interval": interval, "limit": limit}
    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/fapi/v1/klines", params=params)
        resp.raise_for_status()
        data = resp.json()

    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ]
    df = pd.DataFrame(data, columns=cols)
    for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[c] = df[c].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    return df


async def fetch_funding_rate_history(
    symbol: str,
    start_time: Optional[int] = None,
    limit: int = 1000,
) -> pd.DataFrame:
    params: dict = {"symbol": symbol, "limit": limit}
    if start_time:
        params["startTime"] = start_time

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/fapi/v1/fundingRate", params=params)
        resp.raise_for_status()
        data = resp.json()

    df = pd.DataFrame(data)
    if not df.empty:
        df["fundingRate"] = df["fundingRate"].astype(float)
        df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms")
    return df


async def bulk_download_klines(
    symbol: str,
    interval: str = "5m",
    days: int = 30,
) -> pd.DataFrame:
    """Download *days* worth of kline data by iterating backward."""
    end = int(time.time() * 1000)
    start = end - days * 86400 * 1000
    all_dfs: List[pd.DataFrame] = []
    cursor = start

    async with httpx.AsyncClient(timeout=15) as client:
        while cursor < end:
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": cursor,
                "limit": 1500,
            }
            resp = await client.get(f"{BASE_URL}/fapi/v1/klines", params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break

            cols = [
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore",
            ]
            df = pd.DataFrame(data, columns=cols)
            all_dfs.append(df)
            cursor = int(data[-1][6]) + 1  # close_time + 1
            await __import__("asyncio").sleep(0.2)  # respect rate limit

    combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    if not combined.empty:
        for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
            combined[c] = combined[c].astype(float)
        combined["open_time"] = pd.to_datetime(combined["open_time"], unit="ms")
        combined["close_time"] = pd.to_datetime(combined["close_time"], unit="ms")

    # Save
    path = os.path.join(DATA_DIR, f"{symbol}_{interval}_{days}d.parquet")
    combined.to_parquet(path, index=False)
    return combined


# ── Open Interest history ─────────────────────────────────────────

async def fetch_open_interest_history(
    symbol: str,
    period: str = "5m",
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 500,
) -> pd.DataFrame:
    """Download open-interest snapshots from Binance Futures."""
    params: dict = {"symbol": symbol, "period": period, "limit": limit}
    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}/futures/data/openInterestHist", params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    df = pd.DataFrame(data)
    if not df.empty:
        df["sumOpenInterest"] = df["sumOpenInterest"].astype(float)
        df["sumOpenInterestValue"] = df["sumOpenInterestValue"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


async def bulk_download_open_interest(
    symbol: str,
    period: str = "5m",
    days: int = 30,
) -> pd.DataFrame:
    """Download *days* worth of OI history, paginating backward."""
    end = int(time.time() * 1000)
    start = end - days * 86400 * 1000
    all_dfs: List[pd.DataFrame] = []
    cursor = start

    async with httpx.AsyncClient(timeout=15) as client:
        while cursor < end:
            params = {
                "symbol": symbol,
                "period": period,
                "startTime": cursor,
                "limit": 500,
            }
            resp = await client.get(
                f"{BASE_URL}/futures/data/openInterestHist", params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            all_dfs.append(pd.DataFrame(data))
            cursor = int(data[-1]["timestamp"]) + 1
            await __import__("asyncio").sleep(0.3)

    combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    if not combined.empty:
        combined["sumOpenInterest"] = combined["sumOpenInterest"].astype(float)
        combined["sumOpenInterestValue"] = combined["sumOpenInterestValue"].astype(float)
        combined["timestamp"] = pd.to_datetime(combined["timestamp"], unit="ms")
        path = os.path.join(DATA_DIR, f"{symbol}_oi_{days}d.parquet")
        combined.to_parquet(path, index=False)
    return combined


# ── Liquidation / Force-order history ─────────────────────────────

async def fetch_liquidation_history(
    symbol: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 1000,
) -> pd.DataFrame:
    """Download recent forced liquidation orders from Binance Futures.

    NOTE: Binance only returns liquidations from the past ~7 days via
    the public endpoint.  For longer history, consider a third-party
    archive or WebSocket recording.
    """
    params: dict = {"symbol": symbol, "limit": limit}
    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}/fapi/v1/allForceOrders", params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    df = pd.DataFrame(data)
    if not df.empty:
        df["price"] = df["price"].astype(float)
        df["origQty"] = df["origQty"].astype(float)
        df["executedQty"] = df["executedQty"].astype(float)
        df["averagePrice"] = df["averagePrice"].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit="ms")
    return df


async def bulk_download_liquidations(
    symbol: str,
    days: int = 7,
) -> pd.DataFrame:
    """Download liquidation orders, paginating across *days* (max ~7)."""
    end = int(time.time() * 1000)
    start = end - days * 86400 * 1000
    all_dfs: List[pd.DataFrame] = []
    cursor = start

    async with httpx.AsyncClient(timeout=15) as client:
        while cursor < end:
            params = {
                "symbol": symbol,
                "startTime": cursor,
                "limit": 1000,
            }
            resp = await client.get(
                f"{BASE_URL}/fapi/v1/allForceOrders", params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            all_dfs.append(pd.DataFrame(data))
            cursor = int(data[-1]["time"]) + 1
            await __import__("asyncio").sleep(0.3)

    combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    if not combined.empty:
        combined["price"] = combined["price"].astype(float)
        combined["origQty"] = combined["origQty"].astype(float)
        combined["executedQty"] = combined["executedQty"].astype(float)
        combined["averagePrice"] = combined["averagePrice"].astype(float)
        combined["time"] = pd.to_datetime(combined["time"], unit="ms")
        path = os.path.join(DATA_DIR, f"{symbol}_liquidations_{days}d.parquet")
        combined.to_parquet(path, index=False)
    return combined
    print(f"Saved {len(combined)} rows → {path}")
    return combined
