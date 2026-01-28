"""
Enhanced Multi-Factor Strategy
Combines multiple indicators, regime detection, and S/R levels
for higher quality signals
"""
import logging
from typing import Optional, Dict, List

from data.binance_client import BinanceClient
from indicators.ema import get_ema_signals
from indicators.rsi import get_rsi_signals
from indicators.volume import get_volume_signals
from indicators.atr import get_atr_signals
from indicators.advanced import calculate_macd, calculate_bollinger_bands, calculate_stochastic, detect_divergence
from strategy.market_regime import MarketRegimeDetector
from strategy.support_resistance import SupportResistanceDetector
from config.constants import SIGNAL_LONG, SIGNAL_SHORT, SIGNAL_NEUTRAL

logger = logging.getLogger(__name__)


class EnhancedStrategy:
    """
    Advanced multi-factor strategy with:
    - Multi-timeframe confirmation
    - Market regime filtering
    - Support/Resistance awareness
    - Multiple indicator confluence
    - Divergence detection
    """
    
    def __init__(self):
        self.client = BinanceClient()
        self.regime_detector = MarketRegimeDetector()
        self.sr_detector = SupportResistanceDetector()
    
    async def analyze(self, symbol: str) -> Optional[Dict]:
        """Enhanced analysis with multiple confirmation factors"""
        try:
            # Fetch OHLCV data
            ohlcv_1h = await self.client.fetch_ohlcv(symbol, '1h', limit=200)
            ohlcv_4h = await self.client.fetch_ohlcv(symbol, '4h', limit=200)
            
            if not ohlcv_1h or not ohlcv_4h:
                return None
            
            # Extract data
            closes_1h = [c[4] for c in ohlcv_1h]
            highs_1h = [c[2] for c in ohlcv_1h]
            lows_1h = [c[3] for c in ohlcv_1h]
            volumes_1h = [c[5] for c in ohlcv_1h]
            
            closes_4h = [c[4] for c in ohlcv_4h]
            highs_4h = [c[2] for c in ohlcv_4h]
            lows_4h = [c[3] for c in ohlcv_4h]
            volumes_4h = [c[5] for c in ohlcv_4h]
            
            # Market regime check
            regime = self.regime_detector.detect_regime(closes_1h, highs_1h, lows_1h, volumes_1h)
            
            # Skip if unfavorable regime
            if not regime['favorable_for_signals']:
                logger.debug(f"{symbol}: Unfavorable regime - {regime['regime']}")
                return None
            
            # Calculate all indicators for 1H
            ema_1h = get_ema_signals(closes_1h)
            rsi_1h = get_rsi_signals(closes_1h)
            volume_1h = get_volume_signals(volumes_1h)
            atr_1h = get_atr_signals(highs_1h, lows_1h, closes_1h)
            macd_1h = calculate_macd(closes_1h)
            bb_1h = calculate_bollinger_bands(closes_1h)
            stoch_1h = calculate_stochastic(highs_1h, lows_1h, closes_1h)
            
            # Calculate indicators for 4H
            ema_4h = get_ema_signals(closes_4h)
            rsi_4h = get_rsi_signals(closes_4h)
            volume_4h = get_volume_signals(volumes_4h)
            macd_4h = calculate_macd(closes_4h)
            
            # Support/Resistance
            sr_levels = self.sr_detector.find_levels(highs_1h, lows_1h, closes_1h)
            
            # Divergence detection
            rsi_values = [50] * (200 - len(closes_1h)) + [50] * len(closes_1h)  # Placeholder
            divergence = detect_divergence(closes_1h, rsi_values[-50:])
            
            # Generate signal
            signal_type = self._generate_enhanced_signal(
                ema_1h, rsi_1h, volume_1h, atr_1h, macd_1h, bb_1h, stoch_1h,
                ema_4h, rsi_4h, volume_4h, macd_4h,
                regime, sr_levels, divergence
            )
            
            if signal_type == SIGNAL_NEUTRAL:
                return None
            
            current_price = closes_1h[-1]
            
            # Calculate dynamic stop loss and take profit
            stop_loss, take_profit = self._calculate_dynamic_levels(
                signal_type, current_price, atr_1h, sr_levels
            )
            
            return {
                'symbol': symbol,
                'type': signal_type,
                'price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_reward_ratio': abs((take_profit - current_price) / (current_price - stop_loss)),
                'timeframe_1h': {
                    'ema': ema_1h,
                    'rsi': rsi_1h,
                    'volume': volume_1h,
                    'atr': atr_1h,
                    'macd': macd_1h,
                    'bollinger': bb_1h,
                    'stochastic': stoch_1h
                },
                'timeframe_4h': {
                    'ema': ema_4h,
                    'rsi': rsi_4h,
                    'volume': volume_4h,
                    'macd': macd_4h
                },
                'market_regime': regime,
                'support_resistance': sr_levels,
                'divergence': divergence
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
            return None
    
    def _generate_enhanced_signal(
        self, ema_1h, rsi_1h, volume_1h, atr_1h, macd_1h, bb_1h, stoch_1h,
        ema_4h, rsi_4h, volume_4h, macd_4h,
        regime, sr_levels, divergence
    ) -> str:
        """
        Generate signal using multiple confirmation factors
        Requires strong confluence across indicators
        """
        
        # LONG signal criteria
        long_signals = [
            # Trend alignment
            regime['regime'] == 'trending_up' and regime['confidence'] > 0.6,
            ema_4h.get('trend_up', False),
            ema_1h.get('bullish_cross', False) or ema_1h.get('trend_up', False),
            
            # Momentum
            20 < rsi_1h.get('rsi', 50) < 65,  # Not overbought, some momentum
            macd_1h.get('bullish_cross', False) or macd_1h.get('positive', False),
            stoch_1h.get('k', 50) < 80 and not stoch_1h.get('overbought', False),
            
            # Volume confirmation
            volume_1h.get('volume_spike', False) or volume_1h.get('above_average', False),
            
            # Bollinger Bands (price bouncing from lower band)
            bb_1h.get('near_lower', False) or (0.2 < bb_1h.get('percent_b', 0.5) < 0.6),
            
            # Support/Resistance (near support or bouncing)
            sr_levels.get('near_support', False) or not sr_levels.get('near_resistance', False),
            
            # Divergence (bullish divergence is a plus)
            divergence.get('bullish', False) or not divergence.get('bearish', False),
        ]
        
        # SHORT signal criteria
        short_signals = [
            # Trend alignment
            regime['regime'] == 'trending_down' and regime['confidence'] > 0.6,
            ema_4h.get('trend_down', False),
            ema_1h.get('bearish_cross', False) or ema_1h.get('trend_down', False),
            
            # Momentum
            35 < rsi_1h.get('rsi', 50) < 80,  # Not oversold
            macd_1h.get('bearish_cross', False) or not macd_1h.get('positive', False),
            stoch_1h.get('k', 50) > 20 and not stoch_1h.get('oversold', False),
            
            # Volume confirmation
            volume_1h.get('volume_spike', False) or volume_1h.get('above_average', False),
            
            # Bollinger Bands (price near upper band)
            bb_1h.get('near_upper', False) or (0.4 < bb_1h.get('percent_b', 0.5) < 0.8),
            
            # Support/Resistance (near resistance or rejected)
            sr_levels.get('near_resistance', False) or not sr_levels.get('near_support', False),
            
            # Divergence
            divergence.get('bearish', False) or not divergence.get('bullish', False),
        ]
        
        # Require strong confluence: at least 7 out of 10 conditions
        long_score = sum(long_signals)
        short_score = sum(short_signals)
        
        logger.debug(f"Signal scores - Long: {long_score}/10, Short: {short_score}/10")
        
        if long_score >= 7 and long_score > short_score:
            return SIGNAL_LONG
        elif short_score >= 7 and short_score > long_score:
            return SIGNAL_SHORT
        else:
            return SIGNAL_NEUTRAL
    
    def _calculate_dynamic_levels(
        self,
        signal_type: str,
        current_price: float,
        atr: Dict,
        sr_levels: Dict
    ) -> tuple:
        """
        Calculate dynamic stop loss and take profit using ATR and S/R levels
        """
        atr_value = atr.get('atr', current_price * 0.02)
        stop_mult = atr.get('stop_multiplier', 2.0)
        target_mult = atr.get('target_multiplier', 3.0)
        
        if signal_type == SIGNAL_LONG:
            # Stop loss below entry
            stop_loss = current_price - (atr_value * stop_mult)
            
            # Use S/R for stop if closer
            if sr_levels.get('nearest_support'):
                sr_stop = sr_levels['nearest_support'] * 0.995  # Just below support
                if sr_stop > stop_loss and sr_stop < current_price:
                    stop_loss = sr_stop
            
            # Take profit above entry
            take_profit = current_price + (atr_value * target_mult)
            
            # Use resistance as target if reasonable
            if sr_levels.get('nearest_resistance'):
                sr_target = sr_levels['nearest_resistance'] * 0.995  # Just before resistance
                if sr_target > current_price and sr_target < take_profit * 1.2:
                    take_profit = sr_target
        
        else:  # SHORT
            # Stop loss above entry
            stop_loss = current_price + (atr_value * stop_mult)
            
            # Use resistance for stop
            if sr_levels.get('nearest_resistance'):
                sr_stop = sr_levels['nearest_resistance'] * 1.005
                if sr_stop < stop_loss and sr_stop > current_price:
                    stop_loss = sr_stop
            
            # Take profit below entry
            take_profit = current_price - (atr_value * target_mult)
            
            # Use support as target
            if sr_levels.get('nearest_support'):
                sr_target = sr_levels['nearest_support'] * 1.005
                if sr_target < current_price and sr_target > take_profit * 0.8:
                    take_profit = sr_target
        
        return round(stop_loss, 2), round(take_profit, 2)
