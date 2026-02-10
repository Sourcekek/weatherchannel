"""Repository for NOAA forecast snapshots."""

import sqlite3


def save_forecast(
    conn: sqlite3.Connection,
    city_slug: str,
    target_date: str,
    high_temp_f: int,
    source_generated_at: str,
    raw_json: str,
) -> int:
    """Persist a forecast snapshot. Returns the row id."""
    cursor = conn.execute(
        "INSERT INTO forecast_snapshots "
        "(city_slug, target_date, high_temp_f, source_generated_at, raw_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (city_slug, target_date, high_temp_f, source_generated_at, raw_json),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def get_latest_forecast(
    conn: sqlite3.Connection, city_slug: str, target_date: str
) -> dict | None:
    """Get the most recent forecast for a city/date."""
    row = conn.execute(
        "SELECT * FROM forecast_snapshots WHERE city_slug = ? AND target_date = ? "
        "ORDER BY fetched_at DESC LIMIT 1",
        (city_slug, target_date),
    ).fetchone()
    if row is None:
        return None
    return dict(row)
