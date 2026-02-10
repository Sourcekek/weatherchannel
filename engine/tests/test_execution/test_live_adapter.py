"""Tests for LiveAdapter."""

import pytest
import respx
from httpx import Response

from engine.execution.live_adapter import LiveAdapter
from engine.execution.simmer_client import SimmerClient
from engine.models.execution import OrderIntent, OrderStatus

SIMMER_MARKETS_RESPONSE = {
    "markets": [
        {"id": "sim-uuid-123", "polymarket_token_id": "clob-abc"},
        {"id": "sim-uuid-456", "polymarket_token_id": "clob-def"},
    ]
}


@pytest.fixture
def simmer():
    return SimmerClient(api_key="test-key")


@pytest.fixture
def adapter(simmer):
    return LiveAdapter(simmer_client=simmer, venue="simmer")


@pytest.fixture
def sample_intent():
    return OrderIntent(
        run_id="run-1",
        idempotency_key="idem-1",
        market_id="mkt-123",
        clob_token_id="clob-abc",
        side="BUY",
        price=0.10,
        size_usd=5.00,
        city_slug="nyc",
        target_date="2026-02-11",
        bucket_label="34-35°F",
        net_edge=0.08,
    )


def _mock_market_map():
    """Mock the Simmer markets endpoint for token mapping."""
    respx.get("https://api.simmer.markets/api/sdk/markets").mock(
        return_value=Response(200, json=SIMMER_MARKETS_RESPONSE)
    )


class TestLiveAdapter:
    @respx.mock
    def test_execute_buy_success(self, adapter, sample_intent):
        _mock_market_map()
        respx.post("https://api.simmer.markets/api/sdk/trade").mock(
            return_value=Response(200, json={
                "success": True,
                "trade_id": "trade-1",
                "shares_bought": 50.0,
                "fill_price": 0.10,
            })
        )
        result = adapter.execute(sample_intent)
        assert result.status == OrderStatus.FILLED
        assert result.fill_price == 0.10
        assert result.fill_size == 50.0
        assert result.error_message == ""

    @respx.mock
    def test_execute_buy_rejected(self, adapter, sample_intent):
        _mock_market_map()
        respx.post("https://api.simmer.markets/api/sdk/trade").mock(
            return_value=Response(200, json={
                "success": False,
                "error": "Market closed",
            })
        )
        result = adapter.execute(sample_intent)
        assert result.status == OrderStatus.REJECTED
        assert "Market closed" in result.error_message

    @respx.mock
    def test_execute_buy_api_failure(self, adapter, sample_intent):
        _mock_market_map()
        respx.post("https://api.simmer.markets/api/sdk/trade").mock(
            return_value=Response(500, text="Internal Server Error")
        )
        result = adapter.execute(sample_intent)
        assert result.status == OrderStatus.FAILED
        assert "500" in result.error_message

    @respx.mock
    def test_execute_no_simmer_mapping(self, adapter):
        """If CLOB token doesn't map to any Simmer market, reject gracefully."""
        _mock_market_map()
        intent = OrderIntent(
            run_id="run-1",
            idempotency_key="idem-unmapped",
            market_id="mkt-999",
            clob_token_id="unknown-token",
            side="BUY",
            price=0.10,
            size_usd=5.00,
            city_slug="nyc",
            target_date="2026-02-11",
            bucket_label="99°F",
            net_edge=0.05,
        )
        result = adapter.execute(intent)
        assert result.status == OrderStatus.REJECTED
        assert "No Simmer market" in result.error_message

    @respx.mock
    def test_execute_sell_success(self, adapter):
        _mock_market_map()
        respx.post("https://api.simmer.markets/api/sdk/trade").mock(
            return_value=Response(200, json={
                "success": True,
                "trade_id": "sell-1",
                "shares_sold": 25.0,
                "fill_price": 0.50,
            })
        )
        result = adapter.execute_sell(
            market_id="mkt-123",
            shares=25.0,
            idempotency_key="sell-idem-1",
            clob_token_id="clob-abc",
        )
        assert result.status == OrderStatus.FILLED
        assert result.fill_price == 0.50

    @respx.mock
    def test_execute_sell_failure(self, adapter):
        _mock_market_map()
        respx.post("https://api.simmer.markets/api/sdk/trade").mock(
            return_value=Response(400, json={"error": "No shares to sell"})
        )
        result = adapter.execute_sell(
            market_id="mkt-123",
            shares=25.0,
            idempotency_key="sell-idem-2",
            clob_token_id="clob-abc",
        )
        assert result.status == OrderStatus.FAILED
