# Prosperity4

IMC Prosperity 4 algorithmic trading competition. Apr 14–30, 2026.

## Results

| Round | Submission | P&L | Notes |
|---|---|---|---|
| R1 (tutorial) | — | 142,728 | OSM + IPR baseline |
| R1 | v6 (`540d470`) | 10,303 | Best R1 result. OSM pennying. |
| R2 | — | — | TODO |
| R3 | — | — | In progress |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Backtesting

```bash
./tools/run_backtest.sh          # round 1, all days
./tools/run_backtest.sh 1 1-0   # round 1, day 0 only
./tools/run_backtest.sh 1 1--2  # round 1, day -2 only
```

Add `--vis` to open results in the browser visualizer. Logs save to `backtests/` (gitignored).

## Submission

Upload only `src/trader.py`. The platform injects `datamodel` automatically.

Entry point: `Trader.run(state) -> (orders, conversions, traderData)`

## Repo Layout

```
src/trader.py          # submission entry point
src/strategies/        # one strategy file per product family
src/datamodel.py       # vendored datamodel (IDE type hints only)
docs/round_1/          # R1 strategy, notes, data analysis
docs/round_2/          # R2 strategy, notes
docs/round_3/          # R3 strategy, notes
data/                  # raw CSVs from the portal
tools/run_backtest.sh  # backtest wrapper
```

## Branch Strategy

- `dev` — all active work
- `main` — stable milestones only
- `round-3` — R3 development (branch off dev)
