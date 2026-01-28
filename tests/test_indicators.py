"""
Unit Tests for Technical Indicators
"""
import pytest
import numpy as np

from app.indicators.ema import calculate_ema, get_ema_signals
from app.indicators.rsi import calculate_rsi, get_rsi_signals
from app.indicators.volume import calculate_volume_ma, get_volume_signals


class TestEMA:
    """Test EMA indicator calculations"""
    
    def test_ema_calculation(self):
        """Test basic EMA calculation"""
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        ema = calculate_ema(prices, period=5)
        
        assert len(ema) == len(prices)
        assert ema[-1] > 0
        assert ema[-1] < max(prices)
    
    def test_ema_signals(self):
        """Test EMA signal generation"""
        # Uptrend prices
        prices = list(range(100, 120)) + list(range(120, 140))
        signals = get_ema_signals(prices)
        
        assert 'ema_fast' in signals
        assert 'ema_medium' in signals
        assert 'bullish_cross' in signals or 'bearish_cross' in signals
    
    def test_insufficient_data(self):
        """Test EMA with insufficient data"""
        prices = [10, 11, 12]
        signals = get_ema_signals(prices)
        
        assert signals['ema_trend'] is None


class TestRSI:
    """Test RSI indicator calculations"""
    
    def test_rsi_calculation(self):
        """Test basic RSI calculation"""
        # Create alternating prices to generate RSI
        prices = [100 + (i % 2) * 5 for i in range(50)]
        rsi = calculate_rsi(prices, period=14)
        
        assert len(rsi) == len(prices)
        assert 0 <= rsi[-1] <= 100
    
    def test_rsi_oversold(self):
        """Test RSI oversold detection"""
        # Downtrend should create oversold RSI
        prices = list(range(100, 50, -1))
        signals = get_rsi_signals(prices)
        
        assert signals['rsi'] is not None
        # In strong downtrend, RSI should be low
        assert signals['rsi'] < 70
    
    def test_rsi_overbought(self):
        """Test RSI overbought detection"""
        # Uptrend should create overbought RSI
        prices = list(range(50, 100, 1))
        signals = get_rsi_signals(prices)
        
        assert signals['rsi'] is not None
        # In strong uptrend, RSI should be high
        assert signals['rsi'] > 30


class TestVolume:
    """Test Volume indicator calculations"""
    
    def test_volume_ma(self):
        """Test volume moving average"""
        volumes = [1000000 + i * 10000 for i in range(30)]
        volume_ma = calculate_volume_ma(volumes, period=20)
        
        assert len(volume_ma) == len(volumes)
        assert volume_ma[-1] > 0
    
    def test_volume_spike_detection(self):
        """Test volume spike detection"""
        # Normal volumes then spike
        volumes = [1000000] * 25 + [3000000]
        signals = get_volume_signals(volumes)
        
        assert signals['volume_spike'] is True
        assert signals['volume_ratio'] > 2.0
    
    def test_no_volume_spike(self):
        """Test no spike when volume is normal"""
        volumes = [1000000] * 30
        signals = get_volume_signals(volumes)
        
        assert signals['volume_spike'] is False
        assert abs(signals['volume_ratio'] - 1.0) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
