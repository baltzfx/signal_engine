"""
Trend Strategy - 1H and 4H Timeframe Alignment
Generates signals based on multi-timeframe trend confirmation
"""
import logging
from typing import Optional, Dict, List

from data.binance_client import BinanceClient
from indicators.ema import get_ema_signals
from indicators.rsi import get_rsi_signals
from indicators.volume import get_volume_signals
from config.constants import SIGNAL_LONG, SIGNAL_SHORT, SIGNAL_NEUTRAL
from config.settings import settings

logger = logging.getLogger(__name__)


class Trend1H4HStrategy:
    """
    Multi-timeframe trend following strategy
    - Primary: 1H timeframe for entry signals
    - Confirmation: 4H timeframe for trend direction
    """
    
    def __init__(self):
        self.client = BinanceClient()
    
    async def analyze(self, symbol: str) -> Optional[Dict]:
        """
        Analyze symbol across multiple timeframes
        
        Returns:
            Signal dict or None if no signal
        """
        try:
            # Fetch data for both timeframes
            ohlcv_1h = await self.client.fetch_ohlcv(symbol, '1h', limit=200)
            ohlcv_4h = await self.client.fetch_ohlcv(symbol, '4h', limit=200)
            
            if not ohlcv_1h or not ohlcv_4h:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Extract prices and volumes
            prices_1h = [candle[4] for candle in ohlcv_1h]  # Close prices
            volumes_1h = [candle[5] for candle in ohlcv_1h]
            prices_4h = [candle[4] for candle in ohlcv_4h]
            volumes_4h = [candle[5] for candle in ohlcv_4h]
            
            # Calculate indicators for 1H
            ema_1h = get_ema_signals(prices_1h)
            rsi_1h = get_rsi_signals(prices_1h)
            volume_1h = get_volume_signals(volumes_1h)
            
            # Calculate indicators for 4H
            ema_4h = get_ema_signals(prices_4h)
            rsi_4h = get_rsi_signals(prices_4h)
            volume_4h = get_volume_signals(volumes_4h)
            
            # Determine signal
            signal_type = self._generate_signal(
                ema_1h, rsi_1h, volume_1h,
                ema_4h, rsi_4h, volume_4h
            )
            
            if signal_type == SIGNAL_NEUTRAL:
                return None
            
            current_price = prices_1h[-1]
            
            return {
                'symbol': symbol,
                'type': signal_type,
                'price': current_price,
                'timeframe_1h': {
                    'ema': ema_1h,
                    'rsi': rsi_1h,
                    'volume': volume_1h
                },
                'timeframe_4h': {
                    'ema': ema_4h,
                    'rsi': rsi_4h,
                    'volume': volume_4h
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
            return None
    
    def _generate_signal(
        self,
        ema_1h: Dict, rsi_1h: Dict, volume_1h: Dict,
        ema_4h: Dict, rsi_4h: Dict, volume_4h: Dict
    ) -> str:
        """
        Generate signal based on multi-timeframe analysis
        
        Logic:
        - LONG: Bullish trend on 4H + bullish setup on 1H
        - SHORT: Bearish trend on 4H + bearish setup on 1H
        """
        
        # Check 4H trend direction
        trend_4h_bullish = ema_4h.get('trend_up', False)
        trend_4h_bearish = ema_4h.get('trend_down', False)
        
        # Long signal conditions
        long_conditions = [
            trend_4h_bullish,  # 4H uptrend
            ema_1h.get('bullish_cross', False),  # 1H bullish EMA cross
            rsi_1h.get('rsi', 50) < 70,  # Not overbought
            volume_1h.get('volume_spike', False) or volume_1h.get('above_average', False)
        ]
        
        # Short signal conditions
        short_conditions = [
            trend_4h_bearish,  # 4H downtrend
            ema_1h.get('bearish_cross', False),  # 1H bearish EMA cross
            rsi_1h.get('rsi', 50) > 30,  # Not oversold
            volume_1h.get('volume_spike', False) or volume_1h.get('above_average', False)
        ]
        
        # Require at least 3 out of 4 conditions
        if sum(long_conditions) >= 3:
            return SIGNAL_LONG
        elif sum(short_conditions) >= 3:
            return SIGNAL_SHORT
        else:
            return SIGNAL_NEUTRAL
