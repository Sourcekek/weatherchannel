"""Signal generator: orchestrates probability + edge computation for events."""

import logging

from engine.config.schema import EngineConfig
from engine.models.forecast import ForecastPoint
from engine.models.market import MarketEvent
from engine.models.signal import EdgeResult, ReasonCode, Signal
from engine.signal.calibration import compute_sigma
from engine.signal.edge_calculator import compute_edge
from engine.signal.probability import bucket_probability

logger = logging.getLogger(__name__)


class SignalGenerator:
    def __init__(self, config: EngineConfig, run_id: str):
        self.config = config
        self.run_id = run_id

    def generate(
        self,
        events: list[MarketEvent],
        forecasts: dict[tuple[str, str], ForecastPoint],
    ) -> list[EdgeResult]:
        """Generate edge results for all bucket markets across events.

        Args:
            events: Market events to analyze.
            forecasts: Map of (city_slug, target_date) -> ForecastPoint.

        Returns:
            List of EdgeResult sorted by net_edge descending.
        """
        results: list[EdgeResult] = []

        for event in events:
            forecast = forecasts.get((event.city_slug, event.target_date))
            if forecast is None:
                # Generate NO_FORECAST_AVAILABLE for all buckets
                for bm in event.buckets:
                    results.append(
                        EdgeResult(
                            run_id=self.run_id,
                            event_id=event.event_id,
                            market_id=bm.market_id,
                            city_slug=event.city_slug,
                            target_date=event.target_date,
                            bucket_label=bm.group_item_title,
                            bucket_probability=0.0,
                            market_price_yes=bm.outcome_price_yes,
                            gross_edge=0.0,
                            fee_estimate=0.0,
                            slippage_estimate=0.0,
                            net_edge=0.0,
                            reason_code=ReasonCode.NO_FORECAST_AVAILABLE,
                            sigma_used=0.0,
                        )
                    )
                continue

            mu = float(forecast.high_temp_f)
            sigma = compute_sigma(
                event.target_date,
                base=self.config.strategy.uncertainty_base_f,
                per_day=self.config.strategy.uncertainty_per_day_f,
            )

            for bm in event.buckets:
                prob = bucket_probability(bm.bucket, mu, sigma)
                er = compute_edge(
                    run_id=self.run_id,
                    event_id=event.event_id,
                    market_id=bm.market_id,
                    city_slug=event.city_slug,
                    target_date=event.target_date,
                    bucket_label=bm.group_item_title,
                    bucket_probability=prob,
                    market_price_yes=bm.outcome_price_yes,
                    fee_estimate=self.config.strategy.fee_estimate,
                    slippage_estimate=self.config.strategy.slippage_estimate,
                    sigma_used=sigma,
                    min_edge_threshold=self.config.strategy.min_edge_threshold,
                    max_entry_price=self.config.strategy.max_entry_price,
                    accepting_orders=bm.accepting_orders,
                    liquidity=bm.liquidity,
                )
                results.append(er)

        # Sort by net_edge descending
        results.sort(key=lambda r: r.net_edge, reverse=True)
        return results

    def filter_opportunities(self, results: list[EdgeResult]) -> list[EdgeResult]:
        """Filter edge results to only opportunities."""
        return [r for r in results if r.reason_code == ReasonCode.OPPORTUNITY]

    def to_signals(
        self,
        opportunities: list[EdgeResult],
        events: list[MarketEvent],
    ) -> list[Signal]:
        """Convert opportunities to executable signals."""
        # Build market lookup
        market_map: dict[str, dict] = {}
        for event in events:
            for bm in event.buckets:
                market_map[bm.market_id] = {
                    "clob_token_id_yes": bm.clob_token_id_yes,
                    "best_ask": bm.best_ask,
                }

        signals: list[Signal] = []
        for opp in opportunities:
            mkt = market_map.get(opp.market_id)
            if mkt is None:
                continue
            signals.append(
                Signal(
                    edge_result=opp,
                    market_id=opp.market_id,
                    clob_token_id_yes=mkt["clob_token_id_yes"],
                    proposed_size_usd=self.config.risk.max_position_size_usd,
                )
            )
        return signals
