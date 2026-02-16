"""
Centralized configuration — loaded from environment / .env file.
All settings are validated at startup via pydantic-settings.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ── FastAPI ──────────────────────────────────────────────────
    app_name: str = "SignalEngine"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    redis_key_ttl: int = 300  # seconds — default TTL for feature keys

    # ── Binance ──────────────────────────────────────────────────
    binance_futures_ws: str = "wss://fstream.binance.com"
    binance_futures_rest: str = "https://fapi.binance.com"
    # Comma-separated list of symbols (uppercase, no USDT suffix needed)
    symbols: List[str] = Field(
        default_factory=lambda: [
            # ── Top 20 ────────────────────────────────────────────
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
            "MATICUSDT", "UNIUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT",
            "APTUSDT", "ARBUSDT", "OPUSDT", "FILUSDT", "INJUSDT",
            # ── 21-50 ─────────────────────────────────────────────
            "SUIUSDT", "SEIUSDT", "TIAUSDT", "JUPUSDT", "WLDUSDT",
            "STXUSDT", "IMXUSDT", "RUNEUSDT", "FETUSDT", "GRTUSDT",
            "AAVEUSDT", "MKRUSDT", "SNXUSDT", "LDOUSDT", "PENDLEUSDT",
            "THETAUSDT", "ALGOUSDT", "FTMUSDT", "SANDUSDT", "MANAUSDT",
            "GALAUSDT", "AXSUSDT", "APEUSDT", "DYDXUSDT", "GMXUSDT",
            "CRVUSDT", "COMPUSDT", "ENSUSDT", "SSVUSDT", "BLURUSDT",
            # ── 51-80 ─────────────────────────────────────────────
            "CFXUSDT", "ACHUSDT", "AGLDUSDT", "LQTYUSDT", "RDNTUSDT",
            "MASKUSDT", "ILVUSDT", "WOOUSDT", "MAGICUSDT", "TUSDT",
            "XAIUSDT", "MANTAUSDT", "ONDOUSDT", "PYTHUSDT", "JITOUSDT",
            "WUSDT", "ENAUSDT", "ETHFIUSDT", "BOMEUSDT", "REZUSDT",
            "ZROUSDT", "IOUSDT", "ZKUSDT", "LISTAUSDT", "RENDERUSDT",
            "KASUSDT", "CELOUSDT", "SKLUSDT", "ZILUSDT", "QNTUSDT",
            # ── 81-110 ────────────────────────────────────────────
            "ICPUSDT", "VETUSDT", "EOSUSDT", "XTZUSDT", "FLOWUSDT",
            "MINAUSDT", "KAVAUSDT", "ROSEUSDT", "ONEUSDT", "IOTAUSDT",
            "XLMUSDT", "HBARUSDT", "EGLDUSDT", "NEOUSDT", "CHZUSDT",
            "ENJUSDT", "LRCUSDT", "BATUSDT", "COTIUSDT", "SUSHIUSDT",
            "1INCHUSDT", "BANDUSDT", "BALUSDT", "KNCUSDT", "BNTUSDT",
            "ANKRUSDT", "RVNUSDT", "REEFUSDT", "CELRUSDT", "MTLUSDT",
        ],
    )
    ws_max_streams_per_conn: int = 200  # Binance limit per combined stream
    ws_reconnect_delay: float = 3.0
    ws_ping_interval: float = 20.0

    # ── Multi-timeframe analysis ─────────────────────────────────
    timeframes: List[str] = Field(
        default_factory=lambda: ["1m", "5m", "15m", "1h"],
    )
    primary_timeframe: str = "5m"  # Main timeframe for signal generation
    mtf_alignment_required: bool = True  # Require multi-timeframe confirmation
    mtf_min_aligned: int = 2  # Minimum number of timeframes that must align

    # ── Feature engine ───────────────────────────────────────────
    atr_period: int = 14
    ema_fast: int = 9
    ema_slow: int = 21
    vwap_period: int = 20
    funding_zscore_window: int = 50
    oi_delta_window: int = 10
    liq_ratio_window: int = 20
    structure_lookback: int = 20
    orderbook_imbalance_threshold: float = 0.3  # 30 % skew
    wall_pressure_threshold: float = 5.0  # multiplier vs mean

    # ── Event engine ─────────────────────────────────────────────
    event_queue_maxsize: int = 10_000
    liq_spike_threshold: float = 2.0   # z-score
    oi_expansion_threshold: float = 1.5
    atr_expansion_threshold: float = 1.5
    funding_extreme_threshold: float = 2.5  # z-score
    imbalance_flip_threshold: float = 0.2

    # ── Signal engine (V1 rule-based) ────────────────────────────
    signal_score_threshold: float = 0.50
    signal_cooldown_seconds: int = 300  # fallback if tracker disabled

    # ── Signal tracker (TP/SL lifecycle) ─────────────────────────
    tracker_enabled: bool = True
    tp_atr_multiplier: float = 2.0     # TP = entry ± ATR × this
    sl_atr_multiplier: float = 1.0     # SL = entry ∓ ATR × this
    signal_max_ttl: int = 3600         # auto-expire after 1 hour
    price_check_interval: float = 1.0  # seconds between TP/SL scans

    # ── Telegram Bot (for queries) ───────────────────────────────
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""  # Main chat ID for signal notifications
    telegram_allowed_chat_ids: List[str] = []  # List of allowed chat IDs for queries
    telegram_query_timeout: int = 30  # seconds to wait for query processing
    telegram_rate_limit: float = 1.0  # messages per second
    telegram_retry_delay: float = 2.0  # base delay for retry backoff

    # AI settings removed - using basic rule-based responses

    # ── Query Settings ───────────────────────────────────────────
    query_top_symbols_count: int = 5  # Number of top symbols to return
    query_cache_ttl: int = 60  # seconds to cache query results

    # ── AI (Version 2) ───────────────────────────────────────────
    ai_enabled: bool = False
    ai_model_path: str = "research/models/model.json"
    ai_confidence_threshold: float = 0.50

    # ── Funding REST poll ────────────────────────────────────────
    funding_poll_interval: float = 120.0  # seconds

    # ── SQLite ───────────────────────────────────────────────────
    sqlite_db_name: str = "signalengine.db"

    # ── Monitoring ────────────────────────────────────────────────
    monitor_interval: float = 30.0  # seconds between system checks

    # ── Logging ──────────────────────────────────────────────────
    log_level: str = "INFO"
    log_json: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton — import this everywhere
settings = Settings()
