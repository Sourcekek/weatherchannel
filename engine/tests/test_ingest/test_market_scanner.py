"""Tests for market scanner with mocked Gamma client."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from engine.config.defaults import DEFAULT_CITIES
from engine.config.schema import EngineConfig, OpsConfig
from engine.ingest.gamma_client import GammaClient
from engine.ingest.market_scanner import MarketScanner

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def _load_fixture(name: str) -> list[dict]:
    with open(FIXTURE_DIR / name) as f:
        return json.load(f)


class TestMarketScanner:
    def test_scan_finds_events(self):
        nyc_data = _load_fixture("gamma_response_nyc_feb11.json")

        mock_gamma = MagicMock(spec=GammaClient)
        mock_gamma.get_event_by_slug.return_value = nyc_data[0]

        config = EngineConfig(
            cities=DEFAULT_CITIES[:1],  # Just NYC
            ops=OpsConfig(lookahead_days=2, request_delay_ms=0),
        )
        scanner = MarketScanner(config, mock_gamma)
        results = scanner.scan(today=date(2026, 2, 10))

        # 1 city x 2 days = 2 calls
        assert mock_gamma.get_event_by_slug.call_count == 2
        assert len(results) == 2  # Both days return the same fixture

        event, raw_json = results[0]
        assert event.event_id == "evt_123"
        assert len(event.buckets) == 4  # 4 bucket markets in fixture

    def test_scan_skips_missing(self):
        mock_gamma = MagicMock(spec=GammaClient)
        mock_gamma.get_event_by_slug.return_value = None

        config = EngineConfig(
            cities=DEFAULT_CITIES[:1],
            ops=OpsConfig(lookahead_days=1, request_delay_ms=0),
        )
        scanner = MarketScanner(config, mock_gamma)
        results = scanner.scan(today=date(2026, 2, 10))
        assert len(results) == 0

    def test_scan_skips_errors(self):
        mock_gamma = MagicMock(spec=GammaClient)
        mock_gamma.get_event_by_slug.side_effect = Exception("API down")

        config = EngineConfig(
            cities=DEFAULT_CITIES[:1],
            ops=OpsConfig(lookahead_days=1, request_delay_ms=0),
        )
        scanner = MarketScanner(config, mock_gamma)
        results = scanner.scan(today=date(2026, 2, 10))
        assert len(results) == 0

    def test_scan_multiple_cities(self):
        nyc_data = _load_fixture("gamma_response_nyc_feb11.json")

        mock_gamma = MagicMock(spec=GammaClient)
        mock_gamma.get_event_by_slug.return_value = nyc_data[0]

        config = EngineConfig(
            cities=DEFAULT_CITIES[:2],  # NYC + Chicago
            ops=OpsConfig(lookahead_days=1, request_delay_ms=0),
        )
        scanner = MarketScanner(config, mock_gamma)
        results = scanner.scan(today=date(2026, 2, 10))
        # 2 cities x 1 day = 2 calls
        assert mock_gamma.get_event_by_slug.call_count == 2
        assert len(results) == 2

    def test_disabled_city_skipped(self):
        mock_gamma = MagicMock(spec=GammaClient)

        cities = [DEFAULT_CITIES[0].model_copy(update={"enabled": False})]
        config = EngineConfig(
            cities=cities,
            ops=OpsConfig(lookahead_days=1, request_delay_ms=0),
        )
        scanner = MarketScanner(config, mock_gamma)
        results = scanner.scan(today=date(2026, 2, 10))
        assert mock_gamma.get_event_by_slug.call_count == 0
        assert len(results) == 0
