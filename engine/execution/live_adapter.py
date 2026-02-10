"""Live execution adapter: routes orders through Simmer SDK API."""

import logging

from engine.execution.simmer_client import SimmerClient, SimmerClientError
from engine.models.common import utc_now_iso
from engine.models.execution import OrderIntent, OrderResult, OrderStatus

logger = logging.getLogger(__name__)


class LiveAdapter:
    """Execute real trades via Simmer → Polymarket.

    Uses the Polymarket condition_id as the market identifier.
    Simmer's API accepts Polymarket market IDs for trade routing.
    """

    def __init__(self, simmer_client: SimmerClient | None = None):
        self.client = simmer_client or SimmerClient()

    def execute(self, intent: OrderIntent) -> OrderResult:
        """Execute a buy order through Simmer.

        Maps engine OrderIntent to Simmer API call and parses the response.
        """
        logger.info(
            "LIVE: %s %s on %s at $%.4f (size $%.2f, edge %.4f)",
            intent.side,
            intent.bucket_label,
            intent.market_id,
            intent.price,
            intent.size_usd,
            intent.net_edge,
        )

        try:
            # Use condition_id as market identifier for Simmer
            result = self.client.buy(
                market_id=intent.market_id,
                amount_usd=intent.size_usd,
                side="yes" if intent.side == "BUY" else "no",
            )

            if result.get("success") or result.get("trade_id"):
                fill_price = result.get("fill_price") or result.get("price") or intent.price
                fill_size = (
                    result.get("shares_bought")
                    or result.get("shares")
                    or result.get("fill_size")
                    or intent.size_usd
                )
                trade_id = result.get("trade_id", "")
                logger.info(
                    "LIVE FILL: %s shares @ $%.4f (trade_id=%s)",
                    fill_size, fill_price, trade_id,
                )
                return OrderResult(
                    idempotency_key=intent.idempotency_key,
                    status=OrderStatus.FILLED,
                    fill_price=float(fill_price),
                    fill_size=float(fill_size),
                    error_message="",
                    executed_at=utc_now_iso(),
                )
            else:
                error = result.get("error", result.get("message", "Unknown Simmer error"))
                logger.warning("LIVE REJECTED: %s -> %s", intent.market_id, error)
                return OrderResult(
                    idempotency_key=intent.idempotency_key,
                    status=OrderStatus.REJECTED,
                    fill_price=None,
                    fill_size=None,
                    error_message=str(error),
                    executed_at=utc_now_iso(),
                )

        except SimmerClientError as e:
            logger.error("LIVE FAILED: %s -> %s", intent.market_id, e)
            return OrderResult(
                idempotency_key=intent.idempotency_key,
                status=OrderStatus.FAILED,
                fill_price=None,
                fill_size=None,
                error_message=str(e),
                executed_at=utc_now_iso(),
            )

    def execute_sell(
        self,
        market_id: str,
        shares: float,
        idempotency_key: str,
    ) -> OrderResult:
        """Execute a sell order through Simmer."""
        logger.info("LIVE SELL: %s, %.2f shares", market_id, shares)
        try:
            result = self.client.sell(
                market_id=market_id,
                shares=shares,
                side="yes",
            )

            if result.get("success") or result.get("trade_id"):
                fill_price = result.get("fill_price") or result.get("price") or 0.0
                fill_size = result.get("shares_sold") or result.get("shares") or shares
                logger.info(
                    "LIVE SELL FILL: %.2f shares @ $%.4f",
                    fill_size, fill_price,
                )
                return OrderResult(
                    idempotency_key=idempotency_key,
                    status=OrderStatus.FILLED,
                    fill_price=float(fill_price),
                    fill_size=float(fill_size),
                    error_message="",
                    executed_at=utc_now_iso(),
                )
            else:
                error = result.get("error", "Unknown sell error")
                return OrderResult(
                    idempotency_key=idempotency_key,
                    status=OrderStatus.REJECTED,
                    fill_price=None,
                    fill_size=None,
                    error_message=str(error),
                    executed_at=utc_now_iso(),
                )

        except SimmerClientError as e:
            return OrderResult(
                idempotency_key=idempotency_key,
                status=OrderStatus.FAILED,
                fill_price=None,
                fill_size=None,
                error_message=str(e),
                executed_at=utc_now_iso(),
            )
