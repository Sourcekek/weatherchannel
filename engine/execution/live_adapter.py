"""Live execution adapter: routes orders through Simmer SDK API."""

import logging

from engine.execution.simmer_client import SimmerClient, SimmerClientError
from engine.models.common import utc_now_iso
from engine.models.execution import OrderIntent, OrderResult, OrderStatus

logger = logging.getLogger(__name__)


class LiveAdapter:
    """Execute trades via Simmer SDK.

    Supports both `simmer` venue ($SIM virtual) and `polymarket` venue (real USDC).
    Maps Polymarket CLOB token IDs to Simmer UUIDs before trading.
    """

    def __init__(
        self,
        simmer_client: SimmerClient | None = None,
        venue: str = "simmer",
    ):
        self.client = simmer_client or SimmerClient()
        self.venue = venue  # "simmer" for $SIM, "polymarket" for real USDC
        self._token_map: dict[str, str] | None = None

    def _resolve_simmer_id(self, clob_token_id: str, market_id: str) -> str | None:
        """Resolve a Polymarket CLOB token ID to a Simmer market UUID."""
        if self._token_map is None:
            logger.info("Building Polymarket→Simmer token map...")
            self._token_map = self.client.build_token_to_simmer_map()
            logger.info("Mapped %d Simmer weather markets", len(self._token_map))

        simmer_id = self._token_map.get(clob_token_id)
        if simmer_id is None:
            logger.warning(
                "No Simmer market found for token %s (market_id=%s)",
                clob_token_id[:20] + "...", market_id,
            )
        return simmer_id

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

        # Resolve Simmer market UUID from Polymarket CLOB token ID
        simmer_market_id = self._resolve_simmer_id(intent.clob_token_id, intent.market_id)
        if simmer_market_id is None:
            return OrderResult(
                idempotency_key=intent.idempotency_key,
                status=OrderStatus.REJECTED,
                fill_price=None,
                fill_size=None,
                error_message=f"No Simmer market found for token {intent.clob_token_id[:20]}...",
                executed_at=utc_now_iso(),
            )

        try:
            result = self.client.buy(
                market_id=simmer_market_id,
                amount_usd=intent.size_usd,
                side="yes" if intent.side == "BUY" else "no",
                venue=self.venue,
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
        clob_token_id: str = "",
    ) -> OrderResult:
        """Execute a sell order through Simmer."""
        # Resolve Simmer ID for sells too
        simmer_id = self._resolve_simmer_id(clob_token_id, market_id) if clob_token_id else None
        trade_market_id = simmer_id or market_id

        logger.info("LIVE SELL: %s (simmer=%s), %.2f shares", market_id, trade_market_id, shares)
        try:
            result = self.client.sell(
                market_id=trade_market_id,
                shares=shares,
                side="yes",
                venue=self.venue,
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
