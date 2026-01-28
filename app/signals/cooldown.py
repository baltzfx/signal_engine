"""
Signal Cooldown Manager
Prevents duplicate signals for the same symbol within a timeframe
"""
import logging
from typing import Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SignalCooldown:
    """Manage signal cooldown periods per symbol"""
    
    def __init__(self, cooldown_hours: int = 4):
        """
        Args:
            cooldown_hours: Hours to wait before allowing another signal for same symbol+direction
        """
        self.cooldown_hours = cooldown_hours
        self.last_signals: Dict[str, datetime] = {}
    
    def can_signal(self, symbol: str, signal_type: str) -> bool:
        """
        Check if enough time has passed since last signal
        
        Args:
            symbol: Trading pair
            signal_type: LONG or SHORT
            
        Returns:
            True if signal is allowed
        """
        key = f"{symbol}:{signal_type}"
        
        if key not in self.last_signals:
            return True
        
        last_time = self.last_signals[key]
        time_passed = datetime.utcnow() - last_time
        cooldown_period = timedelta(hours=self.cooldown_hours)
        
        if time_passed < cooldown_period:
            remaining = cooldown_period - time_passed
            logger.info(
                f"Signal cooldown active for {symbol} {signal_type}: "
                f"{remaining.seconds // 3600}h {(remaining.seconds % 3600) // 60}m remaining"
            )
            return False
        
        return True
    
    def register_signal(self, symbol: str, signal_type: str) -> None:
        """Register that a signal was sent"""
        key = f"{symbol}:{signal_type}"
        self.last_signals[key] = datetime.utcnow()
        logger.debug(f"Registered signal cooldown for {key}")
    
    def reset(self, symbol: str = None) -> None:
        """Reset cooldown for a symbol or all symbols"""
        if symbol:
            self.last_signals = {
                k: v for k, v in self.last_signals.items()
                if not k.startswith(symbol)
            }
        else:
            self.last_signals.clear()
