"""Dry-run execution adapter: logs intent, returns simulated fill."""

import logging

from engine.models.common import utc_now_iso
from engine.models.execution import OrderIntent, OrderResult, OrderStatus

logger = logging.getLogger(__name__)


class DryRunAdapter:
    def execute(self, intent: OrderIntent) -> OrderResult:
        """Simulate execution: return a fill at the intent price."""
        logger.info(
            "DRY-RUN: %s %s on %s at $%.4f (size $%.2f, edge %.4f)",
            intent.side,
            intent.bucket_label,
            intent.market_id,
            intent.price,
            intent.size_usd,
            intent.net_edge,
        )
        return OrderResult(
            idempotency_key=intent.idempotency_key,
            status=OrderStatus.DRY_RUN,
            fill_price=intent.price,
            fill_size=intent.size_usd,
            error_message="",
            executed_at=utc_now_iso(),
        )
