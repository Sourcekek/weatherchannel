"""Weather Trading Dashboard — FastAPI backend serving real-time data + controls."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from engine.storage.database import connect, run_migrations

DB_PATH = Path(__file__).parent.parent / "data" / "engine.db"
CONFIG_PATH = Path(__file__).parent.parent / "ops" / "configs" / "live.yaml"
DASHBOARD_HTML = Path(__file__).parent.parent / "static" / "dashboard.html"

app = FastAPI(title="Weather Trading Dashboard", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _conn() -> sqlite3.Connection:
    conn = connect(DB_PATH)
    run_migrations(conn)
    return conn


# ── Data endpoints ──────────────────────────────────────────────


@app.get("/api/status")
def get_status():
    """Engine status: mode, paused, kill switch, exposure."""
    conn = _conn()
    try:
        state = {}
        for row in conn.execute("SELECT key, value FROM system_state").fetchall():
            state[row[0]] = row[1]

        exposure = conn.execute(
            "SELECT COALESCE(SUM(size_usd), 0) FROM positions WHERE status='open'"
        ).fetchone()[0]

        position_count = conn.execute(
            "SELECT COUNT(*) FROM positions WHERE status='open'"
        ).fetchone()[0]

        return {
            "mode": state.get("mode", "dry-run"),
            "paused": state.get("paused", "false") == "true",
            "kill_switch": state.get("kill_switch", "false") == "true",
            "total_exposure_usd": round(exposure, 2),
            "open_positions": position_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    finally:
        conn.close()


@app.get("/api/positions")
def get_positions():
    """All open positions with P&L."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, market_id, city_slug, target_date, bucket_label, "
            "entry_price, current_price, size_usd, unrealized_pnl, status, opened_at "
            "FROM positions WHERE status='open' ORDER BY opened_at DESC"
        ).fetchall()
        return [
            {
                "id": r[0], "market_id": r[1], "city_slug": r[2],
                "target_date": r[3], "bucket_label": r[4],
                "entry_price": r[5], "current_price": r[6],
                "size_usd": r[7], "unrealized_pnl": round(r[8] or 0, 4),
                "status": r[9], "opened_at": r[10],
                "pnl_pct": round(((r[6] - r[5]) / r[5] * 100) if r[5] else 0, 1),
            }
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/api/runs")
def get_runs(limit: int = 50):
    """Recent scan runs."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT run_id, mode, started_at, completed_at, status, "
            "cities_scanned, events_found, opportunities_found, "
            "orders_attempted, orders_succeeded, best_edge, error_message "
            "FROM runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "run_id": r[0], "mode": r[1], "started_at": r[2],
                "completed_at": r[3], "status": r[4],
                "cities_scanned": r[5], "events_found": r[6],
                "opportunities_found": r[7], "orders_attempted": r[8],
                "orders_succeeded": r[9], "best_edge": r[10],
                "error_message": r[11],
            }
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/api/edges")
def get_recent_edges(limit: int = 50):
    """Recent edge calculations — opportunities and near-misses."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT run_id, city_slug, target_date, bucket_label, "
            "bucket_probability, market_price_yes, net_edge, reason_code, "
            "sigma_used, created_at "
            "FROM edge_results "
            "WHERE reason_code IN ('OPPORTUNITY', 'EDGE_BELOW_THRESHOLD') "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "run_id": r[0], "city_slug": r[1], "target_date": r[2],
                "bucket_label": r[3], "probability": round(r[4], 4),
                "market_price": round(r[5], 4), "net_edge": round(r[6], 4),
                "reason_code": r[7], "sigma": round(r[8], 2),
                "created_at": r[9],
            }
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/api/risk-blocks")
def get_risk_blocks(limit: int = 50):
    """Recent risk check failures."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT run_id, check_name, block_reason, detail, created_at "
            "FROM risk_checks WHERE passed = 0 "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "run_id": r[0], "check_name": r[1], "block_reason": r[2],
                "detail": r[3], "created_at": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/api/forecasts")
def get_forecasts():
    """Latest forecast per city/date."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT city_slug, target_date, high_temp_f, fetched_at "
            "FROM forecast_snapshots "
            "WHERE id IN ("
            "  SELECT MAX(id) FROM forecast_snapshots "
            "  GROUP BY city_slug, target_date"
            ") ORDER BY target_date, city_slug"
        ).fetchall()
        return [
            {
                "city_slug": r[0], "target_date": r[1],
                "high_temp_f": r[2], "fetched_at": r[3],
            }
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/api/orders")
def get_orders(limit: int = 50):
    """Recent order intents + results."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT oi.idempotency_key, oi.city_slug, oi.bucket_label, "
            "oi.target_date, oi.price, oi.size_usd, oi.net_edge, oi.created_at, "
            "orr.status, orr.fill_price, orr.fill_size, orr.error_message "
            "FROM order_intents oi "
            "LEFT JOIN order_results orr ON oi.idempotency_key = orr.idempotency_key "
            "ORDER BY oi.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "idempotency_key": r[0], "city_slug": r[1],
                "bucket_label": r[2], "target_date": r[3],
                "price": r[4], "size_usd": r[5], "net_edge": round(r[6], 4),
                "created_at": r[7], "status": r[8],
                "fill_price": r[9], "fill_size": r[10],
                "error_message": r[11],
            }
            for r in rows
        ]
    finally:
        conn.close()


@app.get("/api/health")
def get_health():
    """Quick health check."""
    conn = _conn()
    try:
        last_run = conn.execute(
            "SELECT completed_at FROM runs ORDER BY completed_at DESC LIMIT 1"
        ).fetchone()
        last_run_at = last_run[0] if last_run else None

        age_minutes = None
        if last_run_at:
            try:
                completed = datetime.fromisoformat(last_run_at)
                if completed.tzinfo is None:
                    completed = completed.replace(tzinfo=UTC)
                age_minutes = round(
                    (datetime.now(UTC) - completed).total_seconds() / 60, 1
                )
            except (ValueError, TypeError):
                pass

        return {
            "db_ok": True,
            "last_run_at": last_run_at,
            "last_run_age_minutes": age_minutes,
        }
    except Exception as e:
        return {"db_ok": False, "error": str(e)}
    finally:
        conn.close()


# ── Config endpoints (read + write) ────────────────────────────


class ConfigUpdate(BaseModel):
    """Partial config update — only provided fields are changed."""
    strategy: dict | None = None
    risk: dict | None = None
    execution: dict | None = None
    ops: dict | None = None


@app.get("/api/config")
def get_config():
    """Read current live config."""
    if not CONFIG_PATH.exists():
        raise HTTPException(404, "Config file not found")
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@app.post("/api/config")
def update_config(update: ConfigUpdate):
    """Merge-update config fields and write back to live.yaml."""
    if not CONFIG_PATH.exists():
        raise HTTPException(404, "Config file not found")

    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f) or {}

    changed = []
    for section_name in ("strategy", "risk", "execution", "ops"):
        patch = getattr(update, section_name)
        if patch:
            if section_name not in cfg:
                cfg[section_name] = {}
            for k, v in patch.items():
                old = cfg[section_name].get(k)
                if old != v:
                    changed.append(f"{section_name}.{k}: {old} → {v}")
                    cfg[section_name][k] = v

    if not changed:
        return {"status": "no_change", "changed": []}

    # Backup before writing
    backup = CONFIG_PATH.with_suffix(".yaml.bak")
    backup.write_text(CONFIG_PATH.read_text())

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    return {"status": "updated", "changed": changed}


# ── Control endpoints ───────────────────────────────────────────


@app.post("/api/control/pause")
def pause_engine():
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO system_state (key, value, updated_at) "
            "VALUES ('paused', 'true', CURRENT_TIMESTAMP)"
        )
        conn.commit()
        return {"status": "paused"}
    finally:
        conn.close()


@app.post("/api/control/resume")
def resume_engine():
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO system_state (key, value, updated_at) "
            "VALUES ('paused', 'false', CURRENT_TIMESTAMP)"
        )
        conn.commit()
        return {"status": "resumed"}
    finally:
        conn.close()


@app.post("/api/control/kill-switch")
def toggle_kill_switch(active: bool = True):
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO system_state (key, value, updated_at) "
            "VALUES ('kill_switch', ?, CURRENT_TIMESTAMP)",
            ("true" if active else "false",),
        )
        conn.commit()
        return {"status": "kill_switch", "active": active}
    finally:
        conn.close()


# ── Serve dashboard ─────────────────────────────────────────────


@app.get("/")
def serve_dashboard():
    if DASHBOARD_HTML.exists():
        return FileResponse(DASHBOARD_HTML, media_type="text/html")
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8777)
