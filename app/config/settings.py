"""
Environment Configuration
Loads settings from environment variables with defaults
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings from environment"""
    
    # Binance API
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
    
    # Trading Pairs
    TRADING_PAIRS: List[str] = [
        pair.strip() for pair in os.getenv(
            "TRADING_PAIRS", 
            "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT"
        ).split(",") if pair.strip()
    ]
    
    # Timeframes
    TIMEFRAMES: List[str] = ["1h", "4h"]
    PRIMARY_TIMEFRAME: str = "1h"
    CONFIRMATION_TIMEFRAME: str = "4h"
    
    # Strategy Thresholds
    RSI_OVERSOLD: float = float(os.getenv("RSI_OVERSOLD", "30"))
    RSI_OVERBOUGHT: float = float(os.getenv("RSI_OVERBOUGHT", "70"))
    VOLUME_SPIKE_MULTIPLIER: float = float(os.getenv("VOLUME_SPIKE_MULTIPLIER", "2.0"))
    
    # Filters
    MIN_LIQUIDITY_USDT: float = float(os.getenv("MIN_LIQUIDITY_USDT", "1000000"))
    MAX_SPREAD_PERCENT: float = float(os.getenv("MAX_SPREAD_PERCENT", "0.1"))
    
    # Confidence Scoring
    MIN_CONFIDENCE_SCORE: float = float(os.getenv("MIN_CONFIDENCE_SCORE", "75"))
    
    # Strategy Selection
    USE_ENHANCED_STRATEGY: bool = os.getenv("USE_ENHANCED_STRATEGY", "true").lower() == "true"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Scheduler
    SCAN_INTERVAL_SECONDS: int = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))  # 5 min
    
    # Data Cache
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "60"))
    
    # Database (optional)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///signals.db")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
