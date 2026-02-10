"""Normal CDF bucket probability calculator with continuity correction."""

from scipy.stats import norm

from engine.models.market import BucketType, TemperatureBucket


def bucket_probability(bucket: TemperatureBucket, mu: float, sigma: float) -> float:
    """Compute the probability that the temperature falls in the given bucket.

    Uses +-0.5 continuity correction for integer temperature rounding.

    Args:
        bucket: The temperature bucket definition.
        mu: Forecast mean temperature.
        sigma: Forecast uncertainty (standard deviation).

    Returns:
        Probability in [0, 1].
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")

    if bucket.bucket_type == BucketType.RANGE:
        # P(low <= T <= high) = Phi((high + 0.5 - mu) / sigma) - Phi((low - 0.5 - mu) / sigma)
        p = norm.cdf((bucket.high + 0.5 - mu) / sigma) - norm.cdf(
            (bucket.low - 0.5 - mu) / sigma
        )

    elif bucket.bucket_type == BucketType.EXACT:
        # P(T == temp) = Phi((temp + 0.5 - mu) / sigma) - Phi((temp - 0.5 - mu) / sigma)
        p = norm.cdf((bucket.low + 0.5 - mu) / sigma) - norm.cdf(
            (bucket.low - 0.5 - mu) / sigma
        )

    elif bucket.bucket_type == BucketType.OR_HIGHER:
        # P(T >= temp) = 1 - Phi((temp - 0.5 - mu) / sigma)
        p = 1.0 - norm.cdf((bucket.low - 0.5 - mu) / sigma)

    elif bucket.bucket_type == BucketType.OR_BELOW:
        # P(T <= temp) = Phi((temp + 0.5 - mu) / sigma)
        p = norm.cdf((bucket.low + 0.5 - mu) / sigma)

    else:
        raise ValueError(f"Unknown bucket type: {bucket.bucket_type}")

    return float(p)
