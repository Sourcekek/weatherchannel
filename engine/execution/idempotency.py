"""Idempotency key generation and duplicate detection."""

import hashlib
import sqlite3


def generate_idempotency_key(
    run_id: str, market_id: str, side: str, price: float
) -> str:
    """Generate a deterministic idempotency key.

    Same run + market + side + price = same key = duplicate.
    """
    raw = f"{run_id}|{market_id}|{side}|{price:.4f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class IdempotencyChecker:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def is_duplicate(self, key: str) -> bool:
        """Check if an idempotency key already exists in order_intents."""
        row = self.conn.execute(
            "SELECT 1 FROM order_intents WHERE idempotency_key = ?", (key,)
        ).fetchone()
        return row is not None
