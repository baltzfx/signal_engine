"""
Daily Summary Generator
Creates performance summaries of signal performance
"""
import logging
from typing import Dict, List
from datetime import datetime, timedelta

from tracking.open_signals import OpenSignalsTracker
from tracking.outcomes import OutcomeTracker
from notifier.telegram import TelegramNotifier

logger = logging.getLogger(__name__)


class DailySummary:
    """Generate and send daily performance summaries"""
    
    def __init__(self):
        self.tracker = OpenSignalsTracker()
        self.outcome_tracker = OutcomeTracker()
        self.notifier = TelegramNotifier()
    
    async def generate_and_send_summary(self) -> bool:
        """Generate daily summary and send via Telegram"""
        try:
            # Get signals from last 24 hours
            signals_24h = self._get_recent_signals(hours=24)
            
            # Calculate statistics
            stats = self.outcome_tracker.calculate_win_rate(signals_24h)
            
            # Format message
            message = self._format_summary_message(stats, signals_24h)
            
            # Send to Telegram
            return await self.notifier.send_message(message)
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}", exc_info=True)
            return False
    
    def _get_recent_signals(self, hours: int = 24) -> List[Dict]:
        """Get signals from the last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        all_signals = self.tracker.get_open_signals() + self.tracker.get_closed_signals()
        
        recent = [
            s for s in all_signals
            if datetime.fromisoformat(s.get('created_at', s.get('timestamp'))) >= cutoff
        ]
        
        return recent
    
    def _format_summary_message(self, stats: Dict, signals: List[Dict]) -> str:
        """Format daily summary message"""
        
        win_rate = stats.get('win_rate', 0)
        total_trades = stats.get('total_trades', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        avg_win = stats.get('avg_win', 0)
        avg_loss = stats.get('avg_loss', 0)
        
        # Calculate total R
        total_r = 0
        if signals:
            for signal in signals:
                outcome = signal.get('outcome', {})
                if outcome:
                    pnl_pct = outcome.get('pnl_percent', 0)
                    # Assuming 1R = 1% risk
                    total_r += pnl_pct
        
        # Determine emoji based on performance
        if win_rate >= 60:
            emoji = "🎯"
        elif win_rate >= 50:
            emoji = "✅"
        elif win_rate >= 40:
            emoji = "📊"
        else:
            emoji = "⚠️"
        
        message = f"""
{emoji} <b>Daily Signal Summary</b> {emoji}

<b>📅 Last 24 Hours</b>

<b>Performance:</b>
• Signals Sent: {len(signals)}
• Closed Trades: {total_trades}
• Wins: {wins} | Losses: {losses}
• Win Rate: {win_rate:.1f}%

<b>Returns:</b>
• Avg Win: +{avg_win:.2f}%
• Avg Loss: {avg_loss:.2f}%
• Total R: {total_r:+.2f}R

<b>Open Positions:</b>
• Currently Tracking: {len(self.tracker.get_open_signals())} signals

<i>Keep following the rules. Quality over quantity.</i>

<b>📊 Stats generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
""".strip()
        
        return message
