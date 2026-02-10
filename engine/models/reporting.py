"""Reporting and operational health models."""

from dataclasses import dataclass, field


@dataclass
class RunSummary:
    run_id: str
    mode: str
    cities_scanned: int = 0
    events_found: int = 0
    buckets_analyzed: int = 0
    opportunities_found: int = 0
    blocked_count: int = 0
    block_reasons: dict[str, int] = field(default_factory=dict)
    orders_attempted: int = 0
    orders_succeeded: int = 0
    orders_failed: int = 0
    best_edge: float = 0.0
    best_edge_label: str = ""
    total_exposure_usd: float = 0.0
    daily_pnl_usd: float = 0.0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PositionSnapshot:
    market_id: str
    city_slug: str
    target_date: str
    bucket_label: str
    entry_price: float
    current_price: float
    size_usd: float
    unrealized_pnl: float
    status: str  # "open" or "closed"


@dataclass(frozen=True)
class HealthStatus:
    db_connected: bool
    gamma_api_reachable: bool
    noaa_api_reachable: bool
    last_run_age_minutes: float | None
    forecast_freshness_ok: bool
    market_data_freshness_ok: bool
    kill_switch_active: bool
    paused: bool
    mode: str
