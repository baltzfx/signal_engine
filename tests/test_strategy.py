"""
Unit Tests for Trading Strategy
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.strategy.trend_1h_4h import Trend1H4HStrategy
from app.strategy.filters import SignalFilters
from app.config.constants import SIGNAL_LONG, SIGNAL_SHORT, SIGNAL_NEUTRAL


class TestTrend1H4HStrategy:
    """Test multi-timeframe trend strategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create strategy instance"""
        return Trend1H4HStrategy()
    
    def test_signal_generation_logic(self, strategy):
        """Test signal generation logic"""
        # Mock bullish scenario
        ema_1h = {
            'trend_up': True,
            'bullish_cross': True,
            'bearish_cross': False
        }
        rsi_1h = {'rsi': 55}
        volume_1h = {'volume_spike': True, 'above_average': True}
        
        ema_4h = {
            'trend_up': True,
            'trend_down': False
        }
        rsi_4h = {'rsi': 60}
        volume_4h = {'above_average': True}
        
        signal_type = strategy._generate_signal(
            ema_1h, rsi_1h, volume_1h,
            ema_4h, rsi_4h, volume_4h
        )
        
        assert signal_type == SIGNAL_LONG
    
    def test_bearish_signal(self, strategy):
        """Test bearish signal generation"""
        ema_1h = {
            'trend_down': True,
            'bullish_cross': False,
            'bearish_cross': True
        }
        rsi_1h = {'rsi': 45}
        volume_1h = {'volume_spike': True, 'above_average': True}
        
        ema_4h = {
            'trend_up': False,
            'trend_down': True
        }
        rsi_4h = {'rsi': 40}
        volume_4h = {'above_average': True}
        
        signal_type = strategy._generate_signal(
            ema_1h, rsi_1h, volume_1h,
            ema_4h, rsi_4h, volume_4h
        )
        
        assert signal_type == SIGNAL_SHORT
    
    def test_neutral_signal(self, strategy):
        """Test neutral (no signal) when conditions not met"""
        ema_1h = {
            'trend_up': False,
            'bullish_cross': False,
            'bearish_cross': False
        }
        rsi_1h = {'rsi': 50}
        volume_1h = {'volume_spike': False, 'above_average': False}
        
        ema_4h = {
            'trend_up': False,
            'trend_down': False
        }
        rsi_4h = {'rsi': 50}
        volume_4h = {'above_average': False}
        
        signal_type = strategy._generate_signal(
            ema_1h, rsi_1h, volume_1h,
            ema_4h, rsi_4h, volume_4h
        )
        
        assert signal_type == SIGNAL_NEUTRAL


class TestSignalFilters:
    """Test signal quality filters"""
    
    @pytest.fixture
    def filters(self):
        """Create filters instance"""
        return SignalFilters()
    
    @pytest.mark.asyncio
    async def test_liquidity_filter_pass(self, filters):
        """Test liquidity filter passes with high volume"""
        with patch.object(filters.client, 'fetch_24h_volume', 
                         return_value=2000000):
            result = await filters.check_liquidity('BTCUSDT')
            assert result is True
    
    @pytest.mark.asyncio
    async def test_liquidity_filter_fail(self, filters):
        """Test liquidity filter fails with low volume"""
        with patch.object(filters.client, 'fetch_24h_volume', 
                         return_value=100000):
            result = await filters.check_liquidity('LOWVOLUMEUSDT')
            assert result is False
    
    @pytest.mark.asyncio
    async def test_spread_filter(self, filters):
        """Test spread filter logic"""
        mock_orderbook = {
            'bids': [[99.95, 10]],
            'asks': [[100.05, 10]]
        }
        
        with patch.object(filters.client, 'fetch_orderbook',
                         return_value=mock_orderbook):
            result = await filters.check_spread('BTCUSDT')
            # Spread is (100.05-99.95)/100 = 0.1%
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
