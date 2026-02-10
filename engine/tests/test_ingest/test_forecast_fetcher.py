"""Tests for forecast fetcher with mocked NOAA client."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from engine.config.defaults import DEFAULT_CITIES
from engine.ingest.forecast_fetcher import ForecastFetcher
from engine.ingest.noaa_client import NoaaClient

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def _load_noaa(name: str) -> dict:
    with open(FIXTURE_DIR / name) as f:
        return json.load(f)


class TestForecastFetcher:
    def test_fetch_success(self):
        mock_noaa = MagicMock(spec=NoaaClient)
        mock_noaa.get_forecast.return_value = _load_noaa("noaa_forecast_nyc.json")

        fetcher = ForecastFetcher(mock_noaa)
        nyc = DEFAULT_CITIES[0]
        result = fetcher.fetch(nyc, "2026-02-11")

        assert result is not None
        assert result.city_slug == "nyc"
        assert result.target_date == "2026-02-11"
        assert result.high_temp_f == 38

    def test_cache_hit(self):
        mock_noaa = MagicMock(spec=NoaaClient)
        mock_noaa.get_forecast.return_value = _load_noaa("noaa_forecast_nyc.json")

        fetcher = ForecastFetcher(mock_noaa)
        nyc = DEFAULT_CITIES[0]

        r1 = fetcher.fetch(nyc, "2026-02-11")
        r2 = fetcher.fetch(nyc, "2026-02-11")

        assert r1 is not None
        assert r2 is not None
        assert r1.high_temp_f == r2.high_temp_f
        # Only one API call due to cache
        assert mock_noaa.get_forecast.call_count == 1

    def test_cache_miss_different_date(self):
        mock_noaa = MagicMock(spec=NoaaClient)
        mock_noaa.get_forecast.return_value = _load_noaa("noaa_forecast_nyc.json")

        fetcher = ForecastFetcher(mock_noaa)
        nyc = DEFAULT_CITIES[0]

        fetcher.fetch(nyc, "2026-02-11")
        fetcher.fetch(nyc, "2026-02-12")

        assert mock_noaa.get_forecast.call_count == 2

    def test_no_matching_date(self):
        mock_noaa = MagicMock(spec=NoaaClient)
        mock_noaa.get_forecast.return_value = _load_noaa("noaa_forecast_nyc.json")

        fetcher = ForecastFetcher(mock_noaa)
        nyc = DEFAULT_CITIES[0]
        # Date not in fixture periods
        result = fetcher.fetch(nyc, "2026-02-20")
        assert result is None

    def test_api_error(self):
        mock_noaa = MagicMock(spec=NoaaClient)
        mock_noaa.get_forecast.side_effect = Exception("NOAA down")

        fetcher = ForecastFetcher(mock_noaa)
        nyc = DEFAULT_CITIES[0]
        result = fetcher.fetch(nyc, "2026-02-11")
        assert result is None

    def test_chicago_forecast(self):
        mock_noaa = MagicMock(spec=NoaaClient)
        mock_noaa.get_forecast.return_value = _load_noaa(
            "noaa_forecast_chicago.json"
        )

        fetcher = ForecastFetcher(mock_noaa)
        chicago = DEFAULT_CITIES[1]
        result = fetcher.fetch(chicago, "2026-02-11")

        assert result is not None
        assert result.high_temp_f == 30

    def test_clear_cache(self):
        mock_noaa = MagicMock(spec=NoaaClient)
        mock_noaa.get_forecast.return_value = _load_noaa("noaa_forecast_nyc.json")

        fetcher = ForecastFetcher(mock_noaa)
        nyc = DEFAULT_CITIES[0]
        fetcher.fetch(nyc, "2026-02-11")
        fetcher.clear_cache()
        fetcher.fetch(nyc, "2026-02-11")

        assert mock_noaa.get_forecast.call_count == 2
