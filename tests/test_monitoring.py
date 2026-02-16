"""Tests for app.core.monitoring."""

from app.core.monitoring import inc, gauge, get_counters, get_gauges, get_system_metrics


class TestMonitoring:
    def test_counter_increment(self):
        inc("test_counter")
        inc("test_counter")
        inc("test_counter")
        counters = get_counters()
        assert counters["test_counter"] >= 3

    def test_gauge_set(self):
        gauge("test_gauge", 42.5)
        gauges = get_gauges()
        assert gauges["test_gauge"] == 42.5

    def test_gauge_overwrite(self):
        gauge("overwrite_gauge", 1.0)
        gauge("overwrite_gauge", 2.0)
        assert get_gauges()["overwrite_gauge"] == 2.0

    def test_system_metrics(self):
        metrics = get_system_metrics()
        assert "cpu_percent" in metrics
        assert "memory_rss_mb" in metrics
        assert "uptime_seconds" in metrics
        assert metrics["memory_rss_mb"] > 0
