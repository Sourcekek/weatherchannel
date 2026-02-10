"""Shared test fixtures."""

import sqlite3
from pathlib import Path

import pytest
import yaml

from engine.config.defaults import DEFAULT_CITIES
from engine.config.schema import EngineConfig


@pytest.fixture
def tmp_db(tmp_path: Path) -> sqlite3.Connection:
    """Create a temporary SQLite database with config_snapshots table."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE config_snapshots ("
        "  config_hash TEXT PRIMARY KEY,"
        "  config_json TEXT NOT NULL,"
        "  created_at TEXT NOT NULL"
        ")"
    )
    conn.commit()
    return conn


@pytest.fixture
def default_config() -> EngineConfig:
    """Return default EngineConfig with default cities."""
    return EngineConfig(cities=DEFAULT_CITIES)


@pytest.fixture
def config_yaml_path(tmp_path: Path) -> Path:
    """Write a minimal valid config YAML and return its path."""
    data = {
        "strategy": {"min_edge_threshold": 0.05},
        "risk": {"max_position_size_usd": 5.00},
        "execution": {"mode": "dry-run", "adapter": "dry-run"},
    }
    path = tmp_path / "test_config.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
    return path


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"
