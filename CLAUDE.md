# CLAUDE.md

You are working on **weatherchannel** — a repository for building and operating an OpenClaw-controlled weather market trading system.
This file is your persistent operating guide. Read it at session start.

If you make a repeatable mistake that is not covered here, report it and add a new rule under **The Mistake Log**.

---

## Worktree Awareness

You may be running in a **git worktree** with parallel agents and branches.
Before doing anything:

1. Run `git worktree list`
2. Run `git branch --show-current`
3. Run `git remote -v`
4. Do not modify `main` directly unless explicitly asked
5. Do not rebase or force-push unless explicitly asked
6. If you need upstream updates, use `git fetch origin` then `git merge origin/main` (not rebase)
7. Check open PRs before broad refactors: `gh pr list --state open`

Your working directory is isolated. The remote history is shared.

---

## Project Mission

Build a deterministic weather-market trading stack with:
- OpenClaw as orchestration and control plane
- A deterministic strategy engine (no LLM-driven entry/exit logic)
- Strict risk controls and auditability
- Repeatable operator workflows through chat commands and cron

The repository currently contains handoff/spec documents and should evolve into an implementation repo without losing traceability.

---

## Tech Stack (Target)

| Layer | Technology |
|-------|-----------|
| Orchestration | OpenClaw (skills, cron, chat control) |
| Strategy Engine | Python 3.11+ |
| Market Data | Polymarket Gamma/CLOB APIs |
| Forecast Data | NOAA/NWS API (`api.weather.gov`) |
| Execution Adapter | Simmer/Polymarket integration (optional in early phases) |
| Storage | SQLite (initial), PostgreSQL (scale) |
| Observability | Structured logs + run summaries + risk event logs |
| Security | OpenClaw sandbox + exec approvals + pairing/allowlists |

---

## Architecture (Target State)

```
weatherchannel/
├── OPENCLAW.md                 # Primary project handoff + analysis
├── CLAUDE.md                   # This workflow guide
├── docs/
│   ├── architecture.md
│   ├── risk-policy.md
│   └── runbooks/
├── engine/
│   ├── src/
│   │   ├── ingest/
│   │   ├── signal/
│   │   ├── risk/
│   │   ├── execution/
│   │   └── reporting/
│   └── tests/
├── skills/
│   └── weather-trader/
│       ├── SKILL.md
│       └── scripts/
└── ops/
    ├── configs/
    └── examples/
```

If folders are missing, create them incrementally when implementing work.

---

## Development Workflow

### Session Start Protocol

Every session, before coding:

1. `git fetch origin`
2. `git log --oneline -5`
3. Read this file
4. Read `/Users/charles/weatherchannel/OPENCLAW.md`
5. If present, read the task-specific spec file
6. Confirm branch purpose

### Plan -> Execute -> Verify Loop

This is mandatory.

**Plan**
- Define exactly what will be built/changed
- List files to modify
- Define acceptance criteria
- Identify risks and unknowns

**Execute**
- Follow approved plan
- Make small, atomic changes
- Keep deterministic behavior and risk controls intact
- Stop and reassess if plan assumptions break

**Verify**
- Run all relevant checks for changed scope
- Fix failures before reporting done
- Summarize what was validated and what was not

You are not done until verification passes for the affected area.

---

## Verification Standards

### For docs-only changes
Run:
1. `git diff --check`
2. `rg -n "TODO|FIXME" /Users/charles/weatherchannel` (ensure no accidental placeholders)
3. Manually verify links/paths referenced in changed docs

### For Python engine changes
Run (when configured):
1. `python -m pytest -q`
2. `python -m ruff check .`
3. `python -m ruff format --check .`
4. `python -m mypy engine/src` (if mypy config exists)

### For OpenClaw skill changes
Run:
1. Validate `SKILL.md` metadata and command references
2. Smoke-test core skill commands in dry-run mode
3. Verify no command enables live execution by default

### For risk/execution changes
Run:
1. Deterministic replay test on fixed input snapshots
2. Idempotency checks for order submission paths
3. Kill-switch and pause/resume behavior checks

---

## Commit Convention

Use conventional commits with specific scope.

