"""Tests for executor, dry-run adapter, idempotency, and live adapter."""

import sqlite3
from pathlib import Path

import pytest

from engine.execution.dry_run import DryRunAdapter
from engine.execution.executor import Executor
from engine.execution.idempotency import IdempotencyChecker, generate_idempotency_key
from engine.execution.live_adapter import LiveAdapter
from engine.models.execution import OrderIntent, OrderStatus
from engine.storage.database import connect, run_migrations


def _make_db(tmp_path: Path) -> sqlite3.Connection:
    conn = connect(tmp_path / "test.db")
    run_migrations(conn)
    return conn


def _make_intent(
    idem_key: str = "test_key_001", run_id: str = "run1"
) -> OrderIntent:
    return OrderIntent(
        run_id=run_id,
        idempotency_key=idem_key,
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


class TestIdempotencyKey:
    def test_deterministic(self):
        k1 = generate_idempotency_key("run1", "m1", "BUY", 0.075)
        k2 = generate_idempotency_key("run1", "m1", "BUY", 0.075)
        assert k1 == k2

    def test_different_run(self):
        k1 = generate_idempotency_key("run1", "m1", "BUY", 0.075)
        k2 = generate_idempotency_key("run2", "m1", "BUY", 0.075)
        assert k1 != k2

    def test_different_price(self):
        k1 = generate_idempotency_key("run1", "m1", "BUY", 0.075)
        k2 = generate_idempotency_key("run1", "m1", "BUY", 0.080)
        assert k1 != k2

    def test_length(self):
        k = generate_idempotency_key("run1", "m1", "BUY", 0.075)
        assert len(k) == 32


class TestIdempotencyChecker:
    def test_not_duplicate(self, tmp_path: Path):
        db = _make_db(tmp_path)
        checker = IdempotencyChecker(db)
        assert checker.is_duplicate("new_key") is False

    def test_duplicate_after_insert(self, tmp_path: Path):
        db = _make_db(tmp_path)
        checker = IdempotencyChecker(db)

        from engine.storage import order_repo
        order_repo.save_order_intent(db, _make_intent("dup_key"))

        assert checker.is_duplicate("dup_key") is True


class TestDryRunAdapter:
    def test_returns_dry_run_status(self):
        adapter = DryRunAdapter()
        intent = _make_intent()
        result = adapter.execute(intent)

        assert result.status == OrderStatus.DRY_RUN
        assert result.fill_price == 0.075
        assert result.fill_size == 5.0
        assert result.error_message == ""


class TestLiveAdapter:
    def test_raises_not_implemented(self):
        adapter = LiveAdapter()
        with pytest.raises(NotImplementedError, match="Gate B"):
            adapter.execute(_make_intent())


class TestExecutor:
    def test_dry_run_success(self, tmp_path: Path):
        db = _make_db(tmp_path)
        executor = Executor(db, DryRunAdapter())
        result = executor.execute(_make_intent())

        assert result.status == OrderStatus.DRY_RUN
        assert result.fill_price == 0.075

    def test_duplicate_rejected(self, tmp_path: Path):
        db = _make_db(tmp_path)
        executor = Executor(db, DryRunAdapter())
        intent = _make_intent("dup_test")

        r1 = executor.execute(intent)
        assert r1.status == OrderStatus.DRY_RUN

        r2 = executor.execute(intent)
        assert r2.status == OrderStatus.DUPLICATE

    def test_kill_switch_blocks(self, tmp_path: Path):
        db = _make_db(tmp_path)
        db.execute(
            "UPDATE system_state SET value = 'true' WHERE key = 'kill_switch'"
        )
        db.commit()

        executor = Executor(db, DryRunAdapter())
        result = executor.execute(_make_intent())

        assert result.status == OrderStatus.REJECTED
        assert "Kill switch" in result.error_message

    def test_live_adapter_fails_gracefully(self, tmp_path: Path):
        db = _make_db(tmp_path)
        executor = Executor(db, LiveAdapter())
        result = executor.execute(_make_intent())

        assert result.status == OrderStatus.FAILED
        assert "Gate B" in result.error_message
