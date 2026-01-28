"""
Signal Filters - Liquidity, Funding, Spread
Quality filters to eliminate low-quality signals
"""
import logging
from typing import Optional, Dict

from data.binance_client import BinanceClient
from config.settings import settings

logger = logging.getLogger(__name__)


class SignalFilters:
    """Filter signals based on market quality metrics"""
    
    def __init__(self):
        self.client = BinanceClient()
    
    async def apply_filters(self, symbol: str) -> Dict[str, bool]:
        """
        Apply all filters to a symbol
        
        Returns:
            Dict with filter results and pass/fail status
        """
        liquidity_ok = await self.check_liquidity(symbol)
        spread_ok = await self.check_spread(symbol)
        funding_ok = await self.check_funding_rate(symbol)
        
        return {
            'liquidity': liquidity_ok,
            'spread': spread_ok,
            'funding': funding_ok,
            'all_passed': liquidity_ok and spread_ok and funding_ok
        }
    
    async def check_liquidity(self, symbol: str) -> bool:
        """
        Check if symbol has sufficient liquidity
        
        Uses 24h volume as proxy for liquidity
        """
        try:
            volume_24h = await self.client.fetch_24h_volume(symbol)
            
            if volume_24h is None:
                logger.warning(f"Could not fetch volume for {symbol}")
                return False
            
            is_liquid = volume_24h >= settings.MIN_LIQUIDITY_USDT
            
            if not is_liquid:
                logger.debug(
                    f"{symbol} failed liquidity filter: "
                    f"${volume_24h:,.0f} < ${settings.MIN_LIQUIDITY_USDT:,.0f}"
                )
            
            return is_liquid
            
        except Exception as e:
            logger.error(f"Error checking liquidity for {symbol}: {e}")
            return False
    
    async def check_spread(self, symbol: str) -> bool:
        """
        Check if bid-ask spread is acceptable
        
        Wide spreads indicate low liquidity or high volatility
        """
        try:
            orderbook = await self.client.fetch_orderbook(symbol)
            
            if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
                logger.warning(f"Could not fetch orderbook for {symbol}")
                return False
            
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            
            mid_price = (best_bid + best_ask) / 2
            spread_percent = ((best_ask - best_bid) / mid_price) * 100
            
            is_tight = spread_percent <= settings.MAX_SPREAD_PERCENT
            
            if not is_tight:
                logger.debug(
                    f"{symbol} failed spread filter: "
                    f"{spread_percent:.3f}% > {settings.MAX_SPREAD_PERCENT}%"
                )
            
            return is_tight
            
        except Exception as e:
            logger.error(f"Error checking spread for {symbol}: {e}")
            return False
    
    async def check_funding_rate(self, symbol: str) -> bool:
        """
        Check if funding rate is not extremely skewed
        
        Extreme funding rates can indicate overheated positions
        Returns True if funding is acceptable or unavailable (spot)
        """
        try:
            funding_rate = await self.client.fetch_funding_rate(symbol)
            
            # If no funding rate (spot markets), pass filter
            if funding_rate is None:
                return True
            
            # Convert to percentage
            funding_percent = funding_rate * 100
            
            # Flag if funding is extremely high (>0.1% per 8h)
            is_acceptable = abs(funding_percent) < 0.1
            
            if not is_acceptable:
                logger.debug(
                    f"{symbol} has extreme funding rate: {funding_percent:.4f}%"
                )
            
            return is_acceptable
            
        except Exception as e:
            logger.warning(f"Error checking funding rate for {symbol}: {e}")
            return True  # Pass filter if can't fetch
