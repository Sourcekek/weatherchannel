"""Repository for risk check results."""

import sqlite3

from engine.models.risk import RiskCheckResult


def save_risk_checks(
    conn: sqlite3.Connection,
    run_id: str,
    idempotency_key: str,
    checks: list[RiskCheckResult],
) -> None:
    """Persist all risk check results for an order intent."""
    for check in checks:
        conn.execute(
            "INSERT INTO risk_checks "
            "(run_id, idempotency_key, check_name, passed, block_reason, detail) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                idempotency_key,
                check.check_name,
                int(check.passed),
                check.block_reason.value if check.block_reason else None,
                check.detail,
            ),
        )
    conn.commit()


def get_risk_checks_for_intent(
    conn: sqlite3.Connection, idempotency_key: str
) -> list[dict]:
    """Get all risk checks for an order intent."""
    rows = conn.execute(
        "SELECT * FROM risk_checks WHERE idempotency_key = ?",
        (idempotency_key,),
    ).fetchall()
    return [dict(r) for r in rows]
