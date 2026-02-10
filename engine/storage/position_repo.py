"""Repository for positions and daily PnL."""

import sqlite3


def save_position(
    conn: sqlite3.Connection,
    market_id: str,
    city_slug: str,
    target_date: str,
    bucket_label: str,
    entry_price: float,
    size_usd: float,
) -> int:
    """Create an open position. Returns the row id."""
    cursor = conn.execute(
        "INSERT INTO positions "
        "(market_id, city_slug, target_date, bucket_label, entry_price, "
        "current_price, size_usd, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'open')",
        (market_id, city_slug, target_date, bucket_label, entry_price, entry_price, size_usd),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def get_open_positions(conn: sqlite3.Connection) -> list[dict]:
    """Get all open positions."""
    rows = conn.execute(
        "SELECT * FROM positions WHERE status = 'open'"
    ).fetchall()
    return [dict(r) for r in rows]


def get_open_positions_for_city(conn: sqlite3.Connection, city_slug: str) -> list[dict]:
    """Get open positions for a specific city."""
    rows = conn.execute(
        "SELECT * FROM positions WHERE status = 'open' AND city_slug = ?",
        (city_slug,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_total_open_exposure(conn: sqlite3.Connection) -> float:
    """Get total USD exposure across all open positions."""
    row = conn.execute(
        "SELECT COALESCE(SUM(size_usd), 0.0) FROM positions WHERE status = 'open'"
    ).fetchone()
    return float(row[0])


def get_city_open_exposure(conn: sqlite3.Connection, city_slug: str) -> float:
    """Get USD exposure for a specific city."""
    row = conn.execute(
        "SELECT COALESCE(SUM(size_usd), 0.0) FROM positions "
        "WHERE status = 'open' AND city_slug = ?",
        (city_slug,),
    ).fetchone()
    return float(row[0])


def close_position(conn: sqlite3.Connection, position_id: int) -> None:
    """Close a position."""
    conn.execute(
        "UPDATE positions SET status = 'closed', closed_at = CURRENT_TIMESTAMP "
        "WHERE id = ?",
        (position_id,),
    )
    conn.commit()


def save_daily_pnl(
    conn: sqlite3.Connection,
    date: str,
    realized_pnl: float,
    unrealized_pnl: float,
) -> None:
    """Upsert daily PnL record."""
    total = realized_pnl + unrealized_pnl
    conn.execute(
        "INSERT INTO daily_pnl (date, realized_pnl, unrealized_pnl, total_pnl) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(date) DO UPDATE SET "
        "realized_pnl = excluded.realized_pnl, "
        "unrealized_pnl = excluded.unrealized_pnl, "
        "total_pnl = excluded.total_pnl, "
        "updated_at = CURRENT_TIMESTAMP",
        (date, realized_pnl, unrealized_pnl, total),
    )
    conn.commit()


def get_daily_pnl(conn: sqlite3.Connection, date: str) -> dict | None:
    """Get PnL for a specific date."""
    row = conn.execute(
        "SELECT * FROM daily_pnl WHERE date = ?", (date,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)
