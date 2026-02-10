"""Tests for all 10 individual risk checks."""

from engine.models.risk import BlockReason
from engine.risk.checks import (
    cooldown,
    daily_loss,
    kill_switch,
    paused,
    per_city_exposure,
    position_size,
    slippage,
    time_to_resolution,
    total_exposure,
    trades_per_run,
)


class TestKillSwitch:
    def test_pass(self):
        r = kill_switch.check(False)
        assert r.passed is True

    def test_fail(self):
        r = kill_switch.check(True)
        assert r.passed is False
        assert r.block_reason == BlockReason.KILL_SWITCH


class TestPaused:
    def test_pass(self):
        assert paused.check(False).passed is True

    def test_fail(self):
        r = paused.check(True)
        assert r.passed is False
        assert r.block_reason == BlockReason.PAUSED


class TestPositionSize:
    def test_pass(self):
        assert position_size.check(5.0, 5.0).passed is True

    def test_fail(self):
        r = position_size.check(5.01, 5.0)
        assert r.passed is False
        assert r.block_reason == BlockReason.POSITION_SIZE

    def test_boundary(self):
        assert position_size.check(5.0, 5.0).passed is True


class TestTradesPerRun:
    def test_pass(self):
        assert trades_per_run.check(2, 3).passed is True

    def test_fail(self):
        r = trades_per_run.check(3, 3)
        assert r.passed is False
        assert r.block_reason == BlockReason.TRADES_PER_RUN

    def test_boundary(self):
        assert trades_per_run.check(2, 3).passed is True
        assert trades_per_run.check(3, 3).passed is False


class TestTotalExposure:
    def test_pass(self):
        assert total_exposure.check(20.0, 5.0, 25.0).passed is True

    def test_fail(self):
        r = total_exposure.check(21.0, 5.0, 25.0)
        assert r.passed is False
        assert r.block_reason == BlockReason.TOTAL_EXPOSURE

    def test_boundary(self):
        assert total_exposure.check(20.0, 5.0, 25.0).passed is True
        assert total_exposure.check(20.01, 5.0, 25.0).passed is False


class TestPerCityExposure:
    def test_pass(self):
        assert per_city_exposure.check(5.0, 5.0, 10.0).passed is True

    def test_fail(self):
        r = per_city_exposure.check(6.0, 5.0, 10.0)
        assert r.passed is False
        assert r.block_reason == BlockReason.PER_CITY_EXPOSURE


class TestDailyLoss:
    def test_pass(self):
        assert daily_loss.check(5.0, 10.0).passed is True

    def test_fail(self):
        r = daily_loss.check(10.01, 10.0)
        assert r.passed is False
        assert r.block_reason == BlockReason.DAILY_LOSS

    def test_boundary(self):
        assert daily_loss.check(10.0, 10.0).passed is True


class TestCooldown:
    def test_pass_no_previous(self):
        assert cooldown.check(None, 30).passed is True

    def test_pass_enough_time(self):
        assert cooldown.check(31.0, 30).passed is True

    def test_fail(self):
        r = cooldown.check(15.0, 30)
        assert r.passed is False
        assert r.block_reason == BlockReason.COOLDOWN

    def test_boundary(self):
        assert cooldown.check(30.0, 30).passed is True
        assert cooldown.check(29.9, 30).passed is False


class TestTimeToResolution:
    def test_pass(self):
        assert time_to_resolution.check(12.0, 6.0).passed is True

    def test_fail(self):
        r = time_to_resolution.check(5.0, 6.0)
        assert r.passed is False
        assert r.block_reason == BlockReason.TIME_TO_RESOLUTION

    def test_boundary(self):
        assert time_to_resolution.check(6.0, 6.0).passed is True
        assert time_to_resolution.check(5.99, 6.0).passed is False


class TestSlippage:
    def test_pass(self):
        assert slippage.check(0.10, 0.105, 0.05).passed is True

    def test_fail(self):
        r = slippage.check(0.10, 0.20, 0.05)
        assert r.passed is False
        assert r.block_reason == BlockReason.SLIPPAGE

    def test_zero_bid(self):
        r = slippage.check(0.0, 0.10, 0.05)
        assert r.passed is False
        assert r.block_reason == BlockReason.SLIPPAGE
