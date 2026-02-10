"""Tests for risk engine: all pass, single fail, kill switch override."""

import sqlite3
from pathlib import Path

from engine.config.schema import RiskConfig
from engine.models.signal import EdgeResult, ReasonCode, Signal
from engine.risk.engine import RiskEngine
from engine.risk.state_tracker import StateTracker
from engine.storage.database import connect, run_migrations


def _make_signal(city_slug: str = "nyc") -> Signal:
    er = EdgeResult(
        run_id="run1",
        event_id="e1",
        market_id="m1",
        city_slug=city_slug,
        target_date="2026-02-11",
        bucket_label="36-37F",
        bucket_probability=0.26,
        market_price_yes=0.075,
        gross_edge=0.185,
        fee_estimate=0.02,
        slippage_estimate=0.01,
        net_edge=0.155,
        reason_code=ReasonCode.OPPORTUNITY,
        sigma_used=2.5,
    )
    return Signal(
        edge_result=er,
        market_id="m1",
        clob_token_id_yes="tok_yes",
        proposed_size_usd=5.0,
    )


def _make_db(tmp_path: Path) -> sqlite3.Connection:
    conn = connect(tmp_path / "test.db")
    run_migrations(conn)
    return conn


class TestRiskEngine:
    def test_all_checks_pass(self, tmp_path: Path):
        db = _make_db(tmp_path)
        state = StateTracker(db)
        state.hydrate()

        engine = RiskEngine(RiskConfig(), state)
        signal = _make_signal()
        # Use a far-future end date
        verdict = engine.evaluate(signal, "2099-12-31T23:59:59Z")

        assert verdict.approved is True
        assert len(verdict.checks) == 10
        assert all(c.passed for c in verdict.checks)

    def test_kill_switch_blocks(self, tmp_path: Path):
        db = _make_db(tmp_path)
        db.execute(
            "UPDATE system_state SET value = 'true' WHERE key = 'kill_switch'"
        )
        db.commit()

        state = StateTracker(db)
        state.hydrate()

        engine = RiskEngine(RiskConfig(), state)
        verdict = engine.evaluate(_make_signal(), "2099-12-31T23:59:59Z")

        assert verdict.approved is False
        assert any(
            r.block_reason is not None and r.block_reason.value == "KILL_SWITCH"
            for r in verdict.checks
        )
        # All 10 checks still ran (no short-circuit)
        assert len(verdict.checks) == 10

    def test_trades_per_run_blocks(self, tmp_path: Path):
        db = _make_db(tmp_path)
        state = StateTracker(db)
        state.hydrate()
        state.trades_this_run = 3  # Exceeds default max of 3

        engine = RiskEngine(RiskConfig(), state)
        verdict = engine.evaluate(_make_signal(), "2099-12-31T23:59:59Z")

        assert verdict.approved is False
        assert len(verdict.block_reasons) >= 1

    def test_near_resolution_blocks(self, tmp_path: Path):
        db = _make_db(tmp_path)
        state = StateTracker(db)
        state.hydrate()

        engine = RiskEngine(RiskConfig(), state)
        # End date in 1 hour (less than 6h minimum)
        from datetime import UTC, datetime, timedelta
        soon = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        verdict = engine.evaluate(_make_signal(), soon)

        assert verdict.approved is False
        assert any(
            r.block_reason is not None
            and r.block_reason.value == "TIME_TO_RESOLUTION"
            for r in verdict.checks
        )

    def test_state_tracker_record_trade(self, tmp_path: Path):
        db = _make_db(tmp_path)
        state = StateTracker(db)
        state.hydrate()

        assert state.trades_this_run == 0
        state.record_trade("nyc", 5.0)
        assert state.trades_this_run == 1
