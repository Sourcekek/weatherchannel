"""YAML config loader with snapshot persistence and runtime get/set."""

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from engine.config.defaults import DEFAULT_CITIES
from engine.config.schema import EngineConfig


def load_config(path: str | Path) -> EngineConfig:
    """Load and validate config from a YAML file.

    If no cities are specified in the YAML, injects DEFAULT_CITIES.
    """
    path = Path(path)
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    if "cities" not in raw or not raw["cities"]:
        raw["cities"] = [c.model_dump() for c in DEFAULT_CITIES]

    return EngineConfig(**raw)


def config_hash(config: EngineConfig) -> str:
    """Compute a deterministic SHA256 hash of the config."""
    data = config.model_dump_json(indent=None)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def snapshot_config(config: EngineConfig, db: Any) -> str:
    """Persist a config snapshot to the database if it changed. Returns the hash."""
    h = config_hash(config)
    cursor = db.execute(
        "SELECT 1 FROM config_snapshots WHERE config_hash = ?", (h,)
    )
    if cursor.fetchone() is None:
        db.execute(
            "INSERT INTO config_snapshots (config_hash, config_json, created_at) "
            "VALUES (?, ?, CURRENT_TIMESTAMP)",
            (h, config.model_dump_json()),
        )
        db.commit()
    return h


def get_config_value(config: EngineConfig, dotted_key: str) -> Any:
    """Get a config value by dotted key path. E.g. 'risk.max_position_size_usd'."""
    parts = dotted_key.split(".")
    obj: Any = config
    for part in parts:
        if isinstance(obj, list):
            obj = obj[int(part)]
        elif hasattr(obj, part):
            obj = getattr(obj, part)
        elif isinstance(obj, dict):
            obj = obj[part]
        else:
            raise KeyError(f"Config key not found: {dotted_key}")
    return obj


def set_config_value(config: EngineConfig, dotted_key: str, value: Any) -> EngineConfig:
    """Set a config value by dotted key path and re-validate.

    Returns a new EngineConfig instance.
    """
    data = json.loads(config.model_dump_json())
    parts = dotted_key.split(".")
    target = data
    for part in parts[:-1]:
        target = target[part]
    # Attempt type coercion for common cases
    old_value = target.get(parts[-1])
    if isinstance(old_value, int) and isinstance(value, str):
        value = int(value)
    elif isinstance(old_value, float) and isinstance(value, str):
        value = float(value)
    target[parts[-1]] = value
    return EngineConfig(**data)
