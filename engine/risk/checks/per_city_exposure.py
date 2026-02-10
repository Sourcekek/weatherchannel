"""Per-city exposure check: blocks if city exposure would exceed limit."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(
    city_exposure_usd: float,
    proposed_size_usd: float,
    max_per_city_exposure_usd: float,
) -> RiskCheckResult:
    new_total = city_exposure_usd + proposed_size_usd
    if new_total > max_per_city_exposure_usd:
        return RiskCheckResult(
            check_name="per_city_exposure",
            passed=False,
            block_reason=BlockReason.PER_CITY_EXPOSURE,
            detail=f"${new_total:.2f} > limit ${max_per_city_exposure_usd:.2f}",
        )
    return RiskCheckResult(
        check_name="per_city_exposure",
        passed=True,
        block_reason=None,
        detail="ok",
    )
