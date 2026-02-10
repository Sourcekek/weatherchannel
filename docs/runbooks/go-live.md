# Go-Live Runbook

## Quality Gates

### Gate A: Deterministic Paper Operation (Required)

- [ ] Repeatable decisions from identical frozen inputs
- [ ] No unhandled exceptions in 100 consecutive dry-run scans
- [ ] Complete run summaries with reason codes for every decision
- [ ] All pytest/ruff/mypy passing
- [ ] Risk checks produce correct verdicts for all scenarios

### Gate B: Controlled Live Micro-Capital (Required)

- [ ] LiveAdapter implemented with Simmer/Polymarket integration
- [ ] Hard risk limits confirmed at runtime (max $5/trade, $25 total)
- [ ] Kill switch tested: blocks within 1 scan cycle
- [ ] No duplicate orders under retry scenarios
- [ ] 48h monitored dry-run with live market data
- [ ] All runbooks exercised at least once

### Gate C: Scale Readiness (Optional)

- [ ] Stable positive expectancy over 2+ weeks of paper trading
- [ ] Healthy operational metrics (scan duration, API freshness, error rates)
- [ ] All runbooks exercised at least once

## Enabling Live Mode

1. Implement `LiveAdapter` in `engine/execution/live_adapter.py`
2. Configure `SIMMER_API_KEY` in `.env`
3. Create a live config:
   ```bash
   cp ops/configs/example-live.yaml ops/configs/live.yaml
   # Edit live.yaml with appropriate limits
   ```
4. Run with `--live` flag:
   ```bash
   python -m engine scan --live --config ops/configs/live.yaml
   ```

## Risk Tightening for Initial Live

Start with tighter limits than defaults:
- `max_position_size_usd: 2.00`
- `max_trades_per_run: 1`
- `max_total_exposure_usd: 10.00`
- `max_daily_loss_usd: 5.00`

Gradually loosen as confidence builds.

## Monitoring

- Check `python -m engine status` after each scan
- Review `data/engine.db` for anomalies
- Keep kill switch accessible at all times
