"""
Advanced Technical Indicators
MACD, Bollinger Bands, Stochastic, ADX
"""
import numpy as np
from typing import List, Dict, Tuple


def calculate_macd(
    prices: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Dict:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Returns:
        Dict with MACD line, signal line, and histogram
    """
    if len(prices) < slow:
        return {'macd': 0, 'signal': 0, 'histogram': 0, 'bullish': False, 'bearish': False}
    
    # Calculate EMAs
    prices_array = np.array(prices)
    
    # Fast EMA
    fast_ema = np.zeros_like(prices_array)
    fast_ema[fast - 1] = np.mean(prices_array[:fast])
    multiplier_fast = 2 / (fast + 1)
    for i in range(fast, len(prices)):
        fast_ema[i] = (prices_array[i] - fast_ema[i - 1]) * multiplier_fast + fast_ema[i - 1]
    
    # Slow EMA
    slow_ema = np.zeros_like(prices_array)
    slow_ema[slow - 1] = np.mean(prices_array[:slow])
    multiplier_slow = 2 / (slow + 1)
    for i in range(slow, len(prices)):
        slow_ema[i] = (prices_array[i] - slow_ema[i - 1]) * multiplier_slow + slow_ema[i - 1]
    
    # MACD line
    macd_line = fast_ema - slow_ema
    
    # Signal line (EMA of MACD)
    signal_line = np.zeros_like(macd_line)
    signal_line[slow + signal - 2] = np.mean(macd_line[slow - 1:slow + signal - 1])
    multiplier_signal = 2 / (signal + 1)
    for i in range(slow + signal - 1, len(prices)):
        signal_line[i] = (macd_line[i] - signal_line[i - 1]) * multiplier_signal + signal_line[i - 1]
    
    # Histogram
    histogram = macd_line - signal_line
    
    # Detect crossovers
    bullish_cross = False
    bearish_cross = False
    if len(histogram) >= 2:
        if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
            bullish_cross = True
        elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
            bearish_cross = True
    
    return {
        'macd': macd_line[-1],
        'signal': signal_line[-1],
        'histogram': histogram[-1],
        'bullish_cross': bullish_cross,
        'bearish_cross': bearish_cross,
        'positive': histogram[-1] > 0,
        'increasing': len(histogram) >= 2 and histogram[-1] > histogram[-2]
    }


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Dict:
    """
    Calculate Bollinger Bands
    
    Returns:
        Dict with upper, middle, lower bands and position
    """
    if len(prices) < period:
        return {
            'upper': 0, 'middle': 0, 'lower': 0,
            'percent_b': 0.5, 'squeeze': False,
            'near_lower': False, 'near_upper': False
        }
    
    prices_array = np.array(prices)
    
    # Middle band (SMA)
    middle = np.mean(prices_array[-period:])
    
    # Standard deviation
    std = np.std(prices_array[-period:])
    
    # Upper and lower bands
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    # %B indicator (where price is relative to bands)
    current_price = prices[-1]
    percent_b = (current_price - lower) / (upper - lower) if upper != lower else 0.5
    
    # Bandwidth
    bandwidth = ((upper - lower) / middle) * 100
    
    # Squeeze detection (low volatility)
    squeeze = bandwidth < 2.5
    
    return {
        'upper': upper,
        'middle': middle,
        'lower': lower,
        'percent_b': percent_b,
        'bandwidth': bandwidth,
        'squeeze': squeeze,
        'near_lower': percent_b < 0.2,
        'near_upper': percent_b > 0.8,
        'oversold': percent_b < 0,
        'overbought': percent_b > 1
    }


def calculate_stochastic(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    k_period: int = 14,
    d_period: int = 3
) -> Dict:
    """
    Calculate Stochastic Oscillator
    
    Returns:
        Dict with %K, %D, and signals
    """
    if len(closes) < k_period:
        return {'k': 50, 'd': 50, 'oversold': False, 'overbought': False}
    
    k_values = []
    
    for i in range(k_period - 1, len(closes)):
        high_max = max(highs[i - k_period + 1:i + 1])
        low_min = min(lows[i - k_period + 1:i + 1])
        
        if high_max != low_min:
            k = ((closes[i] - low_min) / (high_max - low_min)) * 100
        else:
            k = 50
        
        k_values.append(k)
    
    # %D is SMA of %K
    if len(k_values) >= d_period:
        d = np.mean(k_values[-d_period:])
    else:
        d = k_values[-1] if k_values else 50
    
    current_k = k_values[-1] if k_values else 50
    
    return {
        'k': current_k,
        'd': d,
        'oversold': current_k < 20,
        'overbought': current_k > 80,
        'bullish_cross': len(k_values) >= 2 and current_k > d and k_values[-2] <= d,
        'bearish_cross': len(k_values) >= 2 and current_k < d and k_values[-2] >= d
    }


def detect_divergence(
    prices: List[float],
    indicator: List[float],
    lookback: int = 20
) -> Dict:
    """
    Detect bullish/bearish divergence between price and indicator
    
    Returns:
        Dict with divergence signals
    """
    if len(prices) < lookback or len(indicator) < lookback:
        return {'bullish': False, 'bearish': False, 'hidden_bullish': False, 'hidden_bearish': False}
    
    recent_prices = prices[-lookback:]
    recent_indicator = indicator[-lookback:]
    
    # Find recent lows and highs
    price_low_idx = np.argmin(recent_prices)
    price_high_idx = np.argmax(recent_prices)
    
    bullish_div = False
    bearish_div = False
    
    # Bullish divergence: price making lower low, indicator making higher low
    if price_low_idx < lookback - 5:  # Not at the very end
        later_prices = recent_prices[price_low_idx:]
        later_indicators = recent_indicator[price_low_idx:]
        
        if len(later_prices) > 0:
            if min(later_prices) > recent_prices[price_low_idx] * 0.98:
                if min(later_indicators) > recent_indicator[price_low_idx]:
                    bullish_div = True
    
    # Bearish divergence: price making higher high, indicator making lower high
    if price_high_idx < lookback - 5:
        later_prices = recent_prices[price_high_idx:]
        later_indicators = recent_indicator[price_high_idx:]
        
        if len(later_prices) > 0:
            if max(later_prices) < recent_prices[price_high_idx] * 1.02:
                if max(later_indicators) < recent_indicator[price_high_idx]:
                    bearish_div = True
    
    return {
        'bullish': bullish_div,
        'bearish': bearish_div,
        'hidden_bullish': False,  # Placeholder for hidden divergence
        'hidden_bearish': False
    }
