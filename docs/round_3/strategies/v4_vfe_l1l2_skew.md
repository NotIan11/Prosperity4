# v4 — VFE L1-L2 skew (CURRENT FLOOR)

**Status**: tested, ship-candidate
**Commit**: TBD
**Date**: 2026-04-26

## Hypothesis

Per `docs/round_3/research/10_iacobus_l1_l2_signal.md`: when VFE's L1 spread
is much narrower than its L2 spread (`diff = L1_spread - L2_spread <= -3`),
mid drifts up over the next 1-5 ticks (r=-0.21 at h=1, t=-37 across 30k samples).
Cheap quote-skew bias: lean both quotes up by 1 tick when this fires.

## Changes from previous version (v2)

- Added `l1_l2_diff(depth)` helper.
- `PassiveMarketMaker` accepts `use_l1l2`, `l1l2_threshold`, `l1l2_skew`;
  when `diff <= threshold`, shifts both bid and ask up by `l1l2_skew` ticks.
- VFE config: `use_l1l2=True, l1l2_threshold=-3, l1l2_skew=1`.

## Code

- `src/trader.py` — `l1_l2_diff()` + 3 new kwargs on `PassiveMarketMaker`.
- Snapshot: `docs/round_3/strategies/snapshots/v4_trader.py`.

## Backtest

```
venv/bin/prosperity4btest cli src/trader.py 3 --merge-pnl --no-out
```

| Day | v2 PnL | v4 PnL | Δ |
|-----|--------|--------|---|
| 0 | 15,685 | 15,713 | +28 |
| 1 | 11,426 | 11,616 | +190 |
| 2 | 6,565 | 6,854 | +289 |
| **Total** | **33,676** | **34,182** | **+506 (+1.5%)** |

| Metric | v1 | v2 | **v4** |
|--------|------|------|------|
| Total PnL | 31,606 | 33,676 | **34,182** |
| Sharpe | 2.50 | 2.46 | **2.57** |
| Max DD (abs) | 4,459 | 4,264 | **4,264** |
| Max DD (%) | 1.25 | 1.20 | **0.85** |
| Calmar | 7.09 | 7.90 | **8.02** |

VFE per-day: day 0 5,942 → 5,970, day 1 1,464 → 1,652, day 2 3,256 → 3,545.

## Learnings

- Best version on **every metric** so far: PnL up, Sharpe up, DD% nearly cut in
  half (1.20 → 0.85), Calmar up.
- The L1-L2 signal is a tiny per-firing edge (~+1 tick), but it fires often
  enough on VFE (~2.5% of ticks) that the cumulative bias matters.
- Same direction as the abandoned v3 flow signal but **way less sticky** —
  fires on a per-tick orderbook condition, not a trailing window. Cleaner.
- HYDROGEL untouched, identical numbers.

## Decision

**New floor.** Future versions stack on v4. Submission candidate.

## Next candidates

- **v5** — Voucher butterfly (long VEV_5400 / short VEV_5300) gated on smile
  RMSE > rolling median. Per EDA #13: standalone PnL 47.5, Sharpe 1.33.
  Big upside, biggest complexity (need the BS module wired in).
- **v6** — HYDROGEL outer layer at half_edge=9 (more passive layer for when
  the wall is full). Cheap experiment.
- **v7** — HYDROGEL inventory skew tuning (current 0.04 — sweep {0.03, 0.05}).
