"""Executor: coordinates kill switch recheck, idempotency, persist, dispatch."""

import logging
import sqlite3

from engine.execution.dry_run import DryRunAdapter
from engine.execution.idempotency import IdempotencyChecker
from engine.execution.live_adapter import LiveAdapter
from engine.models.common import utc_now_iso
from engine.models.execution import OrderIntent, OrderResult, OrderStatus
from engine.storage import order_repo, state_repo

logger = logging.getLogger(__name__)


class Executor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        adapter: DryRunAdapter | LiveAdapter,
    ):
        self.conn = conn
        self.adapter = adapter
        self.idem = IdempotencyChecker(conn)

    def execute(self, intent: OrderIntent) -> OrderResult:
        """Execute an order intent through the full safety pipeline.

        1. Recheck kill switch (defense in depth)
        2. Check idempotency
        3. Persist intent
        4. Dispatch to adapter
        5. Persist result
        """
        # 1. Defense-in-depth kill switch check
        if state_repo.is_kill_switch_active(self.conn):
            logger.warning(
                "Kill switch active at executor level, blocking %s",
                intent.idempotency_key,
            )
            return OrderResult(
                idempotency_key=intent.idempotency_key,
                status=OrderStatus.REJECTED,
                fill_price=None,
                fill_size=None,
                error_message="Kill switch active at executor level",
                executed_at=utc_now_iso(),
            )

        # 2. Idempotency check
        if self.idem.is_duplicate(intent.idempotency_key):
            logger.info(
                "Duplicate idempotency key %s, skipping",
                intent.idempotency_key,
            )
            return OrderResult(
                idempotency_key=intent.idempotency_key,
                status=OrderStatus.DUPLICATE,
                fill_price=None,
                fill_size=None,
                error_message="Duplicate idempotency key",
                executed_at=utc_now_iso(),
            )

        # 3. Persist intent
        order_repo.save_order_intent(self.conn, intent)

        # 4. Dispatch to adapter
        try:
            result = self.adapter.execute(intent)
        except Exception as e:
            logger.exception("Execution failed for %s", intent.idempotency_key)
            result = OrderResult(
                idempotency_key=intent.idempotency_key,
                status=OrderStatus.FAILED,
                fill_price=None,
                fill_size=None,
                error_message=str(e),
                executed_at=utc_now_iso(),
            )

        # 5. Persist result
        order_repo.save_order_result(self.conn, result)
        return result
