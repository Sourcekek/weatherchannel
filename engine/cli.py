"""CLI entry point for the weather trading engine."""

import argparse
import logging

from engine.config.loader import get_config_value, load_config, set_config_value
from engine.config.schema import ExecutionMode
from engine.pipeline.scan_pipeline import ScanPipeline
from engine.reporting.health_checker import HealthChecker
from engine.reporting.position_tracker import PositionTracker
from engine.storage import state_repo
from engine.storage.database import connect, run_migrations

DEFAULT_CONFIG = "ops/configs/default.yaml"
DEFAULT_DB = "data/engine.db"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="engine",
        description="Weather market trading engine",
    )
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG, help="Config YAML path"
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite DB path")

    sub = parser.add_subparsers(dest="command")

    # scan
    scan_p = sub.add_parser("scan", help="Run one scan cycle")
    scan_p.add_argument(
        "--live", action="store_true", help="Enable live execution"
    )

    # status
    sub.add_parser("status", help="Show positions and exposure")

    # health
    sub.add_parser("health", help="Run health checks")

    # config show / config set
    config_p = sub.add_parser("config", help="Config operations")
    config_sub = config_p.add_subparsers(dest="config_command")
    config_sub.add_parser("show", help="Display current config")
    set_p = config_sub.add_parser("set", help="Set a config value")
    set_p.add_argument("keyvalue", help="key=value to set")

    # pause / resume / kill-switch
    sub.add_parser("pause", help="Pause scanning")
    sub.add_parser("resume", help="Resume scanning")
    ks_p = sub.add_parser("kill-switch", help="Toggle kill switch")
    ks_p.add_argument("state", choices=["on", "off"])

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config(args.config)

    if args.command == "scan":
        return _cmd_scan(config, args)
    elif args.command == "status":
        return _cmd_status(config, args)
    elif args.command == "health":
        return _cmd_health(config, args)
    elif args.command == "config":
        return _cmd_config(config, args)
    elif args.command == "pause":
        return _cmd_pause(args)
    elif args.command == "resume":
        return _cmd_resume(args)
    elif args.command == "kill-switch":
        return _cmd_kill_switch(args)
    else:
        parser.print_help()
        return 1


def _cmd_scan(config, args) -> int:
    if args.live:
        config = config.model_copy(
            update={"execution": {"mode": "live", "adapter": "simmer"}}
        )
    if config.execution.mode == ExecutionMode.LIVE:
        print("WARNING: Running in LIVE mode")
    pipeline = ScanPipeline(config, args.db)
    summary = pipeline.run()
    return 0 if not summary.errors else 1


def _cmd_status(config, args) -> int:
    conn = connect(args.db)
    run_migrations(conn)
    tracker = PositionTracker(conn)
    positions = tracker.get_open_positions()
    exposure = tracker.total_exposure()

    mode = state_repo.get_mode(conn)
    paused = state_repo.is_paused(conn)
    kill = state_repo.is_kill_switch_active(conn)

    print(f"Mode: {mode} | Paused: {paused} | Kill switch: {kill}")
    print(f"Open positions: {len(positions)} | Exposure: ${exposure:.2f}")
    for p in positions:
        print(
            f"  {p.city_slug} {p.bucket_label}: "
            f"${p.size_usd:.2f} @ {p.entry_price:.4f}"
        )
    conn.close()
    return 0


def _cmd_health(config, args) -> int:
    conn = connect(args.db)
    run_migrations(conn)
    checker = HealthChecker(conn)
    status = checker.check()

    print(f"DB: {'OK' if status.db_connected else 'FAIL'}")
    print(f"Gamma API: {'OK' if status.gamma_api_reachable else 'FAIL'}")
    print(f"NOAA API: {'OK' if status.noaa_api_reachable else 'FAIL'}")
    if status.last_run_age_minutes is not None:
        print(f"Last run: {status.last_run_age_minutes:.0f} min ago")
    else:
        print("Last run: never")
    print(f"Mode: {status.mode}")
    print(f"Paused: {status.paused}")
    print(f"Kill switch: {status.kill_switch_active}")
    conn.close()
    return 0


def _cmd_config(config, args) -> int:
    if args.config_command == "show":
        print(config.model_dump_json(indent=2))
        return 0
    elif args.config_command == "set":
        kv = args.keyvalue
        if "=" not in kv:
            print("Error: use key=value format")
            return 1
        key, value = kv.split("=", 1)
        try:
            new_config = set_config_value(config, key.strip(), value.strip())
            print(f"Set {key} = {get_config_value(new_config, key.strip())}")
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1
    else:
        print("Use: config show | config set key=value")
        return 1


def _cmd_pause(args) -> int:
    conn = connect(args.db)
    run_migrations(conn)
    state_repo.set_system_state(conn, "paused", "true")
    state_repo.log_operator_command(conn, "pause", result="paused")
    print("System paused")
    conn.close()
    return 0


def _cmd_resume(args) -> int:
    conn = connect(args.db)
    run_migrations(conn)
    state_repo.set_system_state(conn, "paused", "false")
    state_repo.log_operator_command(conn, "resume", result="resumed")
    print("System resumed")
    conn.close()
    return 0


def _cmd_kill_switch(args) -> int:
    conn = connect(args.db)
    run_migrations(conn)
    value = "true" if args.state == "on" else "false"
    state_repo.set_system_state(conn, "kill_switch", value)
    state_repo.log_operator_command(
        conn, "kill-switch", args=args.state, result=f"kill_switch={value}"
    )
    print(f"Kill switch: {args.state}")
    conn.close()
    return 0
