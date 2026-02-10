"""Tests for NOAA API client with mocked httpx."""

import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from engine.ingest.noaa_client import NoaaClient

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def noaa() -> NoaaClient:
    return NoaaClient(
        base_url="https://test-noaa.example.com",
        max_retries=1,
        retry_base_delay=0.01,  # Fast retries in tests
    )


@pytest.fixture
def nyc_forecast() -> dict:
    with open(FIXTURE_DIR / "noaa_forecast_nyc.json") as f:
        return json.load(f)


class TestGetForecast:
    @respx.mock
    def test_success(self, noaa: NoaaClient, nyc_forecast: dict):
        respx.get(
            "https://test-noaa.example.com/gridpoints/OKX/37,39/forecast"
        ).mock(return_value=httpx.Response(200, json=nyc_forecast))

        result = noaa.get_forecast("OKX", 37, 39)
        assert "properties" in result
        periods = result["properties"]["periods"]
        assert len(periods) == 5

    @respx.mock
    def test_user_agent_header(self, noaa: NoaaClient, nyc_forecast: dict):
        route = respx.get(
            "https://test-noaa.example.com/gridpoints/OKX/37,39/forecast"
        ).mock(return_value=httpx.Response(200, json=nyc_forecast))

        noaa.get_forecast("OKX", 37, 39)
        assert route.called
        request = route.calls[0].request
        assert "weatherchannel" in request.headers["user-agent"]

    @respx.mock
    def test_retry_on_503(self, noaa: NoaaClient, nyc_forecast: dict):
        route = respx.get(
            "https://test-noaa.example.com/gridpoints/OKX/37,39/forecast"
        ).mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json=nyc_forecast),
            ]
        )

        with patch("engine.ingest.noaa_client.time.sleep"):
            result = noaa.get_forecast("OKX", 37, 39)
        assert "properties" in result
        assert route.call_count == 2

    @respx.mock
    def test_exhausted_retries(self, noaa: NoaaClient):
        respx.get(
            "https://test-noaa.example.com/gridpoints/OKX/37,39/forecast"
        ).mock(return_value=httpx.Response(503))

        with patch("engine.ingest.noaa_client.time.sleep"), pytest.raises(httpx.HTTPStatusError):
            noaa.get_forecast("OKX", 37, 39)
