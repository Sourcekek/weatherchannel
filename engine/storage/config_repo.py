"""Repository for config snapshots (thin wrapper — main logic in config/loader.py)."""

import sqlite3


def get_config_snapshot(conn: sqlite3.Connection, config_hash: str) -> dict | None:
    """Get a config snapshot by hash."""
    row = conn.execute(
        "SELECT * FROM config_snapshots WHERE config_hash = ?",
        (config_hash,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_all_config_snapshots(conn: sqlite3.Connection) -> list[dict]:
    """Get all config snapshots ordered by creation time."""
    rows = conn.execute(
        "SELECT * FROM config_snapshots ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]
