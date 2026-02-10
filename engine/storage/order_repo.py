"""Repository for order intents and results."""

import sqlite3

from engine.models.execution import OrderIntent, OrderResult


def save_order_intent(conn: sqlite3.Connection, intent: OrderIntent) -> int:
    """Persist an order intent. Returns the row id."""
    cursor = conn.execute(
        "INSERT INTO order_intents "
        "(run_id, idempotency_key, market_id, clob_token_id, side, price, "
        "size_usd, city_slug, target_date, bucket_label, net_edge) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            intent.run_id,
            intent.idempotency_key,
            intent.market_id,
            intent.clob_token_id,
            intent.side,
            intent.price,
            intent.size_usd,
            intent.city_slug,
            intent.target_date,
            intent.bucket_label,
            intent.net_edge,
        ),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def save_order_result(conn: sqlite3.Connection, result: OrderResult) -> int:
    """Persist an order result. Returns the row id."""
    cursor = conn.execute(
        "INSERT INTO order_results "
        "(idempotency_key, status, fill_price, fill_size, error_message, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            result.idempotency_key,
            result.status.value,
            result.fill_price,
            result.fill_size,
            result.error_message,
            result.executed_at,
        ),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def get_order_intent_by_key(
    conn: sqlite3.Connection, idempotency_key: str
) -> dict | None:
    """Get an order intent by idempotency key."""
    row = conn.execute(
        "SELECT * FROM order_intents WHERE idempotency_key = ?",
        (idempotency_key,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_order_results_for_run(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    """Get all order results for a run via intents."""
    rows = conn.execute(
        "SELECT r.* FROM order_results r "
        "JOIN order_intents i ON r.idempotency_key = i.idempotency_key "
        "WHERE i.run_id = ?",
        (run_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_last_trade_time_for_market(
    conn: sqlite3.Connection, market_id: str
) -> str | None:
    """Get the most recent execution time for a market."""
    row = conn.execute(
        "SELECT r.executed_at FROM order_results r "
        "JOIN order_intents i ON r.idempotency_key = i.idempotency_key "
        "WHERE i.market_id = ? AND r.status IN ('DRY_RUN', 'FILLED') "
        "ORDER BY r.executed_at DESC LIMIT 1",
        (market_id,),
    ).fetchone()
    if row is None:
        return None
    return row[0]
