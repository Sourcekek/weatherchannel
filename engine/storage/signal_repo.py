"""Repository for edge/signal computation results."""

import sqlite3

from engine.models.signal import EdgeResult


def save_edge_result(conn: sqlite3.Connection, er: EdgeResult) -> int:
    """Persist an edge result. Returns the row id."""
    cursor = conn.execute(
        "INSERT INTO edge_results "
        "(run_id, event_id, market_id, city_slug, target_date, bucket_label, "
        "bucket_probability, market_price_yes, gross_edge, fee_estimate, "
        "slippage_estimate, net_edge, reason_code, sigma_used) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            er.run_id,
            er.event_id,
            er.market_id,
            er.city_slug,
            er.target_date,
            er.bucket_label,
            er.bucket_probability,
            er.market_price_yes,
            er.gross_edge,
            er.fee_estimate,
            er.slippage_estimate,
            er.net_edge,
            er.reason_code.value,
            er.sigma_used,
        ),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def get_edge_results_for_run(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    """Get all edge results for a run."""
    rows = conn.execute(
        "SELECT * FROM edge_results WHERE run_id = ? ORDER BY net_edge DESC",
        (run_id,),
    ).fetchall()
    return [dict(r) for r in rows]
