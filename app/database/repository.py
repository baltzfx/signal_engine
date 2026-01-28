"""
Signal Repository
Database operations for signals
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from database.models import Signal, RejectedSignal, PerformanceMetrics
from database.connection import db
from config.constants import STATUS_OPEN, STATUS_CLOSED, OUTCOME_WIN, OUTCOME_LOSS

logger = logging.getLogger(__name__)


class SignalRepository:
    """Repository for signal database operations"""
    
    def __init__(self):
        self.session = db.get_session()
    
    def create_signal(self, signal_data: Dict) -> Signal:
        """Create a new signal in database"""
        try:
            signal = Signal(
                symbol=signal_data['symbol'],
                signal_type=signal_data['type'],
                entry_price=signal_data['price'],
                stop_loss=signal_data.get('stop_loss'),
                take_profit=signal_data.get('take_profit'),
                confidence=signal_data.get('confidence'),
                risk_reward_ratio=signal_data.get('risk_reward_ratio'),
                timeframe_1h=signal_data.get('timeframe_1h'),
                timeframe_4h=signal_data.get('timeframe_4h'),
                market_regime=signal_data.get('market_regime'),
                support_resistance=signal_data.get('support_resistance'),
                filters=signal_data.get('filters'),
                status=STATUS_OPEN,
                outcome='PENDING'
            )
            
            self.session.add(signal)
            self.session.commit()
            self.session.refresh(signal)
            
            logger.info(f"Signal created: {signal.id} - {signal.symbol} {signal.signal_type}")
            return signal
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating signal: {e}", exc_info=True)
            raise
    
    def get_open_signals(self) -> List[Signal]:
        """Get all open signals"""
        try:
            return self.session.query(Signal).filter(
                Signal.status == STATUS_OPEN
            ).all()
        except Exception as e:
            logger.error(f"Error fetching open signals: {e}")
            return []
    
    def get_signal_by_id(self, signal_id: int) -> Optional[Signal]:
        """Get signal by ID"""
        try:
            return self.session.query(Signal).filter(Signal.id == signal_id).first()
        except Exception as e:
            logger.error(f"Error fetching signal {signal_id}: {e}")
            return None
    
    def update_signal_outcome(
        self,
        signal_id: int,
        outcome_data: Dict
    ) -> bool:
        """Update signal with outcome data"""
        try:
            signal = self.get_signal_by_id(signal_id)
            if not signal:
                return False
            
            signal.current_price = outcome_data.get('current_price')
            signal.pnl_percent = outcome_data.get('pnl_percent')
            signal.pnl_points = outcome_data.get('pnl_points')
            signal.outcome = outcome_data.get('outcome')
            signal.updated_at = datetime.utcnow()
            
            if outcome_data.get('should_close'):
                signal.status = STATUS_CLOSED
                signal.exit_price = outcome_data.get('current_price')
                signal.exit_reason = outcome_data.get('reason')
                signal.closed_at = datetime.utcnow()
            
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating signal {signal_id}: {e}")
            return False
    
    def get_recent_signals(self, hours: int = 24) -> List[Signal]:
        """Get signals from last N hours"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            return self.session.query(Signal).filter(
                Signal.created_at >= cutoff
            ).all()
        except Exception as e:
            logger.error(f"Error fetching recent signals: {e}")
            return []
    
    def get_closed_signals(self, days: int = 7) -> List[Signal]:
        """Get closed signals from last N days"""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            return self.session.query(Signal).filter(
                and_(
                    Signal.status == STATUS_CLOSED,
                    Signal.created_at >= cutoff
                )
            ).all()
        except Exception as e:
            logger.error(f"Error fetching closed signals: {e}")
            return []
    
    def log_rejected_signal(
        self,
        symbol: str,
        signal_type: str,
        rejection_reason: str,
        confidence_score: float = None,
        analysis_summary: Dict = None
    ):
        """Log a rejected signal"""
        try:
            rejected = RejectedSignal(
                symbol=symbol,
                signal_type=signal_type,
                rejection_reason=rejection_reason,
                confidence_score=confidence_score,
                analysis_summary=analysis_summary
            )
            
            self.session.add(rejected)
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error logging rejected signal: {e}")
    
    def get_rejection_stats(self, days: int = 7) -> Dict:
        """Get rejection statistics"""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            results = self.session.query(
                RejectedSignal.rejection_reason,
                func.count(RejectedSignal.id).label('count')
            ).filter(
                RejectedSignal.created_at >= cutoff
            ).group_by(
                RejectedSignal.rejection_reason
            ).all()
            
            total = sum(r.count for r in results)
            reasons = {r.rejection_reason: r.count for r in results}
            
            return {
                'total': total,
                'reasons': reasons,
                'days': days
            }
            
        except Exception as e:
            logger.error(f"Error fetching rejection stats: {e}")
            return {'total': 0, 'reasons': {}}
    
    def calculate_win_rate(self, signals: List[Signal]) -> Dict:
        """Calculate win rate from signals"""
        closed = [s for s in signals if s.outcome in [OUTCOME_WIN, OUTCOME_LOSS]]
        
        if not closed:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        wins = [s for s in closed if s.outcome == OUTCOME_WIN]
        losses = [s for s in closed if s.outcome == OUTCOME_LOSS]
        
        win_rate = (len(wins) / len(closed)) * 100
        avg_win = sum(s.pnl_percent for s in wins) / len(wins) if wins else 0
        avg_loss = sum(s.pnl_percent for s in losses) / len(losses) if losses else 0
        
        return {
            'total_trades': len(closed),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2)
        }
    
    def save_daily_metrics(self, metrics: Dict):
        """Save daily performance metrics"""
        try:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check if exists
            existing = self.session.query(PerformanceMetrics).filter(
                PerformanceMetrics.date == date
            ).first()
            
            if existing:
                # Update existing
                for key, value in metrics.items():
                    setattr(existing, key, value)
            else:
                # Create new
                perf = PerformanceMetrics(date=date, **metrics)
                self.session.add(perf)
            
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving daily metrics: {e}")
    
    def cleanup_old_data(self, days: int = 30):
        """Delete old closed signals"""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            deleted = self.session.query(Signal).filter(
                and_(
                    Signal.status == STATUS_CLOSED,
                    Signal.closed_at < cutoff
                )
            ).delete()
            
            self.session.commit()
            logger.info(f"Cleaned up {deleted} old signals")
            
            return deleted
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error cleaning up old data: {e}")
            return 0
    
    def close(self):
        """Close database session"""
        self.session.close()
