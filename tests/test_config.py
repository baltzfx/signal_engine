"""Tests for app.core.config."""

from app.core.config import Settings


class TestConfig:
    def test_default_settings_load(self):
        s = Settings()
        assert s.app_name == "SignalEngine"
        assert s.signal_score_threshold == 0.60
        assert s.signal_cooldown_seconds == 300

    def test_symbols_has_defaults(self):
        s = Settings()
        assert len(s.symbols) >= 100
        assert "BTCUSDT" in s.symbols
        assert "ETHUSDT" in s.symbols

    def test_redis_defaults(self):
        s = Settings()
        assert s.redis_url == "redis://localhost:6379/0"
        assert s.redis_max_connections == 50

    def test_ai_disabled_by_default(self):
        s = Settings()
        assert s.ai_enabled is False
        assert s.ai_confidence_threshold == 0.65

    def test_sqlite_db_name(self):
        s = Settings()
        assert s.sqlite_db_name == "signalengine.db"

    def test_monitor_interval(self):
        s = Settings()
        assert s.monitor_interval == 30.0

    def test_tracker_defaults(self):
        s = Settings()
        assert s.tracker_enabled is True
        assert s.tp_atr_multiplier == 2.0
        assert s.sl_atr_multiplier == 1.0
        assert s.signal_max_ttl == 3600
        assert s.price_check_interval == 1.0
