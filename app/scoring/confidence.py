"""
⭐ Enhanced Confidence Scoring System
Calculates a confidence score (0-100) for each signal based on multiple factors
Now includes: regime, S/R levels, divergence, and multi-indicator confluence
"""
import logging
from typing import Dict

from config.constants import (
    WEIGHT_TREND, WEIGHT_MOMENTUM, WEIGHT_VOLUME, 
    WEIGHT_LIQUIDITY, WEIGHT_FUNDING, SIGNAL_LONG, SIGNAL_SHORT
)
from config.settings import settings

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculate enhanced confidence scores for trading signals"""
    
    def calculate_score(
        self,
        signal_type: str,
        timeframe_1h: Dict,
        timeframe_4h: Dict,
        filters: Dict,
        regime: Dict = None,
        sr_levels: Dict = None,
        divergence: Dict = None
    ) -> float:
        """
        Calculate overall confidence score (0-100)
        
        Args:
            signal_type: LONG or SHORT
            timeframe_1h: 1H indicators dict
            timeframe_4h: 4H indicators dict
            filters: Filter results dict
            regime: Market regime dict (optional)
            sr_levels: Support/Resistance dict (optional)
            divergence: Divergence signals dict (optional)
            
        Returns:
            Confidence score between 0-100
        """
        scores = {
            'trend': self._score_trend(signal_type, timeframe_1h, timeframe_4h),
            'momentum': self._score_momentum(signal_type, timeframe_1h, timeframe_4h),
            'volume': self._score_volume(timeframe_1h, timeframe_4h),
            'liquidity': self._score_liquidity(filters),
            'funding': self._score_funding(filters),
            'regime': self._score_regime(signal_type, regime) if regime else 50,
            'sr_alignment': self._score_sr_alignment(signal_type, sr_levels) if sr_levels else 50,
            'divergence': self._score_divergence(signal_type, divergence) if divergence else 50,
            'confluence': self._score_confluence(signal_type, timeframe_1h)
        }
        
        # Enhanced weighted average with new factors
        total_score = (
            scores['trend'] * 0.20 +
            scores['momentum'] * 0.15 +
            scores['volume'] * 0.15 +
            scores['liquidity'] * 0.10 +
            scores['funding'] * 0.05 +
            scores['regime'] * 0.15 +
            scores['sr_alignment'] * 0.10 +
            scores['divergence'] * 0.05 +
            scores['confluence'] * 0.05
        )
        
        logger.debug(f"Enhanced confidence breakdown: {scores} -> Total: {total_score:.1f}")
        
        return round(total_score, 1)
    
    def _score_trend(self, signal_type: str, tf_1h: Dict, tf_4h: Dict) -> float:
        """
        Score trend alignment (0-100)
        Higher score when trends align across timeframes
        """
        score = 0
        ema_1h = tf_1h.get('ema', {})
        ema_4h = tf_4h.get('ema', {})
        
        if signal_type == SIGNAL_LONG:
            # Check bullish alignment
            if ema_4h.get('trend_up'):
                score += 50
            if ema_1h.get('trend_up'):
                score += 30
            if ema_1h.get('bullish_cross'):
                score += 20
                
        elif signal_type == SIGNAL_SHORT:
            # Check bearish alignment
            if ema_4h.get('trend_down'):
                score += 50
            if ema_1h.get('trend_down'):
                score += 30
            if ema_1h.get('bearish_cross'):
                score += 20
        
        return min(score, 100)
    
    def _score_momentum(self, signal_type: str, tf_1h: Dict, tf_4h: Dict) -> float:
        """
        Score momentum strength using RSI (0-100)
        """
        score = 0
        rsi_1h = tf_1h.get('rsi', {})
        rsi_4h = tf_4h.get('rsi', {})
        
        rsi_val_1h = rsi_1h.get('rsi', 50)
        rsi_val_4h = rsi_4h.get('rsi', 50)
        
        if signal_type == SIGNAL_LONG:
            # Prefer RSI in bullish zone (40-60) not overbought
            if 40 <= rsi_val_1h <= 60:
                score += 40
            elif rsi_val_1h < 40:
                score += 30  # Oversold can be good for longs
            
            if 40 <= rsi_val_4h <= 60:
                score += 40
            elif rsi_val_4h < 40:
                score += 30
                
        elif signal_type == SIGNAL_SHORT:
            # Prefer RSI in bearish zone (40-60) not oversold
            if 40 <= rsi_val_1h <= 60:
                score += 40
            elif rsi_val_1h > 60:
                score += 30  # Overbought can be good for shorts
            
            if 40 <= rsi_val_4h <= 60:
                score += 40
            elif rsi_val_4h > 60:
                score += 30
        
        return min(score, 100)
    
    def _score_volume(self, tf_1h: Dict, tf_4h: Dict) -> float:
        """
        Score volume confirmation (0-100)
        Higher score for volume spikes and increasing volume
        """
        score = 0
        vol_1h = tf_1h.get('volume', {})
        vol_4h = tf_4h.get('volume', {})
        
        # 1H volume
        if vol_1h.get('volume_spike'):
            score += 40
        elif vol_1h.get('above_average'):
            score += 25
        
        if vol_1h.get('increasing_volume'):
            score += 20
        
        # 4H volume
        if vol_4h.get('volume_spike'):
            score += 25
        elif vol_4h.get('above_average'):
            score += 15
        
        return min(score, 100)
    
    def _score_liquidity(self, filters: Dict) -> float:
        """
        Score liquidity quality (0-100)
        Based on filter results
        """
        passed_liquidity = filters.get('liquidity', False)
        passed_spread = filters.get('spread', False)
        
        score = 0
        if passed_liquidity:
            score += 60
        if passed_spread:
            score += 40
        
        return score
    
    def _score_regime(self, signal_type: str, regime: Dict) -> float:
        """Score based on market regime alignment"""
        regime_type = regime.get('regime', 'unknown')
        confidence = regime.get('confidence', 0)
        
        if signal_type == SIGNAL_LONG:
            if regime_type == 'trending_up':
                return 100 * confidence
            elif regime_type == 'trending_down':
                return 20
            else:
                return 40
        else:  # SHORT
            if regime_type == 'trending_down':
                return 100 * confidence
            elif regime_type == 'trending_up':
                return 20
            else:
                return 40
    
    def _score_sr_alignment(self, signal_type: str, sr_levels: Dict) -> float:
        """Score based on support/resistance alignment"""
        score = 50  # Base score
        
        if signal_type == SIGNAL_LONG:
            # Good: near support, bad: near resistance
            if sr_levels.get('near_support', False):
                score += 40
            if sr_levels.get('near_resistance', False):
                score -= 30
            
            # Bonus for strong support
            support_strength = sr_levels.get('support_strength', 0)
            score += support_strength * 10
            
        else:  # SHORT
            # Good: near resistance, bad: near support
            if sr_levels.get('near_resistance', False):
                score += 40
            if sr_levels.get('near_support', False):
                score -= 30
            
            # Bonus for strong resistance
            resistance_strength = sr_levels.get('resistance_strength', 0)
            score += resistance_strength * 10
        
        return max(0, min(100, score))
    
    def _score_divergence(self, signal_type: str, divergence: Dict) -> float:
        """Score based on divergence signals"""
        if signal_type == SIGNAL_LONG:
            if divergence.get('bullish', False):
                return 100  # Strong bullish confirmation
            elif divergence.get('bearish', False):
                return 20  # Conflicting signal
            else:
                return 50  # Neutral
        else:  # SHORT
            if divergence.get('bearish', False):
                return 100
            elif divergence.get('bullish', False):
                return 20
            else:
                return 50
    
    def _score_confluence(self, signal_type: str, timeframe_1h: Dict) -> float:
        """
        Score based on multi-indicator confluence
        More indicators agreeing = higher score
        """
        agreements = 0
        total_indicators = 0
        
        # Check MACD
        macd = timeframe_1h.get('macd', {})
        if signal_type == SIGNAL_LONG:
            if macd.get('bullish_cross', False) or macd.get('positive', False):
                agreements += 1
        else:
            if macd.get('bearish_cross', False) or not macd.get('positive', False):
                agreements += 1
        total_indicators += 1
        
        # Check Stochastic
        stoch = timeframe_1h.get('stochastic', {})
        if signal_type == SIGNAL_LONG:
            if stoch.get('oversold', False) or stoch.get('bullish_cross', False):
                agreements += 1
        else:
            if stoch.get('overbought', False) or stoch.get('bearish_cross', False):
                agreements += 1
        total_indicators += 1
        
        # Check Bollinger Bands
        bb = timeframe_1h.get('bollinger', {})
        if signal_type == SIGNAL_LONG:
            if bb.get('near_lower', False) or bb.get('oversold', False):
                agreements += 1
        else:
            if bb.get('near_upper', False) or bb.get('overbought', False):
                agreements += 1
        total_indicators += 1
        
        # Calculate confluence score
        if total_indicators > 0:
            confluence_ratio = agreements / total_indicators
            return confluence_ratio * 100
        
        return 50
        return score
    
    def _score_funding(self, filters: Dict) -> float:
        """
        Score funding rate quality (0-100)
        Neutral/acceptable funding is best
        """
        passed_funding = filters.get('funding', True)
        
        return 100 if passed_funding else 50
    
    def meets_threshold(self, score: float) -> bool:
        """Check if score meets minimum threshold"""
        return score >= settings.MIN_CONFIDENCE_SCORE
