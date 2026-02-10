"""NOAA forecast data models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastPeriod:
    name: str
    start_time: str
    end_time: str
    temperature: int
    temperature_unit: str
    is_daytime: bool
    short_forecast: str


@dataclass(frozen=True)
class ForecastPoint:
    city_slug: str
    target_date: str  # YYYY-MM-DD
    high_temp_f: int
    source_generated_at: str
    fetched_at: str
    raw_periods: list[ForecastPeriod]
