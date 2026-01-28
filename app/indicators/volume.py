"""
Volume Analysis Indicators
"""
import numpy as np
from typing import List

from config.constants import VOLUME_MA_PERIOD
from config.settings import settings


def calculate_volume_ma(volumes: List[float], period: int = VOLUME_MA_PERIOD) -> List[float]:
    """
    Calculate Simple Moving Average of volume
    
    Args:
        volumes: List of volume values
        period: MA period
        
    Returns:
        List of volume MA values
    """
    volumes_array = np.array(volumes)
    volume_ma = np.zeros_like(volumes_array)
    
    for i in range(period - 1, len(volumes)):
        volume_ma[i] = np.mean(volumes_array[i - period + 1:i + 1])
    
    return volume_ma.tolist()


def get_volume_signals(volumes: List[float]) -> dict:
    """
    Analyze volume patterns and detect spikes
    
    Returns:
        Dict with volume metrics and signals
    """
    if len(volumes) < VOLUME_MA_PERIOD:
        return {
            'current_volume': volumes[-1] if volumes else 0,
            'volume_ma': None,
            'volume_spike': False,
            'volume_ratio': 1.0,
            'increasing_volume': False
        }
    
    volume_ma = calculate_volume_ma(volumes)
    current_volume = volumes[-1]
    avg_volume = volume_ma[-1]
    
    # Calculate volume ratio
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # Detect volume spike
    volume_spike = volume_ratio >= settings.VOLUME_SPIKE_MULTIPLIER
    
    # Check if volume is increasing over last 3 periods
    increasing_volume = False
    if len(volumes) >= 3:
        increasing_volume = volumes[-1] > volumes[-2] > volumes[-3]
    
    return {
        'current_volume': current_volume,
        'volume_ma': avg_volume,
        'volume_spike': volume_spike,
        'volume_ratio': volume_ratio,
        'increasing_volume': increasing_volume,
        'above_average': volume_ratio > 1.2,
        'below_average': volume_ratio < 0.8
    }


def calculate_obv(prices: List[float], volumes: List[float]) -> List[float]:
    """
    Calculate On-Balance Volume (OBV)
    
    Args:
        prices: List of closing prices
        volumes: List of volumes
        
    Returns:
        List of OBV values
    """
    if len(prices) != len(volumes) or len(prices) < 2:
        return [0] * len(prices)
    
    obv = [0]
    
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif prices[i] < prices[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    
    return obv
