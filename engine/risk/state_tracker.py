"""Risk state tracker: in-memory + DB state for exposure, trades, loss."""

import sqlite3
from datetime import UTC, datetime

from engine.storage import order_repo, position_repo, state_repo


class StateTracker:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.trades_this_run = 0
        self._total_exposure: float | None = None
        self._city_exposure: dict[str, float] = {}

    def hydrate(self) -> None:
        """Load state from DB."""
        self._total_exposure = position_repo.get_total_open_exposure(self.conn)
        self._city_exposure.clear()

    @property
    def kill_switch_active(self) -> bool:
        return state_repo.is_kill_switch_active(self.conn)

    @property
    def is_paused(self) -> bool:
        return state_repo.is_paused(self.conn)

    @property
    def total_exposure(self) -> float:
        if self._total_exposure is None:
            self._total_exposure = position_repo.get_total_open_exposure(self.conn)
        return self._total_exposure

    def city_exposure(self, city_slug: str) -> float:
        if city_slug not in self._city_exposure:
            self._city_exposure[city_slug] = position_repo.get_city_open_exposure(
                self.conn, city_slug
            )
        return self._city_exposure[city_slug]

    def daily_loss(self) -> float:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        pnl = position_repo.get_daily_pnl(self.conn, today)
        if pnl is None:
            return 0.0
        total = pnl["total_pnl"]
        return abs(total) if total < 0 else 0.0

    def minutes_since_last_trade(self, market_id: str) -> float | None:
        last_time = order_repo.get_last_trade_time_for_market(self.conn, market_id)
        if last_time is None:
            return None
        try:
            last_dt = datetime.fromisoformat(last_time)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=UTC)
            delta = datetime.now(UTC) - last_dt
            return delta.total_seconds() / 60
        except (ValueError, TypeError):
            return None

    def record_trade(self, city_slug: str, size_usd: float) -> None:
        """Update in-memory state after a trade."""
        self.trades_this_run += 1
        if self._total_exposure is not None:
            self._total_exposure += size_usd
        if city_slug in self._city_exposure:
            self._city_exposure[city_slug] += size_usd
