"""Health checker: DB connectivity, API reachability, data freshness."""

import sqlite3

import httpx

from engine.models.reporting import HealthStatus
from engine.storage import state_repo


class HealthChecker:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def check(self) -> HealthStatus:
        db_ok = self._check_db()
        gamma_ok = self._check_gamma()
        noaa_ok = self._check_noaa()
        last_run_age = self._last_run_age_minutes()
        forecast_ok = True  # Placeholder
        market_ok = True  # Placeholder
        kill_switch = state_repo.is_kill_switch_active(self.conn)
        is_paused = state_repo.is_paused(self.conn)
        mode = state_repo.get_mode(self.conn)

        return HealthStatus(
            db_connected=db_ok,
            gamma_api_reachable=gamma_ok,
            noaa_api_reachable=noaa_ok,
            last_run_age_minutes=last_run_age,
            forecast_freshness_ok=forecast_ok,
            market_data_freshness_ok=market_ok,
            kill_switch_active=kill_switch,
            paused=is_paused,
            mode=mode,
        )

    def _check_db(self) -> bool:
        try:
            self.conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _check_gamma(self) -> bool:
        try:
            resp = httpx.get(
                "https://gamma-api.polymarket.com/events?limit=1",
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _check_noaa(self) -> bool:
        try:
            resp = httpx.get(
                "https://api.weather.gov",
                headers={"User-Agent": "weatherchannel-health/0.1.0"},
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _last_run_age_minutes(self) -> float | None:
        run = state_repo.get_latest_run(self.conn)
        if run is None:
            return None
        completed = run.get("completed_at")
        if completed is None:
            return None
        try:
            from datetime import UTC, datetime

            end = datetime.fromisoformat(completed)
            if end.tzinfo is None:
                end = end.replace(tzinfo=UTC)
            delta = datetime.now(UTC) - end
            return delta.total_seconds() / 60
        except (ValueError, TypeError):
            return None
