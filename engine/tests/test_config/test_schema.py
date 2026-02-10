"""Tests for config schema validation."""

import pytest
from pydantic import ValidationError

from engine.config.schema import (
    CityConfig,
    EngineConfig,
    ExecutionConfig,
    ExecutionMode,
    RiskConfig,
    StrategyConfig,
)


class TestEngineConfig:
    def test_defaults(self):
        config = EngineConfig()
        assert config.execution.mode == ExecutionMode.DRY_RUN
        assert config.strategy.min_edge_threshold == 0.05
        assert config.risk.max_position_size_usd == 5.00

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            EngineConfig(unknown_field="bad")

    def test_nested_extra_fields_rejected(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            StrategyConfig(min_edge_threshold=0.05, bogus=True)

    def test_execution_mode_default_is_dry_run(self):
        config = ExecutionConfig()
        assert config.mode == ExecutionMode.DRY_RUN

    def test_execution_mode_live(self):
        config = ExecutionConfig(mode="live", adapter="simmer")
        assert config.mode == ExecutionMode.LIVE


class TestStrategyConfig:
    def test_valid(self):
        config = StrategyConfig(min_edge_threshold=0.10, max_entry_price=0.12)
        assert config.min_edge_threshold == 0.10
        assert config.max_entry_price == 0.12

    def test_threshold_bounds(self):
        with pytest.raises(ValidationError):
            StrategyConfig(min_edge_threshold=-0.01)
        with pytest.raises(ValidationError):
            StrategyConfig(min_edge_threshold=1.5)

    def test_uncertainty_must_be_positive(self):
        with pytest.raises(ValidationError):
            StrategyConfig(uncertainty_base_f=0.0)


class TestRiskConfig:
    def test_defaults(self):
        config = RiskConfig()
        assert config.max_position_size_usd == 5.00
        assert config.max_trades_per_run == 3
        assert config.max_total_exposure_usd == 25.00
        assert config.cooldown_minutes == 30

    def test_position_size_must_be_positive(self):
        with pytest.raises(ValidationError):
            RiskConfig(max_position_size_usd=0.0)

    def test_trades_per_run_at_least_one(self):
        with pytest.raises(ValidationError):
            RiskConfig(max_trades_per_run=0)

    def test_slippage_ceiling_bounds(self):
        RiskConfig(slippage_ceiling=0.0)  # min ok
        RiskConfig(slippage_ceiling=1.0)  # max ok
        with pytest.raises(ValidationError):
            RiskConfig(slippage_ceiling=1.1)


class TestCityConfig:
    def test_valid(self):
        city = CityConfig(
            name="Test City",
            slug="test",
            noaa_grid_id="TST",
            noaa_grid_x=10,
            noaa_grid_y=20,
        )
        assert city.enabled is True

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CityConfig(
                name="Test",
                slug="test",
                noaa_grid_id="TST",
                noaa_grid_x=10,
                noaa_grid_y=20,
                population=1000000,
            )
