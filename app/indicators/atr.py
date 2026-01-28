"""
Average True Range (ATR) Indicator
Used for dynamic stop loss and volatility measurement
"""
import numpy as np
from typing import List, Dict


def calculate_true_range(highs: List[float], lows: List[float], closes: List[float]) -> List[float]:
    """
    Calculate True Range
    TR = max(high - low, abs(high - previous_close), abs(low - previous_close))
    """
    true_ranges = [highs[0] - lows[0]]  # First TR is just high - low
    
    for i in range(1, len(highs)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        true_ranges.append(max(hl, hc, lc))
    
    return true_ranges


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    """
    Calculate Average True Range (ATR)
    
    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of close prices
        period: ATR period (default 14)
        
    Returns:
        List of ATR values
    """
    if len(highs) < period or len(lows) < period or len(closes) < period:
        return [0] * len(closes)
    
    true_ranges = calculate_true_range(highs, lows, closes)
    atr = [0] * len(closes)
    
    # First ATR is simple average of TR
    atr[period - 1] = np.mean(true_ranges[:period])
    
    # Subsequent ATRs use smoothing
    for i in range(period, len(closes)):
        atr[i] = (atr[i - 1] * (period - 1) + true_ranges[i]) / period
    
    return atr


def get_atr_signals(highs: List[float], lows: List[float], closes: List[float]) -> Dict:
    """
    Calculate ATR and derive signals
    
    Returns:
        Dict with ATR value, volatility state, and dynamic levels
    """
    if len(closes) < 14:
        return {
            'atr': 0,
            'atr_percent': 0,
            'volatility': 'unknown',
            'stop_multiplier': 2.0,
            'target_multiplier': 3.0
        }
    
    atr = calculate_atr(highs, lows, closes, period=14)
    current_atr = atr[-1]
    current_price = closes[-1]
    
    # ATR as percentage of price
    atr_percent = (current_atr / current_price) * 100
    
    # Classify volatility
    if atr_percent < 1.5:
        volatility = 'low'
        stop_mult = 1.5
        target_mult = 2.5
    elif atr_percent < 3.0:
        volatility = 'medium'
        stop_mult = 2.0
        target_mult = 3.0
    else:
        volatility = 'high'
        stop_mult = 2.5
        target_mult = 4.0
    
    # Check if volatility is expanding
    atr_ma = np.mean(atr[-20:]) if len(atr) >= 20 else current_atr
    expanding = current_atr > atr_ma * 1.2
    contracting = current_atr < atr_ma * 0.8
    
    return {
        'atr': current_atr,
        'atr_percent': round(atr_percent, 2),
        'volatility': volatility,
        'expanding': expanding,
        'contracting': contracting,
        'stop_multiplier': stop_mult,
        'target_multiplier': target_mult
    }
