"""Tests for Gamma API client with mocked httpx."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from engine.ingest.gamma_client import GammaClient

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def gamma() -> GammaClient:
    return GammaClient(base_url="https://test-gamma.example.com")


@pytest.fixture
def nyc_fixture() -> list[dict]:
    with open(FIXTURE_DIR / "gamma_response_nyc_feb11.json") as f:
        return json.load(f)


class TestGetEventBySlug:
    @respx.mock
    def test_success(self, gamma: GammaClient, nyc_fixture: list[dict]):
        respx.get(
            "https://test-gamma.example.com/events",
            params={"slug": "test-slug"},
        ).mock(return_value=httpx.Response(200, json=nyc_fixture))

        result = gamma.get_event_by_slug("test-slug")
        assert result is not None
        assert result["id"] == "evt_123"

    @respx.mock
    def test_not_found(self, gamma: GammaClient):
        respx.get(
            "https://test-gamma.example.com/events",
            params={"slug": "nonexistent"},
        ).mock(return_value=httpx.Response(404))

        result = gamma.get_event_by_slug("nonexistent")
        assert result is None

    @respx.mock
    def test_empty_list(self, gamma: GammaClient):
        respx.get(
            "https://test-gamma.example.com/events",
            params={"slug": "empty"},
        ).mock(return_value=httpx.Response(200, json=[]))

        result = gamma.get_event_by_slug("empty")
        assert result is None

    @respx.mock
    def test_server_error(self, gamma: GammaClient):
        respx.get(
            "https://test-gamma.example.com/events",
            params={"slug": "error"},
        ).mock(return_value=httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            gamma.get_event_by_slug("error")


class TestGetActiveWeatherEvents:
    @respx.mock
    def test_skips_missing(self, gamma: GammaClient, nyc_fixture: list[dict]):
        respx.get(
            "https://test-gamma.example.com/events",
            params={"slug": "found"},
        ).mock(return_value=httpx.Response(200, json=nyc_fixture))

        respx.get(
            "https://test-gamma.example.com/events",
            params={"slug": "missing"},
        ).mock(return_value=httpx.Response(404))

        results = gamma.get_active_weather_events(["found", "missing"])
        assert len(results) == 1

    @respx.mock
    def test_skips_errors(self, gamma: GammaClient):
        respx.get(
            "https://test-gamma.example.com/events",
            params={"slug": "error"},
        ).mock(return_value=httpx.Response(500))

        results = gamma.get_active_weather_events(["error"])
        assert len(results) == 0
