"""Uncertainty calibration: sigma scaling by days until resolution."""

from datetime import UTC, datetime

MIN_SIGMA = 1.0  # Floor to prevent overconfidence on same-day forecasts


def compute_sigma(
    target_date: str,
    now: datetime | None = None,
    base: float = 2.5,
    per_day: float = 0.5,
) -> float:
    """Compute forecast uncertainty sigma based on days until target.

    Args:
        target_date: Target date in YYYY-MM-DD format.
        now: Current time (defaults to UTC now).
        base: Base sigma in degrees F.
        per_day: Additional sigma per day out.

    Returns:
        Sigma in degrees F, floored at MIN_SIGMA.
    """
    if now is None:
        now = datetime.now(UTC)

    # Parse target date as end-of-day UTC
    target = datetime.strptime(target_date, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, tzinfo=UTC
    )
    days_out = max(0.0, (target - now).total_seconds() / 86400)
    sigma = base + (days_out * per_day)
    return max(sigma, MIN_SIGMA)
