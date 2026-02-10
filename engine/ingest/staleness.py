"""Staleness checks for market data and forecasts."""

from datetime import UTC, datetime


def is_market_data_stale(
    fetched_at_iso: str, max_age_minutes: int, now: datetime | None = None
) -> bool:
    """Check if market data is stale based on fetch time."""
    if now is None:
        now = datetime.now(UTC)
    fetched = _parse_timestamp(fetched_at_iso)
    if fetched is None:
        return True
    age_minutes = (now - fetched).total_seconds() / 60
    return age_minutes > max_age_minutes


def is_forecast_stale(
    source_generated_at_iso: str, max_age_minutes: int, now: datetime | None = None
) -> bool:
    """Check if a forecast is stale based on its generation time."""
    if now is None:
        now = datetime.now(UTC)
    generated = _parse_timestamp(source_generated_at_iso)
    if generated is None:
        return True
    age_minutes = (now - generated).total_seconds() / 60
    return age_minutes > max_age_minutes


def forecast_staleness_hours(
    source_generated_at_iso: str, now: datetime | None = None
) -> float:
    """Get staleness of a forecast in hours."""
    if now is None:
        now = datetime.now(UTC)
    generated = _parse_timestamp(source_generated_at_iso)
    if generated is None:
        return float("inf")
    return (now - generated).total_seconds() / 3600


def _parse_timestamp(iso_str: str) -> datetime | None:
    """Parse an ISO timestamp, handling various formats."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None
