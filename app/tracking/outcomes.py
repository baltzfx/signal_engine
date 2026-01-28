"""
Outcome Tracker
Evaluates signal performance and determines win/loss outcomes
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from data.binance_client import BinanceClient
from config.constants import (
    SIGNAL_LONG, SIGNAL_SHORT, 
    OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_PENDING,
    SIGNAL_EXPIRY_HOURS, TRACKING_WINDOW_HOURS,
    DEFAULT_RISK_REWARD_RATIO
)

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """Track and evaluate signal outcomes"""
    
    def __init__(self):
        self.client = BinanceClient()
    
    async def evaluate_signal(self, signal: Dict) -> Optional[Dict]:
        """
        Evaluate current outcome for a signal
        
        Returns:
            Outcome dict with current status, PnL, etc.
        """
        try:
            symbol = signal['symbol']
            signal_type = signal['type']
            entry_price = signal['price']
            
            # Get current price
            ticker = await self.client.fetch_ticker(symbol)
            if not ticker:
                logger.warning(f"Could not fetch ticker for {symbol}")
                return None
            
            current_price = ticker['last']
            
            # Calculate PnL
            pnl_data = self._calculate_pnl(
                signal_type, entry_price, current_price
            )
            
            # Determine outcome
            outcome = self._determine_outcome(signal, pnl_data)
            
            return {
                'current_price': current_price,
                'pnl_percent': pnl_data['pnl_percent'],
                'pnl_points': pnl_data['pnl_points'],
                'outcome': outcome['result'],
                'should_close': outcome['should_close'],
                'reason': outcome['reason'],
                'updated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating signal: {e}", exc_info=True)
            return None
    
    def _calculate_pnl(
        self, 
        signal_type: str, 
        entry_price: float, 
        current_price: float
    ) -> Dict:
        """Calculate PnL in percent and points"""
        if signal_type == SIGNAL_LONG:
            pnl_points = current_price - entry_price
            pnl_percent = (pnl_points / entry_price) * 100
        else:  # SHORT
            pnl_points = entry_price - current_price
            pnl_percent = (pnl_points / entry_price) * 100
        
        return {
            'pnl_points': pnl_points,
            'pnl_percent': pnl_percent
        }
    
    def _determine_outcome(self, signal: Dict, pnl_data: Dict) -> Dict:
        """
        Determine if signal is WIN, LOSS, or PENDING
        
        Uses simple profit targets and stop losses
        Target: +2% (or configurable R:R)
        Stop: -1%
        """
        pnl_percent = pnl_data['pnl_percent']
        
        # Define thresholds
        profit_target = 2.0  # 2% profit target
        stop_loss = -1.0     # 1% stop loss
        
        # Check age of signal
        created_at = signal.get('created_at', signal.get('timestamp'))
        signal_age = datetime.utcnow() - datetime.fromisoformat(created_at)
        
        # Expired signal
        if signal_age > timedelta(hours=TRACKING_WINDOW_HOURS):
            if pnl_percent > 0:
                return {
                    'result': OUTCOME_WIN,
                    'should_close': True,
                    'reason': 'Expired with profit'
                }
            else:
                return {
                    'result': OUTCOME_LOSS,
                    'should_close': True,
                    'reason': 'Expired without profit'
                }
        
        # Hit profit target
        if pnl_percent >= profit_target:
            return {
                'result': OUTCOME_WIN,
                'should_close': True,
                'reason': f'Profit target hit: +{pnl_percent:.2f}%'
            }
        
        # Hit stop loss
        if pnl_percent <= stop_loss:
            return {
                'result': OUTCOME_LOSS,
                'should_close': True,
                'reason': f'Stop loss hit: {pnl_percent:.2f}%'
            }
        
        # Still pending
        return {
            'result': OUTCOME_PENDING,
            'should_close': False,
            'reason': f'In progress: {pnl_percent:+.2f}%'
        }
    
    def calculate_win_rate(self, signals: list) -> Dict:
        """
        Calculate win rate statistics from closed signals
        
        Returns:
            Dict with win rate, avg profit, avg loss, etc.
        """
        closed_signals = [
            s for s in signals 
            if s.get('outcome', {}).get('outcome') in [OUTCOME_WIN, OUTCOME_LOSS]
        ]
        
        if not closed_signals:
            return {
                'total_signals': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        wins = [
            s for s in closed_signals 
            if s['outcome']['outcome'] == OUTCOME_WIN
        ]
        losses = [
            s for s in closed_signals 
            if s['outcome']['outcome'] == OUTCOME_LOSS
        ]
        
        win_rate = (len(wins) / len(closed_signals)) * 100 if closed_signals else 0
        
        avg_win = sum(
            s['outcome']['pnl_percent'] for s in wins
        ) / len(wins) if wins else 0
        
        avg_loss = sum(
            s['outcome']['pnl_percent'] for s in losses
        ) / len(losses) if losses else 0
        
        return {
            'total_signals': len(closed_signals),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2)
        }
