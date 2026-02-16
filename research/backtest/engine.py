"""
Research: Backtesting engine.

Simulates the rule-based signal engine (and optionally AI) against
historical feature DataFrames to evaluate signal quality.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    total_signals: int = 0
    longs: int = 0
    shorts: int = 0
    wins: int = 0
    losses: int = 0
    avg_return: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    returns: List[float] = field(default_factory=list)
    signals: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.wins / max(self.total_signals, 1)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_signals": self.total_signals,
            "win_rate": round(self.win_rate, 4),
            "avg_return": round(self.avg_return, 4),
            "sharpe": round(self.sharpe, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "longs": self.longs,
            "shorts": self.shorts,
        }


def backtest_signals(
    df: pd.DataFrame,
    score_threshold: float = 0.60,
    forward_periods: int = 6,
    cooldown_periods: int = 6,
) -> BacktestResult:
    """
    Walk through the feature DataFrame row by row,
    generate signals using the scoring logic, and evaluate
    forward returns.

    Expects columns: ema_slope, vwap_distance, atr, range_expansion,
    oi_delta, funding_zscore, breakout_bull, breakout_bear, close

    Returns BacktestResult with detailed stats.
    """
    result = BacktestResult()
    cooldown_until = -1

    closes = df["close"].values
    n = len(df)

    for i in range(n - forward_periods):
        if i < cooldown_until:
            continue

        row = df.iloc[i]
        score, direction = _simple_score(row)

        if score < score_threshold:
            continue

        # Forward return
        entry_price = closes[i]
        exit_price = closes[min(i + forward_periods, n - 1)]
        ret = (exit_price - entry_price) / entry_price
        if direction == "short":
            ret = -ret

        result.total_signals += 1
        result.returns.append(ret)
        if direction == "long":
            result.longs += 1
        else:
            result.shorts += 1
        if ret > 0:
            result.wins += 1
        else:
            result.losses += 1

        result.signals.append({
            "index": i,
            "direction": direction,
            "score": round(score, 4),
            "return": round(ret, 6),
        })

        cooldown_until = i + cooldown_periods

    # Aggregate
    if result.returns:
        arr = np.array(result.returns)
        result.avg_return = float(arr.mean())
        std = arr.std()
        result.sharpe = float(arr.mean() / std * np.sqrt(252 * 12)) if std > 0 else 0.0
        cumulative = np.cumprod(1 + arr)
        peaks = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - peaks) / peaks
        result.max_drawdown = float(drawdowns.min())

    return result


def _simple_score(row: pd.Series) -> tuple[float, str]:
    """Lightweight replica of the production scoring for backtesting."""
    bull = 0
    bear = 0
    score_parts = []

    # EMA slope
    ema_sl = float(row.get("ema_slope", 0) or 0)
    if ema_sl > 0.001:
        bull += 1
        score_parts.append(min(abs(ema_sl) / 0.01, 1.0) * 0.20)
    elif ema_sl < -0.001:
        bear += 1
        score_parts.append(min(abs(ema_sl) / 0.01, 1.0) * 0.20)
    else:
        score_parts.append(0)

    # VWAP
    vd = float(row.get("vwap_distance", 0) or 0)
    if vd > 0:
        bull += 1
    elif vd < 0:
        bear += 1
    score_parts.append(min(abs(vd) / 0.02, 1.0) * 0.10)

    # Range expansion
    re_val = float(row.get("range_expansion", 1) or 1)
    score_parts.append(min(max(re_val - 1, 0) / 2, 1.0) * 0.15)

    # OI delta
    oi = float(row.get("oi_delta", 0) or 0)
    score_parts.append(min(abs(oi) * 10, 1.0) * 0.15)

    # Funding z-score
    fz = float(row.get("funding_zscore", 0) or 0)
    if abs(fz) > 2.0:
        score_parts.append(0.15)
        if fz > 0:
            bear += 1
        else:
            bull += 1
    else:
        score_parts.append(0)

    # Breakout
    if row.get("breakout_bull", 0):
        bull += 1
        score_parts.append(0.15)
    elif row.get("breakout_bear", 0):
        bear += 1
        score_parts.append(0.15)
    else:
        score_parts.append(0)

    # Event quality proxy
    score_parts.append(0.05)

    direction = "long" if bull >= bear else "short"
    return sum(score_parts), direction
