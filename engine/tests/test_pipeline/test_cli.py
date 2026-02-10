"""Tests for CLI commands."""

from pathlib import Path

from engine.cli import main


class TestCLI:
    def test_no_command_returns_1(self, capsys):
        result = main([])
        assert result == 1

    def test_config_show(self, tmp_path: Path, capsys):
        config_path = tmp_path / "test.yaml"
        config_path.write_text("")
        result = main(["--config", str(config_path), "config", "show"])
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_pause_resume(self, tmp_path: Path, capsys):
        db_path = str(tmp_path / "test.db")
        config_path = tmp_path / "test.yaml"
        config_path.write_text("")

        result = main([
            "--config", str(config_path), "--db", db_path, "pause"
        ])
        assert result == 0
        captured = capsys.readouterr()
        assert "paused" in captured.out.lower()

        result = main([
            "--config", str(config_path), "--db", db_path, "resume"
        ])
        assert result == 0
        captured = capsys.readouterr()
        assert "resumed" in captured.out.lower()

    def test_kill_switch(self, tmp_path: Path, capsys):
        db_path = str(tmp_path / "test.db")
        config_path = tmp_path / "test.yaml"
        config_path.write_text("")

        result = main([
            "--config", str(config_path), "--db", db_path,
            "kill-switch", "on",
        ])
        assert result == 0
        captured = capsys.readouterr()
        assert "on" in captured.out.lower()

    def test_status(self, tmp_path: Path, capsys):
        db_path = str(tmp_path / "test.db")
        config_path = tmp_path / "test.yaml"
        config_path.write_text("")

        result = main([
            "--config", str(config_path), "--db", db_path, "status",
        ])
        assert result == 0
        captured = capsys.readouterr()
        assert "Mode" in captured.out

    def test_config_set(self, tmp_path: Path, capsys):
        config_path = tmp_path / "test.yaml"
        config_path.write_text("")
        result = main([
            "--config", str(config_path),
            "config", "set", "risk.max_position_size_usd=10.0",
        ])
        assert result == 0
        captured = capsys.readouterr()
        assert "10.0" in captured.out
