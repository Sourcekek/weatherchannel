"""Repository for system state, operator commands, and run tracking."""

import sqlite3

# --- System state ---

def get_system_state(conn: sqlite3.Connection, key: str) -> str | None:
    """Get a system state value."""
    row = conn.execute(
        "SELECT value FROM system_state WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        return None
    return row[0]


def set_system_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set a system state value."""
    conn.execute(
        "INSERT INTO system_state (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
        (key, value),
    )
    conn.commit()


def is_kill_switch_active(conn: sqlite3.Connection) -> bool:
    return get_system_state(conn, "kill_switch") == "true"


def is_paused(conn: sqlite3.Connection) -> bool:
    return get_system_state(conn, "paused") == "true"


def get_mode(conn: sqlite3.Connection) -> str:
    return get_system_state(conn, "mode") or "dry-run"


# --- Operator commands ---

def log_operator_command(
    conn: sqlite3.Connection, command: str, args: str = "", result: str = ""
) -> int:
    """Log an operator command for audit."""
    cursor = conn.execute(
        "INSERT INTO operator_commands (command, args, result) VALUES (?, ?, ?)",
        (command, args, result),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def get_recent_operator_commands(
    conn: sqlite3.Connection, limit: int = 20
) -> list[dict]:
    """Get recent operator commands."""
    rows = conn.execute(
        "SELECT * FROM operator_commands ORDER BY executed_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# --- Runs ---

def create_run(
    conn: sqlite3.Connection, run_id: str, mode: str, config_hash: str | None = None
) -> None:
    """Record the start of a pipeline run."""
    conn.execute(
        "INSERT INTO runs (run_id, mode, config_hash) VALUES (?, ?, ?)",
        (run_id, mode, config_hash),
    )
    conn.commit()


def complete_run(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    summary_json: str | None = None,
    error_message: str | None = None,
    **metrics: int | float | None,
) -> None:
    """Record run completion with metrics."""
    sets = ["completed_at = CURRENT_TIMESTAMP", "status = ?"]
    params: list = [status]

    if summary_json is not None:
        sets.append("summary_json = ?")
        params.append(summary_json)
    if error_message is not None:
        sets.append("error_message = ?")
        params.append(error_message)
    for key, val in metrics.items():
        if val is not None:
            sets.append(f"{key} = ?")
            params.append(val)

    params.append(run_id)
    conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE run_id = ?", params)
    conn.commit()


def get_latest_run(conn: sqlite3.Connection) -> dict | None:
    """Get the most recent run."""
    row = conn.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_run(conn: sqlite3.Connection, run_id: str) -> dict | None:
    """Get a specific run by ID."""
    row = conn.execute(
        "SELECT * FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)
