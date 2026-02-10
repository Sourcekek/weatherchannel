"""Initial schema: all 12+ tables for the weather trading engine."""

import sqlite3

DDL = [
    # Market events from Gamma API
    """
    CREATE TABLE IF NOT EXISTS market_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL,
        slug TEXT NOT NULL,
        city_slug TEXT NOT NULL,
        target_date TEXT NOT NULL,
        title TEXT NOT NULL,
        raw_json TEXT NOT NULL,
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(event_id, fetched_at)
    )
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_market_events_city_date "
        "ON market_events(city_slug, target_date)"
    ),

    # Individual bucket markets
    """
    CREATE TABLE IF NOT EXISTS bucket_markets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_row_id INTEGER NOT NULL REFERENCES market_events(id),
        market_id TEXT NOT NULL,
        condition_id TEXT NOT NULL,
        clob_token_id_yes TEXT NOT NULL,
        clob_token_id_no TEXT NOT NULL,
        outcome_price_yes REAL NOT NULL,
        best_bid REAL NOT NULL,
        best_ask REAL NOT NULL,
        last_trade_price REAL NOT NULL,
        liquidity REAL NOT NULL,
        volume_24hr REAL NOT NULL,
        maker_base_fee REAL NOT NULL,
        taker_base_fee REAL NOT NULL,
        order_min_size REAL NOT NULL,
        accepting_orders INTEGER NOT NULL,
        end_date TEXT NOT NULL,
        group_item_title TEXT NOT NULL,
        group_item_threshold TEXT NOT NULL,
        bucket_type TEXT NOT NULL,
        bucket_low INTEGER NOT NULL,
        bucket_high INTEGER NOT NULL,
        bucket_unit TEXT NOT NULL DEFAULT 'F',
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_bucket_markets_market_id ON bucket_markets(market_id)",

    # NOAA forecast snapshots
    """
    CREATE TABLE IF NOT EXISTS forecast_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_slug TEXT NOT NULL,
        target_date TEXT NOT NULL,
        high_temp_f INTEGER NOT NULL,
        source_generated_at TEXT NOT NULL,
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        raw_json TEXT NOT NULL,
        UNIQUE(city_slug, target_date, fetched_at)
    )
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_forecast_city_date "
        "ON forecast_snapshots(city_slug, target_date)"
    ),

    # Edge/signal computation results
    """
    CREATE TABLE IF NOT EXISTS edge_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        event_id TEXT NOT NULL,
        market_id TEXT NOT NULL,
        city_slug TEXT NOT NULL,
        target_date TEXT NOT NULL,
        bucket_label TEXT NOT NULL,
        bucket_probability REAL NOT NULL,
        market_price_yes REAL NOT NULL,
        gross_edge REAL NOT NULL,
        fee_estimate REAL NOT NULL,
        slippage_estimate REAL NOT NULL,
        net_edge REAL NOT NULL,
        reason_code TEXT NOT NULL,
        sigma_used REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_edge_results_run ON edge_results(run_id)",

    # Risk check results per intent
    """
    CREATE TABLE IF NOT EXISTS risk_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        check_name TEXT NOT NULL,
        passed INTEGER NOT NULL,
        block_reason TEXT,
        detail TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_risk_checks_run ON risk_checks(run_id)",

    # Order intents (pre-execution)
    """
    CREATE TABLE IF NOT EXISTS order_intents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        idempotency_key TEXT UNIQUE NOT NULL,
        market_id TEXT NOT NULL,
        clob_token_id TEXT NOT NULL,
        side TEXT NOT NULL,
        price REAL NOT NULL,
        size_usd REAL NOT NULL,
        city_slug TEXT NOT NULL,
        target_date TEXT NOT NULL,
        bucket_label TEXT NOT NULL,
        net_edge REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_order_intents_run ON order_intents(run_id)",

    # Order execution results
    """
    CREATE TABLE IF NOT EXISTS order_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idempotency_key TEXT NOT NULL REFERENCES order_intents(idempotency_key),
        status TEXT NOT NULL,
        fill_price REAL,
        fill_size REAL,
        error_message TEXT NOT NULL DEFAULT '',
        executed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_order_results_key ON order_results(idempotency_key)",

    # Open/closed positions
    """
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        market_id TEXT NOT NULL,
        city_slug TEXT NOT NULL,
        target_date TEXT NOT NULL,
        bucket_label TEXT NOT NULL,
        entry_price REAL NOT NULL,
        current_price REAL NOT NULL,
        size_usd REAL NOT NULL,
        unrealized_pnl REAL NOT NULL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'open',
        opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        closed_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
    "CREATE INDEX IF NOT EXISTS idx_positions_city ON positions(city_slug)",

    # Daily PnL tracking
    """
    CREATE TABLE IF NOT EXISTS daily_pnl (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        realized_pnl REAL NOT NULL DEFAULT 0.0,
        unrealized_pnl REAL NOT NULL DEFAULT 0.0,
        total_pnl REAL NOT NULL DEFAULT 0.0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Config snapshots
    """
    CREATE TABLE IF NOT EXISTS config_snapshots (
        config_hash TEXT PRIMARY KEY,
        config_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # System state
    """
    CREATE TABLE IF NOT EXISTS system_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Insert default system state
    "INSERT OR IGNORE INTO system_state (key, value) VALUES ('mode', 'dry-run')",
    "INSERT OR IGNORE INTO system_state (key, value) VALUES ('paused', 'false')",
    "INSERT OR IGNORE INTO system_state (key, value) VALUES ('kill_switch', 'false')",

    # Operator command audit log
    """
    CREATE TABLE IF NOT EXISTS operator_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command TEXT NOT NULL,
        args TEXT NOT NULL DEFAULT '',
        result TEXT NOT NULL DEFAULT '',
        executed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # Pipeline run log
    """
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT UNIQUE NOT NULL,
        mode TEXT NOT NULL,
        config_hash TEXT,
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        status TEXT NOT NULL DEFAULT 'running',
        cities_scanned INTEGER NOT NULL DEFAULT 0,
        events_found INTEGER NOT NULL DEFAULT 0,
        opportunities_found INTEGER NOT NULL DEFAULT 0,
        orders_attempted INTEGER NOT NULL DEFAULT 0,
        orders_succeeded INTEGER NOT NULL DEFAULT 0,
        best_edge REAL,
        summary_json TEXT,
        error_message TEXT
    )
    """,
]


def up(conn: sqlite3.Connection) -> None:
    for stmt in DDL:
        conn.execute(stmt)
    conn.commit()
