"""Tests for ExitPipeline."""

import sqlite3

import pytest
import respx
from httpx import Response

from engine.config.defaults import DEFAULT_CITIES
from engine.config.schema import EngineConfig
from engine.pipeline.exit_pipeline import ExitPipeline
from engine.storage import position_repo, state_repo
from engine.storage.database import run_migrations


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    return conn


@pytest.fixture
def config():
    return EngineConfig(cities=DEFAULT_CITIES)


@pytest.fixture
def pipeline(config, db):
    from engine.ingest.gamma_client import GammaClient
    return ExitPipeline(config, db, GammaClient(), "run-exit-1")


class TestExitPipeline:
    def test_no_positions_returns_empty(self, pipeline):
        summary = pipeline.run()
        assert summary["positions_checked"] == 0
        assert summary["exits_found"] == 0

    def test_respects_kill_switch(self, pipeline, db):
        state_repo.set_system_state(db, "kill_switch", "true")
        position_repo.save_position(db, "mkt-1", "nyc", "2026-02-11", "34-35°F", 0.10, 5.0)
        summary = pipeline.run()
        assert summary["positions_checked"] == 0

    def test_respects_paused(self, pipeline, db):
        state_repo.set_system_state(db, "paused", "true")
        position_repo.save_position(db, "mkt-1", "nyc", "2026-02-11", "34-35°F", 0.10, 5.0)
        summary = pipeline.run()
        assert summary["positions_checked"] == 0

    @respx.mock
    def test_exit_when_above_threshold(self, pipeline, db, config):
        position_repo.save_position(db, "mkt-1", "nyc", "2026-02-11", "34-35°F", 0.10, 5.0)

        # Mock Gamma API returning price above exit threshold
        respx.get("https://gamma-api.polymarket.com/markets/mkt-1").mock(
            return_value=Response(200, json={
                "outcomePrices": '["0.55", "0.45"]',
            })
        )

        summary = pipeline.run()
        assert summary["positions_checked"] == 1
        assert summary["exits_found"] == 1
        assert summary["exits_executed"] == 1

        # Position should be closed
        open_positions = position_repo.get_open_positions(db)
        assert len(open_positions) == 0

    @respx.mock
    def test_hold_when_below_threshold(self, pipeline, db):
        position_repo.save_position(db, "mkt-1", "nyc", "2026-02-11", "34-35°F", 0.10, 5.0)

        respx.get("https://gamma-api.polymarket.com/markets/mkt-1").mock(
            return_value=Response(200, json={
                "outcomePrices": '["0.20", "0.80"]',
            })
        )

        summary = pipeline.run()
        assert summary["positions_checked"] == 1
        assert summary["exits_found"] == 0
        assert summary["prices_updated"] == 1

        # Position should still be open with updated price
        positions = position_repo.get_open_positions(db)
        assert len(positions) == 1

    @respx.mock
    def test_mark_to_market_updates_price(self, pipeline, db):
        position_repo.save_position(db, "mkt-1", "nyc", "2026-02-11", "34-35°F", 0.10, 5.0)

        respx.get("https://gamma-api.polymarket.com/markets/mkt-1").mock(
            return_value=Response(200, json={
                "outcomePrices": '["0.20", "0.80"]',
            })
        )

        pipeline.run()

        # Check price was updated
        positions = position_repo.get_open_positions_with_ids(db)
        assert len(positions) == 1
        assert positions[0]["current_price"] == pytest.approx(0.20)
        # PnL: (0.20 - 0.10) / 0.10 * 5.0 = 5.0
        assert positions[0]["unrealized_pnl"] == pytest.approx(5.0)
