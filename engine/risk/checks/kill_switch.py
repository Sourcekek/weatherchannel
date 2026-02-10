"""Kill switch check: blocks if emergency stop is active."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(kill_switch_active: bool) -> RiskCheckResult:
    if kill_switch_active:
        return RiskCheckResult(
            check_name="kill_switch",
            passed=False,
            block_reason=BlockReason.KILL_SWITCH,
            detail="Kill switch is active",
        )
    return RiskCheckResult(
        check_name="kill_switch", passed=True, block_reason=None, detail="ok"
    )
