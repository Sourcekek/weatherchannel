"""Market data models for Polymarket weather bucket contracts."""

from dataclasses import dataclass
from enum import StrEnum


class BucketType(StrEnum):
    OR_HIGHER = "or_higher"
    OR_BELOW = "or_below"
    RANGE = "range"
    EXACT = "exact"


class TemperatureUnit(StrEnum):
    FAHRENHEIT = "F"
    CELSIUS = "C"


@dataclass(frozen=True)
class TemperatureBucket:
    bucket_type: BucketType
    low: int
    high: int
    unit: TemperatureUnit = TemperatureUnit.FAHRENHEIT


@dataclass(frozen=True)
class BucketMarket:
    market_id: str
    condition_id: str
    clob_token_id_yes: str
    clob_token_id_no: str
    outcome_price_yes: float
    best_bid: float
    best_ask: float
    last_trade_price: float
    liquidity: float
    volume_24hr: float
    maker_base_fee: float
    taker_base_fee: float
    order_min_size: float
    accepting_orders: bool
    end_date: str
    group_item_title: str
    group_item_threshold: str
    bucket: TemperatureBucket


@dataclass(frozen=True)
class MarketEvent:
    event_id: str
    slug: str
    city_slug: str
    target_date: str  # YYYY-MM-DD
    title: str
    buckets: list[BucketMarket]
