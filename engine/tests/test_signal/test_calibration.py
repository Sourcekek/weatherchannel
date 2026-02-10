"""Tests for uncertainty calibration: sigma computation."""

from datetime import UTC, datetime

from engine.signal.calibration import MIN_SIGMA, compute_sigma


class TestComputeSigma:
    def test_same_day(self):
        """Same-day: sigma ≈ base + fractional days * per_day."""
        now = datetime(2026, 2, 11, 12, 0, 0, tzinfo=UTC)
        sigma = compute_sigma("2026-02-11", now=now, base=2.5, per_day=0.5)
        # ~0.5 days out -> 2.5 + 0.25 = 2.75
        assert 2.5 <= sigma <= 3.0

    def test_one_day_out(self):
        """1 day out: sigma ≈ 2.5 + 1.0 * 0.5 = 3.0."""
        now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)
        sigma = compute_sigma("2026-02-11", now=now, base=2.5, per_day=0.5)
        assert 2.9 <= sigma <= 3.3

    def test_seven_days_out(self):
        """7 days out: sigma ≈ 2.5 + 7 * 0.5 = 6.0."""
        now = datetime(2026, 2, 4, 0, 0, 0, tzinfo=UTC)
        sigma = compute_sigma("2026-02-11", now=now, base=2.5, per_day=0.5)
        assert 5.5 <= sigma <= 6.5

    def test_min_sigma_floor(self):
        """Sigma should never go below MIN_SIGMA."""
        now = datetime(2026, 2, 11, 23, 59, 0, tzinfo=UTC)
        sigma = compute_sigma("2026-02-11", now=now, base=0.5, per_day=0.0)
        assert sigma >= MIN_SIGMA

    def test_past_date_uses_floor(self):
        """Past date should use floor (days_out = 0)."""
        now = datetime(2026, 2, 15, 0, 0, 0, tzinfo=UTC)
        sigma = compute_sigma("2026-02-11", now=now, base=2.5, per_day=0.5)
        assert sigma == 2.5

    def test_custom_params(self):
        now = datetime(2026, 2, 10, 0, 0, 0, tzinfo=UTC)
        sigma = compute_sigma("2026-02-12", now=now, base=3.0, per_day=1.0)
        # ~3 days out -> 3.0 + 3.0 = 6.0
        assert 5.5 <= sigma <= 6.5
