"""Total exposure check: blocks if adding proposed would exceed limit."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(
    current_exposure_usd: float,
    proposed_size_usd: float,
    max_total_exposure_usd: float,
) -> RiskCheckResult:
    new_total = current_exposure_usd + proposed_size_usd
    if new_total > max_total_exposure_usd:
        return RiskCheckResult(
            check_name="total_exposure",
            passed=False,
            block_reason=BlockReason.TOTAL_EXPOSURE,
            detail=f"${new_total:.2f} > limit ${max_total_exposure_usd:.2f}",
        )
    return RiskCheckResult(
        check_name="total_exposure", passed=True, block_reason=None, detail="ok"
    )
