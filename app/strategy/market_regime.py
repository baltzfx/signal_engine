"""
Market Regime Detection
Determines if market is trending, ranging, or volatile
"""
import logging
from typing import Dict, List
import numpy as np

logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """Detect current market regime/condition"""
    
    def detect_regime(
        self,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float]
    ) -> Dict:
        """
        Detect market regime based on price action
        
        Returns:
            Dict with regime type and characteristics
        """
        if len(prices) < 50:
            return self._default_regime()
        
        # Calculate trend strength
        trend_strength = self._calculate_trend_strength(prices)
        
        # Calculate ranging score
        ranging_score = self._calculate_ranging_score(highs, lows, prices)
        
        # Calculate volatility
        volatility = self._calculate_volatility(prices)
        
        # Determine regime
        if trend_strength > 0.6:
            regime = 'trending_up'
            confidence = trend_strength
        elif trend_strength < -0.6:
            regime = 'trending_down'
            confidence = abs(trend_strength)
        elif ranging_score > 0.7:
            regime = 'ranging'
            confidence = ranging_score
        elif volatility > 0.8:
            regime = 'volatile'
            confidence = volatility
        else:
            regime = 'transitional'
            confidence = 0.5
        
        return {
            'regime': regime,
            'confidence': round(confidence, 2),
            'trend_strength': round(trend_strength, 2),
            'ranging_score': round(ranging_score, 2),
            'volatility': round(volatility, 2),
            'favorable_for_signals': self._is_favorable(regime)
        }
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """
        Calculate trend strength using linear regression slope
        Returns: -1 (strong down) to +1 (strong up)
        """
        recent = prices[-50:]
        x = np.arange(len(recent))
        
        # Linear regression
        slope, _ = np.polyfit(x, recent, 1)
        
        # Normalize slope
        avg_price = np.mean(recent)
        normalized_slope = (slope * len(recent)) / avg_price
        
        # Clamp to [-1, 1]
        return max(-1, min(1, normalized_slope))
    
    def _calculate_ranging_score(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> float:
        """
        Calculate ranging score (0 to 1)
        High score = price bouncing between well-defined levels
        """
        recent_highs = highs[-50:]
        recent_lows = lows[-50:]
        recent_closes = closes[-50:]
        
        # Calculate range
        max_high = max(recent_highs)
        min_low = min(recent_lows)
        range_size = max_high - min_low
        
        if range_size == 0:
            return 0
        
        # Check how many times price touched top/bottom of range
        top_touches = sum(1 for h in recent_highs if h > max_high * 0.98)
        bottom_touches = sum(1 for l in recent_lows if l < min_low * 1.02)
        
        # Check price distribution (should be spread out in ranging)
        price_std = np.std(recent_closes)
        price_mean = np.mean(recent_closes)
        coefficient_of_variation = price_std / price_mean if price_mean > 0 else 0
        
        # Ranging score increases with touches and moderate CV
        touch_score = min(1, (top_touches + bottom_touches) / 20)
        cv_score = 1 - abs(coefficient_of_variation - 0.02) / 0.05
        
        return (touch_score + cv_score) / 2
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """
        Calculate volatility score (0 to 1)
        Based on price changes and standard deviation
        """
        recent = prices[-30:]
        
        # Calculate returns
        returns = [abs(recent[i] - recent[i-1]) / recent[i-1] 
                  for i in range(1, len(recent))]
        
        # Average absolute return
        avg_return = np.mean(returns)
        
        # Normalize (2% avg return = volatility of 1)
        volatility = min(1, avg_return / 0.02)
        
        return volatility
    
    def _is_favorable(self, regime: str) -> bool:
        """Check if regime is favorable for trading signals"""
        # Trending markets are best for trend-following strategies
        # Avoid ranging and highly volatile markets
        return regime in ['trending_up', 'trending_down']
    
    def _default_regime(self) -> Dict:
        """Default regime when insufficient data"""
        return {
            'regime': 'unknown',
            'confidence': 0,
            'trend_strength': 0,
            'ranging_score': 0,
            'volatility': 0,
            'favorable_for_signals': False
        }
