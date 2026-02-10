# Incident Runbook: Stale Data

## Stale Forecast Data

### Definition
A forecast is stale when `source_generated_at` exceeds `forecast_max_age_minutes` (default: 360 minutes / 6 hours).

### Symptoms
- Edge results annotated with `STALE_FORECAST_DATA` reason code
- Forecast staleness > configured max age

### Behavior
- Stale forecasts are still used but with elevated uncertainty
- Sigma increases by +1.0F per 12 hours of staleness
- This naturally reduces edge calculations and makes opportunities less likely
- The system self-corrects by being more conservative with stale data

### Response
1. Usually no action needed — uncertainty elevation handles it
2. If NOAA is consistently stale, check their service status
3. Forecasts refresh on next successful scan

## Stale Market Data

### Definition
Market data is stale when `fetched_at` exceeds `market_data_max_age_minutes` (default: 30 minutes).

### Symptoms
- Market prices may not reflect current order book
- Risk of executing at outdated prices

### Behavior
- Market data is refreshed every scan cycle
- Stale data primarily affects between-scan decisions

### Response
1. Increase scan frequency: `config set ops.scan_interval_minutes=30`
2. If market data is consistently stale, check Gamma API connectivity

## Prevention

- Keep `ops.scan_interval_minutes` shorter than `ops.market_data_max_age_minutes`
- Monitor health check output for freshness warnings
- The engine's conservative default limits provide a buffer against stale-data risk
