"""Paused check: blocks if system is paused."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(is_paused: bool) -> RiskCheckResult:
    if is_paused:
        return RiskCheckResult(
            check_name="paused",
            passed=False,
            block_reason=BlockReason.PAUSED,
            detail="System is paused",
        )
    return RiskCheckResult(
        check_name="paused", passed=True, block_reason=None, detail="ok"
    )
