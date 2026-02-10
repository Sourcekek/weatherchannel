"""Default city configurations with pre-resolved NOAA grid coordinates."""

from engine.config.schema import CityConfig

DEFAULT_CITIES: list[CityConfig] = [
    CityConfig(
        name="New York City",
        slug="nyc",
        noaa_grid_id="OKX",
        noaa_grid_x=37,
        noaa_grid_y=39,
    ),
    CityConfig(
        name="Chicago",
        slug="chicago",
        noaa_grid_id="LOT",
        noaa_grid_x=66,
        noaa_grid_y=77,
    ),
    CityConfig(
        name="Seattle",
        slug="seattle",
        noaa_grid_id="SEW",
        noaa_grid_x=124,
        noaa_grid_y=61,
    ),
    CityConfig(
        name="Atlanta",
        slug="atlanta",
        noaa_grid_id="FFC",
        noaa_grid_x=50,
        noaa_grid_y=82,
    ),
    CityConfig(
        name="Dallas",
        slug="dallas",
        noaa_grid_id="FWD",
        noaa_grid_x=87,
        noaa_grid_y=107,
    ),
]
