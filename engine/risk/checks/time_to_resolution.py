"""Time-to-resolution check: blocks if market resolves too soon."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(hours_to_resolution: float, min_hours: float) -> RiskCheckResult:
    if hours_to_resolution < min_hours:
        return RiskCheckResult(
            check_name="time_to_resolution",
            passed=False,
            block_reason=BlockReason.TIME_TO_RESOLUTION,
            detail=f"{hours_to_resolution:.1f}h < {min_hours:.1f}h minimum",
        )
    return RiskCheckResult(
        check_name="time_to_resolution",
        passed=True,
        block_reason=None,
        detail="ok",
    )
