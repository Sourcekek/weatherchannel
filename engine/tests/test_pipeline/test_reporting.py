"""Tests for reporting: summarizer, formatters."""

from engine.models.execution import OrderResult, OrderStatus
from engine.models.reporting import RunSummary
from engine.models.risk import BlockReason, RiskCheckResult, RiskVerdict
from engine.models.signal import EdgeResult, ReasonCode
from engine.reporting.formatters import (
    format_summary_chat,
    format_summary_json,
    format_summary_text,
)
from engine.reporting.run_summarizer import RunSummarizer


def _make_edge(net_edge: float = 0.15, reason: ReasonCode = ReasonCode.OPPORTUNITY):
    return EdgeResult(
        run_id="run1",
        event_id="e1",
        market_id="m1",
        city_slug="nyc",
        target_date="2026-02-11",
        bucket_label="36-37F",
        bucket_probability=0.26,
        market_price_yes=0.075,
        gross_edge=0.185,
        fee_estimate=0.02,
        slippage_estimate=0.01,
        net_edge=net_edge,
        reason_code=reason,
        sigma_used=2.5,
    )


class TestRunSummarizer:
    def test_basic_flow(self):
        s = RunSummarizer("run1", "dry-run")
        s.record_scan(5, 10)
        s.record_edge_results([
            _make_edge(0.15),
            _make_edge(-0.05, ReasonCode.NEGATIVE_EDGE),
        ])

        verdict = RiskVerdict(approved=True, checks=[
            RiskCheckResult("kill_switch", True, None, "ok"),
        ])
        s.record_risk_verdict(verdict)

        result = OrderResult(
            idempotency_key="k1",
            status=OrderStatus.DRY_RUN,
            fill_price=0.075,
            fill_size=5.0,
            error_message="",
            executed_at="2026-02-10T15:00:00Z",
        )
        s.record_order_result(result)
        s.record_exposure(8.50, -1.20)
        s.record_duration(2.5)

        summary = s.finalize()
        assert summary.cities_scanned == 5
        assert summary.events_found == 10
        assert summary.opportunities_found == 1
        assert summary.orders_succeeded == 1
        assert summary.best_edge == 0.15

    def test_blocked_counts(self):
        s = RunSummarizer("run1", "dry-run")
        verdict = RiskVerdict(approved=False, checks=[
            RiskCheckResult("daily_loss", False, BlockReason.DAILY_LOSS, "over"),
        ])
        s.record_risk_verdict(verdict)
        summary = s.finalize()
        assert summary.blocked_count == 1
        assert summary.block_reasons["DAILY_LOSS"] == 1


class TestFormatters:
    def test_text_format(self):
        summary = RunSummary(
            run_id="abc12345-test",
            mode="dry-run",
            cities_scanned=5,
            events_found=10,
            buckets_analyzed=70,
            opportunities_found=3,
            orders_attempted=2,
            orders_succeeded=2,
            best_edge=0.187,
            best_edge_label="NYC 36-37F $0.075",
            total_exposure_usd=8.50,
            daily_pnl_usd=-1.20,
            duration_seconds=3.2,
        )
        text = format_summary_text(summary)
        assert "dry-run" in text
        assert "abc12345" in text
        assert "+0.187" in text

    def test_json_format(self):
        summary = RunSummary(run_id="test", mode="dry-run")
        j = format_summary_json(summary)
        import json
        data = json.loads(j)
        assert data["run_id"] == "test"

    def test_chat_format(self):
        summary = RunSummary(
            run_id="abc123",
            mode="dry-run",
            cities_scanned=5,
            events_found=10,
            buckets_analyzed=70,
            opportunities_found=3,
        )
        chat = format_summary_chat(summary)
        assert "**Scan Complete**" in chat
        assert "dry-run" in chat
