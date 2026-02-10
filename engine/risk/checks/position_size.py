"""Position size check: blocks if proposed size exceeds limit."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(proposed_size_usd: float, max_position_size_usd: float) -> RiskCheckResult:
    if proposed_size_usd > max_position_size_usd:
        return RiskCheckResult(
            check_name="position_size",
            passed=False,
            block_reason=BlockReason.POSITION_SIZE,
            detail=f"${proposed_size_usd:.2f} > limit ${max_position_size_usd:.2f}",
        )
    return RiskCheckResult(
        check_name="position_size", passed=True, block_reason=None, detail="ok"
    )
