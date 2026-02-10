"""Exhaustive tests for slug parser: all 4 bucket types, negatives, invalid."""

from engine.ingest.slug_parser import (
    build_event_slug,
    parse_bucket_suffix,
    parse_event_slug,
)
from engine.models.market import BucketType, TemperatureUnit


class TestParseBucketSuffix:
    # OR_HIGHER
    def test_or_higher_f(self):
        result = parse_bucket_suffix("44forhigher")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.OR_HIGHER
        assert result.bucket.low == 44
        assert result.bucket.high == 44
        assert result.bucket.unit == TemperatureUnit.FAHRENHEIT

    def test_or_higher_c(self):
        result = parse_bucket_suffix("10corhigher")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.OR_HIGHER
        assert result.bucket.unit == TemperatureUnit.CELSIUS

    # OR_BELOW
    def test_or_below_f(self):
        result = parse_bucket_suffix("33forbelow")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.OR_BELOW
        assert result.bucket.low == 33
        assert result.bucket.high == 33

    def test_or_below_c(self):
        result = parse_bucket_suffix("5corbelow")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.OR_BELOW
        assert result.bucket.unit == TemperatureUnit.CELSIUS

    # RANGE
    def test_range_f(self):
        result = parse_bucket_suffix("42-43f")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.RANGE
        assert result.bucket.low == 42
        assert result.bucket.high == 43
        assert result.bucket.unit == TemperatureUnit.FAHRENHEIT

    def test_range_c(self):
        result = parse_bucket_suffix("5-6c")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.RANGE
        assert result.bucket.unit == TemperatureUnit.CELSIUS

    def test_range_negative(self):
        result = parse_bucket_suffix("neg1-2f")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.RANGE
        assert result.bucket.low == -1
        assert result.bucket.high == 2

    # EXACT
    def test_exact_f(self):
        result = parse_bucket_suffix("38f")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.EXACT
        assert result.bucket.low == 38
        assert result.bucket.high == 38

    def test_exact_c(self):
        result = parse_bucket_suffix("22c")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.EXACT
        assert result.bucket.unit == TemperatureUnit.CELSIUS

    def test_negative_exact(self):
        result = parse_bucket_suffix("neg5f")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.EXACT
        assert result.bucket.low == -5

    # Case insensitive
    def test_case_insensitive(self):
        result = parse_bucket_suffix("44FORHIGHER")
        assert result is not None
        assert result.bucket.bucket_type == BucketType.OR_HIGHER

    # Invalid
    def test_invalid_empty(self):
        assert parse_bucket_suffix("") is None

    def test_invalid_nonsense(self):
        assert parse_bucket_suffix("foobar") is None

    def test_invalid_no_unit(self):
        assert parse_bucket_suffix("42-43") is None

    def test_invalid_missing_type(self):
        assert parse_bucket_suffix("42") is None


class TestBuildEventSlug:
    def test_basic(self):
        slug = build_event_slug("nyc", 2026, 2, 11)
        assert slug == "highest-temperature-in-nyc-on-february-11-2026"

    def test_different_city(self):
        slug = build_event_slug("chicago", 2026, 3, 1)
        assert slug == "highest-temperature-in-chicago-on-march-1-2026"


class TestParseEventSlug:
    def test_roundtrip(self):
        slug = build_event_slug("nyc", 2026, 2, 11)
        parsed = parse_event_slug(slug)
        assert parsed is not None
        assert parsed.city_slug == "nyc"
        assert parsed.year == 2026
        assert parsed.month == 2
        assert parsed.day == 11

    def test_invalid(self):
        assert parse_event_slug("not-a-valid-slug") is None

    def test_bad_month(self):
        assert parse_event_slug(
            "highest-temperature-in-nyc-on-smarch-11-2026"
        ) is None
