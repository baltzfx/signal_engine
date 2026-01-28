"""
Open Signals Tracker
Tracks active signals and monitors their outcomes
Now uses SQLite database for persistence
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from config.constants import STATUS_OPEN, STATUS_CLOSED
from tracking.outcomes import OutcomeTracker
from database.repository import SignalRepository

logger = logging.getLogger(__name__)


class OpenSignalsTracker:
    """Track and persist open trading signals using SQLite"""
    
    def __init__(self):
        self.repo = SignalRepository()
        self.outcome_tracker = OutcomeTracker()
    
    async def save_signals(self, new_signals: List[Dict]) -> None:
        """Add new signals to tracking"""
        for signal in new_signals:
            self.repo.create_signal(signal)
        
        logger.info(f"Added {len(new_signals)} signals to tracking")
    
    async def update_outcomes(self) -> None:
        """Update outcomes for all open signals"""
        open_signals = self.repo.get_open_signals()
        
        if not open_signals:
            logger.debug("No open signals to update")
            return
        
        logger.info(f"Updating outcomes for {len(open_signals)} signals")
        
        updated_count = 0
        closed_count = 0
        
        for db_signal in open_signals:
            # Convert to dict for outcome tracker
            signal_dict = {
                'symbol': db_signal.symbol,
                'type': db_signal.signal_type,
                'price': db_signal.entry_price,
                'stop_loss': db_signal.stop_loss,
                'take_profit': db_signal.take_profit,
                'created_at': db_signal.created_at.isoformat(),
                'timestamp': db_signal.created_at.isoformat()
            }
            
            outcome = await self.outcome_tracker.evaluate_signal(signal_dict)
            
            if outcome:
                self.repo.update_signal_outcome(db_signal.id, outcome)
                updated_count += 1
                
                if outcome.get('should_close', False):
                    self.repo.close_signal(db_signal.id)
                    closed_count += 1
        
        logger.info(f"Updated {updated_count} signals, closed {closed_count} signals")
    
    def get_open_signals(self) -> List[Dict]:
        """Get all open signals"""
        db_signals = self.repo.get_open_signals()
        return [self._signal_to_dict(s) for s in db_signals]
    
    def get_closed_signals(self) -> List[Dict]:
        """Get all closed signals"""
        db_signals = self.repo.get_closed_signals()
        return [self._signal_to_dict(s) for s in db_signals]
    
    def cleanup_old_signals(self, days: int = 30) -> int:
        """
        Remove closed signals older than specified days
        
        Returns:
            Number of signals removed
        """
        return self.repo.cleanup_old_data(days=days)
    
    def _signal_to_dict(self, db_signal) -> Dict:
        """Convert database signal to dict"""
        return {
            'id': db_signal.id,
            'symbol': db_signal.symbol,
            'type': db_signal.signal_type,
            'status': db_signal.status,
            'price': db_signal.entry_price,
            'stop_loss': db_signal.stop_loss,
            'take_profit': db_signal.take_profit,
            'confidence': db_signal.confidence,
            'outcome': {
                'outcome': db_signal.outcome,
                'pnl_percent': db_signal.pnl_percent,
                'current_price': db_signal.current_price
            } if db_signal.outcome else None,
            'created_at': db_signal.created_at.isoformat(),
            'timestamp': db_signal.created_at.isoformat()
        }
        
        removed = original_count - len(self.signals)
        
        if removed > 0:
            self._save_signals()
            logger.info(f"Cleaned up {removed} old signals")
        
        return removed
