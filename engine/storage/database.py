"""SQLite connection manager with WAL mode and migration support."""

import importlib
import sqlite3
from pathlib import Path

MIGRATIONS_PACKAGE = "engine.storage.migrations"


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def run_migrations(conn: sqlite3.Connection) -> list[str]:
    """Run all pending migrations in order. Returns list of applied migration names."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_versions ("
        "  version TEXT PRIMARY KEY,"
        "  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ")"
    )
    conn.commit()

    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_versions").fetchall()
    }

    migrations = _discover_migrations()
    newly_applied = []

    for name in sorted(migrations):
        if name not in applied:
            mod = importlib.import_module(f"{MIGRATIONS_PACKAGE}.{name}")
            mod.up(conn)
            conn.execute(
                "INSERT INTO schema_versions (version) VALUES (?)", (name,)
            )
            conn.commit()
            newly_applied.append(name)

    return newly_applied


def _discover_migrations() -> list[str]:
    """Discover migration modules by naming convention v###_*.py."""
    migrations_dir = Path(__file__).parent / "migrations"
    results = []
    for p in migrations_dir.glob("v[0-9]*_*.py"):
        if p.stem != "__init__":
            results.append(p.stem)
    return sorted(results)
