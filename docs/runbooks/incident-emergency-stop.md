# Incident Runbook: Emergency Stop

## When to Use

- Unexpected losses exceeding daily limit
- System behaving incorrectly (wrong prices, wrong calculations)
- External event requiring immediate halt (exchange outage, market manipulation)
- Any situation where continued trading is unsafe

## Procedure

### 1. Activate Kill Switch

```bash
python -m engine kill-switch on
```

This immediately:
- Blocks all new orders at both risk engine and executor level
- Takes effect within the current scan cycle
- Is logged in the operator_commands audit table

### 2. Verify Kill Switch Active

```bash
python -m engine status
```

Confirm output shows `Kill switch: True`.

### 3. Assess Situation

- Review open positions: `python -m engine status`
- Review recent runs in the database
- Check for any unusual edge results or order patterns

### 4. Manage Open Positions

The kill switch does NOT close existing positions. If positions need manual closure:
1. Review each position in the status output
2. Manually close on Polymarket if needed
3. Update the database if positions are closed externally

### 5. Investigate Root Cause

- Check recent run summaries
- Review edge_results for anomalous probabilities
- Check forecast data for accuracy
- Review market data for stale or incorrect prices

### 6. Recovery

Once the issue is resolved:

```bash
# Deactivate kill switch
python -m engine kill-switch off

# Run a dry-run scan to verify normal behavior
python -m engine scan

# Resume if scan looks correct
python -m engine resume
```

## Kill Switch vs Pause

| Feature | Kill Switch | Pause |
|---------|-----------|-------|
| Blocks new scans | No (scan runs, orders blocked) | Yes (scan aborts) |
| Blocks orders | Yes (both risk + executor) | Yes (risk check) |
| Defense in depth | 2 layers | 1 layer |
| Use for | Emergencies | Planned maintenance |
