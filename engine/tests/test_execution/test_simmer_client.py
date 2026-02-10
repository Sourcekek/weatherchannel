"""Tests for SimmerClient."""

import pytest
import respx
from httpx import Response

from engine.execution.simmer_client import SimmerClient, SimmerClientError


@pytest.fixture
def client():
    return SimmerClient(api_key="test-key-123")


class TestSimmerClient:
    @respx.mock
    def test_buy_success(self, client):
        respx.post("https://api.simmer.markets/api/sdk/trade").mock(
            return_value=Response(200, json={
                "success": True,
                "trade_id": "trade-abc",
                "shares_bought": 50.0,
                "fill_price": 0.10,
            })
        )
        result = client.buy(market_id="mkt-1", amount_usd=5.0)
        assert result["success"] is True
        assert result["trade_id"] == "trade-abc"
        assert result["shares_bought"] == 50.0

    @respx.mock
    def test_buy_api_error(self, client):
        respx.post("https://api.simmer.markets/api/sdk/trade").mock(
            return_value=Response(400, json={"error": "Insufficient funds"})
        )
        with pytest.raises(SimmerClientError, match="400"):
            client.buy(market_id="mkt-1", amount_usd=5.0)

    @respx.mock
    def test_sell_success(self, client):
        respx.post("https://api.simmer.markets/api/sdk/trade").mock(
            return_value=Response(200, json={
                "success": True,
                "trade_id": "trade-sell",
                "shares_sold": 25.0,
                "fill_price": 0.50,
            })
        )
        result = client.sell(market_id="mkt-1", shares=25.0)
        assert result["success"] is True

    @respx.mock
    def test_get_portfolio(self, client):
        respx.get("https://api.simmer.markets/api/sdk/portfolio").mock(
            return_value=Response(200, json={
                "balance_usdc": 100.0,
                "total_exposure": 25.0,
                "positions_count": 3,
            })
        )
        result = client.get_portfolio()
        assert result["balance_usdc"] == 100.0

    @respx.mock
    def test_get_positions(self, client):
        respx.get("https://api.simmer.markets/api/sdk/positions").mock(
            return_value=Response(200, json={
                "positions": [
                    {"market_id": "m1", "shares_yes": 10, "pnl": 0.5},
                ]
            })
        )
        positions = client.get_positions()
        assert len(positions) == 1
        assert positions[0]["market_id"] == "m1"

    def test_no_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("SIMMER_API_KEY", raising=False)
        with pytest.raises(SimmerClientError, match="not set"):
            SimmerClient(api_key="")

    @respx.mock
    def test_get_weather_markets(self, client):
        respx.get("https://api.simmer.markets/api/markets").mock(
            return_value=Response(200, json={
                "markets": [
                    {"id": "m1", "event_name": "NYC Feb 11"},
                    {"id": "m2", "event_name": "Chicago Feb 11"},
                ]
            })
        )
        markets = client.get_weather_markets()
        assert len(markets) == 2
