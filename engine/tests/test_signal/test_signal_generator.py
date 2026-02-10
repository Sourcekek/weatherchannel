"""Tests for signal generator: full pipeline with events + forecasts."""

from engine.config.schema import EngineConfig
from engine.models.forecast import ForecastPoint
from engine.models.market import (
    BucketMarket,
    BucketType,
    MarketEvent,
    TemperatureBucket,
)
from engine.models.signal import ReasonCode
from engine.signal.signal_generator import SignalGenerator


def _make_bucket(
    market_id: str,
    bucket_type: BucketType,
    low: int,
    high: int,
    price_yes: float,
    title: str,
) -> BucketMarket:
    return BucketMarket(
        market_id=market_id,
        condition_id=f"c_{market_id}",
        clob_token_id_yes=f"tok_yes_{market_id}",
        clob_token_id_no=f"tok_no_{market_id}",
        outcome_price_yes=price_yes,
        best_bid=price_yes - 0.01,
        best_ask=price_yes + 0.01,
        last_trade_price=price_yes,
        liquidity=100.0,
        volume_24hr=50.0,
        maker_base_fee=0.0,
        taker_base_fee=0.02,
        order_min_size=1.0,
        accepting_orders=True,
        end_date="2026-02-11T23:59:59Z",
        group_item_title=title,
        group_item_threshold="1",
        bucket=TemperatureBucket(bucket_type, low, high),
    )


def _make_event(city: str, date: str, buckets: list[BucketMarket]) -> MarketEvent:
    return MarketEvent(
        event_id=f"evt_{city}_{date}",
        slug=f"highest-temperature-in-{city}-on-{date}",
        city_slug=city,
        target_date=date,
        title=f"Temp in {city}",
        buckets=buckets,
    )


class TestSignalGenerator:
    def test_generates_results_for_all_buckets(self):
        event = _make_event("nyc", "2026-02-11", [
            _make_bucket("m1", BucketType.RANGE, 36, 37, 0.075, "36-37F"),
            _make_bucket("m2", BucketType.OR_HIGHER, 44, 44, 0.005, "44+F"),
        ])
        forecast = ForecastPoint(
            city_slug="nyc",
            target_date="2026-02-11",
            high_temp_f=38,
            source_generated_at="2026-02-10T12:00:00Z",
            fetched_at="2026-02-10T15:00:00Z",
            raw_periods=[],
        )

        config = EngineConfig()
        gen = SignalGenerator(config, "run1")
        results = gen.generate(
            [event], {("nyc", "2026-02-11"): forecast}
        )

        assert len(results) == 2
        # Sorted by net_edge descending
        assert results[0].net_edge >= results[1].net_edge

    def test_no_forecast_marks_all_buckets(self):
        event = _make_event("nyc", "2026-02-11", [
            _make_bucket("m1", BucketType.RANGE, 36, 37, 0.075, "36-37F"),
        ])

        config = EngineConfig()
        gen = SignalGenerator(config, "run1")
        results = gen.generate([event], {})

        assert len(results) == 1
        assert results[0].reason_code == ReasonCode.NO_FORECAST_AVAILABLE

    def test_opportunity_detection(self):
        # Low-priced bucket near the forecast mean = opportunity
        event = _make_event("nyc", "2026-02-11", [
            _make_bucket("m1", BucketType.RANGE, 37, 38, 0.075, "37-38F"),
        ])
        forecast = ForecastPoint(
            city_slug="nyc",
            target_date="2026-02-11",
            high_temp_f=38,
            source_generated_at="2026-02-10T12:00:00Z",
            fetched_at="2026-02-10T15:00:00Z",
            raw_periods=[],
        )

        config = EngineConfig()
        gen = SignalGenerator(config, "run1")
        results = gen.generate(
            [event], {("nyc", "2026-02-11"): forecast}
        )
        opps = gen.filter_opportunities(results)

        assert len(opps) >= 1
        assert opps[0].reason_code == ReasonCode.OPPORTUNITY

    def test_multiple_events_ranked(self):
        event1 = _make_event("nyc", "2026-02-11", [
            _make_bucket("m1", BucketType.RANGE, 37, 38, 0.075, "37-38F"),
        ])
        event2 = _make_event("chicago", "2026-02-11", [
            _make_bucket("m2", BucketType.RANGE, 29, 30, 0.075, "29-30F"),
        ])
        forecasts = {
            ("nyc", "2026-02-11"): ForecastPoint(
                "nyc", "2026-02-11", 38, "2026-02-10T12:00:00Z",
                "2026-02-10T15:00:00Z", [],
            ),
            ("chicago", "2026-02-11"): ForecastPoint(
                "chicago", "2026-02-11", 30, "2026-02-10T12:00:00Z",
                "2026-02-10T15:00:00Z", [],
            ),
        }

        config = EngineConfig()
        gen = SignalGenerator(config, "run1")
        results = gen.generate([event1, event2], forecasts)

        assert len(results) == 2
        # Both should be sorted by net_edge
        assert results[0].net_edge >= results[1].net_edge

    def test_to_signals(self):
        event = _make_event("nyc", "2026-02-11", [
            _make_bucket("m1", BucketType.RANGE, 37, 38, 0.075, "37-38F"),
        ])
        forecast = ForecastPoint(
            "nyc", "2026-02-11", 38, "2026-02-10T12:00:00Z",
            "2026-02-10T15:00:00Z", [],
        )

        config = EngineConfig()
        gen = SignalGenerator(config, "run1")
        results = gen.generate(
            [event], {("nyc", "2026-02-11"): forecast}
        )
        opps = gen.filter_opportunities(results)
        signals = gen.to_signals(opps, [event])

        assert len(signals) >= 1
        assert signals[0].market_id == "m1"
        assert signals[0].clob_token_id_yes == "tok_yes_m1"
        assert signals[0].proposed_size_usd == 5.0
