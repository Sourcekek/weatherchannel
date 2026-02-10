"""Exit pipeline: monitors open positions and exits when price exceeds threshold."""

import json
import logging
import sqlite3

import httpx

from engine.config.schema import EngineConfig, ExecutionMode
from engine.execution.idempotency import generate_idempotency_key
from engine.execution.live_adapter import LiveAdapter
from engine.models.common import utc_now_iso
from engine.models.execution import OrderIntent, OrderResult, OrderStatus
from engine.storage import order_repo, position_repo, state_repo

logger = logging.getLogger(__name__)


class ExitPipeline:
    """Scan open positions and exit when price exceeds threshold.

    This runs after the entry scan in each cycle. It:
    1. Loads open positions from DB
    2. Fetches current prices from Gamma API
    3. Sells positions where price >= min_exit_price
    4. Respects kill switch and pause state
    """

    def __init__(
        self,
        config: EngineConfig,
        conn: sqlite3.Connection,
        gamma_client: object,  # GammaClient (not used directly; prices fetched via httpx)
        run_id: str,
    ):
        self.config = config
        self.conn = conn
        self.gamma = gamma_client
        self.run_id = run_id

    def run(self) -> dict:
        """Execute exit scan. Returns summary dict."""
        summary = {
            "positions_checked": 0,
            "exits_found": 0,
            "exits_executed": 0,
            "exits_failed": 0,
            "prices_updated": 0,
        }

        # Respect system state
        if state_repo.is_kill_switch_active(self.conn):
            logger.warning("Kill switch active, skipping exits")
            return summary
        if state_repo.is_paused(self.conn):
            logger.warning("System paused, skipping exits")
            return summary

        positions = position_repo.get_open_positions_with_ids(self.conn)
        if not positions:
            return summary

        summary["positions_checked"] = len(positions)
        logger.info("Checking %d open positions for exit", len(positions))

        # Fetch current prices for all open position markets
        price_map = self._fetch_current_prices(positions)
        min_exit = self.config.strategy.min_exit_price

        for pos in positions:
            market_id = pos["market_id"]
            position_id = pos["id"]
            current_price = price_map.get(market_id)

            if current_price is None:
                logger.debug("No current price for market %s, skipping", market_id)
                continue

            # Update mark-to-market
            position_repo.update_position_price(self.conn, position_id, current_price)
            summary["prices_updated"] += 1

            # Check exit condition
            if current_price >= min_exit:
                summary["exits_found"] += 1
                entry_price = pos["entry_price"]
                size_usd = pos["size_usd"]
                shares = size_usd / entry_price if entry_price > 0 else 0.0

                logger.info(
                    "EXIT: %s %s price $%.4f >= $%.4f threshold (entry $%.4f)",
                    pos["city_slug"], pos["bucket_label"],
                    current_price, min_exit, entry_price,
                )

                result = self._execute_exit(pos, shares, current_price)
                if result.status in (OrderStatus.DRY_RUN, OrderStatus.FILLED):
                    summary["exits_executed"] += 1
                    position_repo.close_position(self.conn, position_id)
                    # Record realized PnL
                    pnl = shares * (current_price - entry_price)
                    logger.info(
                        "EXIT DONE: %s %s realized PnL $%.2f",
                        pos["city_slug"], pos["bucket_label"], pnl,
                    )
                else:
                    summary["exits_failed"] += 1
            else:
                logger.debug(
                    "HOLD: %s %s price $%.4f < $%.4f threshold",
                    pos["city_slug"], pos["bucket_label"],
                    current_price, min_exit,
                )

        return summary

    def _fetch_current_prices(self, positions: list[dict]) -> dict[str, float]:
        """Fetch current YES prices for open position markets from Gamma."""
        price_map: dict[str, float] = {}
        unique_markets = {p["market_id"] for p in positions}

        for market_id in unique_markets:
            try:
                resp = httpx.get(
                    f"https://gamma-api.polymarket.com/markets/{market_id}",
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    prices_raw = data.get("outcomePrices", "[]")
                    prices = (
                        json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    )
                    if prices:
                        price_map[market_id] = float(prices[0])
                else:
                    logger.debug("Gamma market %s returned %d", market_id, resp.status_code)
            except Exception:
                logger.debug("Failed to fetch price for market %s", market_id, exc_info=True)

        return price_map

    def _execute_exit(self, pos: dict, shares: float, current_price: float) -> OrderResult:
        """Execute an exit order (dry-run or live)."""
        idem_key = generate_idempotency_key(
            self.run_id, pos["market_id"], "SELL", current_price,
        )

        # Check idempotency
        existing = order_repo.get_order_intent_by_key(self.conn, idem_key)
        if existing is not None:
            return OrderResult(
                idempotency_key=idem_key,
                status=OrderStatus.DUPLICATE,
                fill_price=None,
                fill_size=None,
                error_message="Duplicate exit order",
                executed_at=utc_now_iso(),
            )

        # Save intent
        intent = OrderIntent(
            run_id=self.run_id,
            idempotency_key=idem_key,
            market_id=pos["market_id"],
            clob_token_id="",  # Not needed for sell via Simmer
            side="SELL",
            price=current_price,
            size_usd=pos["size_usd"],
            city_slug=pos["city_slug"],
            target_date=pos["target_date"],
            bucket_label=pos["bucket_label"],
            net_edge=current_price - pos["entry_price"],
        )
        order_repo.save_order_intent(self.conn, intent)

        if self.config.execution.mode == ExecutionMode.DRY_RUN:
            logger.info(
                "DRY-RUN EXIT: SELL %s %.2f shares @ $%.4f",
                pos["bucket_label"], shares, current_price,
            )
            result = OrderResult(
                idempotency_key=idem_key,
                status=OrderStatus.DRY_RUN,
                fill_price=current_price,
                fill_size=shares,
                error_message="",
                executed_at=utc_now_iso(),
            )
        else:
            # Live sell via Simmer
            adapter = LiveAdapter()
            result = adapter.execute_sell(
                market_id=pos["market_id"],
                shares=shares,
                idempotency_key=idem_key,
            )

        order_repo.save_order_result(self.conn, result)
        return result
