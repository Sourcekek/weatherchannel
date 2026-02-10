"""Continuous scan daemon — runs the scan pipeline on a fixed interval.

Designed to run as a background process with zero AI cost per scan.
All trade logic is deterministic; no LLM sessions are spawned.

Usage:
    python -m engine daemon --live --config ops/configs/live.yaml
    python -m engine daemon --interval 120  # every 2 minutes (default)
    python -m engine daemon --stop           # stop running daemon
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from engine.config.schema import EngineConfig, ExecutionMode
from engine.pipeline.scan_pipeline import ScanPipeline

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 120  # 2 minutes
MAX_BACKOFF = 600  # 10 minutes max backoff after repeated failures
PID_DIR = Path("data")
PID_FILE = PID_DIR / "daemon.pid"
STATE_FILE = PID_DIR / "daemon_state.json"
LOG_DIR = Path("logs")
MAX_LOG_FILES = 100  # Keep last 100 scan logs


class ScanDaemon:
    """Runs scan pipeline in a loop with crash recovery and signal handling."""

    def __init__(
        self,
        config: EngineConfig,
        db_path: str = "data/engine.db",
        interval: int = DEFAULT_INTERVAL,
        live: bool = False,
    ):
        self.config = config
        self.db_path = db_path
        self.interval = interval
        self.live = live
        self._running = False
        self._consecutive_failures = 0
        self._total_scans = 0
        self._total_successes = 0
        self._total_failures = 0
        self._started_at: str | None = None

        if live:
            self.config = config.model_copy(
                update={
                    "execution": config.execution.model_copy(
                        update={"mode": ExecutionMode.LIVE, "adapter": "simmer"}
                    )
                }
            )

    def start(self) -> None:
        """Start the daemon loop."""
        self._check_not_already_running()
        self._write_pid()
        self._setup_signals()
        self._running = True
        self._started_at = datetime.now(UTC).isoformat()

        mode_label = "LIVE" if self.config.execution.mode == ExecutionMode.LIVE else "DRY-RUN"
        logger.info(
            "Daemon started — mode=%s interval=%ds pid=%d",
            mode_label, self.interval, os.getpid(),
        )
        if self.config.execution.mode == ExecutionMode.LIVE:
            logger.warning("⚠️  LIVE MODE — real money at stake")

        print(f"🔄 Scan daemon started (pid {os.getpid()}, {mode_label}, every {self.interval}s)")
        print(f"   Logs: {LOG_DIR}/")
        print("   Stop: python -m engine daemon --stop")

        try:
            self._loop()
        except KeyboardInterrupt:
            logger.info("Daemon interrupted by keyboard")
        finally:
            self._cleanup()

    def _loop(self) -> None:
        """Main scan loop with backoff on failures."""
        while self._running:
            scan_start = time.monotonic()
            success = self._run_one_scan()

            if success:
                self._consecutive_failures = 0
                wait = self.interval
            else:
                self._consecutive_failures += 1
                backoff = min(
                    self.interval * (2 ** self._consecutive_failures),
                    MAX_BACKOFF,
                )
                wait = backoff
                logger.warning(
                    "Scan failed (%d consecutive), backing off %ds",
                    self._consecutive_failures, wait,
                )

            self._save_state()

            # Sleep in 1-second increments so we can respond to signals
            elapsed = time.monotonic() - scan_start
            remaining = max(0, wait - elapsed)
            sleep_until = time.monotonic() + remaining

            while self._running and time.monotonic() < sleep_until:
                time.sleep(1)

    def _run_one_scan(self) -> bool:
        """Execute a single scan cycle. Returns True on success."""
        self._total_scans += 1
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f"scan_{timestamp}.log"

        # Set up per-scan file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        try:
            logger.info("=== Scan #%d starting ===", self._total_scans)
            pipeline = ScanPipeline(self.config, self.db_path)
            summary = pipeline.run()

            if summary.errors:
                self._total_failures += 1
                logger.error(
                    "Scan #%d completed with errors: %s",
                    self._total_scans, summary.errors,
                )
                return False
            else:
                self._total_successes += 1
                logger.info(
                    "Scan #%d OK — %d opportunities, %d orders (%d filled)",
                    self._total_scans,
                    summary.opportunities_found,
                    summary.orders_attempted,
                    summary.orders_succeeded,
                )
                return True

        except Exception:
            self._total_failures += 1
            logger.exception("Scan #%d crashed", self._total_scans)
            return False

        finally:
            root_logger.removeHandler(file_handler)
            file_handler.close()
            self._rotate_logs()

    def _rotate_logs(self) -> None:
        """Keep only the most recent log files."""
        if not LOG_DIR.exists():
            return
        logs = sorted(LOG_DIR.glob("scan_*.log"))
        if len(logs) > MAX_LOG_FILES:
            for old in logs[: len(logs) - MAX_LOG_FILES]:
                old.unlink(missing_ok=True)

    def _setup_signals(self) -> None:
        """Handle SIGTERM and SIGINT for graceful shutdown."""
        def _stop(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Received %s, shutting down gracefully...", sig_name)
            print(f"\n⏹️  Received {sig_name}, finishing current cycle...")
            self._running = False

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)

    def _check_not_already_running(self) -> None:
        """Prevent duplicate daemons."""
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                # Check if process is actually running
                os.kill(pid, 0)
                print(f"❌ Daemon already running (pid {pid}). Stop it first:")
                print("   python -m engine daemon --stop")
                sys.exit(1)
            except (ProcessLookupError, ValueError):
                # Stale PID file — process is dead
                PID_FILE.unlink(missing_ok=True)
            except PermissionError:
                # Process exists but we can't signal it
                print(f"❌ Daemon may be running (pid {pid}), can't verify.")
                sys.exit(1)

    def _write_pid(self) -> None:
        PID_DIR.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))

    def _save_state(self) -> None:
        """Persist daemon stats for status reporting."""
        state = {
            "pid": os.getpid(),
            "started_at": self._started_at,
            "interval": self.interval,
            "mode": self.config.execution.mode.value,
            "total_scans": self._total_scans,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "consecutive_failures": self._consecutive_failures,
            "last_update": datetime.now(UTC).isoformat(),
        }
        STATE_FILE.write_text(json.dumps(state, indent=2))

    def _cleanup(self) -> None:
        """Remove PID file on exit."""
        PID_FILE.unlink(missing_ok=True)
        self._save_state()
        logger.info(
            "Daemon stopped — %d scans (%d ok, %d failed)",
            self._total_scans, self._total_successes, self._total_failures,
        )
        print(
            f"⏹️  Daemon stopped — {self._total_scans} scans "
            f"({self._total_successes} ok, {self._total_failures} failed)"
        )


def stop_daemon() -> int:
    """Stop a running daemon by sending SIGTERM."""
    if not PID_FILE.exists():
        print("No daemon running (no PID file found)")
        return 1

    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        print("Corrupt PID file, removing")
        PID_FILE.unlink(missing_ok=True)
        return 1

    try:
        os.kill(pid, 0)  # Check if alive
    except ProcessLookupError:
        print(f"Daemon not running (stale pid {pid}), cleaning up")
        PID_FILE.unlink(missing_ok=True)
        STATE_FILE.unlink(missing_ok=True)
        return 0

    print(f"Stopping daemon (pid {pid})...")
    os.kill(pid, signal.SIGTERM)

    # Wait up to 60s for graceful shutdown
    for _ in range(60):
        time.sleep(1)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            print("✅ Daemon stopped")
            PID_FILE.unlink(missing_ok=True)
            return 0

    print("⚠️  Daemon didn't stop in 60s, sending SIGKILL")
    os.kill(pid, signal.SIGKILL)
    PID_FILE.unlink(missing_ok=True)
    return 0


def daemon_status() -> int:
    """Print daemon status from state file."""
    if not STATE_FILE.exists():
        print("No daemon state found")
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, 0)
                print(f"  (but PID file exists: {pid}, process running)")
            except (ProcessLookupError, ValueError):
                print("  (stale PID file found)")
        return 1

    state = json.loads(STATE_FILE.read_text())
    pid = state.get("pid", "?")

    # Check if actually running
    running = False
    try:
        os.kill(int(pid), 0)
        running = True
    except (ProcessLookupError, ValueError, TypeError):
        pass

    status_icon = "🟢" if running else "🔴"
    mode = state.get("mode", "unknown").upper()
    interval = state.get("interval", "?")

    print(f"{status_icon} Daemon {'running' if running else 'stopped'}")
    print(f"  PID: {pid}")
    print(f"  Mode: {mode}")
    print(f"  Interval: {interval}s")
    print(f"  Started: {state.get('started_at', '?')}")
    print(f"  Total scans: {state.get('total_scans', 0)}")
    print(f"  Successes: {state.get('total_successes', 0)}")
    print(f"  Failures: {state.get('total_failures', 0)}")
    print(f"  Consecutive failures: {state.get('consecutive_failures', 0)}")
    print(f"  Last update: {state.get('last_update', '?')}")
    return 0
