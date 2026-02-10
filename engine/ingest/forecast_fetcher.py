"""Forecast fetcher: retrieves and caches NOAA forecasts for target dates."""

import logging

from engine.config.schema import CityConfig
from engine.ingest.noaa_client import NoaaClient
from engine.models.common import utc_now_iso
from engine.models.forecast import ForecastPeriod, ForecastPoint

logger = logging.getLogger(__name__)


class ForecastFetcher:
    def __init__(self, noaa_client: NoaaClient):
        self.noaa = noaa_client
        self._cache: dict[tuple[str, str], ForecastPoint] = {}

    def fetch(self, city: CityConfig, target_date: str) -> ForecastPoint | None:
        """Fetch forecast for a city and target date.

        Uses in-memory cache to avoid duplicate requests within a scan cycle.
        """
        cache_key = (city.slug, target_date)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            raw = self.noaa.get_forecast(
                city.noaa_grid_id, city.noaa_grid_x, city.noaa_grid_y
            )
            point = _extract_forecast_point(raw, city.slug, target_date)
            if point is not None:
                self._cache[cache_key] = point
            return point
        except Exception:
            logger.exception(
                "Failed to fetch forecast for %s on %s",
                city.slug, target_date,
            )
            return None

    def clear_cache(self) -> None:
        self._cache.clear()


def _extract_forecast_point(
    raw: dict, city_slug: str, target_date: str
) -> ForecastPoint | None:
    """Extract the daytime high temperature for a target date from NOAA response."""
    properties = raw.get("properties", {})
    periods = properties.get("periods", [])
    generated_at = properties.get("generatedAt", "")

    parsed_periods: list[ForecastPeriod] = []
    high_temp: int | None = None

    for p in periods:
        period = ForecastPeriod(
            name=p.get("name", ""),
            start_time=p.get("startTime", ""),
            end_time=p.get("endTime", ""),
            temperature=int(p.get("temperature", 0)),
            temperature_unit=p.get("temperatureUnit", "F"),
            is_daytime=bool(p.get("isDaytime", False)),
            short_forecast=p.get("shortForecast", ""),
        )
        parsed_periods.append(period)

        # Match daytime period for target date
        if (
            period.is_daytime
            and _period_matches_date(period, target_date)
            and (high_temp is None or period.temperature > high_temp)
        ):
            high_temp = period.temperature

    if high_temp is None:
        logger.warning(
            "No daytime high found for %s on %s in %d periods",
            city_slug, target_date, len(periods),
        )
        return None

    return ForecastPoint(
        city_slug=city_slug,
        target_date=target_date,
        high_temp_f=high_temp,
        source_generated_at=generated_at,
        fetched_at=utc_now_iso(),
        raw_periods=parsed_periods,
    )


def _period_matches_date(period: ForecastPeriod, target_date: str) -> bool:
    """Check if a forecast period's start time matches the target date."""
    try:
        # NOAA times are ISO format like "2026-02-11T06:00:00-05:00"
        start = period.start_time
        # Extract just the date portion
        date_str = start[:10]
        return date_str == target_date
    except (ValueError, IndexError):
        return False
