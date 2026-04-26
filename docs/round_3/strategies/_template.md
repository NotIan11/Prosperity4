# vN — <name>

**Status**: draft / tested / submitted / abandoned
**Commit**: `<sha>` (tag: `vN`)
**Date**: YYYY-MM-DD

## Hypothesis

What edge are we trying to capture? One paragraph.

## Changes from previous version

- bullet
- bullet

## Code

- `src/trader.py` — what's in it (paste the relevant class/method names).
- New files: …

## Backtest

```
venv/bin/prosperity4btest cli src/trader.py 3 --merge-pnl --no-out
```

| Day | PnL |
|-----|-----|
| 0 | |
| 1 | |
| 2 | |
| **Total** | |

| Metric | Value |
|--------|-------|
| Sharpe | |
| Max DD (abs) | |
| Max DD (%) | |
| Sortino | |
| Calmar | |

Per-product PnL on the best day (paste from BT log):

```
HYDROGEL_PACK: …
VELVETFRUIT_EXTRACT: …
VEV_*: …
```

## Learnings

- What worked.
- What surprised us.
- What to try next.

## Decision

Ship / iterate / abandon. Why.
