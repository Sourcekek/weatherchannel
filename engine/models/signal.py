"""Signal and edge computation models."""

from dataclasses import dataclass
from enum import StrEnum


class ReasonCode(StrEnum):
    OPPORTUNITY = "OPPORTUNITY"
    EDGE_BELOW_THRESHOLD = "EDGE_BELOW_THRESHOLD"
    PRICE_ABOVE_MAX_ENTRY = "PRICE_ABOVE_MAX_ENTRY"
    NOT_ACCEPTING_ORDERS = "NOT_ACCEPTING_ORDERS"
    ZERO_LIQUIDITY = "ZERO_LIQUIDITY"
    NO_FORECAST_AVAILABLE = "NO_FORECAST_AVAILABLE"
    STALE_FORECAST_DATA = "STALE_FORECAST_DATA"
    STALE_MARKET_DATA = "STALE_MARKET_DATA"
    BUCKET_PARSE_ERROR = "BUCKET_PARSE_ERROR"
    PROBABILITY_SUM_WARNING = "PROBABILITY_SUM_WARNING"
    NEGATIVE_EDGE = "NEGATIVE_EDGE"
    INSUFFICIENT_SPREAD = "INSUFFICIENT_SPREAD"


@dataclass(frozen=True)
class BucketProbability:
    bucket_label: str
    probability: float
    mu: float
    sigma: float


@dataclass(frozen=True)
class EdgeResult:
    run_id: str
    event_id: str
    market_id: str
    city_slug: str
    target_date: str
    bucket_label: str
    bucket_probability: float
    market_price_yes: float
    gross_edge: float
    fee_estimate: float
    slippage_estimate: float
    net_edge: float
    reason_code: ReasonCode
    sigma_used: float


@dataclass(frozen=True)
class Signal:
    edge_result: EdgeResult
    market_id: str
    clob_token_id_yes: str
    proposed_size_usd: float
