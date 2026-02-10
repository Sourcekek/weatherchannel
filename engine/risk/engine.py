"""Risk engine: runs all 10 checks (no short-circuit) and returns verdict."""

from datetime import UTC, datetime

from engine.config.schema import RiskConfig
from engine.models.risk import RiskCheckResult, RiskVerdict
from engine.models.signal import Signal
from engine.risk.checks import (
    cooldown,
    daily_loss,
    kill_switch,
    paused,
    per_city_exposure,
    position_size,
    slippage,
    time_to_resolution,
    total_exposure,
    trades_per_run,
)
from engine.risk.state_tracker import StateTracker


class RiskEngine:
    def __init__(self, risk_config: RiskConfig, state: StateTracker):
        self.config = risk_config
        self.state = state

    def evaluate(self, signal: Signal, market_end_date: str) -> RiskVerdict:
        """Run all 10 risk checks. Never short-circuits — full audit trail."""
        checks: list[RiskCheckResult] = []

        # 1. Kill switch
        checks.append(kill_switch.check(self.state.kill_switch_active))

        # 2. Paused
        checks.append(paused.check(self.state.is_paused))

        # 3. Position size
        checks.append(
            position_size.check(
                signal.proposed_size_usd, self.config.max_position_size_usd
            )
        )

        # 4. Trades per run
        checks.append(
            trades_per_run.check(
                self.state.trades_this_run, self.config.max_trades_per_run
            )
        )

        # 5. Total exposure
        checks.append(
            total_exposure.check(
                self.state.total_exposure,
                signal.proposed_size_usd,
                self.config.max_total_exposure_usd,
            )
        )

        # 6. Per-city exposure
        checks.append(
            per_city_exposure.check(
                self.state.city_exposure(signal.edge_result.city_slug),
                signal.proposed_size_usd,
                self.config.max_per_city_exposure_usd,
            )
        )

        # 7. Daily loss
        checks.append(
            daily_loss.check(self.state.daily_loss(), self.config.max_daily_loss_usd)
        )

        # 8. Cooldown
        checks.append(
            cooldown.check(
                self.state.minutes_since_last_trade(signal.market_id),
                self.config.cooldown_minutes,
            )
        )

        # 9. Time to resolution
        hours = _hours_to_resolution(market_end_date)
        checks.append(
            time_to_resolution.check(hours, self.config.min_hours_to_resolution)
        )

        # 10. Slippage
        # Need best_bid/ask from the edge result's market data
        # Signal doesn't carry these directly; use edge_result fields
        checks.append(
            slippage.check(
                signal.edge_result.market_price_yes,  # proxy: use price as bid
                signal.edge_result.market_price_yes * 1.02,  # rough ask estimate
                self.config.slippage_ceiling,
            )
        )

        approved = all(c.passed for c in checks)
        return RiskVerdict(approved=approved, checks=checks)


def _hours_to_resolution(end_date_str: str) -> float:
    """Compute hours until market end date from now."""
    try:
        end = datetime.fromisoformat(end_date_str)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        delta = end - datetime.now(UTC)
        return max(0.0, delta.total_seconds() / 3600)
    except (ValueError, TypeError):
        return 0.0
