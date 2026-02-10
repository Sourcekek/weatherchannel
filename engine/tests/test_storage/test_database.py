"""Tests for database connection, WAL mode, and migrations."""

from pathlib import Path

from engine.storage.database import connect, run_migrations


class TestConnect:
    def test_wal_mode(self, tmp_path: Path):
        db = connect(tmp_path / "test.db")
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        db.close()

    def test_foreign_keys_enabled(self, tmp_path: Path):
        db = connect(tmp_path / "test.db")
        fk = db.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        db.close()

    def test_row_factory(self, tmp_path: Path):
        db = connect(tmp_path / "test.db")
        db.execute("CREATE TABLE t (x TEXT)")
        db.execute("INSERT INTO t VALUES ('hello')")
        row = db.execute("SELECT x FROM t").fetchone()
        assert row["x"] == "hello"
        db.close()


class TestMigrations:
    def test_creates_all_tables(self, tmp_path: Path):
        db = connect(tmp_path / "test.db")
        applied = run_migrations(db)
        assert "v001_initial" in applied

        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {
            "schema_versions",
            "market_events",
            "bucket_markets",
            "forecast_snapshots",
            "edge_results",
            "risk_checks",
            "order_intents",
            "order_results",
            "positions",
            "daily_pnl",
            "config_snapshots",
            "system_state",
            "operator_commands",
            "runs",
        }
        assert expected.issubset(tables)
        db.close()

    def test_idempotent(self, tmp_path: Path):
        db = connect(tmp_path / "test.db")
        applied1 = run_migrations(db)
        applied2 = run_migrations(db)
        assert len(applied1) > 0
        assert len(applied2) == 0
        db.close()

    def test_default_system_state(self, tmp_path: Path):
        db = connect(tmp_path / "test.db")
        run_migrations(db)
        rows = {
            row["key"]: row["value"]
            for row in db.execute("SELECT key, value FROM system_state").fetchall()
        }
        assert rows["mode"] == "dry-run"
        assert rows["paused"] == "false"
        assert rows["kill_switch"] == "false"
        db.close()