Examples:
```
feat(engine): add NOAA bucket probability mapper
feat(skill): add weather-trader status and pause commands
fix(risk): enforce max daily loss before order intent
refactor(ingest): split gamma and clob clients
docs(handoff): tighten operator runbook and edge definitions
test(execution): add idempotent order replay coverage
```

Rules:
- One logical change per commit
- No vague messages (`fix`, `update`, `changes`)
- If behavior changes, include tests or explicit validation notes

---

## Code Rules

### Deterministic Strategy Rules
- Do not let LLM outputs directly decide trade entries/exits
- All decisions must come from deterministic logic over persisted inputs
- Every decision must emit machine-readable reason codes

### Risk Rules
- Enforce hard limits before execution:
  - max position per trade
  - max trades per run
  - max total exposure
  - max daily loss
  - slippage ceiling
  - minimum time-to-resolution
- If a risk check fails, no order intent is created

### Service Boundaries
- Keep ingest, signal, risk, execution, and reporting separate
- Do not mix transport/adapters with strategy logic
- Keep config loading/validation centralized

### Logging and Audit
- No silent failures
- Log each pipeline stage with stable IDs
- Persist enough state to reconstruct any action post-hoc

### Secrets and Config
- Never hardcode API keys
- Keep secrets in environment/config only
- Do not print secrets in logs or chat summaries

---

## OpenClaw Integration Rules

- OpenClaw is orchestration/control, not core strategy logic
- Skill commands must support dry-run first
- Live mode must be explicit opt-in and reversible
- Cron jobs should run in isolated sessions
- Operator control commands must always include current state:
  - mode (`dry-run` or `live`)
  - paused status
  - kill-switch status

---

## Testing Rules

- Tests mirror source structure
- New behavior requires:
  - one happy path test
  - one edge/failure test
- External APIs are mocked in unit tests
- Deterministic snapshot tests are required for signal logic
- Execution tests must include duplicate/retry scenarios

---

## PR Discipline

- Keep PRs focused and reviewable
- Include:
  - what changed
  - why it changed
  - how it was verified
  - known risks/follow-ups
- If PR touches risk or execution logic, call that out explicitly

---

## Deployment and Ops Guardrails

- Default system mode remains dry-run until explicitly enabled
- Do not roll out live execution without passing defined quality gates
- Keep migration/infra/config changes coordinated and explicit
- Prefer prevention over rollback, but keep rollback path documented

---

## Environment Variables (Expected)

- `SIMMER_API_KEY` (if using Simmer execution endpoints)
- `OPENCLAW_HOME` / `OPENCLAW_STATE_DIR` (when required by runtime layout)
- Any execution venue credentials (never committed)
- Optional observability keys (if enabled)

NOAA/NWS forecast API is public; do not add fake API key dependencies for it.

---

## The Mistake Log

Add new rules when recurring mistakes appear.

### Architecture Mistakes
- Do not place strategy logic in OpenClaw command wrappers
- Do not couple risk checks to chat/UI formatting code
- Do not bypass module boundaries for convenience

### Strategy and Risk Mistakes
- Do not call this risk-free arbitrage in code/docs unless mathematically riskless
- Do not execute when data is stale or unresolved mapping is ambiguous
- Do not skip slippage checks in live mode

### Testing Mistakes
- Do not weaken passing tests to fit new code
- Do not ship behavior changes without coverage or explicit replay evidence

### Git Mistakes
- Do not commit secrets, credentials, `.env`, or private keys
- Do not force-push shared branches without coordination

### Operations Mistakes
- Do not enable live mode by default
- Do not remove pause/kill controls from operator surface
- Do not ship without clear runbook updates when behavior changes

---

## What "Done" Means

A task is done only when:

1. Code/docs implement the requested change
2. Relevant verification checks pass
3. Risks are documented when behavior changed
4. Commit messages follow convention
5. No secrets were introduced
6. Operator-facing behavior remains clear and controllable
7. If a new recurring mistake was found, The Mistake Log was updated

If any item is missing, it is not done.

---

*Last updated: 2026-02-10. This file should be kept current as weatherchannel evolves.*
