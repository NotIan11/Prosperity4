# Prosperity4

IMC Prosperity 4 algorithmic trading competition repo (Apr 14–30, 2026).

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./tools/run_backtest.sh          # backtest round 1, all days
./tools/run_backtest.sh 1 1-0   # backtest round 1, day 0 only
```

## Submitting

Upload `src/trader.py` (and any files it imports from `src/`) via the IMC portal. The platform injects `datamodel` — do not include it in the zip.

## Structure

| Path | Purpose |
|---|---|
| `src/trader.py` | Submission entry point |
| `src/strategies/` | Strategy implementations |
| `docs/` | Research notes and references |
| `data/` | Raw round CSVs |
| `notebooks/` | Exploratory analysis |
| `backtests/` | Backtest output (gitignored) |
| `tools/run_backtest.sh` | Backtest wrapper |
