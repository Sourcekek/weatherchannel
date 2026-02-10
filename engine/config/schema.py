"""Pydantic v2 configuration schema with strict validation."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ExecutionMode(StrEnum):
    DRY_RUN = "dry-run"
    LIVE = "live"


class ExecutionAdapter(StrEnum):
    DRY_RUN = "dry-run"
    SIMMER = "simmer"


class ExecutionVenue(StrEnum):
    SIMMER = "simmer"        # $SIM virtual trading
    POLYMARKET = "polymarket"  # Real USDC trading


class CityConfig(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    slug: str
    noaa_grid_id: str
    noaa_grid_x: int
    noaa_grid_y: int
    enabled: bool = True


class StrategyConfig(BaseModel):
    model_config = {"extra": "forbid"}

    min_edge_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    max_entry_price: float = Field(default=0.15, ge=0.0, le=1.0)
    min_exit_price: float = Field(default=0.45, ge=0.0, le=1.0)
    uncertainty_base_f: float = Field(default=2.5, gt=0.0)
    uncertainty_per_day_f: float = Field(default=0.5, ge=0.0)
    fee_estimate: float = Field(default=0.02, ge=0.0, le=1.0)
    slippage_estimate: float = Field(default=0.01, ge=0.0, le=1.0)


class RiskConfig(BaseModel):
    model_config = {"extra": "forbid"}

    max_position_size_usd: float = Field(default=5.00, gt=0.0)
    max_trades_per_run: int = Field(default=3, ge=1)
    max_total_exposure_usd: float = Field(default=25.00, gt=0.0)
    max_per_city_exposure_usd: float = Field(default=10.00, gt=0.0)
    max_daily_loss_usd: float = Field(default=10.00, gt=0.0)
    cooldown_minutes: int = Field(default=30, ge=0)
    min_hours_to_resolution: float = Field(default=6.0, ge=0.0)
    slippage_ceiling: float = Field(default=0.05, ge=0.0, le=1.0)


class ExecutionConfig(BaseModel):
    model_config = {"extra": "forbid"}

    mode: ExecutionMode = ExecutionMode.DRY_RUN
    adapter: ExecutionAdapter = ExecutionAdapter.DRY_RUN
    venue: ExecutionVenue = ExecutionVenue.SIMMER


class AlertConfig(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool = False
    webhook_url: str = ""


class OpsConfig(BaseModel):
    model_config = {"extra": "forbid"}

    scan_interval_minutes: int = Field(default=60, ge=1)
    forecast_max_age_minutes: int = Field(default=360, ge=1)
    market_data_max_age_minutes: int = Field(default=30, ge=1)
    lookahead_days: int = Field(default=7, ge=1, le=14)
    request_delay_ms: int = Field(default=200, ge=0)


class EngineConfig(BaseModel):
    model_config = {"extra": "forbid"}

    strategy: StrategyConfig = StrategyConfig()
    risk: RiskConfig = RiskConfig()
    execution: ExecutionConfig = ExecutionConfig()
    alerts: AlertConfig = AlertConfig()
    ops: OpsConfig = OpsConfig()
    cities: list[CityConfig] = []
