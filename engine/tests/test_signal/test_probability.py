"""Snapshot tests for bucket probability with hand-verified values."""

import pytest

from engine.models.market import BucketType, TemperatureBucket
from engine.signal.probability import bucket_probability


class TestBucketProbability:
    def test_range_36_37_mu38_sigma2_5(self):
        """Hand-verified: P(36 <= T <= 37 | mu=38, sigma=2.5) ≈ 0.2613."""
        bucket = TemperatureBucket(BucketType.RANGE, low=36, high=37)
        p = bucket_probability(bucket, mu=38.0, sigma=2.5)
        assert p == pytest.approx(0.2613, abs=0.005)

    def test_or_higher_44_mu38_sigma2_5(self):
        """P(T >= 44 | mu=38, sigma=2.5) = 1 - Phi((43.5-38)/2.5) = 1 - Phi(2.2) ≈ 0.0139."""
        bucket = TemperatureBucket(BucketType.OR_HIGHER, low=44, high=44)
        p = bucket_probability(bucket, mu=38.0, sigma=2.5)
        assert p == pytest.approx(0.0139, abs=0.002)

    def test_or_below_33_mu38_sigma2_5(self):
        """Hand-verified: P(T <= 33 | mu=38, sigma=2.5) ≈ 0.0359."""
        bucket = TemperatureBucket(BucketType.OR_BELOW, low=33, high=33)
        p = bucket_probability(bucket, mu=38.0, sigma=2.5)
        assert p == pytest.approx(0.0359, abs=0.005)

    def test_exact_38_mu38_sigma2_5(self):
        """Exact bucket at the mean should have moderate probability."""
        bucket = TemperatureBucket(BucketType.EXACT, low=38, high=38)
        p = bucket_probability(bucket, mu=38.0, sigma=2.5)
        assert 0.1 < p < 0.25

    def test_sum_approx_one(self):
        """All buckets for a complete event should sum to ~1.0."""
        mu, sigma = 38.0, 2.5
        total = 0.0

        # OR_BELOW 33
        total += bucket_probability(
            TemperatureBucket(BucketType.OR_BELOW, 33, 33), mu, sigma
        )
        # Ranges: 34-35, 36-37, 38-39, 40-41, 42-43
        for low in range(34, 44, 2):
            total += bucket_probability(
                TemperatureBucket(BucketType.RANGE, low, low + 1), mu, sigma
            )
        # OR_HIGHER 44
        total += bucket_probability(
            TemperatureBucket(BucketType.OR_HIGHER, 44, 44), mu, sigma
        )

        assert total == pytest.approx(1.0, abs=0.01)

    def test_or_higher_at_mean(self):
        """P(T >= mu) should be ~0.58 (continuity correction shifts up)."""
        bucket = TemperatureBucket(BucketType.OR_HIGHER, low=38, high=38)
        p = bucket_probability(bucket, mu=38.0, sigma=2.5)
        assert 0.5 < p < 0.65

    def test_or_below_at_mean(self):
        """P(T <= mu) should be ~0.58 (continuity correction shifts up)."""
        bucket = TemperatureBucket(BucketType.OR_BELOW, low=38, high=38)
        p = bucket_probability(bucket, mu=38.0, sigma=2.5)
        assert 0.5 < p < 0.65

    def test_narrow_sigma(self):
        """With sigma=1.0, probability concentrates near mean."""
        near = TemperatureBucket(BucketType.RANGE, low=37, high=38)
        far = TemperatureBucket(BucketType.RANGE, low=44, high=45)
        p_near = bucket_probability(near, mu=38.0, sigma=1.0)
        p_far = bucket_probability(far, mu=38.0, sigma=1.0)
        assert p_near > 0.5
        assert p_far < 0.001

    def test_negative_sigma_raises(self):
        bucket = TemperatureBucket(BucketType.EXACT, low=38, high=38)
        with pytest.raises(ValueError):
            bucket_probability(bucket, mu=38.0, sigma=-1.0)

    def test_zero_sigma_raises(self):
        bucket = TemperatureBucket(BucketType.EXACT, low=38, high=38)
        with pytest.raises(ValueError):
            bucket_probability(bucket, mu=38.0, sigma=0.0)
