# Risk Policy

## Overview

All trading decisions pass through 10 mandatory risk checks before execution. No check is ever skipped — the system always runs all 10 for full audit trails.

## Risk Checks

| # | Check | Default Limit | Blocks When |
|---|-------|--------------|-------------|
| 1 | Kill switch | N/A | `kill_switch == true` in system_state |
| 2 | Paused | N/A | `paused == true` in system_state |
| 3 | Position size | $5.00 | Proposed trade > limit |
| 4 | Trades per run | 3 | Trades this scan cycle >= limit |
| 5 | Total exposure | $25.00 | All open positions + proposed > limit |
| 6 | Per-city exposure | $10.00 | City positions + proposed > limit |
| 7 | Daily loss | $10.00 | Absolute daily loss > limit |
| 8 | Cooldown | 30 min | Last trade on same market < cooldown |
| 9 | Time to resolution | 6 hours | Market end_date < min hours away |
| 10 | Slippage | 5% | Bid-ask spread > ceiling |

## Kill Switch

The kill switch operates at two levels for defense in depth:

1. **Risk engine level**: Checked as part of the 10 checks. If active, verdict is "blocked."
2. **Executor level**: Re-checked before every order dispatch. Blocks even if risk engine was somehow bypassed.

### Activating Kill Switch

```bash
python -m engine kill-switch on
```

### Deactivating Kill Switch

```bash
python -m engine kill-switch off
```

### Behavior

- Immediately blocks all new orders in the current and future scan cycles
- Does not close existing positions (manual intervention required)
- Logged as operator command in audit trail

## Escalation

If daily loss exceeds the configured limit:
1. All new trades are automatically blocked
2. Operator should investigate open positions
3. Consider activating kill switch if losses continue

## Configuration

All risk limits are configurable via `ops/configs/default.yaml` under the `risk:` section. Changes are validated by Pydantic and snapshotted to the database for audit.

## Audit Trail

Every risk check result is persisted to the `risk_checks` table with:
- Run ID
- Idempotency key
- Check name
- Pass/fail
- Block reason (if failed)
- Detail message
