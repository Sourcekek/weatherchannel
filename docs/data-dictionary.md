# Data Dictionary

## Domain Models

### MarketEvent
Groups bucket markets by city/date event.
- `event_id`: Polymarket event ID
- `slug`: Event slug (e.g., `highest-temperature-in-nyc-on-february-11-2026`)
- `city_slug`: City identifier (nyc, chicago, seattle, atlanta, dallas)
- `target_date`: Target date (YYYY-MM-DD)
- `buckets`: List of BucketMarket

### BucketMarket
Individual temperature bucket contract within an event.
- `market_id`: Polymarket market ID
- `condition_id`: Contract condition ID
- `clob_token_id_yes` / `clob_token_id_no`: CLOB order book token IDs
- `outcome_price_yes`: Current Yes price (0.0 to 1.0)
- `best_bid` / `best_ask`: Current order book spread
- `accepting_orders`: Whether the market is open for trading
- `bucket`: TemperatureBucket definition

### TemperatureBucket
- `bucket_type`: OR_HIGHER, OR_BELOW, RANGE, EXACT
- `low` / `high`: Temperature bounds (integers, Fahrenheit by default)
- `unit`: F or C

### ForecastPoint
NOAA forecast for a city on a target date.
- `high_temp_f`: Forecast daytime high in Fahrenheit
- `source_generated_at`: When NOAA generated the forecast
- `fetched_at`: When we fetched it

### EdgeResult
Signal computation result for one bucket.
- `bucket_probability`: P(bucket) from normal CDF
- `market_price_yes`: Current market price
- `gross_edge`: P - price
- `net_edge`: gross - fees - slippage
- `reason_code`: OPPORTUNITY, EDGE_BELOW_THRESHOLD, etc.
- `sigma_used`: Uncertainty parameter used

### RiskVerdict
Result of all 10 risk checks.
- `approved`: True if all checks passed
- `checks`: List of RiskCheckResult with pass/fail and reason

### OrderIntent / OrderResult
Pre-execution intent and post-execution result.
- `idempotency_key`: SHA256 hash preventing duplicate orders
- `status`: PENDING, DRY_RUN, SUBMITTED, FILLED, REJECTED, FAILED, DUPLICATE

## Database Tables

### market_events
Snapshots of Polymarket events with raw JSON for audit.

### bucket_markets
Individual bucket market data linked to events via `event_row_id`.

### forecast_snapshots
NOAA forecast data with raw JSON. Keyed by (city_slug, target_date, fetched_at).

### edge_results
Signal computation outputs. Keyed by run_id. Sorted by net_edge.

### risk_checks
Individual risk check results. Keyed by (run_id, idempotency_key).

### order_intents
Pre-execution order intents with UNIQUE idempotency_key constraint.

### order_results
Post-execution results linked to intents via idempotency_key.

### positions
Open/closed positions with mark-to-market tracking.

### daily_pnl
Daily realized + unrealized PnL. Keyed by date (YYYY-MM-DD).

### config_snapshots
Config versions with SHA256 hash. For audit trail.

### system_state
Key-value store for mode, paused, kill_switch.

### operator_commands
Audit log of operator actions (pause, resume, kill-switch).

### runs
Pipeline run log with metrics and summary JSON.

### schema_versions
Migration tracking table.
