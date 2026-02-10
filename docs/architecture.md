# Architecture

## System Overview

Weatherchannel is a deterministic weather-market trading engine that exploits forecast/price mismatches on Polymarket temperature bucket contracts.

```
                    +-----------+
                    | OpenClaw  |
                    | (skills)  |
                    +-----+-----+
                          |
                    +-----v-----+
                    |    CLI    |
                    | (argparse)|
                    +-----+-----+
                          |
                    +-----v---------+
                    | Scan Pipeline |
                    +---+---+---+---+
                        |   |   |
           +------------+   |   +------------+
           |                |                |
    +------v------+  +------v------+  +------v------+
    |   Ingest    |  |   Signal    |  |    Risk     |
    | - Gamma API |  | - Normal CDF|  | - 10 checks |
    | - NOAA API  |  | - Edge calc |  | - State     |
    | - Slug parse|  | - Calibrate |  |   tracker   |
    +------+------+  +------+------+  +------+------+
           |                |                |
           +--------+-------+--------+-------+
                    |                |
             +------v------+  +------v------+
             |  Execution  |  |  Reporting  |
             | - Dry-run   |  | - Summarizer|
             | - Live stub |  | - Formatters|
             | - Idempotent|  | - Health    |
             +------+------+  +------+------+
                    |                |
                    +--------+-------+
                             |
                      +------v------+
                      |   Storage   |
                      | - SQLite    |
                      | - 14 tables |
                      | - Repos     |
                      +-------------+
```

## Module Descriptions

### engine/config/
Pydantic v2 strict-mode configuration with YAML loading, snapshot persistence, and runtime get/set. Extra fields are rejected. Default mode is always `dry-run`.

### engine/models/
Frozen dataclasses for all domain types: markets, forecasts, signals, risk verdicts, orders, and reporting. These are pure data — no I/O or side effects.

### engine/storage/
SQLite with WAL mode, migration runner, and repository layer for all 14 tables. Row-level CRUD with dict returns for flexibility.

### engine/ingest/
API clients for Gamma (market data) and NOAA (forecasts). Slug parser handles all 4 bucket types including negative temperatures. Market scanner constructs deterministic slugs per city/date and handles 404s gracefully.

### engine/signal/
Normal CDF probability calculator with +-0.5 continuity correction. Uncertainty scales linearly with days-to-resolution. Edge = P(bucket) - market_price - fees - slippage.

### engine/risk/
10 mandatory risk checks that always run (no short-circuit) for full audit trails. State tracker hydrates from DB and updates in-memory on trades.

### engine/execution/
Executor with defense-in-depth kill switch recheck, SHA256 idempotency keys, and adapter pattern. Dry-run adapter simulates fills; live adapter is a stub that raises `NotImplementedError` until Gate B is passed.

### engine/reporting/
Run summarizer, position tracker, health checker, and three output formatters (text, JSON, chat-friendly markdown).

### engine/pipeline/
Scan pipeline orchestrates the full cycle: init, ingest markets, ingest forecasts, generate signals, risk-check + execute, report.

## Data Flow

1. **Scan** → Gamma API → `market_events` + `bucket_markets`
2. **Forecast** → NOAA API → `forecast_snapshots`
3. **Signal** → Normal CDF → `edge_results`
4. **Risk** → 10 checks → `risk_checks`
5. **Execute** → Adapter → `order_intents` + `order_results` + `positions`
6. **Report** → Summary → `runs`

## Key Design Decisions

- **Pre-resolved NOAA grids**: Avoids runtime points API call, reduces latency and failure modes.
- **Deterministic slug construction**: No fuzzy search. 404 = no market, skip.
- **No short-circuit in risk checks**: Full audit trail for every decision.
- **Idempotency keys**: SHA256 of (run_id, market_id, side, price). Prevents duplicate orders under retry.
- **SQLite WAL mode**: Concurrent reads during scan without blocking writes.
