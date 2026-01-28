"""
Signal Validator
Validates signal data structure and prevents duplicate signals
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from config.constants import SIGNAL_LONG, SIGNAL_SHORT

logger = logging.getLogger(__name__)


class SignalValidator:
    """Validate and deduplicate signals"""
    
    def __init__(self):
        self.recent_signals: List[Dict] = []
        self.dedup_window_minutes = 60  # Don't send duplicate signal within 1 hour
    
    def validate(self, signal: Dict) -> bool:
        """
        Validate signal structure and data
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['symbol', 'type', 'price', 'confidence', 'timestamp']
        
        # Check required fields
        for field in required_fields:
            if field not in signal:
                logger.error(f"Signal missing required field: {field}")
                return False
        
        # Validate signal type
        if signal['type'] not in [SIGNAL_LONG, SIGNAL_SHORT]:
            logger.error(f"Invalid signal type: {signal['type']}")
            return False
        
        # Validate price
        if not isinstance(signal['price'], (int, float)) or signal['price'] <= 0:
            logger.error(f"Invalid price: {signal['price']}")
            return False
        
        # Validate confidence
        confidence = signal['confidence']
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 100:
            logger.error(f"Invalid confidence: {confidence}")
            return False
        
        return True
    
    def is_duplicate(self, signal: Dict) -> bool:
        """
        Check if this signal is a duplicate of a recent signal
        
        Duplicate = same symbol + same direction within time window
        """
        current_time = datetime.fromisoformat(signal['timestamp'])
        cutoff_time = current_time - timedelta(minutes=self.dedup_window_minutes)
        
        # Clean up old signals
        self.recent_signals = [
            s for s in self.recent_signals
            if datetime.fromisoformat(s['timestamp']) > cutoff_time
        ]
        
        # Check for duplicate
        for recent in self.recent_signals:
            if (recent['symbol'] == signal['symbol'] and 
                recent['type'] == signal['type']):
                logger.info(
                    f"Duplicate signal detected for {signal['symbol']} "
                    f"{signal['type']} (within {self.dedup_window_minutes} min)"
                )
                return True
        
        # Add to recent signals
        self.recent_signals.append(signal)
        return False
    
    def check_signal(self, signal: Dict) -> bool:
        """
        Full signal check: validate structure and check for duplicates
        
        Returns:
            True if signal is valid and not duplicate
        """
        if not self.validate(signal):
            return False
        
        if self.is_duplicate(signal):
            return False
        
        return True
