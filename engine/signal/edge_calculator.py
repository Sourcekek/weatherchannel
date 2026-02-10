"""Edge calculation: determines whether a bucket is an opportunity."""

from engine.models.signal import EdgeResult, ReasonCode


def compute_edge(
    run_id: str,
    event_id: str,
    market_id: str,
    city_slug: str,
    target_date: str,
    bucket_label: str,
    bucket_probability: float,
    market_price_yes: float,
    fee_estimate: float,
    slippage_estimate: float,
    sigma_used: float,
    min_edge_threshold: float,
    max_entry_price: float,
    accepting_orders: bool,
    liquidity: float,
) -> EdgeResult:
    """Compute edge for a single bucket market.

    Returns an EdgeResult with the appropriate reason code.
    """
    gross_edge = bucket_probability - market_price_yes
    net_edge = gross_edge - fee_estimate - slippage_estimate

    # Determine reason code
    if not accepting_orders:
        reason = ReasonCode.NOT_ACCEPTING_ORDERS
    elif liquidity <= 0:
        reason = ReasonCode.ZERO_LIQUIDITY
    elif market_price_yes > max_entry_price:
        reason = ReasonCode.PRICE_ABOVE_MAX_ENTRY
    elif net_edge < 0:
        reason = ReasonCode.NEGATIVE_EDGE
    elif net_edge < min_edge_threshold:
        reason = ReasonCode.EDGE_BELOW_THRESHOLD
    else:
        reason = ReasonCode.OPPORTUNITY

    return EdgeResult(
        run_id=run_id,
        event_id=event_id,
        market_id=market_id,
        city_slug=city_slug,
        target_date=target_date,
        bucket_label=bucket_label,
        bucket_probability=bucket_probability,
        market_price_yes=market_price_yes,
        gross_edge=gross_edge,
        fee_estimate=fee_estimate,
        slippage_estimate=slippage_estimate,
        net_edge=net_edge,
        reason_code=reason,
        sigma_used=sigma_used,
    )
