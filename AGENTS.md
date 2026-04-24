# Prosperity4 — Project Conventions

## Python

- Always use `.venv/bin/pip` (never global pip3).
- Python 3.13 is used locally; production platform runs 3.11 — avoid 3.12+ syntax where possible.

## Running Backtests

```bash
./tools/run_backtest.sh          # round 1, all days
./tools/run_backtest.sh 1 1-0   # round 1, day 0 only
```

Logs save to `backtests/` (gitignored).

## Submission

- `src/` is the submission directory. Keep it free of dev-only imports.
- The backtester injects `datamodel` as a top-level module — `from datamodel import ...` works without a relative path.
- Submission entry point: `src/trader.py`, class `Trader`, method `run(state) -> (orders, conversions, traderData)`.

## Git

- Use conventional commits: `feat:`, `chore:`, `docs:`, `fix:`, `test:`.
- Commit bodies use bullet point format.
- `dev` branch for all work; merge to `main` at approved milestones.
- No remote push without explicit approval.
- No co-author trailers on commits.

## Data

- CSVs are semicolon-separated.
- Raw data lives in `data/` and is committed (small files, useful as truth).
- Backtester has round 1 data bundled — no `--data` flag needed.

## Repo Layout

```
src/trader.py          # submission entry point
src/strategies/        # one file per strategy family
src/datamodel.py       # vendored datamodel (for IDE type hints)
notebooks/             # exploratory scripts
docs/                  # strategy write-ups and references
data/                  # raw CSVs from the portal
backtests/             # gitignored backtest output
tools/run_backtest.sh  # backtest wrapper
```
