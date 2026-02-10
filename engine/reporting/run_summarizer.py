"""Run summarizer: aggregates pipeline outputs into a RunSummary."""

from engine.models.execution import OrderResult, OrderStatus
from engine.models.reporting import RunSummary
from engine.models.risk import RiskVerdict
from engine.models.signal import EdgeResult, ReasonCode


class RunSummarizer:
    def __init__(self, run_id: str, mode: str):
        self.summary = RunSummary(run_id=run_id, mode=mode)

    def record_scan(self, cities_scanned: int, events_found: int) -> None:
        self.summary.cities_scanned = cities_scanned
        self.summary.events_found = events_found

    def record_edge_results(self, results: list[EdgeResult]) -> None:
        self.summary.buckets_analyzed = len(results)
        opps = [r for r in results if r.reason_code == ReasonCode.OPPORTUNITY]
        self.summary.opportunities_found = len(opps)
        if opps:
            best = max(opps, key=lambda r: r.net_edge)
            self.summary.best_edge = best.net_edge
            self.summary.best_edge_label = (
                f"{best.city_slug} {best.bucket_label} "
                f"${best.market_price_yes:.3f}"
            )

    def record_risk_verdict(self, verdict: RiskVerdict) -> None:
        if not verdict.approved:
            self.summary.blocked_count += 1
            for reason in verdict.block_reasons:
                key = reason.value
                self.summary.block_reasons[key] = (
                    self.summary.block_reasons.get(key, 0) + 1
                )

    def record_order_result(self, result: OrderResult) -> None:
        self.summary.orders_attempted += 1
        if result.status in (OrderStatus.DRY_RUN, OrderStatus.FILLED):
            self.summary.orders_succeeded += 1
        elif result.status in (OrderStatus.FAILED, OrderStatus.REJECTED):
            self.summary.orders_failed += 1

    def record_exposure(self, total_exposure: float, daily_pnl: float) -> None:
        self.summary.total_exposure_usd = total_exposure
        self.summary.daily_pnl_usd = daily_pnl

    def record_duration(self, seconds: float) -> None:
        self.summary.duration_seconds = seconds

    def record_error(self, error: str) -> None:
        self.summary.errors.append(error)

    def finalize(self) -> RunSummary:
        return self.summary
