# v15 — v11 flow gate + v12 cap=160 stacked

**Status**: tested, marginal — not worth shipping over v12
**Date**: 2026-04-26

## Hypothesis

v11's flow gate gave free Sharpe at low leverage (8.59→9.29). v12's
leverage bump tanked Sharpe (8.59→5.20). Stacking should let the gate
clean up some of v12's adverse fills.

## Backtest

| | v12 | v15 |
|---|---|---|
| PnL | 460,722 | 458,648 (-2k) |
| Sharpe | 5.20 | 5.50 |
| Max DD | 60,493 | 60,493 |
| Calmar | 7.62 | 7.58 |
| Portal slice | 46,113 | 46,113 (identical) |

## Verdict

Gate barely moves the needle at higher cap — Sharpe lift is real but tiny,
PnL slightly worse, portal slice byte-identical (gate doesn't fire in the
first 1000 ticks of day 2). Not worth shipping over v12, which has live
evidence.
