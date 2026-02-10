# OpenClaw Handoff: Weather Market Trading Tool

## Verified Market Thesis Summary
**As of 2026-02-10 02:36 UTC, here’s the deep verification.**

**Tweet thesis (decoded)**
1. Find Polymarket weather bucket markets (NYC/Chicago/Seattle/Atlanta/Dallas).
2. Compare bucket prices to external forecast data (tweet says NOAA).
3. Buy “undervalued” buckets below ~$0.15.
4. Sell when they rerate above ~$0.45.
5. Repeat every ~2 minutes.

**What is true**
1. The exact weather bucket markets exist and are live now.
2. They are multi-bucket contracts per city/day (e.g., “34-35°F”, “44°F or higher”).
3. Historical price traces show many real `<0.15 -> >0.45` moves.

**Hard evidence**
1. **Live structure today** (example event): `highest-temperature-in-nyc-on-february-11-2026` has 7 buckets with live prices.
2. **Historical replay** on closed city weather events (NYC/Chicago/Seattle/Atlanta/Dallas, Feb 1-9 2026):
   - 31 events
   - 217 bucket markets
   - 81 buckets had `min price < 0.15` and later `max price > 0.45`
   - 22 explicit timestamped threshold-cross examples
3. Examples of real flips:
   - Seattle Feb 3 bucket `55°F or below`: `0.1400 -> 0.6190` in 21.5h
   - Chicago Feb 4 bucket `28-29°F`: `0.1450 -> 0.5650` in 31.8h
   - NYC Feb 3 bucket `32-33°F`: `0.1300 -> 0.5510` in 6.8h
   - Dallas Feb 6 bucket `82°F or higher`: `0.0250 -> 0.5350` in 38.0h

**NOAA-based replication check (current markets)**
Forecasts were pulled for station points near KLGA/KDAL/KSEA/KORD/KATL, converted into bucket probabilities (normal error model), and compared with live prices.

Top current `<0.15` candidates by model edge:
1. NYC Feb 11 `36-37°F`: market `0.075`, model fair `0.262`, edge `+0.187`
2. Seattle Feb 11 `46-47°F`: market `0.045`, model fair `0.194`, edge `+0.149`
3. NYC Feb 11 `34-35°F`: market `0.029`, model fair `0.123`, edge `+0.094`
4. Atlanta Feb 11 `60-61°F`: market `0.080`, model fair `0.123`, edge `+0.043`

So yes: the core mechanic is replicable right now.

**What is overstated / wrong in the tweet framing**
1. This is **not true arbitrage** (not risk-free). It is model-based directional trading.
2. Resolution source is often **Wunderground station history** (e.g., KLGA/KDAL), not NOAA.
3. “Making thousands” is not verifiable from public market data alone (needs wallet-level fills/PnL, fees, slippage, latency).

**Bottom line**
The main thesis is **substantively valid** as a tradable forecasting edge workflow, but the word “arbitrage” is technically inaccurate and the profit claim is unproven without account-level evidence.

