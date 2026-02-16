"""
Research: Offline feature generation.

Mirrors the production feature computations but operates on DataFrames
rather than Redis, enabling fast batch feature engineering for
training and backtesting.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add ATR column."""
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(period).mean()
    return df


def add_ema_slope(df: pd.DataFrame, period: int = 9, lookback: int = 3) -> pd.DataFrame:
    """Add normalised EMA slope."""
    ema = df["close"].ewm(span=period, adjust=False).mean()
    slope = (ema - ema.shift(lookback)) / ((ema + ema.shift(lookback)) / 2)
    df["ema_slope"] = slope
    return df


def add_vwap_distance(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Add VWAP distance (normalised)."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cum_pv = (typical * df["volume"]).rolling(period).sum()
    cum_vol = df["volume"].rolling(period).sum()
    vwap = cum_pv / cum_vol
    df["vwap_distance"] = (df["close"] - vwap) / vwap
    return df


def add_range_expansion(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Ratio of current candle range to average range."""
    candle_range = df["high"] - df["low"]
    avg_range = candle_range.rolling(period).mean()
    df["range_expansion"] = candle_range / avg_range.replace(0, np.nan)
    return df


def add_oi_delta(df: pd.DataFrame, column: str = "open_interest", window: int = 10) -> pd.DataFrame:
    """OI percentage change over window."""
    if column in df.columns:
        df["oi_delta"] = df[column].pct_change(window)
    else:
        df["oi_delta"] = 0.0
    return df


def add_funding_zscore(df: pd.DataFrame, column: str = "funding_rate", window: int = 50) -> pd.DataFrame:
    """Rolling z-score of funding rate."""
    if column in df.columns:
        roll = df[column].rolling(window)
        mean = roll.mean()
        std = roll.std().replace(0, np.nan)
        df["funding_zscore"] = (df[column] - mean) / std
    else:
        df["funding_zscore"] = 0.0
    return df


def add_structure(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    """Breakout detection: close beyond rolling high/low."""
    roll_high = df["high"].rolling(lookback).max().shift(1)
    roll_low = df["low"].rolling(lookback).min().shift(1)
    df["breakout_bull"] = (df["close"] > roll_high).astype(int)
    df["breakout_bear"] = (df["close"] < roll_low).astype(int)
    return df


def add_liquidation_ratio(
    df: pd.DataFrame,
    long_liq_col: str = "long_liqs",
    short_liq_col: str = "short_liqs",
    window: int = 20,
) -> pd.DataFrame:
    """Rolling liquidation ratio and total USD."""
    if long_liq_col in df.columns and short_liq_col in df.columns:
        longs = df[long_liq_col].rolling(window).sum()
        shorts = df[short_liq_col].rolling(window).sum().replace(0, np.nan)
        df["liq_ratio"] = longs / shorts
    else:
        df["liq_ratio"] = 1.0

    if "liq_usd" in df.columns:
        df["liq_total_usd"] = df["liq_usd"].rolling(window).sum()
    else:
        df["liq_total_usd"] = 0.0
    return df


def add_orderbook_imbalance(
    df: pd.DataFrame,
    bid_vol_col: str = "bid_volume",
    ask_vol_col: str = "ask_volume",
) -> pd.DataFrame:
    """Orderbook imbalance: (bid - ask) / (bid + ask)."""
    if bid_vol_col in df.columns and ask_vol_col in df.columns:
        total = df[bid_vol_col] + df[ask_vol_col]
        df["ob_imbalance"] = (df[bid_vol_col] - df[ask_vol_col]) / total.replace(0, np.nan)
    else:
        df["ob_imbalance"] = 0.0
    return df


def add_all_features(
    df: pd.DataFrame,
    atr_period: int = 14,
    ema_period: int = 9,
    vwap_period: int = 20,
    structure_lookback: int = 20,
) -> pd.DataFrame:
    """Convenience: add all features at once."""
    df = add_atr(df, atr_period)
    df = add_ema_slope(df, ema_period)
    df = add_vwap_distance(df, vwap_period)
    df = add_range_expansion(df, atr_period)
    df = add_oi_delta(df)
    df = add_funding_zscore(df)
    df = add_structure(df, structure_lookback)
    df = add_liquidation_ratio(df)
    df = add_orderbook_imbalance(df)
    return df


def create_labels(df: pd.DataFrame, forward_periods: int = 6, threshold_pct: float = 0.5) -> pd.DataFrame:
    """
    Create binary classification labels:
        1 = price moves up > threshold_pct in next forward_periods candles
        0 = otherwise (including down moves)
    """
    future_return = df["close"].shift(-forward_periods) / df["close"] - 1
    df["label"] = (future_return > threshold_pct / 100).astype(int)
    return df
