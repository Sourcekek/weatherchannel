"""Position tracker: open positions and mark-to-market PnL."""

import sqlite3

from engine.models.reporting import PositionSnapshot
from engine.storage import position_repo


class PositionTracker:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_open_positions(self) -> list[PositionSnapshot]:
        rows = position_repo.get_open_positions(self.conn)
        return [
            PositionSnapshot(
                market_id=r["market_id"],
                city_slug=r["city_slug"],
                target_date=r["target_date"],
                bucket_label=r["bucket_label"],
                entry_price=r["entry_price"],
                current_price=r["current_price"],
                size_usd=r["size_usd"],
                unrealized_pnl=r["unrealized_pnl"],
                status=r["status"],
            )
            for r in rows
        ]

    def total_exposure(self) -> float:
        return position_repo.get_total_open_exposure(self.conn)
