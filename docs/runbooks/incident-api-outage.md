# Incident Runbook: API Outage

## Gamma API Outage

### Symptoms
- Scan finds 0 events
- Logs show HTTP errors for gamma-api.polymarket.com

### Behavior
- Engine logs warnings and skips affected city/date pairs
- Scan completes normally with 0 events = empty summary, no error
- No orders are created (no data = no opportunities)

### Response
1. Check Gamma API status manually
2. No immediate action needed — engine is safe with 0 events
3. Monitor for recovery
4. If prolonged (>2h), pause scanning to save API quota:
   ```bash
   python -m engine pause
   ```

## NOAA API Outage

### Symptoms
- Events found but 0 forecasts
- Logs show 503/429 errors for api.weather.gov
- All edge results show `NO_FORECAST_AVAILABLE`

### Behavior
- Engine retries 3x with exponential backoff (5s, 10s, 20s)
- After exhaustion, skips forecast for that city/date
- Events without forecasts get `NO_FORECAST_AVAILABLE` reason code
- No opportunities generated = no orders

### Response
1. Check NOAA status at https://www.weather.gov/
2. The engine handles this gracefully — no action required
3. Forecasts will be fetched on next successful scan
4. If prolonged, the engine continues scanning but produces no trades

## Both APIs Down

### Behavior
- Scan completes in seconds with empty results
- No data persisted, no orders, no risk

### Response
1. Pause scanning to avoid noisy logs
2. Resume when APIs recover
