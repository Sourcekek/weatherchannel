"""Tests for config loading, snapshot persistence, and get/set."""

import sqlite3
from pathlib import Path

import pytest
import yaml

from engine.config.defaults import DEFAULT_CITIES
from engine.config.loader import (
    config_hash,
    get_config_value,
    load_config,
    set_config_value,
    snapshot_config,
)
from engine.config.schema import EngineConfig, ExecutionMode


class TestLoadConfig:
    def test_load_from_yaml(self, config_yaml_path: Path):
        config = load_config(config_yaml_path)
        assert config.execution.mode == ExecutionMode.DRY_RUN
        assert config.strategy.min_edge_threshold == 0.05

    def test_default_cities_injected(self, config_yaml_path: Path):
        config = load_config(config_yaml_path)
        assert len(config.cities) == len(DEFAULT_CITIES)
        assert config.cities[0].slug == "nyc"

    def test_explicit_cities_not_overridden(self, tmp_path: Path):
        data = {
            "cities": [
                {
                    "name": "Test City",
                    "slug": "test",
                    "noaa_grid_id": "TST",
                    "noaa_grid_x": 1,
                    "noaa_grid_y": 2,
                }
            ]
        }
        path = tmp_path / "custom.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)
        config = load_config(path)
        assert len(config.cities) == 1
        assert config.cities[0].slug == "test"

    def test_empty_yaml_uses_defaults(self, tmp_path: Path):
        path = tmp_path / "empty.yaml"
        path.write_text("")
        config = load_config(path)
        assert config.execution.mode == ExecutionMode.DRY_RUN
        assert len(config.cities) == len(DEFAULT_CITIES)

    def test_fixtures_config(self, fixtures_dir: Path):
        config = load_config(fixtures_dir / "config_default.yaml")
        assert config.risk.max_trades_per_run == 3


class TestConfigHash:
    def test_deterministic(self):
        c1 = EngineConfig(cities=DEFAULT_CITIES)
        c2 = EngineConfig(cities=DEFAULT_CITIES)
        assert config_hash(c1) == config_hash(c2)

    def test_different_config_different_hash(self):
        c1 = EngineConfig(cities=DEFAULT_CITIES)
        c2 = EngineConfig(cities=[])
        assert config_hash(c1) != config_hash(c2)


class TestSnapshotConfig:
    def test_persists_to_db(self, default_config: EngineConfig, tmp_db: sqlite3.Connection):
        h = snapshot_config(default_config, tmp_db)
        row = tmp_db.execute(
            "SELECT config_json FROM config_snapshots WHERE config_hash = ?", (h,)
        ).fetchone()
        assert row is not None

    def test_idempotent(self, default_config: EngineConfig, tmp_db: sqlite3.Connection):
        h1 = snapshot_config(default_config, tmp_db)
        h2 = snapshot_config(default_config, tmp_db)
        assert h1 == h2
        count = tmp_db.execute("SELECT COUNT(*) FROM config_snapshots").fetchone()[0]
        assert count == 1


class TestGetConfigValue:
    def test_dotted_key(self, default_config: EngineConfig):
        val = get_config_value(default_config, "risk.max_position_size_usd")
        assert val == 5.00

    def test_top_level(self, default_config: EngineConfig):
        val = get_config_value(default_config, "execution")
        assert val.mode == ExecutionMode.DRY_RUN

    def test_invalid_key(self, default_config: EngineConfig):
        with pytest.raises((KeyError, AttributeError)):
            get_config_value(default_config, "nonexistent.key")


class TestSetConfigValue:
    def test_set_and_revalidate(self, default_config: EngineConfig):
        new_config = set_config_value(default_config, "risk.max_position_size_usd", 10.0)
        assert new_config.risk.max_position_size_usd == 10.0

    def test_set_string_coercion(self, default_config: EngineConfig):
        new_config = set_config_value(default_config, "risk.max_trades_per_run", "5")
        assert new_config.risk.max_trades_per_run == 5

    def test_invalid_value_raises(self, default_config: EngineConfig):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            set_config_value(default_config, "risk.max_position_size_usd", -1.0)
