"""
Exponential Moving Average (EMA) Indicator
"""
import numpy as np
from typing import List

from config.constants import EMA_FAST, EMA_MEDIUM, EMA_SLOW, EMA_TREND


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """
    Calculate EMA for given prices
    
    Args:
        prices: List of closing prices
        period: EMA period
        
    Returns:
        List of EMA values (same length as input)
    """
    prices_array = np.array(prices)
    ema = np.zeros_like(prices_array)
    
    if len(prices) < period:
        return ema.tolist()
    
    # Calculate smoothing multiplier
    multiplier = 2 / (period + 1)
    
    # First EMA is SMA
    ema[period - 1] = np.mean(prices_array[:period])
    
    # Calculate rest of EMAs
    for i in range(period, len(prices)):
        ema[i] = (prices_array[i] - ema[i - 1]) * multiplier + ema[i - 1]
    
    return ema.tolist()


def get_ema_signals(prices: List[float]) -> dict:
    """
    Calculate multiple EMAs and detect crossovers
    
    Returns:
        Dict with EMA values and crossover signals
    """
    if len(prices) < EMA_TREND:
        return {
            'ema_fast': None,
            'ema_medium': None,
            'ema_slow': None,
            'ema_trend': None,
            'bullish_cross': False,
            'bearish_cross': False
        }
    
    ema_fast = calculate_ema(prices, EMA_FAST)
    ema_medium = calculate_ema(prices, EMA_MEDIUM)
    ema_slow = calculate_ema(prices, EMA_SLOW)
    ema_trend = calculate_ema(prices, EMA_TREND)
    
    # Detect crossovers (fast crosses medium)
    bullish_cross = False
    bearish_cross = False
    
    if len(ema_fast) >= 2 and len(ema_medium) >= 2:
        # Current candle: fast > medium, previous: fast < medium
        if ema_fast[-1] > ema_medium[-1] and ema_fast[-2] <= ema_medium[-2]:
            bullish_cross = True
        # Current candle: fast < medium, previous: fast > medium
        elif ema_fast[-1] < ema_medium[-1] and ema_fast[-2] >= ema_medium[-2]:
            bearish_cross = True
    
    return {
        'ema_fast': ema_fast[-1] if ema_fast else None,
        'ema_medium': ema_medium[-1] if ema_medium else None,
        'ema_slow': ema_slow[-1] if ema_slow else None,
        'ema_trend': ema_trend[-1] if ema_trend else None,
        'bullish_cross': bullish_cross,
        'bearish_cross': bearish_cross,
        'trend_up': prices[-1] > ema_trend[-1] if ema_trend else False,
        'trend_down': prices[-1] < ema_trend[-1] if ema_trend else False
    }
