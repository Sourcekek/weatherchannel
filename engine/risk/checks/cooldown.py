"""Cooldown check: blocks if last trade on same market was too recent."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(minutes_since_last_trade: float | None, cooldown_minutes: int) -> RiskCheckResult:
    if minutes_since_last_trade is not None and minutes_since_last_trade < cooldown_minutes:
        return RiskCheckResult(
            check_name="cooldown",
            passed=False,
            block_reason=BlockReason.COOLDOWN,
            detail=f"{minutes_since_last_trade:.1f}min < {cooldown_minutes}min cooldown",
        )
    return RiskCheckResult(
        check_name="cooldown", passed=True, block_reason=None, detail="ok"
    )
