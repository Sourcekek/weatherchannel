"""Tests for staleness checks with boundary conditions."""

from datetime import UTC, datetime

from engine.ingest.staleness import (
    forecast_staleness_hours,
    is_forecast_stale,
    is_market_data_stale,
)


class TestIsMarketDataStale:
    def test_fresh(self):
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)
        fetched = "2026-02-10T11:50:00+00:00"
        assert is_market_data_stale(fetched, 30, now) is False

    def test_stale(self):
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)
        fetched = "2026-02-10T11:00:00+00:00"
        assert is_market_data_stale(fetched, 30, now) is True

    def test_boundary_exact(self):
        now = datetime(2026, 2, 10, 12, 30, 0, tzinfo=UTC)
        fetched = "2026-02-10T12:00:00+00:00"
        # Exactly 30 minutes = not stale (>30 is stale)
        assert is_market_data_stale(fetched, 30, now) is False

    def test_invalid_timestamp(self):
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)
        assert is_market_data_stale("not-a-timestamp", 30, now) is True


class TestIsForecastStale:
    def test_fresh(self):
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)
        generated = "2026-02-10T10:00:00+00:00"
        assert is_forecast_stale(generated, 360, now) is False

    def test_stale(self):
        now = datetime(2026, 2, 10, 20, 0, 0, tzinfo=UTC)
        generated = "2026-02-10T10:00:00+00:00"
        assert is_forecast_stale(generated, 360, now) is True


class TestForecastStalenessHours:
    def test_calculation(self):
        now = datetime(2026, 2, 10, 18, 0, 0, tzinfo=UTC)
        generated = "2026-02-10T12:00:00+00:00"
        assert forecast_staleness_hours(generated, now) == 6.0

    def test_invalid_returns_inf(self):
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)
        assert forecast_staleness_hours("bad", now) == float("inf")
