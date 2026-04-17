# Prosperity4

IMC Prosperity 4 algorithmic trading competition repo — Team [your team name].  
Competition runs **Apr 14–30, 2026**. R1 closes Apr 17.

## Current Results

| Round | Day | Total P&L | Sharpe |
|---|---|---|---|
| R1 (tutorial) | -2 | 45,748 | — |
| R1 (tutorial) | -1 | 49,224 | — |
| R1 (tutorial) | 0 | 47,756 | — |
| **R1 total** | | **142,728** | **27.3** |

Zero limit violations across all tutorial days. All days profitable.

---

## Setup

```bash
git clone https://github.com/NotIan11/Prosperity4.git
cd Prosperity4
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the Backtest

```bash
./tools/run_backtest.sh          # round 1, all tutorial days
./tools/run_backtest.sh 1 1-0   # round 1, day 0 only
./tools/run_backtest.sh 1 1--2  # round 1, day -2 only
```

Backtest logs are saved to `backtests/` (gitignored). Add `--vis` to open results in the browser visualizer.

## Submitting to IMC Portal

Upload **only the contents of `src/`** — the platform injects `datamodel` automatically.  
Do NOT include `.venv/`, `data/`, `notebooks/`, `docs/`, or `backtests/` in the zip.

## Repo Structure

| Path | Purpose |
|---|---|
| `src/trader.py` | Submission entry point — `Trader.run()` |
| `src/strategies/osmium.py` | ASH_COATED_OSMIUM strategy (hardcoded FV=10000) |
| `src/strategies/mean_reversion.py` | INTARIAN_PEPPER_ROOT strategy (EWM market-making) |
| `src/datamodel.py` | Vendored datamodel for IDE type hints (don't submit) |
| `docs/round_1_strategy.md` | R1 strategy rationale + parameter sweep results |
| `docs/datamodel_reference.md` | TradingState / Order / OrderDepth cheatsheet |
| `docs/pitfalls.md` | Common mistakes to avoid |
| `data/` | Raw round CSVs from the portal |
| `notebooks/r1_exploration.py` | Exploratory data analysis |
| `tools/run_backtest.sh` | Backtest wrapper |

## R1 Strategy Summary

**ASH_COATED_OSMIUM** — stable product, mean-reverts tightly to 10,000 (std 5.35).  
Hardcoded fair value = 10,000. Takes any sell order < 10,000 or buy order > 10,000 (free edge), then posts remaining capacity passively at 9,999 / 10,001. Position limit: ±80.

**INTARIAN_PEPPER_ROOT** — volatile, trends ~1,000/day (std 866 across tutorial days).  
Fast EWM fair value (window=2, α=2/3) quotes at FV±1 tick inside a ~13-tick market spread. Near-zero lag prevents directional accumulation in trending markets. Position limit: ±80.

See `docs/round_1_strategy.md` for full rationale and parameter sweep.

## Branch Strategy

- `dev` — all active work
- `main` — stable milestones only, merged at approval
- No push to `main` without team sign-off
