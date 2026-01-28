"""
Support and Resistance Level Detection
Identifies key price levels for better entry timing
"""
import logging
from typing import List, Dict, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class SupportResistanceDetector:
    """Detect support and resistance levels"""
    
    def find_levels(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        lookback: int = 100
    ) -> Dict:
        """
        Find key support and resistance levels
        
        Returns:
            Dict with support/resistance levels and current position
        """
        if len(closes) < lookback:
            return {
                'support_levels': [],
                'resistance_levels': [],
                'near_support': False,
                'near_resistance': False,
                'at_key_level': False
            }
        
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        current_price = closes[-1]
        
        # Find swing highs and lows
        resistance_levels = self._find_swing_highs(recent_highs)
        support_levels = self._find_swing_lows(recent_lows)
        
        # Find nearest levels
        nearest_support = self._find_nearest_below(support_levels, current_price)
        nearest_resistance = self._find_nearest_above(resistance_levels, current_price)
        
        # Check proximity to levels
        near_support = False
        near_resistance = False
        
        if nearest_support:
            distance_pct = ((current_price - nearest_support) / current_price) * 100
            near_support = distance_pct < 1.5  # Within 1.5%
        
        if nearest_resistance:
            distance_pct = ((nearest_resistance - current_price) / current_price) * 100
            near_resistance = distance_pct < 1.5
        
        return {
            'support_levels': sorted(support_levels)[:5],  # Top 5 support
            'resistance_levels': sorted(resistance_levels, reverse=True)[:5],  # Top 5 resistance
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'near_support': near_support,
            'near_resistance': near_resistance,
            'at_key_level': near_support or near_resistance,
            'support_strength': self._calculate_level_strength(support_levels, current_price),
            'resistance_strength': self._calculate_level_strength(resistance_levels, current_price)
        }
    
    def _find_swing_highs(self, highs: List[float], window: int = 5) -> List[float]:
        """Find swing high points"""
        swing_highs = []
        
        for i in range(window, len(highs) - window):
            is_swing_high = True
            current = highs[i]
            
            # Check if this is the highest point in the window
            for j in range(i - window, i + window + 1):
                if j != i and highs[j] >= current:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append(current)
        
        # Cluster nearby levels
        return self._cluster_levels(swing_highs)
    
    def _find_swing_lows(self, lows: List[float], window: int = 5) -> List[float]:
        """Find swing low points"""
        swing_lows = []
        
        for i in range(window, len(lows) - window):
            is_swing_low = True
            current = lows[i]
            
            # Check if this is the lowest point in the window
            for j in range(i - window, i + window + 1):
                if j != i and lows[j] <= current:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append(current)
        
        return self._cluster_levels(swing_lows)
    
    def _cluster_levels(self, levels: List[float], threshold: float = 0.02) -> List[float]:
        """
        Cluster nearby levels together
        threshold: levels within this percent are considered the same
        """
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clustered = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if level is close to last clustered level
            if abs(level - clustered[-1]) / clustered[-1] > threshold:
                clustered.append(level)
        
        return clustered
    
    def _find_nearest_below(self, levels: List[float], price: float) -> float:
        """Find nearest level below current price"""
        below = [l for l in levels if l < price]
        return max(below) if below else None
    
    def _find_nearest_above(self, levels: List[float], price: float) -> float:
        """Find nearest level above current price"""
        above = [l for l in levels if l > price]
        return min(above) if above else None
    
    def _calculate_level_strength(self, levels: List[float], current_price: float) -> float:
        """
        Calculate strength of nearest level
        More touches = stronger level
        """
        nearest = None
        distance = float('inf')
        
        for level in levels:
            dist = abs(level - current_price)
            if dist < distance:
                distance = dist
                nearest = level
        
        if nearest is None:
            return 0
        
        # Count how many times price tested this level (within 1%)
        touches = sum(1 for l in levels if abs(l - nearest) / nearest < 0.01)
        
        # Normalize to 0-1 scale
        return min(1, touches / 3)
