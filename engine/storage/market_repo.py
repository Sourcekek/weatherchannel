"""Repository for market events and bucket markets."""

import sqlite3

from engine.models.market import MarketEvent


def save_market_event(conn: sqlite3.Connection, event: MarketEvent, raw_json: str) -> int:
    """Persist a market event and its buckets. Returns the event row id."""
    cursor = conn.execute(
        "INSERT INTO market_events (event_id, slug, city_slug, target_date, title, raw_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (event.event_id, event.slug, event.city_slug, event.target_date, event.title, raw_json),
    )
    event_row_id = cursor.lastrowid
    assert event_row_id is not None

    for bm in event.buckets:
        conn.execute(
            "INSERT INTO bucket_markets "
            "(event_row_id, market_id, condition_id, clob_token_id_yes, clob_token_id_no, "
            "outcome_price_yes, best_bid, best_ask, last_trade_price, liquidity, volume_24hr, "
            "maker_base_fee, taker_base_fee, order_min_size, accepting_orders, end_date, "
            "group_item_title, group_item_threshold, "
            "bucket_type, bucket_low, bucket_high, bucket_unit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_row_id,
                bm.market_id,
                bm.condition_id,
                bm.clob_token_id_yes,
                bm.clob_token_id_no,
                bm.outcome_price_yes,
                bm.best_bid,
                bm.best_ask,
                bm.last_trade_price,
                bm.liquidity,
                bm.volume_24hr,
                bm.maker_base_fee,
                bm.taker_base_fee,
                bm.order_min_size,
                int(bm.accepting_orders),
                bm.end_date,
                bm.group_item_title,
                bm.group_item_threshold,
                bm.bucket.bucket_type.value,
                bm.bucket.low,
                bm.bucket.high,
                bm.bucket.unit.value,
            ),
        )
    conn.commit()
    return event_row_id


def get_latest_market_event(
    conn: sqlite3.Connection, city_slug: str, target_date: str
) -> dict | None:
    """Get the most recent market event snapshot for a city/date."""
    row = conn.execute(
        "SELECT * FROM market_events WHERE city_slug = ? AND target_date = ? "
        "ORDER BY fetched_at DESC LIMIT 1",
        (city_slug, target_date),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_bucket_markets_for_event(
    conn: sqlite3.Connection, event_row_id: int
) -> list[dict]:
    """Get all bucket markets for an event snapshot."""
    rows = conn.execute(
        "SELECT * FROM bucket_markets WHERE event_row_id = ?",
        (event_row_id,),
    ).fetchall()
    return [dict(r) for r in rows]
