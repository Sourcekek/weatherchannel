# Weather Trading Engine — Status Summary
**Date:** 2026-02-10  
**Branch:** 210  

## Current State

### Engine
- **Mode:** LIVE (trading on Simmer $SIM virtual currency)
- **Cron:** Every 2 minutes via OpenClaw isolated sessions (Haiku 3.5 model)
- **Dashboard:** FastAPI + single-page HTML at `localhost:8777` (not running by default — launch with `.venv/bin/python -m engine.dashboard`)
- **DB:** SQLite at `data/engine.db` — 25 runs, 2219 edge calculations, 11 order intents, 5 positions

### Open Positions (5 total, $10.00 exposure)
| Position | Entry Price | Size | Status |
|---|---|---|---|
| Seattle 46-47°F (Feb 11) × 2 | $0.04 | $2.00 each | Losing — forecast shifted to 51°F |
| NYC 36-37°F (Feb 11) | $0.0575 | $2.00 | Slight profit |
| NYC 33°F or below (Feb 12) | $0.15 | $2.00 | Profitable (+74%) |
| Dallas 80°F or higher (Feb 13) | $0.105 | $2.00 | New — 19.6% edge detected |

### Net P&L: ~-$1.76 (mostly Seattle drag)

## Architecture
```
engine/
├── ingest/          # Gamma/CLOB/NOAA API clients, market scanner, slug parser
├── signal/          # Probability calc, edge detection, calibration
├── risk/            # 10 risk checks (exposure, cooldown, time-to-resolution, etc.)
├── execution/       # Simmer client, live adapter, dry-run, idempotency
├── reporting/       # Position tracker, run summarizer, health checker, formatters
├── pipeline/        # Scan + exit pipelines
├── storage/         # SQLite repos + migrations
├── models/          # Pydantic/dataclass models
├── config/          # Schema, defaults (5 cities), loader
├── dashboard.py     # FastAPI dashboard server (NEW)
├── cli.py           # CLI interface
└── daemon.py        # Daemon mode
static/
└── dashboard.html   # Real-time trading dashboard (NEW)
```

## Key Decisions Made (2026-02-10)

1. **Haiku for cron scans** — Switched from Opus ($108/day) to Haiku 3.5 (~$3.50/day). Scans are command execution + formatting, no reasoning needed.

2. **2-minute scan interval** — Aggressive for data collection. All exposure currently capped so most scans report "blocked" but builds historical edge/signal data.

3. **$10 total exposure cap** — Conservative training wheels. Engine is finding 18-19% edge opportunities it can't act on. Will need to raise when confident.

4. **$2 max position size** — Keeps individual bet risk minimal. 5 positions × $2 = $10 cap hit.

5. **Dashboard built** — Real-time web UI with:
   - KPI cards (exposure, P&L, scan activity)
   - Positions table with live P&L
   - Edge opportunity chart
   - Signal/risk/forecast/order tables
   - **Interactive controls** — adjust all strategy/risk params on the fly, pause/resume, kill switch
   - Auto-refresh (configurable interval)

6. **Simmer $SIM venue** — All trades in virtual currency. Real USDC trading requires wallet setup (Solana via Brave Wallet or `SIMMER_PRIVATE_KEY` env var).

## Live Config (`ops/configs/live.yaml`)
- Min edge threshold: 8%
- Max entry price: $0.15
- Max position: $2.00
- Max exposure: $10.00
- Max per-city: $5.00
- Cooldown: 60 min
- Min hours to resolution: 12h
- Venue: simmer ($SIM)

## Known Issues
1. **Cron delivery errors** — "cron delivery target is missing" appears intermittently despite `channel: whatsapp` being set. Reports still arrive but tagged as errors.
2. **Simmer order timeout** — One trade attempt hung during market mapping (100 markets). Live adapter may need better timeout handling.
3. **Seattle bet losing** — Forecast drifted from ~46°F to 51°F. Narrow 2-degree buckets are inherently high-risk. Consider preferring wider buckets or higher-probability bets.
4. **No daytime forecasts in evening** — NOAA drops same-day daytime periods after hours. Expected behavior, not a bug.
5. **2 failing tests** — `test_requires_api_key` × 2 — API key check tests fail because `SIMMER_API_KEY` is set in env.

## Next Steps
- [ ] Monitor position outcomes over 24-48h
- [ ] Analyze edge accuracy: did our probability estimates match reality?
- [ ] Consider wider bucket preference in signal logic
- [ ] Fix Simmer order timeout handling
- [ ] Raise exposure limits once confidence established
- [ ] Set up real USDC trading when ready
- [ ] Add P&L tracking over time to dashboard
