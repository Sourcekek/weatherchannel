"""Tests for market data models."""

import pytest

from engine.models.market import (
    BucketMarket,
    BucketType,
    MarketEvent,
    TemperatureBucket,
    TemperatureUnit,
)


def _make_bucket_market(
    bucket_type: BucketType = BucketType.RANGE,
    low: int = 36,
    high: int = 37,
) -> BucketMarket:
    return BucketMarket(
        market_id="m1",
        condition_id="c1",
        clob_token_id_yes="tok_yes",
        clob_token_id_no="tok_no",
        outcome_price_yes=0.10,
        best_bid=0.09,
        best_ask=0.11,
        last_trade_price=0.10,
        liquidity=100.0,
        volume_24hr=50.0,
        maker_base_fee=0.0,
        taker_base_fee=0.02,
        order_min_size=1.0,
        accepting_orders=True,
        end_date="2026-02-11T12:00:00Z",
        group_item_title=f"{low}-{high}°F",
        group_item_threshold="3",
        bucket=TemperatureBucket(
            bucket_type=bucket_type, low=low, high=high
        ),
    )


class TestBucketType:
    def test_all_types(self):
        assert BucketType.OR_HIGHER == "or_higher"
        assert BucketType.OR_BELOW == "or_below"
        assert BucketType.RANGE == "range"
        assert BucketType.EXACT == "exact"


class TestTemperatureBucket:
    def test_frozen(self):
        bucket = TemperatureBucket(
            bucket_type=BucketType.RANGE, low=36, high=37
        )
        with pytest.raises(AttributeError):
            bucket.low = 40  # type: ignore[misc]

    def test_default_unit(self):
        bucket = TemperatureBucket(
            bucket_type=BucketType.EXACT, low=22, high=22
        )
        assert bucket.unit == TemperatureUnit.FAHRENHEIT

    def test_celsius(self):
        bucket = TemperatureBucket(
            bucket_type=BucketType.EXACT,
            low=22,
            high=22,
            unit=TemperatureUnit.CELSIUS,
        )
        assert bucket.unit == TemperatureUnit.CELSIUS


class TestBucketMarket:
    def test_construction(self):
        bm = _make_bucket_market()
        assert bm.market_id == "m1"
        assert bm.bucket.bucket_type == BucketType.RANGE

    def test_frozen(self):
        bm = _make_bucket_market()
        with pytest.raises(AttributeError):
            bm.market_id = "other"  # type: ignore[misc]


class TestMarketEvent:
    def test_construction(self):
        event = MarketEvent(
            event_id="e1",
            slug="test-slug",
            city_slug="nyc",
            target_date="2026-02-11",
            title="Test Event",
            buckets=[_make_bucket_market()],
        )
        assert event.event_id == "e1"
        assert len(event.buckets) == 1

    def test_frozen(self):
        event = MarketEvent(
            event_id="e1",
            slug="test-slug",
            city_slug="nyc",
            target_date="2026-02-11",
            title="Test Event",
            buckets=[],
        )
        with pytest.raises(AttributeError):
            event.event_id = "other"  # type: ignore[misc]
