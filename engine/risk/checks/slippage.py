"""Slippage check: blocks if bid-ask spread exceeds ceiling."""

from engine.models.risk import BlockReason, RiskCheckResult


def check(best_bid: float, best_ask: float, slippage_ceiling: float) -> RiskCheckResult:
    if best_bid <= 0:
        return RiskCheckResult(
            check_name="slippage",
            passed=False,
            block_reason=BlockReason.SLIPPAGE,
            detail="Best bid is zero or negative",
        )
    spread = (best_ask - best_bid) / best_bid
    if spread > slippage_ceiling:
        return RiskCheckResult(
            check_name="slippage",
            passed=False,
            block_reason=BlockReason.SLIPPAGE,
            detail=f"Spread {spread:.4f} > ceiling {slippage_ceiling:.4f}",
        )
    return RiskCheckResult(
        check_name="slippage", passed=True, block_reason=None, detail="ok"
    )
