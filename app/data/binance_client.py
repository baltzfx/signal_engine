"""
Binance Client - Read-only Market Data
Fetches OHLCV, orderbook, and funding rate data
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import ccxt

from config.settings import settings
from data.cache import MarketDataCache

logger = logging.getLogger(__name__)


class BinanceClient:
    """Read-only Binance data client"""
    
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}  # Use spot market
        })
        self.cache = MarketDataCache()
        
    async def fetch_ohlcv(
        self, 
        symbol: str, 
        timeframe: str = '1h', 
        limit: int = 100
    ) -> List[List]:
        """
        Fetch OHLCV candlestick data
        
        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        cache_key = f"ohlcv:{symbol}:{timeframe}"
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            self.cache.set(cache_key, ohlcv)
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return []
    
    async def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch current ticker data"""
        cache_key = f"ticker:{symbol}"
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            self.cache.set(cache_key, ticker, ttl=10)  # Short TTL for ticker
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    async def fetch_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Fetch orderbook data for liquidity analysis"""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            return orderbook
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return None
    
    async def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """Fetch current funding rate (futures only)"""
        # Disabled for Spot API - funding rates only available on Futures
        return None
    
    async def fetch_24h_volume(self, symbol: str) -> Optional[float]:
        """Fetch 24h volume in quote currency"""
        ticker = await self.fetch_ticker(symbol)
        if ticker:
            return ticker.get('quoteVolume', 0)
        return None
