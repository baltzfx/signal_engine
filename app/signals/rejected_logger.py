"""
Rejected Signals Logger
Tracks and logs signals that didn't pass quality filters
"""
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class RejectedSignalsLogger:
    """Log rejected signals for analysis and tuning"""
    
    def __init__(self, log_file: str = "data/rejected_signals.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_rejection(
        self,
        symbol: str,
        signal_type: str,
        rejection_reason: str,
        analysis_data: Dict = None,
        confidence_score: float = None
    ) -> None:
        """
        Log a rejected signal
        
        Args:
            symbol: Trading pair
            signal_type: LONG or SHORT
            rejection_reason: Why signal was rejected
            analysis_data: Full analysis data (optional)
            confidence_score: Calculated confidence (optional)
        """
        rejection_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'symbol': symbol,
            'signal_type': signal_type,
            'rejection_reason': rejection_reason,
            'confidence_score': confidence_score
        }
        
        # Add summary of analysis if available
        if analysis_data:
            rejection_entry['analysis_summary'] = {
                'price': analysis_data.get('price'),
                'regime': analysis_data.get('market_regime', {}).get('regime'),
                'atr_percent': analysis_data.get('timeframe_1h', {}).get('atr', {}).get('atr_percent')
            }
        
        # Append to JSONL file
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(rejection_entry) + '\n')
            
            logger.debug(
                f"Logged rejection: {symbol} {signal_type} - {rejection_reason}"
            )
        except Exception as e:
            logger.error(f"Error logging rejection: {e}")
    
    def get_rejection_stats(self, days: int = 7) -> Dict:
        """
        Get statistics on rejected signals
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with rejection statistics
        """
        if not self.log_file.exists():
            return {'total': 0, 'reasons': {}}
        
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        reasons = {}
        total = 0
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()
                        
                        if entry_time >= cutoff:
                            total += 1
                            reason = entry['rejection_reason']
                            reasons[reason] = reasons.get(reason, 0) + 1
                    except:
                        continue
            
            return {
                'total': total,
                'reasons': reasons,
                'days': days
            }
        except Exception as e:
            logger.error(f"Error reading rejection stats: {e}")
            return {'total': 0, 'reasons': {}}
