"""Trades per run check: blocks if max trades reached."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(trades_this_run: int, max_trades_per_run: int) -> RiskCheckResult:
    if trades_this_run >= max_trades_per_run:
        return RiskCheckResult(
            check_name="trades_per_run",
            passed=False,
            block_reason=BlockReason.TRADES_PER_RUN,
            detail=f"{trades_this_run} >= limit {max_trades_per_run}",
        )
    return RiskCheckResult(
        check_name="trades_per_run", passed=True, block_reason=None, detail="ok"
    )
