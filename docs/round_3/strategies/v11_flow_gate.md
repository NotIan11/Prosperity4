# v11 — VFE informed-flow gate (Sharpe-best)

**Status**: tested, ship-candidate (Sharpe winner)
**Date**: 2026-04-26

## Hypothesis

EDA #7: VFE buy-aggressors predict +0.63 ticks of mid drift over 50 ticks
(t=2.64). Use as a *gate* (per v3 lesson — sticky signals as biases blow up;
as gates they help). When recent net aggressor flow is strong, block adding
voucher inventory in the adverse direction.

## Changes from v10

- New `InformedFlowTracker` class. Per tick: parse `state.market_trades["VELVETFRUIT_EXTRACT"]`,
  classify each trade as buy- or sell-aggressor by comparing price vs mid,
  sum signed volume into a 50-tick deque.
- `Trader.run` updates tracker first, then sets `block_long_add` / `block_short_add`
  flags on each `VevOptionTaker` before calling its `run`.
- `VevOptionTaker.run` skips opening new positions when the matching gate is set.
- HG and VFE strategies untouched.

## Backtest

| Metric | v10 | **v11** |
|---|---|---|
| Total PnL | 361,705 | 360,407 (-0.4%) |
| Sharpe | 8.59 | **9.29** |
| Max DD | 42,668 | 42,668 |
| Calmar | 8.48 | 8.45 |
| BT day-2 first-1000 | 35,688 | 35,688 |
| Est live | ~26,050 | ~26,050 |

## Decision

Free Sharpe lift (8.59 → 9.29) at zero PnL/DD cost. Same-tick portal
slice unchanged — the gate fires rarely but cleanly. Stackable with v12.

## Open

- v15 = v11 + v12 (flow gate over leveraged caps). Best of both candidate.
