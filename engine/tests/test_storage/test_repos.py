"""Tests for all repository CRUD operations."""

import sqlite3
from pathlib import Path

import pytest

from engine.models.execution import OrderIntent, OrderResult, OrderStatus
from engine.models.market import (
    BucketMarket,
    BucketType,
    MarketEvent,
    TemperatureBucket,
)
from engine.models.risk import BlockReason, RiskCheckResult
from engine.models.signal import EdgeResult, ReasonCode
from engine.storage import (
    forecast_repo,
    market_repo,
    order_repo,
    position_repo,
    risk_repo,
    signal_repo,
    state_repo,
)
from engine.storage.database import connect, run_migrations


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    conn = connect(tmp_path / "test.db")
    run_migrations(conn)
    return conn


def _make_event() -> MarketEvent:
    bucket = TemperatureBucket(bucket_type=BucketType.RANGE, low=36, high=37)
    bm = BucketMarket(
        market_id="m1",
        condition_id="c1",
        clob_token_id_yes="tok_yes",
        clob_token_id_no="tok_no",
        outcome_price_yes=0.10,
        best_bid=0.09,
        best_ask=0.11,
        last_trade_price=0.10,
        liquidity=100.0,
        volume_24hr=50.0,
        maker_base_fee=0.0,
        taker_base_fee=0.02,
        order_min_size=1.0,
        accepting_orders=True,
        end_date="2026-02-11T12:00:00Z",
        group_item_title="36-37°F",
        group_item_threshold="3",
        bucket=bucket,
    )
    return MarketEvent(
        event_id="e1",
        slug="test-slug",
        city_slug="nyc",
        target_date="2026-02-11",
        title="Test Event",
        buckets=[bm],
    )


class TestMarketRepo:
    def test_save_and_retrieve(self, db: sqlite3.Connection):
        event = _make_event()
        row_id = market_repo.save_market_event(db, event, '{"raw": true}')
        assert row_id > 0

        latest = market_repo.get_latest_market_event(db, "nyc", "2026-02-11")
        assert latest is not None
        assert latest["event_id"] == "e1"

        buckets = market_repo.get_bucket_markets_for_event(db, row_id)
        assert len(buckets) == 1
        assert buckets[0]["market_id"] == "m1"
        assert buckets[0]["bucket_type"] == "range"

    def test_not_found(self, db: sqlite3.Connection):
        assert market_repo.get_latest_market_event(db, "zzz", "2099-01-01") is None


class TestForecastRepo:
    def test_save_and_retrieve(self, db: sqlite3.Connection):
        row_id = forecast_repo.save_forecast(
            db, "nyc", "2026-02-11", 38, "2026-02-10T12:00:00Z", '{"raw": true}'
        )
        assert row_id > 0

        latest = forecast_repo.get_latest_forecast(db, "nyc", "2026-02-11")
        assert latest is not None
        assert latest["high_temp_f"] == 38

    def test_not_found(self, db: sqlite3.Connection):
        assert forecast_repo.get_latest_forecast(db, "zzz", "2099-01-01") is None


class TestSignalRepo:
    def test_save_and_retrieve(self, db: sqlite3.Connection):
        er = EdgeResult(
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
            net_edge=0.155,
            reason_code=ReasonCode.OPPORTUNITY,
            sigma_used=2.5,
        )
        row_id = signal_repo.save_edge_result(db, er)
        assert row_id > 0

        results = signal_repo.get_edge_results_for_run(db, "run1")
        assert len(results) == 1
        assert results[0]["net_edge"] == 0.155


class TestRiskRepo:
    def test_save_and_retrieve(self, db: sqlite3.Connection):
        checks = [
            RiskCheckResult("kill_switch", True, None, "ok"),
            RiskCheckResult("position_size", False, BlockReason.POSITION_SIZE, "too large"),
        ]
        risk_repo.save_risk_checks(db, "run1", "key1", checks)
        results = risk_repo.get_risk_checks_for_intent(db, "key1")
        assert len(results) == 2
        assert results[1]["block_reason"] == "POSITION_SIZE"


