"""
Backtesting Engine
Test strategy on historical data to validate performance
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from strategy.enhanced_strategy import EnhancedStrategy
from config.constants import SIGNAL_LONG, SIGNAL_SHORT

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtest trading strategies on historical data"""
    
    def __init__(self, initial_balance: float = 10000):
        self.initial_balance = initial_balance
        self.strategy = EnhancedStrategy()
    
    def run_backtest(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str = '1h'
    ) -> Dict:
        """
        Run backtest for a symbol over a date range
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            timeframe: Candle timeframe
            
        Returns:
            Backtest results dict
        """
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        
        try:
            # Fetch historical data
            data = self._fetch_historical_data(symbol, start_date, end_date, timeframe)
            
            if data is None or len(data) < 100:
                logger.error("Insufficient data for backtest")
                return None
            
            # Run backtest
            trades = self._simulate_trades(data, symbol)
            
            # Calculate statistics
            stats = self._calculate_statistics(trades, data)
            
            return {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'total_trades': len(trades),
                'trades': trades,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Backtest error: {e}", exc_info=True)
            return None
    
    async def _fetch_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """Fetch and prepare historical OHLCV data"""
        try:
            # Calculate number of candles needed
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            
            # Fetch from exchange
            all_data = []
            current_start = start_dt
            
            while current_start < end_dt:
                ohlcv = await self.strategy.client.fetch_ohlcv(
                    symbol, timeframe, limit=1000
                )
                
                if not ohlcv:
                    break
                
                all_data.extend(ohlcv)
                current_start += timedelta(hours=1000)  # Approx next batch
            
            if not all_data:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(
                all_data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Filter date range
            df = df[(df.index >= start_dt) & (df.index <= end_dt)]
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None
    
    def _simulate_trades(self, data: pd.DataFrame, symbol: str) -> List[Dict]:
        """Simulate trades based on strategy signals"""
        trades = []
        in_position = False
        current_trade = None
        
        # Iterate through data
        for i in range(200, len(data)):  # Start after warmup period
            current_bar = data.iloc[i]
            
            # Get signal at this point
            signal = self._get_historical_signal(data, i, symbol)
            
            if signal and not in_position:
                # Enter trade
                current_trade = {
                    'entry_time': current_bar.name,
                    'entry_price': current_bar['close'],
                    'signal_type': signal['type'],
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit': signal.get('take_profit'),
                    'confidence': signal.get('confidence', 0)
                }
                in_position = True
            
            elif in_position and current_trade:
                # Check exit conditions
                exit_reason = self._check_exit(
                    current_bar,
                    current_trade
                )
                
                if exit_reason:
                    # Close trade
                    current_trade['exit_time'] = current_bar.name
                    current_trade['exit_price'] = current_bar['close']
                    current_trade['exit_reason'] = exit_reason
                    
                    # Calculate PnL
                    if current_trade['signal_type'] == SIGNAL_LONG:
                        pnl_pct = ((current_trade['exit_price'] - current_trade['entry_price']) 
                                   / current_trade['entry_price']) * 100
                    else:
                        pnl_pct = ((current_trade['entry_price'] - current_trade['exit_price']) 
                                   / current_trade['entry_price']) * 100
                    
                    current_trade['pnl_percent'] = round(pnl_pct, 2)
                    current_trade['outcome'] = 'WIN' if pnl_pct > 0 else 'LOSS'
                    
                    trades.append(current_trade)
                    in_position = False
                    current_trade = None
        
        return trades
    
    def _get_historical_signal(self, data: pd.DataFrame, index: int, symbol: str) -> Optional[Dict]:
        """
        Generate signal using historical data up to this point
        This simulates real-time signal generation
        """
        # This is a simplified version - in reality, you'd call the strategy
        # with data only up to 'index' to avoid lookahead bias
        
        # For now, return None (placeholder)
        # In full implementation, extract data slice and call strategy
        return None
    
    def _check_exit(self, current_bar: pd.Series, trade: Dict) -> Optional[str]:
        """Check if trade should be exited"""
        current_price = current_bar['close']
        current_high = current_bar['high']
        current_low = current_bar['low']
        
        if trade['signal_type'] == SIGNAL_LONG:
            # Check stop loss
            if trade.get('stop_loss') and current_low <= trade['stop_loss']:
                return 'stop_loss'
            
            # Check take profit
            if trade.get('take_profit') and current_high >= trade['take_profit']:
                return 'take_profit'
        
        else:  # SHORT
            # Check stop loss
            if trade.get('stop_loss') and current_high >= trade['stop_loss']:
                return 'stop_loss'
            
            # Check take profit
            if trade.get('take_profit') and current_low <= trade['take_profit']:
                return 'take_profit'
        
        # Check time-based exit (e.g., 48 hours)
        trade_duration = current_bar.name - trade['entry_time']
        if trade_duration > timedelta(hours=48):
            return 'time_exit'
        
        return None
    
    def _calculate_statistics(self, trades: List[Dict], data: pd.DataFrame) -> Dict:
        """Calculate backtest performance statistics"""
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'total_return': 0
            }
        
        wins = [t for t in trades if t['outcome'] == 'WIN']
        losses = [t for t in trades if t['outcome'] == 'LOSS']
        
        win_rate = (len(wins) / len(trades)) * 100 if trades else 0
        avg_win = np.mean([t['pnl_percent'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl_percent'] for t in losses]) if losses else 0
        
        # Profit factor
        total_profit = sum([t['pnl_percent'] for t in wins])
        total_loss = abs(sum([t['pnl_percent'] for t in losses]))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Total return
        total_return = sum([t['pnl_percent'] for t in trades])
        
        # Max drawdown
        equity_curve = [self.initial_balance]
        for trade in trades:
            pnl_dollar = equity_curve[-1] * (trade['pnl_percent'] / 100)
            equity_curve.append(equity_curve[-1] + pnl_dollar)
        
        peak = equity_curve[0]
        max_dd = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100
            if dd > max_dd:
                max_dd = dd
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_dd, 2),
            'total_return': round(total_return, 2),
            'final_balance': round(equity_curve[-1], 2)
        }
