"""
Relative Strength Index (RSI) Indicator
"""
import numpy as np
from typing import List

from config.constants import RSI_PERIOD
from config.settings import settings


def calculate_rsi(prices: List[float], period: int = RSI_PERIOD) -> List[float]:
    """
    Calculate RSI indicator
    
    Args:
        prices: List of closing prices
        period: RSI period (default 14)
        
    Returns:
        List of RSI values (same length as input)
    """
    prices_array = np.array(prices)
    rsi = np.zeros_like(prices_array)
    
    if len(prices) <= period:
        return rsi.tolist()
    
    # Calculate price changes
    deltas = np.diff(prices_array)
    
    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Calculate average gains and losses
    avg_gain = np.zeros(len(prices))
    avg_loss = np.zeros(len(prices))
    
    # First average is simple mean
    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])
    
    # Subsequent values use smoothed average
    for i in range(period + 1, len(prices)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period
    
    # Calculate RS and RSI
    for i in range(period, len(prices)):
        if avg_loss[i] == 0:
            rsi[i] = 100
        else:
            rs = avg_gain[i] / avg_loss[i]
            rsi[i] = 100 - (100 / (1 + rs))
    
    return rsi.tolist()


def get_rsi_signals(prices: List[float]) -> dict:
    """
    Calculate RSI and detect overbought/oversold conditions
    
    Returns:
        Dict with RSI value and signal conditions
    """
    if len(prices) < RSI_PERIOD + 1:
        return {
            'rsi': None,
            'oversold': False,
            'overbought': False,
            'bullish_divergence': False,
            'bearish_divergence': False
        }
    
    rsi = calculate_rsi(prices)
    current_rsi = rsi[-1]
    
    return {
        'rsi': current_rsi,
        'oversold': current_rsi < settings.RSI_OVERSOLD,
        'overbought': current_rsi > settings.RSI_OVERBOUGHT,
        'extreme_oversold': current_rsi < 25,
        'extreme_overbought': current_rsi > 75,
        'neutral': settings.RSI_OVERSOLD <= current_rsi <= settings.RSI_OVERBOUGHT
    }