class TestOrderRepo:
    def test_save_intent_and_result(self, db: sqlite3.Connection):
        intent = OrderIntent(
            run_id="run1",
            idempotency_key="idem1",
            market_id="m1",
            clob_token_id="tok_yes",
            side="BUY",
            price=0.075,
            size_usd=5.0,
            city_slug="nyc",
            target_date="2026-02-11",
            bucket_label="36-37F",
            net_edge=0.155,
        )
        row_id = order_repo.save_order_intent(db, intent)
        assert row_id > 0

        found = order_repo.get_order_intent_by_key(db, "idem1")
        assert found is not None
        assert found["market_id"] == "m1"

        result = OrderResult(
            idempotency_key="idem1",
            status=OrderStatus.DRY_RUN,
            fill_price=0.075,
            fill_size=5.0,
            error_message="",
            executed_at="2026-02-10T15:00:00Z",
        )
        order_repo.save_order_result(db, result)

        results = order_repo.get_order_results_for_run(db, "run1")
        assert len(results) == 1
        assert results[0]["status"] == "DRY_RUN"

    def test_duplicate_idempotency_key_rejected(self, db: sqlite3.Connection):
        intent = OrderIntent(
            run_id="run1",
            idempotency_key="idem_dup",
            market_id="m1",
            clob_token_id="tok_yes",
            side="BUY",
            price=0.075,
            size_usd=5.0,
            city_slug="nyc",
            target_date="2026-02-11",
            bucket_label="36-37F",
            net_edge=0.155,
        )
        order_repo.save_order_intent(db, intent)
        with pytest.raises(sqlite3.IntegrityError):
            order_repo.save_order_intent(db, intent)

    def test_last_trade_time(self, db: sqlite3.Connection):
        assert order_repo.get_last_trade_time_for_market(db, "m1") is None

        intent = OrderIntent(
            run_id="run1",
            idempotency_key="trade_time_test",
            market_id="m1",
            clob_token_id="tok_yes",
            side="BUY",
            price=0.075,
            size_usd=5.0,
            city_slug="nyc",
            target_date="2026-02-11",
            bucket_label="36-37F",
            net_edge=0.155,
        )
        order_repo.save_order_intent(db, intent)
        result = OrderResult(
            idempotency_key="trade_time_test",
            status=OrderStatus.DRY_RUN,
            fill_price=0.075,
            fill_size=5.0,
            error_message="",
            executed_at="2026-02-10T15:00:00Z",
        )
        order_repo.save_order_result(db, result)
        last = order_repo.get_last_trade_time_for_market(db, "m1")
        assert last == "2026-02-10T15:00:00Z"


class TestPositionRepo:
    def test_save_and_get_open(self, db: sqlite3.Connection):
        row_id = position_repo.save_position(
            db, "m1", "nyc", "2026-02-11", "36-37F", 0.075, 5.0
        )
        assert row_id > 0
        positions = position_repo.get_open_positions(db)
        assert len(positions) == 1
        assert positions[0]["status"] == "open"

    def test_exposure(self, db: sqlite3.Connection):
        position_repo.save_position(db, "m1", "nyc", "2026-02-11", "36-37F", 0.075, 5.0)
        position_repo.save_position(db, "m2", "chicago", "2026-02-11", "30-31F", 0.10, 3.0)
        assert position_repo.get_total_open_exposure(db) == 8.0
        assert position_repo.get_city_open_exposure(db, "nyc") == 5.0

    def test_close_position(self, db: sqlite3.Connection):
        row_id = position_repo.save_position(
            db, "m1", "nyc", "2026-02-11", "36-37F", 0.075, 5.0
        )
        position_repo.close_position(db, row_id)
        open_pos = position_repo.get_open_positions(db)
        assert len(open_pos) == 0

    def test_daily_pnl(self, db: sqlite3.Connection):
        position_repo.save_daily_pnl(db, "2026-02-10", -1.20, 0.50)
        pnl = position_repo.get_daily_pnl(db, "2026-02-10")
        assert pnl is not None
        assert pnl["realized_pnl"] == -1.20
        assert pnl["total_pnl"] == pytest.approx(-0.70)

        # Upsert
        position_repo.save_daily_pnl(db, "2026-02-10", -0.50, 1.00)
        pnl = position_repo.get_daily_pnl(db, "2026-02-10")
        assert pnl["total_pnl"] == pytest.approx(0.50)


class TestStateRepo:
    def test_system_state(self, db: sqlite3.Connection):
        assert state_repo.get_mode(db) == "dry-run"
        assert state_repo.is_kill_switch_active(db) is False
        assert state_repo.is_paused(db) is False

        state_repo.set_system_state(db, "kill_switch", "true")
        assert state_repo.is_kill_switch_active(db) is True

    def test_operator_commands(self, db: sqlite3.Connection):
        row_id = state_repo.log_operator_command(db, "pause", "", "paused")
        assert row_id > 0
        cmds = state_repo.get_recent_operator_commands(db)
        assert len(cmds) == 1
        assert cmds[0]["command"] == "pause"

    def test_runs(self, db: sqlite3.Connection):
        state_repo.create_run(db, "run1", "dry-run", "hash1")
        run = state_repo.get_run(db, "run1")
        assert run is not None
        assert run["status"] == "running"

        state_repo.complete_run(
            db,
            "run1",
            "completed",
            events_found=5,
            orders_attempted=2,
        )
        run = state_repo.get_run(db, "run1")
        assert run["status"] == "completed"
        assert run["events_found"] == 5

    def test_latest_run(self, db: sqlite3.Connection):
        assert state_repo.get_latest_run(db) is None
        state_repo.create_run(db, "run1", "dry-run")
        latest = state_repo.get_latest_run(db)
        assert latest is not None
        assert latest["run_id"] == "run1"
