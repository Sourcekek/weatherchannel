"""Daily loss check: blocks if daily loss exceeds limit."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(daily_loss_usd: float, max_daily_loss_usd: float) -> RiskCheckResult:
    if daily_loss_usd > max_daily_loss_usd:
        return RiskCheckResult(
            check_name="daily_loss",
            passed=False,
            block_reason=BlockReason.DAILY_LOSS,
            detail=f"${daily_loss_usd:.2f} > limit ${max_daily_loss_usd:.2f}",
        )
    return RiskCheckResult(
        check_name="daily_loss", passed=True, block_reason=None, detail="ok"
    )
