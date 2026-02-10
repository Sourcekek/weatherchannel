# Weather Trader Skill

**Name**: weather-trader
**Version**: 0.1.0
**Description**: Deterministic weather market trading engine for Polymarket temperature bucket contracts.

## Commands

### scan
Run a single scan cycle. Dry-run by default.
```
scan [--live] [--config path]
```

### status
Show current positions, exposure, and system state.
```
status
```

### health
Run health checks: DB, API reachability, data freshness.
```
health
```

### config-show
Display current engine configuration.
```
config-show
```

### config-set
Set a config value with validation.
```
config-set key=value
```

### pause
Pause scanning. No new scans will execute.
```
pause
```

### resume
Resume scanning after a pause.
```
resume
```

### kill-switch
Emergency stop. Blocks all order execution.
```
kill-switch on|off
```

## Safety

- Default mode is always **dry-run**
- Live mode requires explicit `--live` flag
- Kill switch blocks at both risk engine and executor level
- All actions are audit-logged to the database
