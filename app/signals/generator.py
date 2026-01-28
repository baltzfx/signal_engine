"""
Signal Generator
Orchestrates strategy analysis, filtering, and confidence scoring
Now supports both basic and enhanced strategies
"""
import logging
from typing import Optional, Dict
from datetime import datetime
import os

from strategy.trend_1h_4h import Trend1H4HStrategy
from strategy.filters import SignalFilters
from scoring.confidence import ConfidenceScorer
from config.constants import SIGNAL_NEUTRAL, SIGNAL_LONG, SIGNAL_SHORT
from database.repository import SignalRepository

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Main signal generation orchestrator"""
    
    def __init__(self, use_enhanced: bool = True):
        # Use enhanced strategy if available and enabled
        self.use_enhanced = use_enhanced and os.getenv('USE_ENHANCED_STRATEGY', 'true').lower() == 'true'
        
        if self.use_enhanced:
            try:
                from app.strategy.enhanced_strategy import EnhancedStrategy
                self.strategy = EnhancedStrategy()
                logger.info("Using Enhanced Strategy")
            except ImportError:
                logger.warning("Enhanced strategy not available, falling back to basic")
                self.strategy = Trend1H4HStrategy()
                self.use_enhanced = False
        else:
            self.strategy = Trend1H4HStrategy()
        
        self.filters = SignalFilters()
        self.scorer = ConfidenceScorer()
        self.repo = SignalRepository()
    
    async def generate_signal(self, symbol: str) -> Optional[Dict]:
        """
        Generate a complete signal for a symbol
        
        Process:
        1. Analyze with strategy
        2. Apply quality filters
        3. Calculate confidence score
        4. Return signal if meets threshold
        
        Returns:
            Complete signal dict or None
        """
        logger.info(f"Generating signal for {symbol}")
        
        try:
            # Step 0: Check for existing open signals
            open_signals = self.repo.get_open_signals()
            for existing in open_signals:
                if existing.symbol == symbol:
                    logger.info(
                        f"Skipping {symbol} - Open {existing.signal_type} signal already exists "
                        f"(Created: {existing.created_at}, ID: {existing.id})"
                    )
                    return None
            
            # Step 1: Strategy analysis
            analysis = await self.strategy.analyze(symbol)
            
            if not analysis or analysis.get('type') == SIGNAL_NEUTRAL:
                logger.debug(f"No signal detected for {symbol}")
                return None
            
            # Step 2: Apply filters
            filter_results = await self.filters.apply_filters(symbol)
            
            if not filter_results.get('all_passed', False):
                logger.info(
                    f"Signal for {symbol} failed quality filters: {filter_results}"
                )
                return None
            
            # Step 3: Calculate confidence score
            confidence_score = self.scorer.calculate_score(
                signal_type=analysis['type'],
                timeframe_1h=analysis['timeframe_1h'],
                timeframe_4h=analysis['timeframe_4h'],
                filters=filter_results
            )
            
            # Step 4: Check threshold
            if not self.scorer.meets_threshold(confidence_score):
                logger.info(
                    f"Signal for {symbol} below confidence threshold: "
                    f"{confidence_score:.1f}%"
                )
                return None
            
            # Step 5: Calculate Stop Loss and Take Profit using ATR
            price = analysis['price']
            atr_data = analysis['timeframe_1h'].get('atr', {})
            atr_multiplier_sl = atr_data.get('stop_multiplier', 2.0)
            atr_multiplier_tp = atr_data.get('target_multiplier', 3.0)
            atr_value = atr_data.get('atr', price * 0.02)  # Default 2% if no ATR
            
            if analysis['type'] == SIGNAL_LONG:
                stop_loss = price - (atr_value * atr_multiplier_sl)
                take_profit = price + (atr_value * atr_multiplier_tp)
            else:  # SHORT
                stop_loss = price + (atr_value * atr_multiplier_sl)
                take_profit = price - (atr_value * atr_multiplier_tp)
            
            # Calculate risk:reward ratio
            risk = abs(price - stop_loss)
            reward = abs(take_profit - price)
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Calculate expected holding time (based on timeframe)
            # 1H signals typically held 4-24 hours, 4H signals 1-3 days
            holding_time_hours = 12  # Average holding time
            
            # Signal expiry (valid for 1 hour for 1H timeframe)
            from datetime import timedelta
            expiry_time = datetime.utcnow() + timedelta(hours=1)
            
            # Build complete signal
            signal = {
                'symbol': symbol,
                'type': analysis['type'],
                'price': analysis['price'],
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'risk_reward_ratio': round(rr_ratio, 2),
                'holding_time_hours': holding_time_hours,
                'expiry_time': expiry_time.isoformat(),
                'confidence': confidence_score,
                'timestamp': datetime.utcnow().isoformat(),
                'timeframe_1h': analysis['timeframe_1h'],
                'timeframe_4h': analysis['timeframe_4h'],
                'filters': filter_results
            }
            
            logger.info(
                f"✓ Signal generated: {symbol} {analysis['type']} "
                f"@ ${analysis['price']:.2f} (confidence: {confidence_score:.1f}%)"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}", exc_info=True)
            return None
