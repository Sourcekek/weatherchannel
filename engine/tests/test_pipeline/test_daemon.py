"""Tests for the scan daemon."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from engine.daemon import (
    ScanDaemon,
    daemon_status,
    stop_daemon,
)


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    """Redirect PID/state files to temp directory."""
    pid_file = tmp_path / "daemon.pid"
    state_file = tmp_path / "daemon_state.json"
    monkeypatch.setattr("engine.daemon.PID_FILE", pid_file)
    monkeypatch.setattr("engine.daemon.PID_DIR", tmp_path)
    monkeypatch.setattr("engine.daemon.STATE_FILE", state_file)
    monkeypatch.setattr("engine.daemon.LOG_DIR", tmp_path / "logs")
    return {"pid": pid_file, "state": state_file, "dir": tmp_path}


@pytest.fixture
def mock_config():
    """Create a minimal mock config."""
    from engine.config.schema import (
        EngineConfig,
        ExecutionConfig,
        ExecutionMode,
        OpsConfig,
        RiskConfig,
        StrategyConfig,
    )

    return EngineConfig(
        strategy=StrategyConfig(),
        risk=RiskConfig(),
        execution=ExecutionConfig(mode=ExecutionMode.DRY_RUN),
        ops=OpsConfig(),
        cities=[],
    )


class TestScanDaemon:
    """Tests for ScanDaemon lifecycle."""

    def test_creates_pid_file(self, tmp_data, mock_config):
        """Daemon writes PID file on start."""
        daemon = ScanDaemon(mock_config, interval=1)

        # Patch the loop to exit after writing PID
        with patch.object(daemon, "_loop"), patch.object(daemon, "_setup_signals"):
            daemon.start()

        # PID file should have been created then cleaned up
        # State file should exist
        assert tmp_data["state"].exists()

    def test_prevents_duplicate_start(self, tmp_data, mock_config):
        """Cannot start daemon if one is already running."""
        # Write PID of current process (which is running)
        tmp_data["pid"].write_text(str(os.getpid()))

        daemon = ScanDaemon(mock_config)
        with pytest.raises(SystemExit):
            daemon._check_not_already_running()

    def test_cleans_stale_pid(self, tmp_data, mock_config):
        """Stale PID file from dead process is cleaned up."""
        # Use a PID that definitely doesn't exist
        tmp_data["pid"].write_text("999999999")

        daemon = ScanDaemon(mock_config)
        daemon._check_not_already_running()  # Should not raise
        assert not tmp_data["pid"].exists()

    def test_saves_state(self, tmp_data, mock_config):
        """Daemon persists state to JSON file."""
        daemon = ScanDaemon(mock_config, interval=60)
        daemon._started_at = "2026-01-01T00:00:00Z"
        daemon._total_scans = 5
        daemon._total_successes = 4
        daemon._total_failures = 1

        daemon._write_pid()
        daemon._save_state()

        state = json.loads(tmp_data["state"].read_text())
        assert state["total_scans"] == 5
        assert state["total_successes"] == 4
        assert state["total_failures"] == 1
        assert state["interval"] == 60

    def test_live_mode_sets_config(self, tmp_data, mock_config):
        """Passing live=True updates config to LIVE mode."""
        daemon = ScanDaemon(mock_config, live=True)
        assert daemon.config.execution.mode.value == "live"

    def test_dry_run_default(self, tmp_data, mock_config):
        """Default mode is dry-run."""
        daemon = ScanDaemon(mock_config)
        assert daemon.config.execution.mode.value == "dry-run"

    def test_run_one_scan_success(self, tmp_data, mock_config):
        """Successful scan increments success counter."""
        daemon = ScanDaemon(mock_config, interval=1)

        mock_summary = MagicMock()
        mock_summary.errors = []
        mock_summary.opportunities_found = 2
        mock_summary.orders_attempted = 1
        mock_summary.orders_succeeded = 1

        with patch("engine.daemon.ScanPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = mock_summary
            result = daemon._run_one_scan()

        assert result is True
        assert daemon._total_successes == 1
        assert daemon._total_failures == 0

    def test_run_one_scan_failure(self, tmp_data, mock_config):
        """Failed scan increments failure counter."""
        daemon = ScanDaemon(mock_config, interval=1)

        mock_summary = MagicMock()
        mock_summary.errors = ["Something went wrong"]

        with patch("engine.daemon.ScanPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = mock_summary
            result = daemon._run_one_scan()

        assert result is False
        assert daemon._total_successes == 0
        assert daemon._total_failures == 1

    def test_run_one_scan_crash(self, tmp_data, mock_config):
        """Exception in scan is caught and counted as failure."""
        daemon = ScanDaemon(mock_config, interval=1)

        with patch("engine.daemon.ScanPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = RuntimeError("boom")
            result = daemon._run_one_scan()

        assert result is False
        assert daemon._total_failures == 1

    def test_log_rotation(self, tmp_data, mock_config):
        """Old log files are cleaned up."""
        daemon = ScanDaemon(mock_config)
        log_dir = tmp_data["dir"] / "logs"
        log_dir.mkdir()

        # Create 110 log files
        for i in range(110):
            (log_dir / f"scan_{i:04d}.log").write_text(f"log {i}")

        daemon._rotate_logs()

        remaining = list(log_dir.glob("scan_*.log"))
        assert len(remaining) == 100

    def test_cleanup_removes_pid(self, tmp_data, mock_config):
        """Cleanup removes PID file."""
        daemon = ScanDaemon(mock_config)
        daemon._write_pid()
        assert tmp_data["pid"].exists()

        daemon._cleanup()
        assert not tmp_data["pid"].exists()


class TestDaemonControl:
    """Tests for stop/status commands."""

    def test_stop_no_daemon(self, tmp_data):
        """Stop returns 1 when no daemon is running."""
        assert stop_daemon() == 1

    def test_stop_stale_pid(self, tmp_data):
        """Stop cleans up stale PID file."""
        tmp_data["pid"].write_text("999999999")
        assert stop_daemon() == 0
        assert not tmp_data["pid"].exists()

    def test_status_no_state(self, tmp_data):
        """Status returns 1 when no state file exists."""
        assert daemon_status() == 1

    def test_status_with_state(self, tmp_data, capsys):
        """Status prints daemon info from state file."""
        state = {
            "pid": 99999,
            "started_at": "2026-01-01T00:00:00Z",
            "interval": 120,
            "mode": "dry_run",
            "total_scans": 10,
            "total_successes": 9,
            "total_failures": 1,
            "consecutive_failures": 0,
            "last_update": "2026-01-01T00:20:00Z",
        }
        tmp_data["state"].write_text(json.dumps(state))

        daemon_status()
        out = capsys.readouterr().out

        assert "120s" in out
        assert "10" in out  # total scans
