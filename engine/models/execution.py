"""Execution and order models."""

from dataclasses import dataclass
from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    DRY_RUN = "DRY_RUN"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


@dataclass(frozen=True)
class OrderIntent:
    run_id: str
    idempotency_key: str
    market_id: str
    clob_token_id: str
    side: str  # "BUY"
    price: float
    size_usd: float
    city_slug: str
    target_date: str
    bucket_label: str
    net_edge: float


@dataclass(frozen=True)
class OrderResult:
    idempotency_key: str
    status: OrderStatus
    fill_price: float | None
    fill_size: float | None
    error_message: str
    executed_at: str
