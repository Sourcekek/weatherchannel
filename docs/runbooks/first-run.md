# First Run Runbook

## Prerequisites

1. Python 3.11+
2. Virtual environment set up: `python -m venv .venv && source .venv/bin/activate`
3. Package installed: `pip install -e ".[dev]"`
4. Tests passing: `pytest engine/tests/ -q`

## Steps

### 1. Verify config

```bash
python -m engine config show
```

Confirm:
- Mode is `dry-run`
- Risk limits are conservative (defaults)
- 5 cities are configured

### 2. Run health check

```bash
python -m engine health
```

Confirm:
- DB: OK
- Gamma API: OK
- NOAA API: OK

### 3. Run first dry-run scan

```bash
python -m engine scan
```

Expected output:
- Chat-friendly summary showing cities scanned, events found, opportunities
- All orders should be `DRY_RUN` status
- No errors in summary

### 4. Check status

```bash
python -m engine status
```

Shows positions created during dry-run (simulated).

### 5. Verify database

The scan creates `data/engine.db` with all tables populated:
- `runs` table has the completed run
- `edge_results` has signal computations
- `order_intents` has dry-run orders

### 6. Review results

Check that:
- Events were found for at least some cities
- Forecasts were fetched successfully
- Edge calculations produced plausible probabilities
- Risk checks all ran (10 checks per opportunity)

## Troubleshooting

- **No events found**: Markets may not exist for today's dates. Try checking Polymarket directly.
- **NOAA API 503**: The API may be temporarily unavailable. The engine retries 3x automatically.
- **Import errors**: Ensure `pip install -e ".[dev]"` completed successfully.
