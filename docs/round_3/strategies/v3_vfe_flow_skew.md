# v3 — VFE informed-flow skew (ABANDONED)

**Status**: tested, abandoned (regression vs v2)
**Commit**: not committed (failed BT)
**Date**: 2026-04-26

## Hypothesis

Per `docs/round_3/research/12_vfe_informed_flow_offensive.md`: net buy-flow over
last 50 ticks predicts +0.048 corr (t=+8.3) of forward returns. Defensive use:
when net buy-flow > +5, lean inventory long (raise both quotes by 1-2 ticks)
to reduce sells into informed buyers and fill more bids before drift.

## Changes from previous version

- Added `FlowTracker` class: deque of last K=50 tick-net-flow signals.
- `PassiveMarketMaker` accepts a `flow_tracker`; computes `flow_shift`
  capped at ±2 ticks and applies equally to bid/ask.
- VFE config: `flow_threshold=5, flow_max_skew=2`.

## Backtest

| Metric | v2 | v3 (flow only) | Δ |
|--------|------|------|------|
| Total PnL | 33,676 | **31,222** | **-2,454 (-7.3%)** |
| Sharpe | 2.46 | 4.62 | +88% |
| Max DD (abs) | 4,264 | 4,816 | +13% |
| Max DD (%) | 1.20 | 1.24 | +0.04pp |
| Calmar | 7.90 | 6.48 | -18% |

VFE per-day: 5,942 → 2,010 (day 0), 1,464 → 1,702 (day 1), 3,256 → 4,496 (day 2).

## Learnings

- Sharpe nearly **doubled** but we lost meaningful PnL. Flow tracker is too
  defensive on day 0 (where there's healthy two-way flow that isn't toxic).
- The threshold is too sticky — once net flow accumulates one direction, the
  skew sits on for many ticks even after the toxic burst is over.
- Day 2 *gained* (+1,240), suggesting the signal is real on toxic days but
  costs us on benign days.
- The EDA's recommended "expected +20-60 seashells/day" was cross-spread
  taking, NOT passive skew. We mis-translated.

## Decision

**Abandon for now.** Could revisit with: shorter K (e.g. 20), event-decay
threshold, or per-day calibration. Not worth the complexity without
clearer per-day attribution.

## Code removed

- `FlowTracker` class
- `flow_tracker` / `flow_threshold` / `flow_max_skew` kwargs on `PassiveMarketMaker`