**Sources**
- Tweet: [x.com/0xMovez/status/2020803703465238964](https://x.com/0xMovez/status/2020803703465238964)
- Gamma fetch guide: [docs.polymarket.com/developers/gamma-markets-api/fetch-markets-guide](https://docs.polymarket.com/developers/gamma-markets-api/fetch-markets-guide)
- Markets API: [docs.polymarket.com/api-reference/markets/list-markets](https://docs.polymarket.com/api-reference/markets/list-markets)
- Price history API: [docs.polymarket.com/api-reference/pricing/get-price-history-for-a-traded-token](https://docs.polymarket.com/api-reference/pricing/get-price-history-for-a-traded-token)
- Live event example: [gamma-api.polymarket.com/events/slug/highest-temperature-in-nyc-on-february-11-2026](https://gamma-api.polymarket.com/events/slug/highest-temperature-in-nyc-on-february-11-2026)
- CLOB history endpoint: [clob.polymarket.com/prices-history](https://clob.polymarket.com/prices-history)
- NOAA/NWS API: [api.weather.gov](https://api.weather.gov)

---

## Detailed Analysis of the Original Tweet

### What the tweet is doing (communication strategy)
The original post is not only describing a strategy; it is packaged as a conversion funnel:
1. **Social proof**: large cumulative P/L and winning positions shown in video.
2. **Simplicity framing**: “5 simple steps” lowers perceived complexity.
3. **Low-friction onboarding**: suggested micro-capital start ($2-$5).
4. **Authority transfer**: external references to NOAA + named strategy inspiration.
5. **Automation appeal**: “every 2 minutes” implies persistent machine edge over manual traders.

### What the video evidence does and does not prove
What it supports:
- A real profile with many weather-market outcomes and strong aggregate wins.
- Existence of substantial winner distributions in weather contracts.

What it does not prove on its own:
- Entry timestamps and exact fill quality for every shown trade.
- Net profitability after fees, spread, slippage, and market impact.
- Whether returns came specifically from the exact posted rule (`<0.15` entry, `>0.45` exit) vs discretionary adjustments.

### Conceptual mechanics (true underlying system)
The tweet describes a repeatable loop:
1. Collect active city/day weather bucket markets.
2. Infer fair probabilities from forecast distribution.
3. Identify positive edge where model fair value exceeds market price.
4. Enforce risk controls before execution.
5. Exit on rerating, threshold, or time/risk conditions.

This is a **forecast-model trading system**, not a riskless arbitrage system.

### Why the `<0.15 -> >0.45` motif appears often
Weather bucket contracts are prone to repricing because:
- Forecast uncertainty narrows as resolution approaches.
- Liquidity is uneven across bucket tails and mid-bands.
- New forecast updates can abruptly shift implied probabilities.

These factors can produce large relative moves from low-priced states, but not all low-priced buckets are mispriced.

### Key hidden constraints a deployable system must handle
- Venue fees and spread drag
- Slippage in thin buckets
- Fill uncertainty and partial execution
- Forecast model calibration error
- Data freshness and source mismatch (NOAA vs resolution station)
- Correlated exposure across cities/dates
- Regime shifts in weather volatility

### Operational interpretation for build planning
The correct product interpretation is:
- **Valid edge workflow hypothesis**
- Requires deterministic modeling + execution quality + strict risk controls
- Must be evaluated by audited, account-level performance, not dashboard screenshots

---

# OpenClaw Handoff: Weather Market Trading Tool

## 1) Purpose
Build a production-ready, OpenClaw-operated weather market trading system that:
- Detects opportunities from forecast/market mismatches
- Executes safely under strict risk controls
- Is controllable through OpenClaw chat commands
- Is auditable end-to-end (data, decisions, actions)

This handoff is for implementation by OpenClaw as an automation/control layer over a deterministic trading engine.

---

## 2) Product Scope
### In scope
- Weather market scanning and signal generation
- Deterministic trade decision engine (no LLM deciding entries/exits)
- Optional live execution adapter
- OpenClaw skill interface for operations and control
- OpenClaw cron-based autonomous scanning
- Safety controls, logging, reporting, and health monitoring

### Out of scope
- Claims of risk-free or guaranteed arbitrage
- Unbounded autonomous execution without controls
- Manual-only operation without automation and audit logs

---

## 3) Core Principles
- Deterministic first: all trade decisions must be reproducible from stored inputs.
- OpenClaw as orchestrator: scheduling, command/control, alerting, approvals.
- Defense in depth: sandboxing, allowlists, approvals, and kill switch.
- Capital protection before growth: strict hard limits gate all execution.
- Full observability: every decision/action must be explainable.

---

## 4) Target Architecture
## Components
- `strategy-engine` (Python service)
  - Market ingest
  - Forecast ingest (NOAA)
  - Bucket mapping + edge scoring
  - Risk checks
  - Optional execution adapter
  - State and event logging

- `openclaw skill` (`weather-trader`)
  - Operator command surface from chat
  - Calls engine commands
  - Returns structured status and summaries

- `openclaw cron`
  - Isolated recurring scan job
  - Announces summary to configured channel

- `storage`
  - SQLite/Postgres for decisions, orders, fills, config snapshots, and errors

## Responsibility boundaries
- Engine decides and executes (deterministic rules)
- OpenClaw schedules, triggers, reports, and controls
- Messaging channels are output/control interfaces only

---

## 5) Required Repository Layout
```text
openclaw-weather/
  engine/
    src/
      ingest/
      signal/
      risk/
      execution/
      reporting/
    tests/
  skills/
    weather-trader/
      SKILL.md
      scripts/
  ops/
    configs/
    runbooks/
    examples/
  docs/
    architecture.md
    risk-policy.md
```

---

## 6) Engine Requirements
## 6.1 Ingest
- Pull active weather market data
- Pull NOAA forecast data for configured locations/dates
- Normalize and cache data with source timestamps
- Reject stale/missing data for execution paths

## 6.2 Signal
- Parse market event into location/date/metric
- Map forecast to target temperature bucket
- Compute edge metric:
  - `edge = P(bucket) - market_price - fee_estimate - slippage_estimate`
- Support threshold + edge-based entry gating

## 6.3 Risk
Must enforce all of the following before any order:
- Max position size per trade
- Max trades per run
- Max total exposure
- Max exposure per location/market
- Max daily loss limit
- Cooldown / anti-flip-flop checks
- Time-to-resolution minimum
- Slippage ceiling

## 6.4 Execution
- Support dry-run and live modes
- Idempotent order placement keys
- Retry and safe failure behavior
- No duplicate submission on transient errors
- Immediate stop if kill switch is active

## 6.5 Reporting
- Per-run summary (scanned, opportunities, blocked reasons, actions)
- Position/PnL snapshots
- Error/event log with reason codes

---

## 7) OpenClaw Integration Requirements
## 7.1 Skill Commands
Implement a `weather-trader` skill with these command capabilities:
- `scan` (single cycle; supports dry-run/live)
- `status` (positions, exposure, PnL, risk status)
- `config show`
- `config set <key>=<value>` (with validation)
- `pause`
- `resume`
- `health`

## 7.2 Automation
- Use OpenClaw isolated cron job for recurring scans
- Post concise announce summaries to selected channel
- Keep main session noise low

## 7.3 Operator Controls
- Chat-level pause/resume and kill switch visibility
- Clear command responses with machine-readable state fields

---

## 8) Security Baseline (Mandatory)
- DM policy: pairing/allowlist only
- Sandbox enabled for tool execution
- Minimal tool allowlist (only required tools)
- Exec approvals enabled for host-level commands
- No broad public gateway exposure without strong auth
- Store API credentials outside prompts/transcripts
- Run periodic OpenClaw security audits and remediate findings

---

## 9) Config Contract
## Required config domains
- Strategy: thresholds, sizing, locations
- Risk: caps, limits, cooldowns, stop conditions
- Execution: dry-run/live mode, adapter settings
- Alerts: delivery channel/recipient
- Ops: logging level, health-check behavior

## Config behavior
- Strict validation on load
- Reject unknown keys
- Persist validated snapshots with versioning

---

## 10) Data & Audit Requirements
Store at minimum:
- Raw market snapshot references
- Raw forecast snapshot references
- Derived signal values and edge breakdown
- Risk check results and block reasons
- Order intents and execution results
- Position and PnL snapshots
- Operator commands and state transitions (`pause`, `resume`, config changes)

Audit goal: reconstruct any trade decision from persisted artifacts.

---

## 11) Quality Gates
## Gate A: Deterministic paper operation
- Repeatable decisions from identical inputs
- No unhandled exceptions in recurring scans
- Complete run summaries and reason codes

## Gate B: Controlled live micro-capital
- Hard risk limits confirmed in runtime
- Kill switch tested and immediate
- No duplicate orders under retries

## Gate C: Scale readiness
- Stable expectancy under monitored drawdown
- Healthy operational metrics and alerting
- Security posture maintained under automation load

---

## 12) Observability & Incident Handling
## Must-have telemetry
- Scan duration
- Data freshness age
- Opportunities found vs blocked
- Block reason distribution
- Orders attempted/succeeded/failed
- Current exposure and drawdown

## Incident runbook requirements
- API outage behavior
- Stale data behavior
- Rejected order behavior
- High slippage behavior
- Emergency pause/kill switch procedure

---

## 13) Delivery Checklist for OpenClaw
- [ ] Engine scaffold with deterministic scan path
- [ ] Dry-run scan output with structured summary
- [ ] Risk policy implemented and enforced
- [ ] Skill commands wired and validated
- [ ] Isolated cron scan active
- [ ] Alert delivery configured
- [ ] Security baseline configured
- [ ] Audit logs queryable
- [ ] Health checks and runbook documented

---

## 14) Final Implementation Rule
Do not enable or keep live mode active by default. Default execution mode must remain dry-run until operator explicitly enables live trading after passing all quality gates.
